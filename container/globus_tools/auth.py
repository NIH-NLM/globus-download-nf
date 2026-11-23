"""Sign-in for the workflow scripts. Reads GLOBUS_TOKENS (JSON from globus_login.py).

Error messages never contain token text.
"""
import json
import os

import globus_sdk


class AuthError(Exception):
    pass


EXPIRED = "Globus login expired or revoked: run globus_login.py again and update the GLOBUS_TOKENS secret"


def load_tokens(env=os.environ) -> dict:
    raw = env.get("GLOBUS_TOKENS")
    if not raw:
        raise AuthError("GLOBUS_TOKENS is not set: create it with globus_login.py")
    try:
        tokens = json.loads(raw)
    except ValueError:
        raise AuthError("GLOBUS_TOKENS is not valid JSON: recreate it with globus_login.py") from None
    missing = [k for k in ("transfer", "https", "client_id") if not isinstance(tokens, dict) or k not in tokens]
    if missing:
        raise AuthError("GLOBUS_TOKENS is missing: " + ", ".join(missing))
    return tokens


def _authorizer(which: str) -> globus_sdk.RefreshTokenAuthorizer:
    tokens = load_tokens()
    client = globus_sdk.NativeAppAuthClient(tokens["client_id"])
    authorizer = globus_sdk.RefreshTokenAuthorizer(tokens[which], client)
    try:
        authorizer.ensure_valid_token()
    except globus_sdk.GlobusError:
        raise AuthError(EXPIRED) from None
    return authorizer


def transfer_client() -> globus_sdk.TransferClient:
    return globus_sdk.TransferClient(authorizer=_authorizer("transfer"))


def https_authorizer() -> globus_sdk.RefreshTokenAuthorizer:
    return _authorizer("https")
