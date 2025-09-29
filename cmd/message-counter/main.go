package main

import (
	"context"
	"log/slog"
	"os"
	"os/signal"
	"strings"
	"syscall"

	"github.com/carlmjohnson/versioninfo"
	"github.com/eurosky/firehose-processor-aas/internal/pkg/counter"
	"github.com/urfave/cli/v2"
)

func main() {
	app := &cli.App{
		Name:    "message-counter",
		Usage:   "NATS message counter service",
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
				Name:    "instances",
				Usage:   "number of message counter instances to run",
				Value:   1,
				EnvVars: []string{"MESSAGE_COUNTER_INSTANCES"},
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
	numInstances := cctx.Int("instances")

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	setupSignalHandler(ctx, cancel, logger)

	logger.Info("starting message counters", "nats", natsURL, "instances", numInstances)

	errs := make(chan error, numInstances)
	for i := 0; i < numInstances; i++ {
		go func(idx int) {
			l := logger.With("instance", idx)
			mc, err := counter.NewMessageCounter(natsURL, l)
			if err != nil {
				errs <- err
				return
			}
			defer mc.Close()
			if err := mc.Run(ctx); err != nil {
				errs <- err
			}
		}(i)
	}

	select {
	case err := <-errs:
		logger.Error("message counter failed", "error", err)
		return err
	case <-ctx.Done():
		logger.Info("all message counters shutting down")
		return nil
	}
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