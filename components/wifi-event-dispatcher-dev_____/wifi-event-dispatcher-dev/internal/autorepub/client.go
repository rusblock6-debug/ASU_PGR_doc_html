package autorepub

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"time"

	"github.com/rs/zerolog"
)

type Client struct {
	coordinationURL    string
	DistributionURLFor func(host string) string
	httpClient         *http.Client
	logger             zerolog.Logger
}

func NewClient(coordinationURL, distributionPort string, timeout time.Duration, logger zerolog.Logger) *Client {
	return &Client{
		coordinationURL: coordinationURL,
		DistributionURLFor: func(host string) string {
			return fmt.Sprintf("http://%s:%s", host, distributionPort)
		},
		httpClient: &http.Client{
			Timeout: timeout,
		},
		logger: logger,
	}
}

type distributionResponse struct {
	Distribution map[string][]int `json:"distribution"`
}

func (c *Client) GetDistribution(ctx context.Context) (map[string][]int, error) {
	url := c.coordinationURL + "/coordination/distribution"

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
	if err != nil {
		return nil, fmt.Errorf("create request: %w", err)
	}

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("get distribution: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		c.logger.Error().Int("status_code", resp.StatusCode).Msg("get distribution: non-2xx response")
		return nil, fmt.Errorf("get distribution: unexpected status code %d", resp.StatusCode)
	}

	var result distributionResponse
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("get distribution: decode response: %w", err)
	}

	return result.Distribution, nil
}

type autorepubRequest struct {
	VehicleIDs []int `json:"vehicle_ids"`
}

func (c *Client) Suspend(ctx context.Context, distribution map[string][]int) error {
	return c.broadcastVehicleIDs(ctx, "/autorepub/suspend", distribution)
}

func (c *Client) Resume(ctx context.Context, distribution map[string][]int) error {
	return c.broadcastVehicleIDs(ctx, "/autorepub/resume", distribution)
}

func (c *Client) SuspendDirect(ctx context.Context, vehicleIDs []int) error {
	return c.postVehicleIDs(ctx, c.coordinationURL, "/autorepub/suspend", vehicleIDs)
}

func (c *Client) ResumeDirect(ctx context.Context, vehicleIDs []int) error {
	return c.postVehicleIDs(ctx, c.coordinationURL, "/autorepub/resume", vehicleIDs)
}

func (c *Client) broadcastVehicleIDs(ctx context.Context, path string, distribution map[string][]int) error {
	var errs []error
	for host, vehicleIDs := range distribution {
		baseURL := c.DistributionURLFor(host)
		if err := c.postVehicleIDs(ctx, baseURL, path, vehicleIDs); err != nil {
			errs = append(errs, err)
		}
	}
	return errors.Join(errs...)
}

func (c *Client) postVehicleIDs(ctx context.Context, baseURL, path string, vehicleIDs []int) error {
	body, err := json.Marshal(autorepubRequest{VehicleIDs: vehicleIDs})
	if err != nil {
		return fmt.Errorf("%s: marshal request: %w", path, err)
	}

	url := baseURL + path

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, url, bytes.NewReader(body))
	if err != nil {
		return fmt.Errorf("%s: create request: %w", path, err)
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("%s: %w", path, err)
	}
	defer resp.Body.Close()

	c.logger.Info().
		Str("url", url).
		Ints("vehicle_ids", vehicleIDs).
		Int("status_code", resp.StatusCode).
		Msg("autorepub request")

	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return fmt.Errorf("%s: unexpected status code %d", path, resp.StatusCode)
	}

	return nil
}
