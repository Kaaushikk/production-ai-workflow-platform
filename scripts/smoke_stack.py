import http.client
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import func, select

from platform_api.config import get_settings
from platform_api.database import build_engine, build_session_factory
from platform_api.models import OutboxEvent, ProcessedEvent


def request(method: str, path: str, body: bytes, content_type: str) -> tuple[int, bytes]:
    connection = http.client.HTTPConnection("localhost", 8000, timeout=10)
    connection.request(
        method,
        path,
        body=body,
        headers={
            "X-API-Key": os.environ["SMOKE_API_KEY"],
            "Content-Type": content_type,
        },
    )
    response = connection.getresponse()
    payload = response.read()
    connection.close()
    return response.status, payload


def upload_document() -> None:
    boundary = "platform-smoke-boundary"
    body = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="file"; filename="policy.txt"\r\n'
        "Content-Type: text/plain\r\n\r\n"
        "Payment timeouts require retrying after five minutes.\r\n"
        f"--{boundary}--\r\n"
    ).encode()
    status, payload = request(
        "POST", "/v1/documents", body, f"multipart/form-data; boundary={boundary}"
    )
    if status != 201:
        raise RuntimeError(f"Upload failed with {status}: {payload.decode()}")


def query_once() -> None:
    body = json.dumps({"question": "How should payment timeouts be handled?"}).encode()
    status, payload = request("POST", "/v1/ai/query", body, "application/json")
    if status != 200 or not json.loads(payload)["citations"]:
        raise RuntimeError(f"Query failed with {status}: {payload.decode()}")


def wait_for_events(expected: int) -> None:
    factory = build_session_factory(build_engine(get_settings()))
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        with factory() as session:
            published = session.scalar(
                select(func.count()).select_from(OutboxEvent).where(
                    OutboxEvent.published_at.is_not(None)
                )
            )
            processed = session.scalar(select(func.count()).select_from(ProcessedEvent))
        if (published or 0) >= expected and (processed or 0) >= expected:
            return
        time.sleep(0.5)
    raise RuntimeError("Timed out waiting for outbox publication and event processing")


def main() -> None:
    upload_document()
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda _: query_once(), range(8)))
    wait_for_events(9)
    print("Full-stack smoke passed: API, outbox, Kafka, and idempotent consumer")


if __name__ == "__main__":
    main()
