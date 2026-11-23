import json

import globus_login

COLLECTION = "71c2ad2f-ea02-4d0e-8408-ac50f5af0f7d"


class FakeTokenResponse:
    by_resource_server = {
        "transfer.api.globus.org": {
            "refresh_token": "REFRESH_TRANSFER",
            "access_token": "ACCESS_TRANSFER_SECRET",
        },
        COLLECTION: {
            "refresh_token": "REFRESH_HTTPS",
            "access_token": "ACCESS_HTTPS_SECRET",
        },
    }


def test_build_tokens_json_has_refresh_tokens_only():
    out = globus_login.build_tokens_json(FakeTokenResponse(), "my-client-id", COLLECTION)
    assert json.loads(out) == {
        "transfer": "REFRESH_TRANSFER",
        "https": "REFRESH_HTTPS",
        "client_id": "my-client-id",
    }
    assert "ACCESS_TRANSFER_SECRET" not in out
    assert "ACCESS_HTTPS_SECRET" not in out
