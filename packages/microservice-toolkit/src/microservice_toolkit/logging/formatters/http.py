"""Formatação allowlist dos eventos HTTP, sem payloads ou cabeçalhos."""

import json
import logging
from datetime import UTC, datetime


class JsonFormatter(logging.Formatter):
    def format(self, record):
        # Explicit field allowlist avoids serializing request headers, bodies or exceptions.
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "event": "http.request",
            "service": record.service,
            "request_id": record.request_id,
            "method": record.method,
            "route": record.route,
            "status": record.status,
            "duration_ms": record.duration_ms,
        }
        return json.dumps(payload, ensure_ascii=False)
