package domain

import (
	"errors"
	"wifi-event-dispatcher/server/serverpb"
)

func EventFromProto(ev *serverpb.Event) (*Event, error) {
	if ev == nil {
		return nil, errors.New("event is nil")
	}

	if ev.GetMessageId() == "" {
		return nil, errors.New("message_id is empty")
	}

	return NewEvent(
		ev.GetTopic(),
		ev.GetMessageId(),
		ev.GetPayload(),
	)
}
