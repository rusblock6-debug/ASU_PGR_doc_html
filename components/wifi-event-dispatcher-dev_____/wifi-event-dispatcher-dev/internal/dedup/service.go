package dedup

import (
	"context"
	"errors"
	"time"

	goredis "github.com/redis/go-redis/v9"
	"github.com/rs/zerolog"
)

const keyPrefix = "autorepub:dedup:"

// Service defines the deduplication interface used by publisher and consumer.
type Service interface {
	// IsDuplicate checks whether messageID has already been seen.
	// Returns true if the key exists, false if not.
	// On Redis error, returns false + error (fail-open).
	IsDuplicate(ctx context.Context, messageID string) (bool, error)

	// MarkSeen records messageID in Redis with the configured TTL.
	MarkSeen(ctx context.Context, messageID string) error
}

type service struct {
	client *goredis.Client
	ttl    time.Duration
	log    zerolog.Logger
}

// New constructs a Service backed by the provided Redis client.
func New(client *goredis.Client, ttl time.Duration, log zerolog.Logger) Service {
	return &service{
		client: client,
		ttl:    ttl,
		log:    log.With().Str("component", "dedup").Logger(),
	}
}

func buildKey(messageID string) string {
	return keyPrefix + messageID
}

func (s *service) IsDuplicate(ctx context.Context, messageID string) (bool, error) {
	if messageID == "" {
		return false, errors.New("messageID must not be empty")
	}

	_, err := s.client.Get(ctx, buildKey(messageID)).Result()
	if err == nil {
		return true, nil
	}
	if errors.Is(err, goredis.Nil) {
		return false, nil
	}

	// Redis error: fail-open — caller may proceed with the message.
	return false, err
}

func (s *service) MarkSeen(ctx context.Context, messageID string) error {
	if messageID == "" {
		return errors.New("messageID must not be empty")
	}

	return s.client.Set(ctx, buildKey(messageID), "1", s.ttl).Err()
}
