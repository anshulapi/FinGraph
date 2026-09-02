import pytest

from app.config import ConfigurationError, Settings


def test_settings_loads_test_mode_credentials(monkeypatch):
    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_test_example")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "test-secret")

    settings = Settings.from_environment()

    assert settings.razorpay_key_id == "rzp_test_example"
    assert settings.razorpay_key_secret == "test-secret"


def test_settings_rejects_missing_credentials(monkeypatch):
    monkeypatch.delenv("RAZORPAY_KEY_ID", raising=False)
    monkeypatch.delenv("RAZORPAY_KEY_SECRET", raising=False)

    with pytest.raises(ConfigurationError, match="not configured"):
        Settings.from_environment()


def test_settings_rejects_live_mode_key(monkeypatch):
    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_live_example")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "test-secret")

    with pytest.raises(ConfigurationError, match="Test Mode"):
        Settings.from_environment()
