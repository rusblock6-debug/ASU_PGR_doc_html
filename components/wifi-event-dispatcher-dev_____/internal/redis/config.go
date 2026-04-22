package redis

import "time"

// Config holds configuration for the Redis client.
// Environment variables are loaded via envconfig with a "REDIS" prefix
// (e.g. REDIS_ADDR, REDIS_PASSWORD, REDIS_DB, REDIS_DEDUP_TTL).
type Config struct {
	Addr     string `default:"redis:6379"`
	Password string
	DB       int           `default:"1"`
	DedupTTL time.Duration `default:"24h"`
}
