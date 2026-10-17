from config.settings import email_settings_from_env


def test_console_backend_when_no_email_host():
    settings = email_settings_from_env({})
    assert settings["EMAIL_BACKEND"] == "django.core.mail.backends.console.EmailBackend"


def test_smtp_backend_when_email_host_set():
    settings = email_settings_from_env(
        {
            "EMAIL_HOST": "sandbox.smtp.mailtrap.io",
            "EMAIL_HOST_USER": "u",
            "EMAIL_HOST_PASSWORD": "p",
        }
    )
    assert settings["EMAIL_BACKEND"] == "django.core.mail.backends.smtp.EmailBackend"
    assert settings["EMAIL_HOST"] == "sandbox.smtp.mailtrap.io"
    assert settings["EMAIL_PORT"] == 2525
    assert settings["EMAIL_USE_TLS"] is True
