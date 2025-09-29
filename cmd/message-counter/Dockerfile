# Multi-stage build for aggressive caching
FROM golang:1.24-alpine AS builder

# Install ca-certificates for SSL
RUN apk --no-cache add ca-certificates
WORKDIR /app

# Copy go mod files first for better caching
COPY go.mod go.sum ./
RUN --mount=type=cache,target=/go/pkg/mod \
    --mount=type=cache,target=/root/.cache/go-build \
    go mod download

# Copy source code
COPY . .

# Build the specific service
RUN --mount=type=cache,target=/go/pkg/mod \
    --mount=type=cache,target=/root/.cache/go-build \
     CGO_ENABLED=0 go build -installsuffix cgo -o message-counter ./cmd/message-counter

# Final stage - minimal image
FROM scratch

# Copy ca certificates from builder
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/

# Copy binary from builder
COPY --from=builder /app/message-counter /message-counter

# Switch to non-root user (nobody)
USER 65534

# Default command
ENTRYPOINT ["/message-counter"]