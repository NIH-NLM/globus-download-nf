"""Download one file from a Globus collection over HTTPS.

Writes to <out>/<path>.part and renames to <out>/<path> only when the size
matches the listing. A partial .part file is resumed with an HTTP Range request.
Error messages never contain the token.
"""
import argparse
import os
import sys
import time
from urllib.parse import quote

import requests


class DownloadError(Exception):
    pass


def _safe_target(out_root: str, path: str) -> str:
    parts = path.split("/")
    if path.startswith("/") or ".." in parts:
        raise DownloadError(f"refusing unsafe path: {path}")
    return os.path.join(out_root, *parts)


def _attempt(url: str, target: str, size: int, authorizer) -> None:
    part = target + ".part"
    have = os.path.getsize(part) if os.path.exists(part) else 0
    if have > size:
        os.remove(part)
        have = 0
    if have < size:
        headers = {"Authorization": authorizer.get_authorization_header()}
        if have:
            headers["Range"] = f"bytes={have}-"
        with requests.get(url, headers=headers, stream=True, timeout=(30, 300)) as r:
            if r.status_code not in (200, 206):
                raise DownloadError(f"HTTP {r.status_code}")
            mode = "ab" if (have and r.status_code == 206) else "wb"
            with open(part, mode) as fh:
                for chunk in r.iter_content(1 << 20):
                    fh.write(chunk)
    if not os.path.exists(part):  # an empty file: nothing to fetch, but it must still exist
        open(part, "wb").close()
    got = os.path.getsize(part)
    if got != size:
        if got > size:
            os.remove(part)
        raise DownloadError(f"size {got} does not match expected {size}")
    os.replace(part, target)


def download_file(https_server, path, size, out_root, authorizer, retries=3, backoff=2.0) -> str:
    target = _safe_target(out_root, path)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    url = f"{https_server.rstrip('/')}/{quote(path)}"
    last = ""
    for attempt in range(retries):
        try:
            _attempt(url, target, size, authorizer)
            return target
        except DownloadError as e:
            last = str(e)
        except requests.RequestException as e:
            last = type(e).__name__
        time.sleep(backoff * attempt)
    raise DownloadError(f"download failed for {path}: {last}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--https-server", required=True)
    ap.add_argument("--path", required=True)
    ap.add_argument("--size", required=True, type=int)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    try:
        import auth

        download_file(args.https_server, args.path, args.size, args.out, auth.https_authorizer())
    except Exception as e:
        print(f"{e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
