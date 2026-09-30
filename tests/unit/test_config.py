from platform_api.config import Settings


def test_default_settings_are_safe_for_local_development() -> None:
    settings = Settings(_env_file=None)

    assert settings.env == "development"
    assert settings.api_port == 8000
    assert settings.database_url.startswith("postgresql+psycopg://")


def test_environment_values_are_validated(monkeypatch: object) -> None:
    monkeypatch.setenv("APP_API_PORT", "9000")  # type: ignore[attr-defined]

    settings = Settings(_env_file=None)

    assert settings.api_port == 9000

