import os

from locust import HttpUser, between, task


class PlatformUser(HttpUser):
    wait_time = between(0.25, 1.0)

    def on_start(self) -> None:
        self.headers = {"X-API-Key": os.environ["LOAD_TEST_API_KEY"]}

    @task(4)
    def grounded_query(self) -> None:
        self.client.post(
            "/v1/ai/query",
            headers=self.headers,
            json={"question": "How should payment timeouts be handled?"},
            name="POST /v1/ai/query",
        )

    @task(3)
    def hybrid_search(self) -> None:
        self.client.post(
            "/v1/ai/search",
            headers=self.headers,
            json={"query": "payment timeout", "limit": 5},
            name="POST /v1/ai/search",
        )

    @task(1)
    def health(self) -> None:
        self.client.get("/health", name="GET /health")
