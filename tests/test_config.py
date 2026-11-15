from backend.config import Settings


def test_frontend_can_start_without_service_credentials(monkeypatch):
    for key in (
        "APP_ENV", "LOG_LEVEL", "FIREBASE_PROJECT_ID",
        "FIREBASE_SERVICE_ACCOUNT_JSON", "LLM_API_KEY", "LLM_MODEL",
    ):
        monkeypatch.delenv(key, raising=False)

    settings = Settings(_env_file=None)

    assert settings.app_env == "development"
    assert settings.firebase_service_account_json is None
    assert settings.llm_api_key is None


def test_environment_overrides_dotenv_and_secrets_are_redacted(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("APP_ENV=development\nLLM_API_KEY=test-only-placeholder\n")
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.delenv("LLM_API_KEY", raising=False)

    settings = Settings(_env_file=env_file)

    assert settings.app_env == "test"
    assert settings.llm_api_key.get_secret_value() == "test-only-placeholder"
    assert "test-only-placeholder" not in repr(settings)
