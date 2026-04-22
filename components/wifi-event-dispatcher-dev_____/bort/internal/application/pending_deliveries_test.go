package application

import (
	"testing"

	amqp "github.com/rabbitmq/amqp091-go"
)

func TestPendingDeliveries_AddAndTake(t *testing.T) {
	pd := newPendingDeliveries()

	d := amqp.Delivery{MessageId: "msg-1"}
	pd.add("msg-1", d)

	got, ok := pd.take("msg-1")
	if !ok {
		t.Fatal("expected to find delivery")
	}
	if got.MessageId != "msg-1" {
		t.Errorf("got MessageId %q, want %q", got.MessageId, "msg-1")
	}

	// Second take should return false
	_, ok = pd.take("msg-1")
	if ok {
		t.Fatal("expected take to return false after first take")
	}
}

func TestPendingDeliveries_Remove(t *testing.T) {
	pd := newPendingDeliveries()

	pd.add("msg-1", amqp.Delivery{MessageId: "msg-1"})
	pd.remove("msg-1")

	_, ok := pd.take("msg-1")
	if ok {
		t.Fatal("expected delivery to be removed")
	}
}

func TestPendingDeliveries_Drain(t *testing.T) {
	pd := newPendingDeliveries()

	pd.add("msg-1", amqp.Delivery{MessageId: "msg-1"})
	pd.add("msg-2", amqp.Delivery{MessageId: "msg-2"})
	pd.add("msg-3", amqp.Delivery{MessageId: "msg-3"})

	drained := pd.drain()
	if len(drained) != 3 {
		t.Fatalf("got %d deliveries, want 3", len(drained))
	}

	// After drain, map should be empty
	drained2 := pd.drain()
	if len(drained2) != 0 {
		t.Fatalf("got %d deliveries after second drain, want 0", len(drained2))
	}
}

func TestPendingDeliveries_TakeNotFound(t *testing.T) {
	pd := newPendingDeliveries()

	_, ok := pd.take("nonexistent")
	if ok {
		t.Fatal("expected take to return false for nonexistent key")
	}
}
