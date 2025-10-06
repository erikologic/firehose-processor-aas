package main

import (
	"context"
	"fmt"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"strings"
	"sync"
	"sync/atomic"
	"syscall"
	"time"

	"github.com/carlmjohnson/versioninfo"
	"github.com/eurosky/firehose-processor-aas/internal/pkg/consumer"
	"github.com/urfave/cli/v2"
)

func main() {
	app := &cli.App{
		Name:    "pull-consumer",
		Usage:   "NATS JetStream pull-based consumer service",
		Version: versioninfo.Short(),
		Action:  run,
		Flags: []cli.Flag{
			&cli.StringFlag{
				Name:    "nats-url",
				Usage:   "NATS server URL",
				Value:   "nats://localhost:4222",
				EnvVars: []string{"NATS_URL"},
			},
			&cli.IntFlag{
				Name:    "count",
				Usage:   "number of consumer instances to run",
				Value:   1,
				EnvVars: []string{"CONSUMER_COUNT"},
			},
			&cli.IntFlag{
				Name:    "poll-interval",
				Usage:   "poll interval in seconds",
				Value:   60,
				EnvVars: []string{"POLL_INTERVAL_SECONDS"},
			},
			&cli.IntFlag{
				Name:    "batch-size",
				Usage:   "number of messages to fetch per pull",
				Value:   100,
				EnvVars: []string{"BATCH_SIZE"},
			},
			&cli.StringFlag{
				Name:    "log-level",
				Usage:   "log verbosity level (error, warn, info, debug)",
				Value:   "info",
				EnvVars: []string{"LOG_LEVEL"},
			},
		},
	}

	if err := app.Run(os.Args); err != nil {
		slog.Error("application failed", "error", err)
		os.Exit(1)
	}
}

func run(cctx *cli.Context) error {
	logger := configLogger(cctx)
	natsURL := cctx.String("nats-url")
	numConsumers := cctx.Int("count")
	pollInterval := time.Duration(cctx.Int("poll-interval")) * time.Second
	batchSize := cctx.Int("batch-size")

	logger.Info("starting pull consumers",
		"count", numConsumers,
		"poll_interval", pollInterval,
		"batch_size", batchSize,
	)

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	setupSignalHandler(ctx, cancel, logger)

	var consumers []*consumer.PullConsumer
	var mu sync.Mutex
	var totalProcessed int64

	// Metrics endpoint
	http.HandleFunc("/metrics", func(w http.ResponseWriter, r *http.Request) {
		mu.Lock()
		defer mu.Unlock()
		total := atomic.LoadInt64(&totalProcessed)
		for _, c := range consumers {
			total += c.GetTotalCount()
		}
		fmt.Fprintf(w, "%d", total)
	})

	go func() {
		if err := http.ListenAndServe(":8082", nil); err != nil {
			logger.Error("metrics server failed", "error", err)
		}
	}()

	// Start consumers
	errs := make(chan error, numConsumers)
	for i := 0; i < numConsumers; i++ {
		go func(idx int) {
			consumerName := fmt.Sprintf("consumer-%d", idx)
			l := logger.With("consumer", consumerName)

			c, err := consumer.NewPullConsumer(natsURL, consumerName, pollInterval, batchSize, l)
			if err != nil {
				errs <- fmt.Errorf("consumer %d failed to start: %w", idx, err)
				return
			}
			defer c.Close()

			mu.Lock()
			consumers = append(consumers, c)
			mu.Unlock()

			if err := c.Run(ctx); err != nil {
				errs <- fmt.Errorf("consumer %d error: %w", idx, err)
			}
		}(i)
	}

	// Log errors
	go func() {
		for err := range errs {
			if err != nil {
				logger.Error("consumer error", "error", err)
			}
		}
	}()

	// Periodic stats logging
	go func() {
		ticker := time.NewTicker(30 * time.Second)
		defer ticker.Stop()

		for {
			select {
			case <-ctx.Done():
				return
			case <-ticker.C:
				mu.Lock()
				total := atomic.LoadInt64(&totalProcessed)
				for _, c := range consumers {
					total += c.GetTotalCount()
				}
				mu.Unlock()
				logger.Info("consumer stats",
					"total_processed", total,
					"active_consumers", len(consumers),
				)
			}
		}
	}()

	<-ctx.Done()
	logger.Info("shutting down consumers")
	return nil
}

func setupSignalHandler(ctx context.Context, cancel context.CancelFunc, logger *slog.Logger) {
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)

	go func() {
		select {
		case <-sigCh:
			logger.Info("received shutdown signal")
			cancel()
		case <-ctx.Done():
		}
	}()
}

func configLogger(cctx *cli.Context) *slog.Logger {
	var level slog.Level
	switch strings.ToLower(cctx.String("log-level")) {
	case "error":
		level = slog.LevelError
	case "warn":
		level = slog.LevelWarn
	case "info":
		level = slog.LevelInfo
	case "debug":
		level = slog.LevelDebug
	default:
		level = slog.LevelInfo
	}

	logger := slog.New(slog.NewTextHandler(os.Stdout, &slog.HandlerOptions{Level: level}))
	slog.SetDefault(logger)
	return logger
}
