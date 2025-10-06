package firehose

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"log/slog"
	"net/http"
	"net/url"
	"sync/atomic"
	"time"

	"github.com/gorilla/websocket"
	"github.com/nats-io/nats.go"
)

type SimpleSubscriber struct {
	logger      *slog.Logger
	natsConn    *nats.Conn
	js          nats.JetStreamContext
	relayHost   string
	totalEvents int64
}

func NewSimpleSubscriber(relayHost, natsURL string, logger *slog.Logger) (*SimpleSubscriber, error) {
	nc, err := nats.Connect(natsURL)
	if err != nil {
		return nil, fmt.Errorf("failed to connect to NATS: %w", err)
	}

	js, err := nc.JetStream()
	if err != nil {
		return nil, fmt.Errorf("failed to create JetStream context: %w", err)
	}

	streamName := "ATPROTO_FIREHOSE"
	_, err = js.StreamInfo(streamName)
	if err != nil {
		logger.Info("creating JetStream stream", "name", streamName)
		_, err = js.AddStream(&nats.StreamConfig{
			Name:       streamName,
			Subjects:   []string{"atproto.firehose.>"},
			Retention:  nats.LimitsPolicy,
			MaxAge:     5 * time.Minute,
			Storage:    nats.MemoryStorage,
			Duplicates: 5 * time.Minute,
		})
		if err != nil {
			return nil, fmt.Errorf("failed to create stream: %w", err)
		}
	}

	return &SimpleSubscriber{
		logger:    logger,
		natsConn:  nc,
		js:        js,
		relayHost: relayHost,
	}, nil
}

func (s *SimpleSubscriber) Run(ctx context.Context) error {
	dialer := websocket.DefaultDialer
	u, err := url.Parse(s.relayHost)
	if err != nil {
		return fmt.Errorf("invalid relay host URI: %w", err)
	}
	u.Path = "xrpc/com.atproto.sync.subscribeRepos"

	con, _, err := dialer.Dial(u.String(), http.Header{
		"User-Agent": []string{"fpaas-firehose-subscriber/1.0"},
	})
	if err != nil {
		return fmt.Errorf("subscribing to firehose failed: %w", err)
	}
	defer con.Close()

	for {
		select {
		case <-ctx.Done():
			return nil
		default:
			_, message, err := con.ReadMessage()
			if err != nil {
				return err
			}

			atomic.AddInt64(&s.totalEvents, 1)

			hash := sha256.Sum256(message)
			msgID := hex.EncodeToString(hash[:])

			_, err = s.js.Publish("atproto.firehose.raw", message, nats.MsgId(msgID))
			if err != nil {
				return err
			}
		}
	}
}

func (s *SimpleSubscriber) Close() error {
	s.natsConn.Close()
	return nil
}

func (s *SimpleSubscriber) GetTotalEvents() int64 {
	return atomic.LoadInt64(&s.totalEvents)
}