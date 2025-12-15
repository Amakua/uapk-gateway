"""Webhook connector - POST to configured URL."""

import time
from typing import Any

import httpx

from app.gateway.connectors.base import ConnectorConfig, ConnectorResult, ToolConnector


class WebhookConnector(ToolConnector):
    """Connector that POSTs to a configured webhook URL.

    Configuration:
        url: The webhook URL to POST to
        headers: Optional headers to include
        timeout_seconds: Request timeout (default 30s)
        secret_refs: Map of header names to secret names for auth

    No retries are performed (retries=0 as per spec).
    """

    def __init__(self, config: ConnectorConfig, secrets: dict[str, str] | None = None) -> None:
        super().__init__(config, secrets)
        if not config.url:
            raise ValueError("WebhookConnector requires a 'url' in config")

    async def execute(self, params: dict[str, Any]) -> ConnectorResult:
        """Execute the webhook by POSTing params to the configured URL."""
        start_time = time.monotonic()

        url = self.config.url
        headers = self._build_headers()
        headers.setdefault("Content-Type", "application/json")
        timeout = self.config.timeout_seconds

        # Resolve any secrets in params
        resolved_params = self._resolve_all_params(params)

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    url,
                    json=resolved_params,
                    headers=headers,
                )

            duration_ms = int((time.monotonic() - start_time) * 1000)

            if response.status_code >= 200 and response.status_code < 300:
                try:
                    data = response.json()
                except Exception:
                    data = {"raw_response": response.text}

                result = ConnectorResult(
                    success=True,
                    data=data,
                    status_code=response.status_code,
                    duration_ms=duration_ms,
                )
                result.result_hash = result.compute_hash()
                return result
            else:
                return ConnectorResult(
                    success=False,
                    error={
                        "code": f"HTTP_{response.status_code}",
                        "message": f"Webhook returned status {response.status_code}",
                    },
                    status_code=response.status_code,
                    duration_ms=duration_ms,
                )

        except httpx.TimeoutException:
            duration_ms = int((time.monotonic() - start_time) * 1000)
            return ConnectorResult(
                success=False,
                error={
                    "code": "TIMEOUT",
                    "message": f"Webhook request timed out after {timeout}s",
                },
                duration_ms=duration_ms,
            )

        except httpx.RequestError as e:
            duration_ms = int((time.monotonic() - start_time) * 1000)
            return ConnectorResult(
                success=False,
                error={
                    "code": "REQUEST_ERROR",
                    "message": str(e),
                },
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = int((time.monotonic() - start_time) * 1000)
            return ConnectorResult(
                success=False,
                error={
                    "code": "UNKNOWN_ERROR",
                    "message": str(e),
                },
                duration_ms=duration_ms,
            )
