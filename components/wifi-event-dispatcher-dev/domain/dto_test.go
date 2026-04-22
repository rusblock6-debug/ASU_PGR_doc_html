package domain

import (
	"testing"
	"wifi-event-dispatcher/server/serverpb"
)

func TestEventFromProto(t *testing.T) {
	t.Run("valid proto event", func(t *testing.T) {
		pb := &serverpb.Event{
			Topic:     "topic.src",
			MessageId: "msg-789",
			Payload:   []byte("data"),
		}

		ev, err := EventFromProto(pb)
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if ev.Topic != "topic.src" {
			t.Errorf("got topic %q, want %q", ev.Topic, "topic.src")
		}
		if ev.MessageID != "msg-789" {
			t.Errorf("got messageID %q, want %q", ev.MessageID, "msg-789")
		}
	})

	t.Run("nil event returns error", func(t *testing.T) {
		_, err := EventFromProto(nil)
		if err == nil {
			t.Fatal("expected error for nil event")
		}
	})

	t.Run("empty message_id returns error", func(t *testing.T) {
		pb := &serverpb.Event{
			Topic:   "topic.src",
			Payload: []byte("data"),
		}

		_, err := EventFromProto(pb)
		if err == nil {
			t.Fatal("expected error for empty message_id")
		}
	})
}
