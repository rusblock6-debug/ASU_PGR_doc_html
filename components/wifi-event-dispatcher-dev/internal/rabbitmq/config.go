package rabbitmq

import (
	"fmt"
	"net/url"
	"time"
)

type Config struct {
	Host     string `required:"true"`
	Port     uint16 `required:"true"`
	User     string `required:"true"`
	Password string `required:"true"`
	Vhost    string `default:"/"`

	Exchange       string
	ExchangeType   string // "topic"
	ReconnectMin   time.Duration
	ReconnectMax   time.Duration
	ManagementPort uint16 `default:"15672"`
}

func (c *Config) ManagementURL() string {
	return fmt.Sprintf("http://%s:%d", c.Host, c.ManagementPort)
}

func (c *Config) Url() string {
	vhost := url.PathEscape(c.Vhost)

	return fmt.Sprintf(
		"amqp://%s:%s@%s:%d/%s",
		c.User,
		c.Password,
		c.Host,
		c.Port,
		vhost,
	)
}
