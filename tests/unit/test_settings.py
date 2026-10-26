from src.core.config import Settings


def test_ollama_settings_from_environment(monkeypatch):
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "qwen3-vl:4b-instruct")
    settings = Settings(_env_file=None)
    assert settings.ollama_base_url == "http://localhost:11434"
    assert settings.ollama_model == "qwen3-vl:4b-instruct"
