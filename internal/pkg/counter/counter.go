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

	return &MessageCounter{
		logger:    logger,
		natsConn:  nc,
		lastReset: time.Now(),
	}, nil
}

func (mc *MessageCounter) Run(ctx context.Context) error {
	sub, err := mc.natsConn.Subscribe("atproto.firehose.>", func(m *nats.Msg) {
		mc.handleMessage(m)
	})
	if err != nil {
		return fmt.Errorf("failed to subscribe: %w", err)
	}
	defer sub.Unsubscribe()

	mc.logger.Info("message counter started", "subjects", "atproto.firehose.*")

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

	if err := mc.natsConn.Publish("atproto.stats.counter", statsData); err != nil {
		mc.logger.Error("failed to publish stats", "error", err)
	}

	atomic.StoreInt64(&mc.totalCount, 0)
	atomic.StoreInt64(&mc.avgCount, 0)

	mc.lastReset = now
}

func (mc *MessageCounter) Close() error {
	mc.natsConn.Close()
	return nil
}
