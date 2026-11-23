"""One-time login helper. Run it in a Jupyter terminal, not in the workflow.

It prints a login URL, you sign in (choose NIH and use your PIV card), paste
the code Globus shows you, and it prints one JSON line of refresh tokens.
Save that line as the Lifebit secret GLOBUS_TOKENS. Nothing else is printed
to stdout, and access tokens are never printed.
"""
import argparse
import json
import sys

import globus_sdk

TRANSFER_RESOURCE_SERVER = "transfer.api.globus.org"


def build_tokens_json(token_response, client_id: str, collection: str) -> str:
    by_server = token_response.by_resource_server
    return json.dumps(
        {
            "transfer": by_server[TRANSFER_RESOURCE_SERVER]["refresh_token"],
            "https": by_server[collection]["refresh_token"],
            "client_id": client_id,
        }
    )


def requested_scopes(collection: str, data_access: bool) -> list:
    https_scope = f"https://auth.globus.org/scopes/{collection}/https"
    transfer_scope = "urn:globus:auth:scope:transfer.api.globus.org:all"
    if data_access:
        transfer_scope += f"[*https://auth.globus.org/scopes/{collection}/data_access]"
    return [transfer_scope, https_scope]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--client-id", required=True, help="Globus native app client ID")
    ap.add_argument("--collection", required=True, help="Globus collection UUID")
    ap.add_argument(
        "--data-access",
        action="store_true",
        help="also request data_access (only if the collection needs it)",
    )
    args = ap.parse_args(argv)

    client = globus_sdk.NativeAppAuthClient(args.client_id)
    client.oauth2_start_flow(
        requested_scopes(args.collection, args.data_access), refresh_tokens=True
    )
    sys.stderr.write("Open this URL, sign in, and copy the code:\n")
    sys.stderr.write(client.oauth2_get_authorize_url() + "\n")
    sys.stderr.write("Paste the code here: ")
    sys.stderr.flush()
    code = sys.stdin.readline().strip()
    tokens = client.oauth2_exchange_code_for_tokens(code)
    print(build_tokens_json(tokens, args.client_id, args.collection))
    return 0


if __name__ == "__main__":
    sys.exit(main())
