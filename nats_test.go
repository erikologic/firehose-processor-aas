package main

import (
	"sync"
	"testing"
	"time"

	"github.com/nats-io/nats.go"
)

const testNATSURL = "nats://localhost:4222"

func TestNATSConnection(t *testing.T) {
	nc, err := nats.Connect(testNATSURL)
	if err != nil {
		t.Fatalf("Failed to connect to NATS: %v", err)
	}
	defer nc.Close()

	if !nc.IsConnected() {
		t.Fatal("Expected to be connected to NATS")
	}
}

func TestPublishAndSubscribe(t *testing.T) {
	nc, err := nats.Connect(testNATSURL)
	if err != nil {
		t.Fatalf("Failed to connect to NATS: %v", err)
	}
	defer nc.Close()

	subject := "test.queue"
	message := "Hello NATS!"
	received := make(chan string, 1)

	sub, err := nc.Subscribe(subject, func(m *nats.Msg) {
		received <- string(m.Data)
	})
	if err != nil {
		t.Fatalf("Failed to subscribe: %v", err)
	}
	defer sub.Unsubscribe()

	err = nc.Publish(subject, []byte(message))
	if err != nil {
		t.Fatalf("Failed to publish: %v", err)
	}

	select {
	case msg := <-received:
		if msg != message {
			t.Errorf("Expected message '%s', got '%s'", message, msg)
		}
	case <-time.After(2 * time.Second):
		t.Fatal("Timeout waiting for message")
	}
}

func TestQueueGroups(t *testing.T) {
	nc, err := nats.Connect(testNATSURL)
	if err != nil {
		t.Fatalf("Failed to connect to NATS: %v", err)
	}
	defer nc.Close()

	subject := "test.queue.group"
	queueGroup := "workers"
	messages := []string{"msg1", "msg2", "msg3", "msg4", "msg5"}

	received := make(chan string, len(messages))
	var wg sync.WaitGroup

	for i := 0; i < 3; i++ {
		wg.Add(1)
		go func(workerID int) {
			defer wg.Done()
			sub, err := nc.QueueSubscribe(subject, queueGroup, func(m *nats.Msg) {
				received <- string(m.Data)
			})
			if err != nil {
				t.Errorf("Worker %d failed to subscribe: %v", workerID, err)
				return
			}
			defer sub.Unsubscribe()
			time.Sleep(3 * time.Second)
		}(i)
	}

	time.Sleep(100 * time.Millisecond)

	for _, msg := range messages {
		err := nc.Publish(subject, []byte(msg))
		if err != nil {
			t.Fatalf("Failed to publish message '%s': %v", msg, err)
		}
	}

	receivedCount := 0
	timeout := time.After(2 * time.Second)

	for receivedCount < len(messages) {
		select {
		case <-received:
			receivedCount++
		case <-timeout:
			t.Fatalf("Timeout: received %d messages, expected %d", receivedCount, len(messages))
		}
	}

	wg.Wait()

	if receivedCount != len(messages) {
		t.Errorf("Expected %d messages, received %d", len(messages), receivedCount)
	}
}

func TestRequestReply(t *testing.T) {
	nc, err := nats.Connect(testNATSURL)
	if err != nil {
		t.Fatalf("Failed to connect to NATS: %v", err)
	}
	defer nc.Close()

	subject := "test.request"
	expectedReply := "reply data"

	sub, err := nc.Subscribe(subject, func(m *nats.Msg) {
		nc.Publish(m.Reply, []byte(expectedReply))
	})
	if err != nil {
		t.Fatalf("Failed to subscribe: %v", err)
	}
	defer sub.Unsubscribe()

	msg, err := nc.Request(subject, []byte("request data"), 2*time.Second)
	if err != nil {
		t.Fatalf("Request failed: %v", err)
	}

	if string(msg.Data) != expectedReply {
		t.Errorf("Expected reply '%s', got '%s'", expectedReply, string(msg.Data))
	}
}

func TestMultipleMessages(t *testing.T) {
	nc, err := nats.Connect(testNATSURL)
	if err != nil {
		t.Fatalf("Failed to connect to NATS: %v", err)
	}
	defer nc.Close()

	subject := "test.multiple"
	messageCount := 100
	received := make(chan string, messageCount)

	sub, err := nc.Subscribe(subject, func(m *nats.Msg) {
		received <- string(m.Data)
	})
	if err != nil {
		t.Fatalf("Failed to subscribe: %v", err)
	}
	defer sub.Unsubscribe()

	for i := 0; i < messageCount; i++ {
		msg := "message-" + string(rune('0'+i%10))
		err := nc.Publish(subject, []byte(msg))
		if err != nil {
			t.Fatalf("Failed to publish message %d: %v", i, err)
		}
	}

	receivedCount := 0
	timeout := time.After(5 * time.Second)

	for receivedCount < messageCount {
		select {
		case <-received:
			receivedCount++
		case <-timeout:
			t.Fatalf("Timeout: received %d messages, expected %d", receivedCount, messageCount)
		}
	}

	if receivedCount != messageCount {
		t.Errorf("Expected %d messages, received %d", messageCount, receivedCount)
	}
}