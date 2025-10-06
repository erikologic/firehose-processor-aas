package consumer

import (
	"context"
	"fmt"
	"log/slog"
	"math/rand"
	"sync/atomic"
	"time"

	"github.com/nats-io/nats.go"
)

type PullConsumer struct {
	logger       *slog.Logger
	natsConn     *nats.Conn
	js           nats.JetStreamContext
	sub          *nats.Subscription
	pollInterval time.Duration
	batchSize    int
	totalCount   int64
	consumerName string
}

func NewPullConsumer(natsURL string, consumerName string, pollInterval time.Duration, batchSize int, logger *slog.Logger) (*PullConsumer, error) {
	nc, err := nats.Connect(natsURL)
	if err != nil {
		return nil, fmt.Errorf("failed to connect to NATS: %w", err)
	}

	js, err := nc.JetStream()
	if err != nil {
		nc.Close()
		return nil, fmt.Errorf("failed to create JetStream context: %w", err)
	}

	// Create durable pull consumer
	streamName := "ATPROTO_FIREHOSE"
	_, err = js.AddConsumer(streamName, &nats.ConsumerConfig{
		Durable:       consumerName,
		AckPolicy:     nats.AckExplicitPolicy,
		DeliverPolicy: nats.DeliverAllPolicy,
		FilterSubject: "atproto.firehose.>",
	})
	if err != nil && err != nats.ErrConsumerNameAlreadyInUse {
		nc.Close()
		return nil, fmt.Errorf("failed to create consumer: %w", err)
	}

	// Subscribe to the durable consumer
	sub, err := js.PullSubscribe("atproto.firehose.>", consumerName, nats.Bind(streamName, consumerName))
	if err != nil {
		nc.Close()
		return nil, fmt.Errorf("failed to subscribe: %w", err)
	}

	return &PullConsumer{
		logger:       logger,
		natsConn:     nc,
		js:           js,
		sub:          sub,
		pollInterval: pollInterval,
		batchSize:    batchSize,
		consumerName: consumerName,
	}, nil
}

func (c *PullConsumer) Run(ctx context.Context) error {
	// Add jitter to poll interval (±20% random variation)
	jitter := func() time.Duration {
		variance := float64(c.pollInterval) * 0.2
		offset := (rand.Float64() * 2 * variance) - variance
		return c.pollInterval + time.Duration(offset)
	}

	ticker := time.NewTicker(jitter())
	defer ticker.Stop()

	c.logger.Info("pull consumer started",
		"consumer", c.consumerName,
		"poll_interval", c.pollInterval,
		"batch_size", c.batchSize,
	)

	for {
		select {
		case <-ctx.Done():
			return nil
		case <-ticker.C:
			// Reset ticker with new jittered interval
			ticker.Reset(jitter())

			// Pull messages
			msgs, err := c.sub.Fetch(c.batchSize, nats.MaxWait(5*time.Second))
			if err != nil {
				if err == nats.ErrTimeout {
					// No messages available, continue
					continue
				}
				c.logger.Warn("fetch error", "error", err)
				continue
			}

			// Process messages
			for _, msg := range msgs {
				// Simple processing: just count and ack
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
