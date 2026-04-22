package config

import (
	"testing"
)

func TestBortConfig_NanoMqClient(t *testing.T) {
	cfg := BortConfig{
		NanoMq: nanoMqConfig{
			ClientPrefix: "wifi_event_dispatcher",
		},
		TruckID: 42,
	}

	got := cfg.NanoMqClient()
	expected := "wifi_event_dispatcher_42"
	if got != expected {
		t.Fatalf("NanoMqClient() = %q, want %q", got, expected)
	}
}

func TestNanoMqConfig_Url(t *testing.T) {
	cfg := nanoMqConfig{
		Host: "192.168.1.10",
		Port: 1883,
	}

	got := cfg.Url()
	expected := "tcp://192.168.1.10:1883"
	if got != expected {
		t.Fatalf("Url() = %q, want %q", got, expected)
	}
}

func TestServerRpcConfig_Address(t *testing.T) {
	cfg := serverRpcConfig{
		Host: "0.0.0.0",
		Port: ":8085",
	}

	got := cfg.Address()
	expected := "0.0.0.0:8085"
	if got != expected {
		t.Fatalf("Address() = %q, want %q", got, expected)
	}
}

func TestLoadServerConfig(t *testing.T) {
	t.Setenv("RABBIT_HOST", "localhost")
	t.Setenv("RABBIT_PORT", "5672")
	t.Setenv("RABBIT_USER", "guest")
	t.Setenv("RABBIT_PASSWORD", "guest")

	cfg, err := LoadServerConfig()
	if err != nil {
		t.Fatalf("LoadServerConfig() error: %v", err)
	}
	if cfg == nil {
		t.Fatal("expected non-nil ServerAppConfig")
	}
	if cfg.Environment != "development" {
		t.Errorf("Environment = %q, want %q", cfg.Environment, "development")
	}
	if cfg.LogLevel != "DEBUG" {
		t.Errorf("LogLevel = %q, want %q", cfg.LogLevel, "DEBUG")
	}
	if cfg.RabbitmqConfig.Host != "localhost" {
		t.Errorf("RabbitmqConfig.Host = %q, want %q", cfg.RabbitmqConfig.Host, "localhost")
	}
	if cfg.RabbitmqConfig.Port != 5672 {
		t.Errorf("RabbitmqConfig.Port = %d, want %d", cfg.RabbitmqConfig.Port, 5672)
	}
	if cfg.CoordinationURL != "http://sync-service:8000" {
		t.Errorf("CoordinationURL = %q, want default %q", cfg.CoordinationURL, "http://sync-service:8000")
	}
	if cfg.DistributionPort != "8000" {
		t.Errorf("DistributionPort = %q, want default %q", cfg.DistributionPort, "8000")
	}
	if cfg.AutorepubHTTPTimeout.String() != "10s" {
		t.Errorf("AutorepubHTTPTimeout = %v, want 10s", cfg.AutorepubHTTPTimeout)
	}
}

func TestLoadBortConfig(t *testing.T) {
	t.Setenv("RABBIT_HOST", "localhost")
	t.Setenv("RABBIT_PORT", "5672")
	t.Setenv("RABBIT_USER", "guest")
	t.Setenv("RABBIT_PASSWORD", "guest")
	t.Setenv("BORT_TRUCK_ID", "7")
	t.Setenv("BORT_NANOMQ_HOST", "192.168.1.1")
	t.Setenv("BORT_NANOMQ_PORT", "1883")
	t.Setenv("COORDINATION_URL", "http://10.100.109.14:8010")
	t.Setenv("DISTRIBUTION_PORT", "9000")

	cfg, err := LoadBortConfig()
	if err != nil {
		t.Fatalf("LoadBortConfig() error: %v", err)
	}
	if cfg == nil {
		t.Fatal("expected non-nil BortAppConfig")
	}
	if cfg.Bort.TruckID != 7 {
		t.Errorf("Bort.TruckID = %d, want %d", cfg.Bort.TruckID, 7)
	}
	if cfg.Bort.NanoMq.Host != "192.168.1.1" {
		t.Errorf("Bort.NanoMq.Host = %q, want %q", cfg.Bort.NanoMq.Host, "192.168.1.1")
	}
	if cfg.Bort.NanoMq.Port != 1883 {
		t.Errorf("Bort.NanoMq.Port = %d, want %d", cfg.Bort.NanoMq.Port, 1883)
	}
	if cfg.Bort.ServerAddress != "localhost:8085" {
		t.Errorf("Bort.ServerAddress = %q, want %q", cfg.Bort.ServerAddress, "localhost:8085")
	}
	if cfg.CoordinationURL != "http://10.100.109.14:8010" {
		t.Errorf("CoordinationURL = %q, want %q", cfg.CoordinationURL, "http://10.100.109.14:8010")
	}
	if cfg.DistributionPort != "9000" {
		t.Errorf("DistributionPort = %q, want %q", cfg.DistributionPort, "9000")
	}
	if cfg.AutorepubHTTPTimeout.String() != "10s" {
		t.Errorf("AutorepubHTTPTimeout = %v, want 10s", cfg.AutorepubHTTPTimeout)
	}
}

func TestLoadBortConfig_CustomTimeout(t *testing.T) {
	t.Setenv("RABBIT_HOST", "localhost")
	t.Setenv("RABBIT_PORT", "5672")
	t.Setenv("RABBIT_USER", "guest")
	t.Setenv("RABBIT_PASSWORD", "guest")
	t.Setenv("BORT_TRUCK_ID", "7")
	t.Setenv("BORT_NANOMQ_HOST", "192.168.1.1")
	t.Setenv("BORT_NANOMQ_PORT", "1883")
	t.Setenv("COORDINATION_URL", "http://10.100.109.14:8010")
	t.Setenv("AUTOREPUB_HTTP_TIMEOUT", "5s")

	cfg, err := LoadBortConfig()
	if err != nil {
		t.Fatalf("LoadBortConfig() error: %v", err)
	}
	if cfg.AutorepubHTTPTimeout.String() != "5s" {
		t.Errorf("AutorepubHTTPTimeout = %v, want 5s", cfg.AutorepubHTTPTimeout)
	}
}

func TestLoadBortConfig_DefaultCoordinationURL(t *testing.T) {
	t.Setenv("RABBIT_HOST", "localhost")
	t.Setenv("RABBIT_PORT", "5672")
	t.Setenv("RABBIT_USER", "guest")
	t.Setenv("RABBIT_PASSWORD", "guest")
	t.Setenv("BORT_TRUCK_ID", "7")
	t.Setenv("BORT_NANOMQ_HOST", "192.168.1.1")
	t.Setenv("BORT_NANOMQ_PORT", "1883")

	cfg, err := LoadBortConfig()
	if err != nil {
		t.Fatalf("LoadBortConfig() error: %v", err)
	}
	if cfg.CoordinationURL != "http://sync-service:8000" {
		t.Errorf("CoordinationURL = %q, want default %q", cfg.CoordinationURL, "http://sync-service:8000")
	}
}

func TestLoadBortConfig_DefaultDistributionPort(t *testing.T) {
	t.Setenv("RABBIT_HOST", "localhost")
	t.Setenv("RABBIT_PORT", "5672")
	t.Setenv("RABBIT_USER", "guest")
	t.Setenv("RABBIT_PASSWORD", "guest")
	t.Setenv("BORT_TRUCK_ID", "7")
	t.Setenv("BORT_NANOMQ_HOST", "192.168.1.1")
	t.Setenv("BORT_NANOMQ_PORT", "1883")
	t.Setenv("COORDINATION_URL", "http://10.100.109.14:8010")

	cfg, err := LoadBortConfig()
	if err != nil {
		t.Fatalf("LoadBortConfig() error: %v", err)
	}
	if cfg.DistributionPort != "8000" {
		t.Errorf("DistributionPort = %q, want default %q", cfg.DistributionPort, "8000")
	}
}
