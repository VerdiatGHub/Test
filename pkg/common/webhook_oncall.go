package common

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"time"

	"github.com/VersusControl/versus-incident/pkg/config"
)

// WebhookOnCallPayload is the JSON body posted to the webhook endpoint
type WebhookOnCallPayload struct {
	IncidentID string `json:"incident_id"`
	Source     string `json:"source"`
	EventType  string `json:"event_type"`
	Message    string `json:"message"`
}

// WebhookOnCallProvider implements OnCallProvider by POSTing to a generic webhook
type WebhookOnCallProvider struct {
	url        string
	httpClient *http.Client
}

// NewWebhookOnCallProvider creates a new generic webhook on-call provider
func NewWebhookOnCallProvider(url string) *WebhookOnCallProvider {
	return &WebhookOnCallProvider{
		url:        url,
		httpClient: &http.Client{Timeout: 10 * time.Second},
	}
}

// TriggerOnCall escalates an incident by POSTing it to the configured webhook URL
func (p *WebhookOnCallProvider) TriggerOnCall(ctx context.Context, incidentID string, cfg *config.OnCallConfig) error {
	url := p.url
	if cfg != nil && cfg.Webhook.URL != "" {
		url = cfg.Webhook.URL
	}

	payload := WebhookOnCallPayload{
		IncidentID: incidentID,
		Source:     "Versus Incident",
		EventType:  "oncall_escalation",
		Message:    "On-call escalation for incident " + incidentID,
	}

	body, err := json.Marshal(payload)
	if err != nil {
		return fmt.Errorf("failed to marshal webhook on-call payload: %v", err)
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, url, bytes.NewBuffer(body))
	if err != nil {
		return fmt.Errorf("failed to create webhook on-call request: %v", err)
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := p.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("failed to send webhook on-call request: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return fmt.Errorf("webhook on-call endpoint returned non-success status: %d", resp.StatusCode)
	}

	log.Printf("Webhook on-call escalated: %s", incidentID)
	return nil
}
