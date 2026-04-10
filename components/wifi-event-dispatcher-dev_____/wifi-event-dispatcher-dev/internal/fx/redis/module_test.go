package fxredis

import (
	"context"
	"testing"
	"wifi-event-dispatcher/internal/redis"

	"github.com/alicebob/miniredis/v2"
	"github.com/rs/zerolog"
	"go.uber.org/fx/fxtest"
)

func TestNewClient_PingSuccess(t *testing.T) {
	mr, err := miniredis.Run()
	if err != nil {
		t.Fatalf("failed to start miniredis: %v", err)
	}
	defer mr.Close()

	cfg := redis.Config{Addr: mr.Addr()}
	log := zerolog.Nop()

	lc := fxtest.NewLifecycle(t)
	client := NewClient(lc, cfg, log)
	if client == nil {
		t.Fatal("expected non-nil client")
	}

	ctx := context.Background()
	if err := lc.Start(ctx); err != nil {
		t.Fatalf("expected start to succeed, got: %v", err)
	}

	// Verify client is actually connected
	if err := client.Ping(ctx).Err(); err != nil {
		t.Fatalf("expected ping to succeed after start: %v", err)
	}

	if err := lc.Stop(ctx); err != nil {
		t.Fatalf("expected stop to succeed, got: %v", err)
	}
}

func TestNewClient_PingFailure(t *testing.T) {
	cfg := redis.Config{Addr: "localhost:1"} // invalid port
	log := zerolog.Nop()

	lc := fxtest.NewLifecycle(t)
	client := NewClient(lc, cfg, log)
	if client == nil {
		t.Fatal("expected non-nil client")
	}

	err := lc.Start(context.Background())
	if err == nil {
		t.Fatal("expected start to fail with bad Redis address")
	}
}
