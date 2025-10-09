package main

import (
	"context"
	"fmt"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"strings"
	"syscall"

	"github.com/carlmjohnson/versioninfo"
	"github.com/eurosky/firehose-processor-aas/internal/pkg/firehose"
	"github.com/urfave/cli/v2"
)

func main() {
	app := &cli.App{
		Name:    "shuffler",
		Usage:   "ATProto firehose to NATS shuffler service",
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
				Value:   "debug",
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

	// Prometheus metrics endpoint
	http.HandleFunc("/metrics", func(w http.ResponseWriter, r *http.Request) {
		total := s.GetTotalEvents()
		cursor := s.GetLastCursor()

		w.Header().Set("Content-Type", "text/plain; version=0.0.4")
		fmt.Fprintf(w, "# HELP firehose_messages_read_total Total number of messages read from the ATProto firehose\n")
		fmt.Fprintf(w, "# TYPE firehose_messages_read_total counter\n")
		fmt.Fprintf(w, "firehose_messages_read_total %d\n", total)
		fmt.Fprintf(w, "\n")
		fmt.Fprintf(w, "# HELP firehose_cursor_position Current cursor position (sequence number) in the firehose\n")
		fmt.Fprintf(w, "# TYPE firehose_cursor_position gauge\n")
		fmt.Fprintf(w, "firehose_cursor_position %d\n", cursor)
	})

	go func() {
		if err := http.ListenAndServe(":8080", nil); err != nil {
			logger.Error("metrics server failed", "error", err)
		}
	}()

	setupSignalHandler(ctx, cancel, logger)

	if err := s.Run(ctx); err != nil {
		return err
	}

	return nil
}

func setupSignalHandler(ctx context.Context, cancel context.CancelFunc, logger *slog.Logger) {
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)

	go func() {
		select {
		case <-sigCh:
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