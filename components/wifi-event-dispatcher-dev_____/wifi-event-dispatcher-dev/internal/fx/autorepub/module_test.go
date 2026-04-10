package fxautorepub

import (
	"strings"
	"testing"
	"time"
	"wifi-event-dispatcher/internal/autorepub"
	"wifi-event-dispatcher/internal/config"

	"github.com/rs/zerolog"
	"go.uber.org/fx"
)

func TestModule_ProvidesAutorepubClient(t *testing.T) {
	cfg := config.AutorepubConfig{
		CoordinationURL:      "http://coordination:8010",
		DistributionPort:     "8000",
		AutorepubHTTPTimeout: 5 * time.Second,
	}

	var resolved *autorepub.Client
	app := fx.New(
		fx.Supply(cfg, zerolog.Nop()),
		Module,
		fx.Invoke(func(client *autorepub.Client) {
			resolved = client
		}),
	)

	if err := app.Err(); err != nil {
		t.Fatalf("expected fx app to build, got error: %v", err)
	}
	if resolved == nil {
		t.Fatal("expected autorepub client to be injected")
	}
}

func TestModule_MissingDependencyFails(t *testing.T) {
	cfg := config.AutorepubConfig{
		CoordinationURL:      "http://coordination:8010",
		DistributionPort:     "8000",
		AutorepubHTTPTimeout: 5 * time.Second,
	}

	app := fx.New(
		fx.Supply(cfg, zerolog.Nop()),
		fx.Invoke(func(*autorepub.Client) {}),
	)

	err := app.Err()
	if err == nil {
		t.Fatal("expected fx app error when autorepub module is not connected")
	}
	if !strings.Contains(err.Error(), "*autorepub.Client") {
		t.Fatalf("expected missing autorepub client in error, got: %v", err)
	}
}
