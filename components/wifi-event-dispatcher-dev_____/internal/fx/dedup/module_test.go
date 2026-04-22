package fxdedup

import (
	"testing"
	"time"

	"wifi-event-dispatcher/internal/redis"

	goredis "github.com/redis/go-redis/v9"
	"github.com/rs/zerolog"
)

func TestNewService_ReturnsNonNil(t *testing.T) {
	client := goredis.NewClient(&goredis.Options{Addr: "localhost:6379"})
	cfg := redis.Config{DedupTTL: time.Hour}

	svc := NewService(client, cfg, zerolog.Nop())
	if svc == nil {
		t.Fatal("expected non-nil dedup service")
	}
}
