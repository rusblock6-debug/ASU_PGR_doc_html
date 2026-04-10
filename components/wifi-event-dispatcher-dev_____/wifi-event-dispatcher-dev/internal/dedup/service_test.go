package dedup_test

import (
	"context"
	"testing"
	"time"

	"github.com/alicebob/miniredis/v2"
	goredis "github.com/redis/go-redis/v9"
	"github.com/rs/zerolog"

	"wifi-event-dispatcher/internal/dedup"
)

// newTestService creates a DedupService backed by an in-memory miniredis instance.
func newTestService(t *testing.T, ttl time.Duration) (dedup.Service, *miniredis.Miniredis) {
	t.Helper()

	mr, err := miniredis.Run()
	if err != nil {
		t.Fatalf("failed to start miniredis: %v", err)
	}
	t.Cleanup(mr.Close)

	client := goredis.NewClient(&goredis.Options{Addr: mr.Addr()})
	t.Cleanup(func() { _ = client.Close() })

	svc := dedup.New(client, ttl, zerolog.Nop())
	return svc, mr
}

// --- IsDuplicate tests ---

func TestIsDuplicate_NotSeen_ReturnsFalse(t *testing.T) {
	svc, _ := newTestService(t, time.Hour)

	dup, err := svc.IsDuplicate(context.Background(), "msg-not-seen")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if dup {
		t.Fatal("expected false for unseen messageID")
	}
}

func TestIsDuplicate_AlreadySeen_ReturnsTrue(t *testing.T) {
	svc, _ := newTestService(t, time.Hour)
	ctx := context.Background()

	if err := svc.MarkSeen(ctx, "msg-seen"); err != nil {
		t.Fatalf("MarkSeen failed: %v", err)
	}

	dup, err := svc.IsDuplicate(ctx, "msg-seen")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !dup {
		t.Fatal("expected true for already-seen messageID")
	}
}

func TestIsDuplicate_RedisError_ReturnsFalseAndError(t *testing.T) {
	svc, mr := newTestService(t, time.Hour)
	mr.Close() // force connection error

	dup, err := svc.IsDuplicate(context.Background(), "msg-redis-err")
	if err == nil {
		t.Fatal("expected an error when Redis is unavailable")
	}
	if dup {
		t.Fatal("expected false (fail-open) when Redis returns an error")
	}
}

func TestIsDuplicate_EmptyMessageID_ReturnsError(t *testing.T) {
	svc, _ := newTestService(t, time.Hour)

	_, err := svc.IsDuplicate(context.Background(), "")
	if err == nil {
		t.Fatal("expected error for empty messageID")
	}
	if err.Error() != "messageID must not be empty" {
		t.Fatalf("expected 'messageID must not be empty', got %q", err.Error())
	}
}

// --- MarkSeen tests ---

func TestMarkSeen_SetsKeyWithCorrectValueAndTTL(t *testing.T) {
	ttl := time.Hour
	svc, mr := newTestService(t, ttl)

	if err := svc.MarkSeen(context.Background(), "msg-mark"); err != nil {
		t.Fatalf("MarkSeen failed: %v", err)
	}

	val, err := mr.Get("autorepub:dedup:msg-mark")
	if err != nil {
		t.Fatalf("expected key to exist in Redis: %v", err)
	}
	if val != "1" {
		t.Fatalf("expected value '1', got %q", val)
	}

	remaining := mr.TTL("autorepub:dedup:msg-mark")
	if remaining <= 0 || remaining > ttl {
		t.Fatalf("unexpected TTL %v, want (0, %v]", remaining, ttl)
	}
}

func TestMarkSeen_EmptyMessageID_ReturnsError(t *testing.T) {
	svc, _ := newTestService(t, time.Hour)

	err := svc.MarkSeen(context.Background(), "")
	if err == nil {
		t.Fatal("expected error for empty messageID")
	}
	if err.Error() != "messageID must not be empty" {
		t.Fatalf("expected 'messageID must not be empty', got %q", err.Error())
	}
}

func TestMarkSeen_RedisError_ReturnsError(t *testing.T) {
	svc, mr := newTestService(t, time.Hour)
	mr.Close() // force connection error

	err := svc.MarkSeen(context.Background(), "msg-redis-err")
	if err == nil {
		t.Fatal("expected error when Redis is unavailable")
	}
}
