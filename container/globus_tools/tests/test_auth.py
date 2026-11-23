import json

import globus_sdk
import pytest

import auth

SECRET = "SECRET123"
GOOD = json.dumps({"transfer": SECRET + "T", "https": SECRET + "H", "client_id": "cid"})


def test_missing_env_raises_clear_error():
    with pytest.raises(auth.AuthError) as e:
        auth.load_tokens({})
    assert "GLOBUS_TOKENS" in str(e.value)


def test_bad_json_raises_clear_error():
    with pytest.raises(auth.AuthError) as e:
        auth.load_tokens({"GLOBUS_TOKENS": "not json " + SECRET})
    assert SECRET not in str(e.value)


def test_missing_keys_raises_clear_error():
    with pytest.raises(auth.AuthError) as e:
        auth.load_tokens({"GLOBUS_TOKENS": json.dumps({"transfer": SECRET})})
    assert SECRET not in str(e.value)
    assert "https" in str(e.value)


def test_load_tokens_returns_dict():
    assert auth.load_tokens({"GLOBUS_TOKENS": GOOD})["client_id"] == "cid"


def test_expired_token_gives_clear_error_without_token(monkeypatch, capsys):
    class Expired:
        def __init__(self, refresh_token, auth_client, **kw):
            pass

        def ensure_valid_token(self):
            raise globus_sdk.GlobusError("invalid refresh token " + SECRET + "T")

    monkeypatch.setattr(auth.globus_sdk, "RefreshTokenAuthorizer", Expired)
    monkeypatch.setenv("GLOBUS_TOKENS", GOOD)
    for fn in (auth.transfer_client, auth.https_authorizer):
        with pytest.raises(auth.AuthError) as e:
            fn()
        assert SECRET not in str(e.value)
        assert "globus_login.py" in str(e.value)
    captured = capsys.readouterr()
    assert SECRET not in captured.out + captured.err


def test_base64_encoded_json_is_accepted():
    import base64

    enc = base64.b64encode(GOOD.encode()).decode()
    assert auth.load_tokens({"GLOBUS_TOKENS": enc})["transfer"] == SECRET + "T"


def test_bad_value_error_reports_safe_facts_only():
    with pytest.raises(auth.AuthError) as e:
        auth.load_tokens({"GLOBUS_TOKENS": "{{GLOBUS_TOKENS}}"})
    msg = str(e.value)
    assert "length 17" in msg
    assert "starts with '{': yes" in msg
    assert "double quotes: no" in msg
    assert "GLOBUS_TOKENS}}" not in msg


def test_stripped_quotes_error_does_not_leak_token():
    with pytest.raises(auth.AuthError) as e:
        auth.load_tokens({"GLOBUS_TOKENS": "{transfer:" + SECRET + "}"})
    assert SECRET not in str(e.value)
    assert "double quotes: no" in str(e.value)
