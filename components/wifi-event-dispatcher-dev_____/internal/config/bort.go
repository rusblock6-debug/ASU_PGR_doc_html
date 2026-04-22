package config

import (
	"fmt"
)

type BortConfig struct {
	NanoMq        nanoMqConfig `envconfig:"NANOMQ"`
	TruckID       int          `required:"true" envconfig:"TRUCK_ID"`
	ServerAddress string       `envconfig:"SERVER_ADDRESS" default:"localhost:8085"`
}

func (b *BortConfig) NanoMqClient() string {
	return fmt.Sprintf("%s_%d", b.NanoMq.ClientPrefix, b.TruckID)
}

type nanoMqConfig struct {
	Host         string `required:"true"`
	Port         int    `required:"true"`
	ClientPrefix string `default:"wifi_event_dispatcher"`
}

func (n *nanoMqConfig) Url() string {
	return fmt.Sprintf("tcp://%s:%d", n.Host, n.Port)
}
