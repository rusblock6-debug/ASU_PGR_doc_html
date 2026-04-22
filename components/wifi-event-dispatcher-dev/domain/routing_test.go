package domain

import (
	"testing"
)

func TestToDestinationTopic(t *testing.T) {
	tests := []struct {
		input string
		want  string
	}{
		{"bort_4.server.trip_service.src", "bort_4.server.trip_service.dst"},
		{"server.bort_4.trip_service.src", "server.bort_4.trip_service.dst"},
		{"no_suffix_here", "no_suffix_here"},
		{"double.src.src", "double.dst.src"},
	}

	for _, tt := range tests {
		t.Run(tt.input, func(t *testing.T) {
			got := ToDestinationTopic(tt.input)
			if got != tt.want {
				t.Errorf("ToDestinationTopic(%q) = %q, want %q", tt.input, got, tt.want)
			}
		})
	}
}

func TestServerQueueName(t *testing.T) {
	got := ServerQueueName(4, "trip_service")
	want := "server.bort_4.trip_service.src"
	if got != want {
		t.Errorf("ServerQueueName(4, trip_service) = %q, want %q", got, want)
	}
}

func TestBortQueueName(t *testing.T) {
	got := BortQueueName(4, "trip_service")
	want := "bort_4.server.trip_service.src"
	if got != want {
		t.Errorf("BortQueueName(4, trip_service) = %q, want %q", got, want)
	}
}

func TestServerQueuePattern(t *testing.T) {
	got := ServerQueuePattern(42)
	want := `^server\.bort_42\..*\.src$`
	if got != want {
		t.Errorf("ServerQueuePattern(42) = %q, want %q", got, want)
	}
}

func TestBortQueuePattern(t *testing.T) {
	got := BortQueuePattern(7)
	want := `^bort_7\.server\..*\.src$`
	if got != want {
		t.Errorf("BortQueuePattern(7) = %q, want %q", got, want)
	}
}
