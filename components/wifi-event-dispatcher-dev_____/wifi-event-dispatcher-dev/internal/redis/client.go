package redis

import goredis "github.com/redis/go-redis/v9"

// NewClient constructs a go-redis Client from the given Config.
// The caller is responsible for verifying connectivity (e.g. via Ping).
func NewClient(cfg Config) *goredis.Client {
	return goredis.NewClient(&goredis.Options{
		Addr:     cfg.Addr,
		Password: cfg.Password,
		DB:       cfg.DB,
	})
}
