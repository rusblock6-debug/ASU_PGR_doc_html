package rabbitmq

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/url"
	"regexp"
	"time"

	"github.com/rs/zerolog"
)

type ManagementClient struct {
	baseURL  string
	user     string
	password string
	vhost    string
	http     *http.Client
	logger   zerolog.Logger
}

func NewManagementClient(cfg Config, logger zerolog.Logger) *ManagementClient {
	return &ManagementClient{
		baseURL:  cfg.ManagementURL(),
		user:     cfg.User,
		password: cfg.Password,
		vhost:    cfg.Vhost,
		http:     &http.Client{Timeout: 10 * time.Second},
		logger:   logger,
	}
}

type queueInfo struct {
	Name string `json:"name"`
}

func (m *ManagementClient) DiscoverQueues(ctx context.Context, nameRegex string) ([]string, error) {
	vhost := url.PathEscape(m.vhost)
	reqURL := fmt.Sprintf("%s/api/queues/%s?name=%s&use_regex=true&columns=name",
		m.baseURL, vhost, url.QueryEscape(nameRegex))

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, reqURL, nil)
	if err != nil {
		return nil, fmt.Errorf("create request: %w", err)
	}
	req.SetBasicAuth(m.user, m.password)

	resp, err := m.http.Do(req)
	if err != nil {
		return nil, fmt.Errorf("list queues: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return nil, fmt.Errorf("list queues: unexpected status code %d", resp.StatusCode)
	}

	var queues []queueInfo
	if err := json.NewDecoder(resp.Body).Decode(&queues); err != nil {
		return nil, fmt.Errorf("list queues: decode response: %w", err)
	}

	re, err := regexp.Compile(nameRegex)
	if err != nil {
		return nil, fmt.Errorf("compile regex %q: %w", nameRegex, err)
	}

	names := make([]string, 0, len(queues))
	for _, q := range queues {
		if re.MatchString(q.Name) {
			names = append(names, q.Name)
		}
	}

	m.logger.Info().
		Str("pattern", nameRegex).
		Int("total_from_api", len(queues)).
		Int("matched", len(names)).
		Strs("queues", names).
		Msg("discovered queues")

	return names, nil
}
