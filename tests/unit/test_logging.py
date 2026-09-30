import json
import logging

from platform_api.logging import JsonFormatter


def test_json_formatter_emits_machine_readable_fields() -> None:
    record = logging.LogRecord("test", logging.INFO, __file__, 10, "hello", (), None)

    payload = json.loads(JsonFormatter().format(record))

    assert payload["level"] == "INFO"
    assert payload["logger"] == "test"
    assert payload["message"] == "hello"
    assert payload["timestamp"].endswith("+00:00")

