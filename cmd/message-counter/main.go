package main

import (
	"context"
	"fmt"
	"log/slog"
	"os"
	"os/signal"
	"syscall"

	"github.com/eurosky/firehose-processor-aas/internal/pkg/counter"
)

func main() {
	logger := slog.New(slog.NewTextHandler(os.Stdout, &slog.HandlerOptions{Level: slog.LevelInfo}))

	natsURL := os.Getenv("NATS_URL")
	if natsURL == "" {
		natsURL = "nats://localhost:4222"
		if len(os.Args) > 1 {
			natsURL = os.Args[1]
		}
	}

	mc, err := counter.NewMessageCounter(natsURL, logger)
	if err != nil {
		fmt.Printf("Failed to create message counter: %v\n", err)
		os.Exit(1)
	}
	defer mc.Close()

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)

	go func() {
		<-sigCh
		logger.Info("shutting down...")
		cancel()
	}()

	logger.Info("starting message counter", "nats", natsURL)
	if err := mc.Run(ctx); err != nil {
		logger.Error("message counter failed", "error", err)
		os.Exit(1)
	}
}