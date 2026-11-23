"""Campos permitidos no evento de erro, separados do log de acesso."""

import json
import logging
from datetime import UTC, datetime


class ErrorJsonFormatter(logging.Formatter):
    def format(self, record):
        fields = (
            "service",
            "request_id",
            "method",
            "route",
            "status",
            "code",
            "exception_type",
            "traceback",
        )
        return json.dumps(
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "level": record.levelname,
                "event": "http.error",
                "message": getattr(record, "exception_message", None),
                **{key: getattr(record, key, None) for key in fields},
            },
            ensure_ascii=False,
        )
