package rabbitmq

import "testing"

func TestChanSubscription_QueueName(t *testing.T) {
	sub := &ChanSubscription{queueName: "server.bort_4.trip.src"}

	if got := sub.QueueName(); got != "server.bort_4.trip.src" {
		t.Errorf("QueueName() = %q, want server.bort_4.trip.src", got)
	}
}

func TestChanSubscription_QueueName_Empty(t *testing.T) {
	sub := &ChanSubscription{}

	if got := sub.QueueName(); got != "" {
		t.Errorf("QueueName() = %q, want empty", got)
	}
}
