"""List every file under the given paths of a Globus collection, recursively.

Writes one JSON file: {"collection", "https_server", "files": [{"path", "size"}]}.
Paths in the output are relative to the collection root, with no leading slash.
"""
import argparse
import json
import os
import sys

import globus_sdk

PAGE = 1000


def normalize_path(p: str) -> str:
    return p.strip().strip("/")


def _ls_all(client, collection: str, path: str) -> list:
    entries, offset = [], 0
    while True:
        resp = client.operation_ls(
            collection, path="/" + path, limit=PAGE, offset=offset, orderby="name"
        )
        data = resp["DATA"]
        entries.extend(data)
        offset += len(data)
        if not data or offset >= resp["total"]:
            return entries


def list_files(client, collection: str, path: str) -> list:
    path = normalize_path(path)
    files = []
    for e in _ls_all(client, collection, path):
        rel = f"{path}/{e['name']}" if path else e["name"]
        if e["type"] == "dir":
            files.extend(list_files(client, collection, rel))
        else:
            files.append({"path": rel, "size": e["size"]})
    return files


def main(argv=None, client=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--collection", required=True)
    ap.add_argument("--paths", default="/", help="comma separated; default /")
    ap.add_argument("--out", default="listing.json")
    args = ap.parse_args(argv)

    try:
        if client is None:
            import auth

            client = auth.transfer_client()
        https_server = client.get_endpoint(args.collection)["https_server"]
        if not https_server:
            print(
                "this collection has no HTTPS access (https_server is empty): "
                "ask the collection's owner to enable HTTPS",
                file=sys.stderr,
            )
            return 1
        seen = {}
        for p in args.paths.split(","):
            for item in list_files(client, args.collection, p):
                seen[item["path"]] = item
    except Exception as e:  # any failure means no listing: never write a partial one
        print(f"listing failed: {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    with open(args.out, "w") as fh:
        json.dump(
            {
                "collection": args.collection,
                "https_server": https_server,
                "files": list(seen.values()),
            },
            fh,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
