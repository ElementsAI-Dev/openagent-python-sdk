from app.service import build_client_config


def test_build_client_config_keeps_timeout():
    config = build_client_config({"API_BASE_URL": "https://api.example.com", "API_KEY": "secret"})
    assert config["timeout_ms"] == 5000


def test_build_client_config_omits_empty_api_key():
    config = build_client_config({"API_BASE_URL": "https://api.example.com", "API_KEY": ""})
    assert "api_key" not in config
