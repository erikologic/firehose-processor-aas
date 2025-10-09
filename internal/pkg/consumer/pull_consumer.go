package consumer

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"log/slog"
	"math/rand"
	"net/http"
	"sync/atomic"
	"time"

	"github.com/nats-io/nats.go"
)

type PullConsumer struct {
	logger         *slog.Logger
	natsConn       *nats.Conn
	js             nats.JetStreamContext
	sub            *nats.Subscription
	pollInterval   time.Duration
	jitteredPoll   time.Duration
	batchSize      int
	totalCount     int64
	consumerName   string
	webhookURL     string
	useWebhook     bool
	httpClient     *http.Client
}

func NewPullConsumer(natsURL string, consumerName string, pollInterval time.Duration, batchSize int, webhookURL string, useWebhook bool, logger *slog.Logger) (*PullConsumer, error) {
	nc, err := nats.Connect(natsURL)
	if err != nil {
		return nil, fmt.Errorf("failed to connect to NATS: %w", err)
	}

	js, err := nc.JetStream()
	if err != nil {
		nc.Close()
		return nil, fmt.Errorf("failed to create JetStream context: %w", err)
	}

	// Subscribe to stream with unique durable consumer name
	// Each unique consumer name creates an independent consumer that receives ALL messages
	// This is the broadcast/fan-out pattern - each consumer tracks its own position
	sub, err := js.PullSubscribe("atproto.firehose.>", consumerName, nats.DeliverNew(), nats.AckExplicit())
	if err != nil {
		nc.Close()
		return nil, fmt.Errorf("failed to subscribe: %w", err)
	}

	// Calculate jitter once at startup (±50% random variation)
	// This spreads out consumers but keeps their timing stable
	variance := float64(pollInterval) * 0.5
	offset := (rand.Float64() * 2 * variance) - variance
	jitteredPoll := pollInterval + time.Duration(offset)

	return &PullConsumer{
		logger:       logger,
		natsConn:     nc,
		js:           js,
		sub:          sub,
		pollInterval: pollInterval,
		jitteredPoll: jitteredPoll,
		batchSize:    batchSize,
		consumerName: consumerName,
		webhookURL:   webhookURL,
		useWebhook:   useWebhook,
		httpClient: &http.Client{
			Timeout: 10 * time.Second,
		},
	}, nil
}

func (c *PullConsumer) Run(ctx context.Context) error {
	ticker := time.NewTicker(c.jitteredPoll)
	defer ticker.Stop()

	c.logger.Info("pull consumer started",
		"consumer", c.consumerName,
		"poll_interval", c.jitteredPoll,
		"batch_size", c.batchSize,
	)

	for {
		select {
		case <-ctx.Done():
			return nil
		case <-ticker.C:
			// Pull messages at jittered interval
			msgs, err := c.sub.Fetch(c.batchSize, nats.MaxWait(5*time.Second))
			if err != nil {
				if err == nats.ErrTimeout {
					// No messages available, continue
					continue
				}
				c.logger.Warn("fetch error", "error", err)
				continue
			}

			// Send batch to webhook if configured
			if len(msgs) > 0 && c.useWebhook && c.webhookURL != "" {
				if err := c.sendWebhook(msgs); err != nil {
					c.logger.Warn("webhook delivery failed",
						"consumer", c.consumerName,
						"error", err,
						"batch_size", len(msgs),
					)
					// NAK messages so they can be redelivered
					for _, msg := range msgs {
						if nakErr := msg.NakWithDelay(5 * time.Second); nakErr != nil {
							c.logger.Warn("nak error", "error", nakErr)
						}
					}
					// Don't increment counter or ack failed messages
					continue
				}
			}

			// ACK messages after successful webhook delivery (or if webhook is disabled)
			for _, msg := range msgs {
				atomic.AddInt64(&c.totalCount, 1)

				if err := msg.Ack(); err != nil {
					c.logger.Warn("ack error", "error", err)
				}
			}

			if len(msgs) > 0 {
				c.logger.Debug("processed batch",
					"consumer", c.consumerName,
					"count", len(msgs),
					"total", atomic.LoadInt64(&c.totalCount),
				)
			}
		}
	}
}

func (c *PullConsumer) Close() error {
	if c.sub != nil {
		c.sub.Unsubscribe()
	}
	if c.natsConn != nil {
		c.natsConn.Close()
	}
	return nil
}

func (c *PullConsumer) GetTotalCount() int64 {
	return atomic.LoadInt64(&c.totalCount)
}

func (c *PullConsumer) sendWebhook(msgs []*nats.Msg) error {
	// Build payload - array of base64 encoded messages
	type WebhookPayload struct {
		Consumer string   `json:"consumer"`
		Events   [][]byte `json:"events"`
		Count    int      `json:"count"`
	}

	events := make([][]byte, len(msgs))
	for i, msg := range msgs {
		events[i] = msg.Data
	}

	payload := WebhookPayload{
		Consumer: c.consumerName,
		Events:   events,
		Count:    len(msgs),
	}

	body, err := json.Marshal(payload)
	if err != nil {
		return fmt.Errorf("failed to marshal payload: %w", err)
	}

	// Create request
	req, err := http.NewRequest(http.MethodPost, c.webhookURL, bytes.NewReader(body))
	if err != nil {
		return fmt.Errorf("failed to create request: %w", err)
	}

	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-Event-Count", fmt.Sprintf("%d", len(msgs)))

	// Send request
	resp, err := c.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("failed to send request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("webhook returned non-OK status: %d", resp.StatusCode)
	}

	return nil
}
