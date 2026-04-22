package domain

import (
	"testing"
)

func TestNewEvent(t *testing.T) {
	t.Run("valid event with messageID", func(t *testing.T) {
		ev, err := NewEvent("topic.src", "msg-123", []byte("payload"))
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if ev.Topic != "topic.src" {
			t.Errorf("got topic %q, want %q", ev.Topic, "topic.src")
		}
		if ev.MessageID != "msg-123" {
			t.Errorf("got messageID %q, want %q", ev.MessageID, "msg-123")
		}
		if string(ev.Payload) != "payload" {
			t.Errorf("got payload %q, want %q", ev.Payload, "payload")
		}
	})

	t.Run("generates UUID when messageID is empty", func(t *testing.T) {
		ev, err := NewEvent("topic.src", "", []byte("payload"))
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if ev.MessageID == "" {
			t.Error("expected generated messageID, got empty string")
		}
	})

	t.Run("error on empty topic", func(t *testing.T) {
		_, err := NewEvent("", "msg-123", []byte("payload"))
		if err == nil {
			t.Fatal("expected error for empty topic")
		}
	})

	t.Run("error on nil payload", func(t *testing.T) {
		_, err := NewEvent("topic.src", "msg-123", nil)
		if err == nil {
			t.Fatal("expected error for nil payload")
		}
	})
}

func TestEvent_ToProto(t *testing.T) {
	ev := &Event{
		Topic:     "test.topic",
		MessageID: "msg-456",
		Payload:   []byte("data"),
	}

	proto := ev.ToProto()

	if proto.GetTopic() != "test.topic" {
		t.Errorf("got topic %q, want %q", proto.GetTopic(), "test.topic")
	}
	if proto.GetMessageId() != "msg-456" {
		t.Errorf("got messageId %q, want %q", proto.GetMessageId(), "msg-456")
	}
	if string(proto.GetPayload()) != "data" {
		t.Errorf("got payload %q, want %q", proto.GetPayload(), "data")
	}
}
