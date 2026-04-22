package redis

import "testing"

func TestNewClient_ReturnsNonNil(t *testing.T) {
	client := NewClient(Config{Addr: "localhost:6379"})
	if client == nil {
		t.Fatal("expected non-nil redis client")
	}
}

func TestNewClient_AppliesConfig(t *testing.T) {
	cfg := Config{
		Addr:     "custom-host:6380",
		Password: "secret",
		DB:       3,
	}
	client := NewClient(cfg)

	opts := client.Options()
	if opts.Addr != cfg.Addr {
		t.Errorf("expected addr %q, got %q", cfg.Addr, opts.Addr)
	}
	if opts.Password != cfg.Password {
		t.Errorf("expected password %q, got %q", cfg.Password, opts.Password)
	}
	if opts.DB != cfg.DB {
		t.Errorf("expected db %d, got %d", cfg.DB, opts.DB)
	}
}

func TestNewClient_ZeroConfig(t *testing.T) {
	client := NewClient(Config{})
	if client == nil {
		t.Fatal("expected non-nil client even with zero config")
	}
	opts := client.Options()
	if opts.Password != "" {
		t.Errorf("expected empty password for zero config, got %q", opts.Password)
	}
	if opts.DB != 0 {
		t.Errorf("expected db 0 for zero config, got %d", opts.DB)
	}
}
