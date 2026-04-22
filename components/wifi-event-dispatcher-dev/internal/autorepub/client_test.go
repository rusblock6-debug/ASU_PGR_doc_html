package autorepub

import (
	"context"
	"errors"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/rs/zerolog"
)

type roundTripFunc func(*http.Request) (*http.Response, error)

func (f roundTripFunc) RoundTrip(req *http.Request) (*http.Response, error) {
	return f(req)
}

func TestClientSuspendResume_SendExpectedRequest(t *testing.T) {
	testCases := []struct {
		name   string
		path   string
		invoke func(*Client, context.Context, map[string][]int) error
	}{
		{
			name:   "suspend",
			path:   "/autorepub/suspend",
			invoke: (*Client).Suspend,
		},
		{
			name:   "resume",
			path:   "/autorepub/resume",
			invoke: (*Client).Resume,
		},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			var gotMethod string
			var gotPath string
			var gotContentType string
			var gotBody string

			server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				body, err := io.ReadAll(r.Body)
				if err != nil {
					t.Fatalf("read request body: %v", err)
				}

				gotMethod = r.Method
				gotPath = r.URL.Path
				gotContentType = r.Header.Get("Content-Type")
				gotBody = string(body)

				w.WriteHeader(http.StatusOK)
			}))
			defer server.Close()

			client := NewClient("http://coordination.test", "8000", time.Second, zerolog.Nop())
			client.DistributionURLFor = func(_ string) string { return server.URL }

			err := tc.invoke(client, context.Background(), map[string][]int{"node-1": {4, 9, 17}})
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}

			if gotMethod != http.MethodPost {
				t.Fatalf("expected method %q, got %q", http.MethodPost, gotMethod)
			}
			if gotPath != tc.path {
				t.Fatalf("expected path %q, got %q", tc.path, gotPath)
			}
			if gotContentType != "application/json" {
				t.Fatalf("expected content-type application/json, got %q", gotContentType)
			}
			if gotBody != `{"vehicle_ids":[4,9,17]}` {
				t.Fatalf("expected body %q, got %q", `{"vehicle_ids":[4,9,17]}`, gotBody)
			}
		})
	}
}

func TestClientSuspendResume_MultipleHosts_CallsEach(t *testing.T) {
	testCases := []struct {
		name   string
		invoke func(*Client, context.Context, map[string][]int) error
	}{
		{name: "suspend", invoke: (*Client).Suspend},
		{name: "resume", invoke: (*Client).Resume},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			type call struct {
				host string
				body string
			}
			var calls []call

			srv1 := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				body, _ := io.ReadAll(r.Body)
				calls = append(calls, call{host: "node-1", body: string(body)})
				w.WriteHeader(http.StatusOK)
			}))
			defer srv1.Close()

			srv2 := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				body, _ := io.ReadAll(r.Body)
				calls = append(calls, call{host: "node-2", body: string(body)})
				w.WriteHeader(http.StatusOK)
			}))
			defer srv2.Close()

			hostToURL := map[string]string{
				"node-1": srv1.URL,
				"node-2": srv2.URL,
			}
			client := NewClient("http://coordination.test", "8000", time.Second, zerolog.Nop())
			client.DistributionURLFor = func(host string) string { return hostToURL[host] }

			distribution := map[string][]int{
				"node-1": {4, 9},
				"node-2": {17},
			}
			err := tc.invoke(client, context.Background(), distribution)
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}

			if len(calls) != 2 {
				t.Fatalf("expected 2 HTTP calls, got %d", len(calls))
			}
		})
	}
}

func TestClientSuspendResume_EmptyDistribution_NoHTTPCalls(t *testing.T) {
	testCases := []struct {
		name   string
		invoke func(*Client, context.Context, map[string][]int) error
	}{
		{name: "suspend", invoke: (*Client).Suspend},
		{name: "resume", invoke: (*Client).Resume},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			callCount := 0
			server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				callCount++
				w.WriteHeader(http.StatusOK)
			}))
			defer server.Close()

			client := NewClient("http://coordination.test", "8000", time.Second, zerolog.Nop())
			client.DistributionURLFor = func(_ string) string { return server.URL }

			err := tc.invoke(client, context.Background(), map[string][]int{})
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}

			if callCount != 0 {
				t.Fatalf("expected zero HTTP calls for empty distribution, got %d", callCount)
			}
		})
	}
}

func TestClientSuspendResume_Non2xxReturnsErrorWithStatusCode(t *testing.T) {
	testCases := []struct {
		name   string
		invoke func(*Client, context.Context, map[string][]int) error
	}{
		{name: "suspend", invoke: (*Client).Suspend},
		{name: "resume", invoke: (*Client).Resume},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				w.WriteHeader(http.StatusBadGateway)
			}))
			defer server.Close()

			client := NewClient("http://coordination.test", "8000", time.Second, zerolog.Nop())
			client.DistributionURLFor = func(_ string) string { return server.URL }

			err := tc.invoke(client, context.Background(), map[string][]int{"node-1": {4, 9, 17}})
			if err == nil {
				t.Fatal("expected error for non-2xx response")
			}
			if !strings.Contains(err.Error(), "unexpected status code 502") {
				t.Fatalf("expected status code in error, got %q", err.Error())
			}
		})
	}
}

func TestClientSuspendResume_NetworkErrorReturnsError(t *testing.T) {
	testCases := []struct {
		name   string
		path   string
		invoke func(*Client, context.Context, map[string][]int) error
	}{
		{name: "suspend", path: "/autorepub/suspend", invoke: (*Client).Suspend},
		{name: "resume", path: "/autorepub/resume", invoke: (*Client).Resume},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			client := NewClient("http://coordination.test", "8000", time.Second, zerolog.Nop())
			client.DistributionURLFor = func(_ string) string { return "http://distribution.test" }
			client.httpClient = &http.Client{
				Transport: roundTripFunc(func(*http.Request) (*http.Response, error) {
					return nil, errors.New("network down")
				}),
			}

			err := tc.invoke(client, context.Background(), map[string][]int{"node-1": {4}})
			if err == nil {
				t.Fatal("expected network error")
			}
			if !strings.Contains(err.Error(), "network down") {
				t.Fatalf("expected network error message, got %q", err.Error())
			}
			if !strings.Contains(err.Error(), tc.path) {
				t.Fatalf("expected endpoint path in error, got %q", err.Error())
			}
		})
	}
}
