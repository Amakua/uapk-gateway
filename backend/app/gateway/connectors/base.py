"""Abstract base class for tool connectors."""

import hashlib
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ConnectorConfig:
    """Configuration for a connector."""

    connector_type: str
    url: str | None = None
    method: str = "POST"
    headers: dict[str, str] = field(default_factory=dict)
    timeout_seconds: int = 30
    # For secrets - key is the param name, value is the secret name in DB
    secret_refs: dict[str, str] = field(default_factory=dict)
    # Additional connector-specific config
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConnectorResult:
    """Result from a connector execution."""

    success: bool
    data: dict[str, Any] | None = None
    error: dict[str, str] | None = None
    status_code: int | None = None
    duration_ms: int | None = None
    result_hash: str | None = None

    def compute_hash(self) -> str:
        """Compute SHA-256 hash of the result data."""
        if self.data is None:
            return hashlib.sha256(b"null").hexdigest()

        canonical = json.dumps(self.data, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode()).hexdigest()


class ToolConnector(ABC):
    """Abstract base class for tool connectors.

    Connectors execute tools on behalf of agents. Each connector type
    handles a specific execution method (webhook, HTTP request, etc.).
    """

    def __init__(self, config: ConnectorConfig, secrets: dict[str, str] | None = None) -> None:
        """Initialize the connector.

        Args:
            config: Connector configuration
            secrets: Resolved secrets (secret_name -> decrypted_value)
        """
        self.config = config
        self.secrets = secrets or {}

    @abstractmethod
    async def execute(self, params: dict[str, Any]) -> ConnectorResult:
        """Execute the tool with the given parameters.

        Args:
            params: Tool parameters from the action request

        Returns:
            ConnectorResult with success/error status and data
        """
        pass

    def _resolve_param(self, key: str, value: Any) -> Any:
        """Resolve a parameter, substituting secrets if needed."""
        # Check if this param should use a secret
        if key in self.config.secret_refs:
            secret_name = self.config.secret_refs[key]
            if secret_name in self.secrets:
                return self.secrets[secret_name]
        return value

    def _resolve_all_params(self, params: dict[str, Any]) -> dict[str, Any]:
        """Resolve all parameters, substituting secrets."""
        resolved = {}
        for key, value in params.items():
            resolved[key] = self._resolve_param(key, value)
        return resolved

    def _build_headers(self) -> dict[str, str]:
        """Build request headers, resolving any secret refs."""
        headers = dict(self.config.headers)

        # Resolve secret refs in headers
        for header_name, secret_name in self.config.secret_refs.items():
            if header_name.startswith("header:"):
                actual_header = header_name[7:]  # Remove "header:" prefix
                if secret_name in self.secrets:
                    headers[actual_header] = self.secrets[secret_name]

        return headers
