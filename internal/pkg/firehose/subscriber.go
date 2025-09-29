package firehose

import (
	"context"
	"fmt"
	"log/slog"
	"net/http"
	"net/url"
	"sync/atomic"

	"github.com/gorilla/websocket"
	"github.com/nats-io/nats.go"
)

type SimpleSubscriber struct {
	logger      *slog.Logger
	natsConn    *nats.Conn
	relayHost   string
	totalEvents int64
}

func NewSimpleSubscriber(relayHost, natsURL string, logger *slog.Logger) (*SimpleSubscriber, error) {
	nc, err := nats.Connect(natsURL)
	if err != nil {
		return nil, fmt.Errorf("failed to connect to NATS: %w", err)
	}

	return &SimpleSubscriber{
		logger:    logger,
		natsConn:  nc,
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

	s.logger.Info("connecting to ATProto firehose", "url", u.String())
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
			s.logger.Info("shutting down firehose subscriber")
			return nil
		default:
			_, message, err := con.ReadMessage()
			if err != nil {
				s.logger.Error("error reading message", "error", err)
				return err
			}

			atomic.AddInt64(&s.totalEvents, 1)

			err = s.natsConn.Publish("atproto.firehose.raw", message)
			if err != nil {
				s.logger.Error("failed to publish to NATS", "error", err)
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