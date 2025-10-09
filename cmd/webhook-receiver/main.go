package main

import (
	"context"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"strings"
	"sync/atomic"
	"syscall"
	"time"

	"github.com/carlmjohnson/versioninfo"
	"github.com/urfave/cli/v2"
)

var (
	totalWebhookCalls int64
	totalEvents       int64
)

func main() {
	app := &cli.App{
		Name:    "webhook-receiver",
		Usage:   "Simple webhook receiver for testing consumer webhooks",
		Version: versioninfo.Short(),
		Action:  run,
		Flags: []cli.Flag{
			&cli.StringFlag{
				Name:    "port",
				Usage:   "HTTP server port",
				Value:   "8090",
				EnvVars: []string{"PORT"},
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
	port := cctx.String("port")

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	setupSignalHandler(ctx, cancel, logger)

	// Webhook endpoint
	http.HandleFunc("/webhook", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}

		// Read body
		body, err := io.ReadAll(r.Body)
		if err != nil {
			logger.Error("failed to read body", "error", err)
			http.Error(w, "Failed to read body", http.StatusBadRequest)
			return
		}
		defer r.Body.Close()

		// Parse batch count from header (consumers will send this)
		batchSize := 1 // default to 1 event
		if batchHeader := r.Header.Get("X-Event-Count"); batchHeader != "" {
			if parsed, err := fmt.Sscanf(batchHeader, "%d", &batchSize); err == nil && parsed == 1 {
				// Successfully parsed
			}
		}

		// Increment counters
		calls := atomic.AddInt64(&totalWebhookCalls, 1)
		events := atomic.AddInt64(&totalEvents, int64(batchSize))

		// Log at debug level (to avoid spam)
		logger.Debug("webhook received",
			"webhook_call", calls,
			"batch_size", batchSize,
			"total_events", events,
			"size_bytes", len(body),
			"content_type", r.Header.Get("Content-Type"),
		)

		// Respond with 200 OK
		w.WriteHeader(http.StatusOK)
		fmt.Fprintf(w, "OK")
	})

	// Health check endpoint
	http.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		fmt.Fprintf(w, "OK")
	})

	// Metrics endpoint (Prometheus format)
	http.HandleFunc("/metrics", func(w http.ResponseWriter, r *http.Request) {
		calls := atomic.LoadInt64(&totalWebhookCalls)
		events := atomic.LoadInt64(&totalEvents)

		w.Header().Set("Content-Type", "text/plain; version=0.0.4")
		fmt.Fprintf(w, "# HELP webhook_calls_total Total number of webhook HTTP calls received\n")
		fmt.Fprintf(w, "# TYPE webhook_calls_total counter\n")
		fmt.Fprintf(w, "webhook_calls_total %d\n", calls)
		fmt.Fprintf(w, "\n")
		fmt.Fprintf(w, "# HELP webhook_events_total Total number of events received in webhook calls\n")
		fmt.Fprintf(w, "# TYPE webhook_events_total counter\n")
		fmt.Fprintf(w, "webhook_events_total %d\n", events)
	})

	// Root endpoint with stats
	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		calls := atomic.LoadInt64(&totalWebhookCalls)
		events := atomic.LoadInt64(&totalEvents)
		avgBatchSize := float64(0)
		if calls > 0 {
			avgBatchSize = float64(events) / float64(calls)
		}

		w.Header().Set("Content-Type", "text/html")
		fmt.Fprintf(w, `
<!DOCTYPE html>
<html>
<head>
    <title>Webhook Receiver</title>
    <meta http-equiv="refresh" content="5">
    <style>
        body { font-family: monospace; padding: 20px; background: #1a1a1a; color: #e0e0e0; }
        .stats { font-size: 20px; margin: 20px 0; }
        .stat-item {
            background: #2a2a2a;
            padding: 15px;
            margin: 10px 0;
            border-left: 4px solid #4a9eff;
            border-radius: 4px;
        }
        .stat-value {
            color: #4a9eff;
            font-size: 32px;
            font-weight: bold;
        }
        .stat-label {
            color: #888;
            font-size: 14px;
            text-transform: uppercase;
        }
        .endpoint {
            background: #2a2a2a;
            padding: 10px;
            margin: 10px 0;
            border-radius: 4px;
        }
        h1 { color: #4a9eff; }
        h2 { color: #888; font-size: 18px; margin-top: 30px; }
    </style>
</head>
<body>
    <h1>📡 Webhook Receiver</h1>
    <div class="stats">
        <div class="stat-item">
            <div class="stat-label">Webhook Calls</div>
            <div class="stat-value">%d</div>
        </div>
        <div class="stat-item">
            <div class="stat-label">Total Events</div>
            <div class="stat-value">%d</div>
        </div>
        <div class="stat-item">
            <div class="stat-label">Avg Batch Size</div>
            <div class="stat-value">%.1f</div>
        </div>
        <div class="stat-item">
            <div class="stat-label">Uptime</div>
            <div class="stat-value">%s</div>
        </div>
    </div>
    <h2>Endpoints:</h2>
    <div class="endpoint">POST /webhook - Receive webhook payloads (send X-Event-Count header)</div>
    <div class="endpoint">GET /metrics - Prometheus metrics</div>
    <div class="endpoint">GET /health - Health check</div>
    <p><small style="color: #666;">Auto-refreshes every 5 seconds</small></p>
</body>
</html>
`, calls, events, avgBatchSize, time.Since(startTime).Round(time.Second))
	})

	// Start periodic stats logging
	go func() {
		ticker := time.NewTicker(30 * time.Second)
		defer ticker.Stop()

		for {
			select {
			case <-ctx.Done():
				return
			case <-ticker.C:
				calls := atomic.LoadInt64(&totalWebhookCalls)
				events := atomic.LoadInt64(&totalEvents)
				logger.Info("webhook stats",
					"webhook_calls", calls,
					"total_events", events)
			}
		}
	}()

	// Start HTTP server
	server := &http.Server{
		Addr:         ":" + port,
		ReadTimeout:  10 * time.Second,
		WriteTimeout: 10 * time.Second,
	}

	logger.Info("webhook receiver started", "port", port)

	go func() {
		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			logger.Error("server error", "error", err)
			cancel()
		}
	}()

	<-ctx.Done()
	logger.Info("shutting down webhook receiver")

	shutdownCtx, shutdownCancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer shutdownCancel()

	return server.Shutdown(shutdownCtx)
}

var startTime = time.Now()

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
