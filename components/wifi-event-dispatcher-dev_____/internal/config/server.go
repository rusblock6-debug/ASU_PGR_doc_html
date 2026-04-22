package config

import (
	"fmt"
)

type ServerConfig struct {
	Rpc serverRpcConfig
}

type serverRpcConfig struct {
	Host string `default:"0.0.0.0"`
	Port string `default:":8085"`
}

func (c serverRpcConfig) Address() string {
	return fmt.Sprintf("%s%s", c.Host, c.Port)
}
