"""Sign-in for the workflow scripts. Reads GLOBUS_TOKENS (JSON from globus_login.py, or that JSON as base64).

Error messages never contain token text.
"""
import base64
import binascii
import json
import os

import globus_sdk


class AuthError(Exception):
    pass


EXPIRED = "Globus login expired or revoked: run globus_login.py again and update the GLOBUS_TOKENS secret"


def _parse(raw: str):
    # plain JSON first, then base64 of that JSON (survives parameter quoting)
    try:
        return json.loads(raw)
    except ValueError:
        pass
    try:
        return json.loads(base64.b64decode(raw.strip(), validate=True).decode())
    except (ValueError, binascii.Error):
        pass
    # only facts about the value, never the value itself
    yn = lambda b: "yes" if b else "no"
    raise AuthError(
        "GLOBUS_TOKENS is not valid JSON or base64 "
        f"(length {len(raw)}, starts with '{{': {yn(raw.startswith('{'))}, "
        f"double quotes: {yn(chr(34) in raw)}): recreate it with globus_login.py"
    )


def load_tokens(env=os.environ) -> dict:
    raw = env.get("GLOBUS_TOKENS")
    if not raw:
        raise AuthError("GLOBUS_TOKENS is not set: create it with globus_login.py")
    tokens = _parse(raw)
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
