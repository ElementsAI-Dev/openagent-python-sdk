"""Network allowlist execution policy."""

from __future__ import annotations

import fnmatch
from typing import Any
from urllib.parse import urlparse

from pydantic import BaseModel, Field

from openagents.interfaces.tool import (
    ExecutionPolicyPlugin,
    PolicyDecision,
    ToolExecutionRequest,
)


_PRIVATE_PREFIXES = ("127.", "10.", "192.168.", "::1", "localhost")


def _is_private(host: str) -> bool:
    h = host.lower()
    if h in {"localhost", "::1"}:
        return True
    if any(h.startswith(p) for p in _PRIVATE_PREFIXES):
        return True
    if h.startswith("172."):
        parts = h.split(".")
        if len(parts) >= 2 and parts[1].isdigit() and 16 <= int(parts[1]) <= 31:
            return True
    return False


class NetworkAllowlistExecutionPolicy(ExecutionPolicyPlugin):
    """Allowlist host/scheme for network-flavored tools (e.g. ``http_request``)."""

    class Config(BaseModel):
        allow_hosts: list[str] = Field(default_factory=list)
        allow_schemes: list[str] = Field(default_factory=lambda: ["http", "https"])
        applies_to_tools: list[str] = Field(default_factory=lambda: ["http_request"])
        deny_private_networks: bool = True

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config=config or {}, capabilities=set())
        cfg = self.Config.model_validate(self.config)
        self._allow_hosts = [h.lower() for h in cfg.allow_hosts]
        self._allow_schemes = {s.lower() for s in cfg.allow_schemes}
        self._applies = set(cfg.applies_to_tools)
        self._deny_private = cfg.deny_private_networks

    def _host_allowed(self, host: str) -> bool:
        if not self._allow_hosts:
            return False
        for pattern in self._allow_hosts:
            if fnmatch.fnmatchcase(host, pattern):
                return True
        return False

    async def evaluate(self, request: ToolExecutionRequest) -> PolicyDecision:
        if request.tool_id not in self._applies:
            return PolicyDecision(allowed=True, metadata={"policy": "network_allowlist", "skipped": True})
        url = (request.params or {}).get("url", "")
        if not isinstance(url, str) or not url.strip():
            return PolicyDecision(allowed=False, reason="unparseable URL: empty", metadata={"policy": "network_allowlist"})
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        scheme = (parsed.scheme or "").lower()
        if not host:
            return PolicyDecision(allowed=False, reason="unparseable URL: missing host", metadata={"policy": "network_allowlist"})
        meta = {"policy": "network_allowlist", "host": host, "scheme": scheme}
        if scheme not in self._allow_schemes:
            return PolicyDecision(allowed=False, reason=f"scheme '{scheme}' not allowed", metadata=meta)
        if self._deny_private and _is_private(host):
            return PolicyDecision(allowed=False, reason=f"private network '{host}' denied", metadata=meta)
        if not self._host_allowed(host):
            return PolicyDecision(allowed=False, reason=f"host '{host}' not in allow_hosts", metadata=meta)
        return PolicyDecision(allowed=True, metadata=meta)
