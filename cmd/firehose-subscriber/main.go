package main

import (
	"context"
	"log/slog"
	"os"
	"os/signal"
	"strings"
	"syscall"
	"time"

	"github.com/carlmjohnson/versioninfo"
	"github.com/eurosky/firehose-processor-aas/internal/pkg/firehose"
	"github.com/urfave/cli/v2"
)

func main() {
	app := &cli.App{
		Name:    "firehose-subscriber",
		Usage:   "ATProto firehose subscriber service",
		Version: versioninfo.Short(),
		Action:  run,
		Flags: []cli.Flag{
			&cli.StringFlag{
				Name:     "relay-host",
				Usage:    "firehose relay host (e.g., wss://bsky.network)",
				Required: true,
				EnvVars:  []string{"RELAY_HOST"},
			},
			&cli.StringFlag{
				Name:    "nats-url",
				Usage:   "NATS server URL",
				Value:   "nats://localhost:4222",
				EnvVars: []string{"NATS_URL"},
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
	relayHost := cctx.String("relay-host")
	natsURL := cctx.String("nats-url")

	s, err := firehose.NewSimpleSubscriber(relayHost, natsURL, logger)
	if err != nil {
		logger.Error("failed to create subscriber", "error", err)
		return err
	}
	defer s.Close()

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	go func() {
		ticker := time.NewTicker(10 * time.Second)
		defer ticker.Stop()
		for {
			select {
			case <-ticker.C:
				total := s.GetTotalEvents()
				logger.Info("firehose stats", "total_events", total)
			case <-ctx.Done():
				return
			}
		}
	}()

	setupSignalHandler(ctx, cancel, logger)

	logger.Info("starting firehose subscriber", "relay", relayHost, "nats", natsURL)
	if err := s.Run(ctx); err != nil {
		logger.Error("subscriber failed", "error", err)
		return err
	}

	logger.Info("firehose subscriber shutting down")
	return nil
}

func setupSignalHandler(ctx context.Context, cancel context.CancelFunc, logger *slog.Logger) {
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)

	go func() {
		select {
		case <-sigCh:
			logger.Info("shutting down...")
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