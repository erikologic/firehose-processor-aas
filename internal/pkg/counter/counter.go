package counter

import (
	"context"
	"encoding/json"
	"fmt"
	"log/slog"
	"sync/atomic"
	"time"

	"github.com/nats-io/nats.go"
)

type MessageCounter struct {
	logger   *slog.Logger
	natsConn *nats.Conn
	js       nats.JetStreamContext

	avgCount   int64
	totalCount int64

	lastReset time.Time
}

type CounterStats struct {
	Timestamp     time.Time        `json:"timestamp"`
	Period        string           `json:"period"`
	TotalMessages int64            `json:"total_messages"`
	EventTypes    map[string]int64 `json:"event_types"`
}

func NewMessageCounter(natsURL string, logger *slog.Logger) (*MessageCounter, error) {
	nc, err := nats.Connect(natsURL)
	if err != nil {
		return nil, fmt.Errorf("failed to connect to NATS: %w", err)
	}

	js, err := nc.JetStream()
	if err != nil {
		return nil, fmt.Errorf("failed to create JetStream context: %w", err)
	}

	return &MessageCounter{
		logger:    logger,
		natsConn:  nc,
		js:        js,
		lastReset: time.Now(),
	}, nil
}

func (mc *MessageCounter) Run(ctx context.Context) error {
	consumerName := fmt.Sprintf("counter-%d", time.Now().UnixNano())
	sub, err := mc.js.Subscribe("atproto.firehose.>", func(m *nats.Msg) {
		mc.handleMessage(m)
		m.Ack()
	}, nats.Durable(consumerName), nats.DeliverAll())
	if err != nil {
		return fmt.Errorf("failed to subscribe to JetStream: %w", err)
	}
	defer sub.Unsubscribe()

	mc.logger.Info("message counter started", "subjects", "atproto.firehose.>", "consumer", consumerName)

	ticker := time.NewTicker(10 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			mc.emitStats()
		case <-ctx.Done():
			mc.logger.Info("message counter shutting down")
			return nil
	}
	}
}

func (mc *MessageCounter) handleMessage(m *nats.Msg) {
	atomic.AddInt64(&mc.totalCount, 1)

	atomic.AddInt64(&mc.avgCount, 1)
}

func (mc *MessageCounter) emitStats() {
	now := time.Now()
	period := fmt.Sprintf("%.1fs", now.Sub(mc.lastReset).Seconds())

	total := atomic.LoadInt64(&mc.totalCount)
	avg := atomic.LoadInt64(&mc.avgCount)

	stats := CounterStats{
		Timestamp:     now,
		Period:        period,
		TotalMessages: total,
		EventTypes: map[string]int64{
			"avg": avg,
		},
	}

	mc.logger.Info("message counter stats",
		"period", period,
		"total", total,
		"avg", avg,
	)
	atomic.StoreInt64(&mc.avgCount, 0)

	statsData, err := json.Marshal(stats)
	if err != nil {
		mc.logger.Error("failed to marshal stats", "error", err)
		return
	}

	if _, err := mc.js.Publish("atproto.stats.counter", statsData); err != nil {
		mc.logger.Error("failed to publish stats to JetStream", "error", err)
	}

	atomic.StoreInt64(&mc.totalCount, 0)
	atomic.StoreInt64(&mc.avgCount, 0)

	mc.lastReset = now
}

func (mc *MessageCounter) Close() error {
	mc.natsConn.Close()
	return nil
}
