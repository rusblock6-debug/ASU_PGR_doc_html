package rabbitmq

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/rs/zerolog"
)

func TestManagementClient_DiscoverQueues_Success(t *testing.T) {
	queues := []queueInfo{
		{Name: "server.bort_1.trip.src"},
		{Name: "server.bort_1.alert.src"},
	}

	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet {
			t.Errorf("expected GET, got %s", r.Method)
		}

		user, pass, ok := r.BasicAuth()
		if !ok || user != "guest" || pass != "guest" {
			t.Errorf("unexpected auth: %s:%s (ok=%v)", user, pass, ok)
		}

		if got := r.URL.Query().Get("use_regex"); got != "true" {
			t.Errorf("use_regex = %q, want true", got)
		}
		if got := r.URL.Query().Get("columns"); got != "name" {
			t.Errorf("columns = %q, want name", got)
		}
		if got := r.URL.Query().Get("name"); got == "" {
			t.Error("name query param is empty")
		}

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(queues)
	}))
	defer srv.Close()

	client := &ManagementClient{
		baseURL:  srv.URL,
		user:     "guest",
		password: "guest",
		vhost:    "/",
		http:     http.DefaultClient,
		logger:   zerolog.Nop(),
	}

	names, err := client.DiscoverQueues(context.Background(), `^server\.bort_1\..*\.src$`)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if len(names) != 2 {
		t.Fatalf("expected 2 queues, got %d", len(names))
	}
	if names[0] != "server.bort_1.trip.src" {
		t.Errorf("names[0] = %q, want server.bort_1.trip.src", names[0])
	}
	if names[1] != "server.bort_1.alert.src" {
		t.Errorf("names[1] = %q, want server.bort_1.alert.src", names[1])
	}
}

func TestManagementClient_DiscoverQueues_EmptyResult(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Write([]byte("[]"))
	}))
	defer srv.Close()

	client := &ManagementClient{
		baseURL:  srv.URL,
		user:     "guest",
		password: "guest",
		vhost:    "/",
		http:     http.DefaultClient,
		logger:   zerolog.Nop(),
	}

	names, err := client.DiscoverQueues(context.Background(), `^nonexistent$`)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(names) != 0 {
		t.Fatalf("expected 0 queues, got %d", len(names))
	}
}

func TestManagementClient_DiscoverQueues_HTTPError(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		http.Error(w, "internal error", http.StatusInternalServerError)
	}))
	defer srv.Close()

	client := &ManagementClient{
		baseURL:  srv.URL,
		user:     "guest",
		password: "guest",
		vhost:    "/",
		http:     http.DefaultClient,
		logger:   zerolog.Nop(),
	}

	_, err := client.DiscoverQueues(context.Background(), `.*`)
	if err == nil {
		t.Fatal("expected error for non-2xx status")
	}
}

func TestManagementClient_DiscoverQueues_InvalidJSON(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Write([]byte("not json"))
	}))
	defer srv.Close()

	client := &ManagementClient{
		baseURL:  srv.URL,
		user:     "guest",
		password: "guest",
		vhost:    "/",
		http:     http.DefaultClient,
		logger:   zerolog.Nop(),
	}

	_, err := client.DiscoverQueues(context.Background(), `.*`)
	if err == nil {
		t.Fatal("expected error for invalid JSON")
	}
}

func TestNewManagementClient(t *testing.T) {
	cfg := Config{
		Host:           "rabbit-host",
		Port:           5672,
		User:           "user",
		Password:       "pass",
		Vhost:          "/",
		ManagementPort: 15672,
	}

	client := NewManagementClient(cfg, zerolog.Nop())

	if client.baseURL != "http://rabbit-host:15672" {
		t.Errorf("baseURL = %q, want http://rabbit-host:15672", client.baseURL)
	}
	if client.user != "user" {
		t.Errorf("user = %q, want user", client.user)
	}
	if client.password != "pass" {
		t.Errorf("password = %q, want pass", client.password)
	}
	if client.vhost != "/" {
		t.Errorf("vhost = %q, want /", client.vhost)
	}
}

// TestManagementClient_DiscoverQueues_ClientSideFiltering verifies that when
// the Management API returns unfiltered results (ignoring use_regex), the client
// filters queues by the provided regex pattern.
func TestManagementClient_DiscoverQueues_ClientSideFiltering(t *testing.T) {
	// Simulate API returning ALL queues (no server-side filtering)
	allQueues := []queueInfo{
		{Name: "bort_4.server.common.dst"},
		{Name: "bort_4.server.trip.dst"},
		{Name: "bort_4.server.trip.src"},
		{Name: "bort_4.server.common.src"},
		{Name: "cdc-auth-service"},
		{Name: "cdc-trip-service"},
		{Name: "minio-events"},
		{Name: "server.bort_17.trip.src"},
		{Name: "server.bort_4.trip.src"},
		{Name: "server.bort_4.common.src"},
		{Name: "server.bort_4.common.dlq"},
	}

	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(allQueues)
	}))
	defer srv.Close()

	client := &ManagementClient{
		baseURL:  srv.URL,
		user:     "guest",
		password: "guest",
		vhost:    "/",
		http:     http.DefaultClient,
		logger:   zerolog.Nop(),
	}

	tests := []struct {
		name    string
		pattern string
		want    []string
	}{
		{
			name:    "BortQueuePattern filters only bort src queues for truck 4",
			pattern: `^bort_4\.server\..*\.src$`,
			want:    []string{"bort_4.server.trip.src", "bort_4.server.common.src"},
		},
		{
			name:    "ServerQueuePattern filters only server src queues for truck 4",
			pattern: `^server\.bort_4\..*\.src$`,
			want:    []string{"server.bort_4.trip.src", "server.bort_4.common.src"},
		},
		{
			name:    "ServerQueuePattern for truck 17 does not match truck 4",
			pattern: `^server\.bort_17\..*\.src$`,
			want:    []string{"server.bort_17.trip.src"},
		},
		{
			name:    "pattern matches nothing",
			pattern: `^bort_99\.server\..*\.src$`,
			want:    []string{},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			names, err := client.DiscoverQueues(context.Background(), tt.pattern)
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if len(names) != len(tt.want) {
				t.Fatalf("got %d queues %v, want %d %v", len(names), names, len(tt.want), tt.want)
			}
			for i, name := range names {
				if name != tt.want[i] {
					t.Errorf("names[%d] = %q, want %q", i, name, tt.want[i])
				}
			}
		})
	}
}

// TestManagementClient_DiscoverQueues_DoesNotMatchDstOrDlq verifies that .dst
// and .dlq queues are excluded by the .src$ regex anchor.
func TestManagementClient_DiscoverQueues_DoesNotMatchDstOrDlq(t *testing.T) {
	queues := []queueInfo{
		{Name: "server.bort_4.trip.src"},
		{Name: "server.bort_4.trip.dst"},
		{Name: "server.bort_4.trip.dlq"},
	}

	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(queues)
	}))
	defer srv.Close()

	client := &ManagementClient{
		baseURL:  srv.URL,
		user:     "guest",
		password: "guest",
		vhost:    "/",
		http:     http.DefaultClient,
		logger:   zerolog.Nop(),
	}

	names, err := client.DiscoverQueues(context.Background(), `^server\.bort_4\..*\.src$`)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(names) != 1 {
		t.Fatalf("expected 1 queue, got %d: %v", len(names), names)
	}
	if names[0] != "server.bort_4.trip.src" {
		t.Errorf("got %q, want server.bort_4.trip.src", names[0])
	}
}

// TestManagementClient_DiscoverQueues_InvalidRegex verifies that an invalid
// regex pattern returns an error.
func TestManagementClient_DiscoverQueues_InvalidRegex(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Write([]byte("[]"))
	}))
	defer srv.Close()

	client := &ManagementClient{
		baseURL:  srv.URL,
		user:     "guest",
		password: "guest",
		vhost:    "/",
		http:     http.DefaultClient,
		logger:   zerolog.Nop(),
	}

	_, err := client.DiscoverQueues(context.Background(), `[invalid`)
	if err == nil {
		t.Fatal("expected error for invalid regex")
	}
}

// TestManagementClient_DiscoverQueues_BortPatternDoesNotMatchOtherBorts verifies
// that bort_4 pattern does not match bort_42 or bort_40.
func TestManagementClient_DiscoverQueues_BortPatternDoesNotMatchOtherBorts(t *testing.T) {
	queues := []queueInfo{
		{Name: "bort_4.server.trip.src"},
		{Name: "bort_42.server.trip.src"},
		{Name: "bort_40.server.trip.src"},
		{Name: "bort_14.server.trip.src"},
	}

	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(queues)
	}))
	defer srv.Close()

	client := &ManagementClient{
		baseURL:  srv.URL,
		user:     "guest",
		password: "guest",
		vhost:    "/",
		http:     http.DefaultClient,
		logger:   zerolog.Nop(),
	}

	names, err := client.DiscoverQueues(context.Background(), `^bort_4\.server\..*\.src$`)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(names) != 1 {
		t.Fatalf("expected 1 queue, got %d: %v", len(names), names)
	}
	if names[0] != "bort_4.server.trip.src" {
		t.Errorf("got %q, want bort_4.server.trip.src", names[0])
	}
}

func TestManagementClient_DiscoverQueues_VhostEncoding(t *testing.T) {
	var gotRawURL string
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		gotRawURL = r.RequestURI
		w.Header().Set("Content-Type", "application/json")
		w.Write([]byte("[]"))
	}))
	defer srv.Close()

	client := &ManagementClient{
		baseURL:  srv.URL,
		user:     "guest",
		password: "guest",
		vhost:    "my/vhost",
		http:     http.DefaultClient,
		logger:   zerolog.Nop(),
	}

	_, _ = client.DiscoverQueues(context.Background(), `.*`)

	if !testing.Short() {
		// RequestURI preserves percent-encoding
		wantPrefix := "/api/queues/my%2Fvhost?"
		if len(gotRawURL) < len(wantPrefix) || gotRawURL[:len(wantPrefix)] != wantPrefix {
			t.Errorf("raw URL = %q, want prefix %q", gotRawURL, wantPrefix)
		}
	}
}
