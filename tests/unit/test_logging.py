import json
import logging

from opentelemetry import trace
from opentelemetry.trace import NonRecordingSpan, SpanContext, TraceFlags

from platform_api.logging import JsonFormatter


def test_json_formatter_emits_machine_readable_fields() -> None:
    record = logging.LogRecord("test", logging.INFO, __file__, 10, "hello", (), None)

    payload = json.loads(JsonFormatter().format(record))

    assert payload["level"] == "INFO"
    assert payload["logger"] == "test"
    assert payload["message"] == "hello"
    assert payload["timestamp"].endswith("+00:00")


def test_json_formatter_includes_active_trace_correlation() -> None:
    context = SpanContext(
        trace_id=0x1234,
        span_id=0x5678,
        is_remote=False,
        trace_flags=TraceFlags(TraceFlags.SAMPLED),
    )
    record = logging.LogRecord("test", logging.INFO, __file__, 10, "traced", (), None)

    with trace.use_span(NonRecordingSpan(context)):
        payload = json.loads(JsonFormatter().format(record))

    assert payload["trace_id"].endswith("1234")
    assert payload["span_id"].endswith("5678")

