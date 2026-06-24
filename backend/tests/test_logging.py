"""Logging tests."""

import json
import logging

from techbrain.core.context import request_id_context
from techbrain.core.logging import ContextFilter, JsonFormatter


def test_json_formatter_includes_context_and_extra_fields() -> None:
    token = request_id_context.set("logging-test")
    try:
        record = logging.LogRecord(
            name="techbrain.test",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="test.event",
            args=(),
            exc_info=None,
        )
        record.duration_ms = 12.5
        ContextFilter().filter(record)

        payload = json.loads(JsonFormatter().format(record))
    finally:
        request_id_context.reset(token)

    assert payload["event"] == "test.event"
    assert payload["level"] == "INFO"
    assert payload["logger"] == "techbrain.test"
    assert payload["request_id"] == "logging-test"
    assert payload["duration_ms"] == 12.5
