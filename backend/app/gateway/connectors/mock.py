"""Mock connector for testing."""

import asyncio
import time
from typing import Any

from app.gateway.connectors.base import ConnectorConfig, ConnectorResult, ToolConnector


class MockConnector(ToolConnector):
    """Mock connector for testing.

    Configuration (in extra):
        response_data: dict to return as data (default: echo params)
        should_fail: bool to simulate failure
        error_code: error code if failing
        error_message: error message if failing
        delay_ms: simulated delay in milliseconds
        status_code: HTTP status code to return

    Example manifest tool config:
        {
            "connector_type": "mock",
            "extra": {
                "response_data": {"status": "ok"},
                "delay_ms": 100
            }
        }
    """

    async def execute(self, params: dict[str, Any]) -> ConnectorResult:
        """Execute the mock connector."""
        start_time = time.monotonic()

        extra = self.config.extra

        # Simulate delay if configured
        delay_ms = extra.get("delay_ms", 0)
        if delay_ms > 0:
            await asyncio.sleep(delay_ms / 1000)

        duration_ms = int((time.monotonic() - start_time) * 1000)

        # Check if we should simulate failure
        if extra.get("should_fail", False):
            return ConnectorResult(
                success=False,
                error={
                    "code": extra.get("error_code", "MOCK_ERROR"),
                    "message": extra.get("error_message", "Mock connector simulated failure"),
                },
                status_code=extra.get("status_code", 500),
                duration_ms=duration_ms,
            )

        # Build response data
        response_data = extra.get("response_data")
        if response_data is None:
            # Default: echo the params back
            response_data = {
                "echo": params,
                "connector": "mock",
                "timestamp": time.time(),
            }

        result = ConnectorResult(
            success=True,
            data=response_data,
            status_code=extra.get("status_code", 200),
            duration_ms=duration_ms,
        )
        result.result_hash = result.compute_hash()
        return result
