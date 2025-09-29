package main

import (
	"context"
	"fmt"
	"log/slog"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/eurosky/firehose-processor-aas/internal/pkg/firehose"
)

func main() {
	logger := slog.New(slog.NewTextHandler(os.Stdout, &slog.HandlerOptions{Level: slog.LevelInfo}))

	relayHost := os.Getenv("RELAY_HOST")
	if relayHost == "" {
		if len(os.Args) < 2 {
			fmt.Println("Usage: firehose-subscriber <relay_host> [nats_url]")
			fmt.Println("Example: firehose-subscriber wss://bsky.network nats://localhost:4222")
			fmt.Println("Or set RELAY_HOST and NATS_URL environment variables")
			os.Exit(1)
		}
		relayHost = os.Args[1]
	}

	natsURL := os.Getenv("NATS_URL")
	if natsURL == "" {
		natsURL = "nats://localhost:4222"
		if len(os.Args) > 2 {
			natsURL = os.Args[2]
		}
	}

	s, err := firehose.NewSimpleSubscriber(relayHost, natsURL, logger)
	if err != nil {
		fmt.Printf("Failed to create subscriber: %v\n", err)
		os.Exit(1)
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

	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)

	go func() {
		<-sigCh
		logger.Info("shutting down...")
		cancel()
	}()

	logger.Info("starting firehose subscriber", "relay", relayHost, "nats", natsURL)
	if err := s.Run(ctx); err != nil {
		logger.Error("subscriber failed", "error", err)
		os.Exit(1)
	}
}