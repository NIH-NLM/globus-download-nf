"""Copy a folder from one Globus collection to another with Globus Transfer, and wait for it.

Globus does the copying, retries failed files and verifies checksums. Nothing here
touches a token: the Transfer client comes from auth.transfer_client().
"""
import argparse
import sys
import time

import globus_sdk


class TransferFailed(Exception):
    pass


def submit(client, source, dest, source_path, dest_path, label, recursive=True) -> str:
    tdata = globus_sdk.TransferData(
        source_endpoint=source, destination_endpoint=dest, label=label, verify_checksum=True
    )
    tdata.add_item(source_path, dest_path, recursive=recursive)
    return client.submit_transfer(tdata)["task_id"]


def wait(client, task_id, poll=30, sleep=time.sleep, log=print) -> dict:
    while True:
        t = client.get_task(task_id)
        status = t["status"]
        if status == "SUCCEEDED":
            return t
        if status in ("FAILED", "INACTIVE"):
            raise TransferFailed(f"transfer {task_id} {status}: {t.get('nice_status') or t.get('fatal_error')}")
        log(f"{status}: {t['files_transferred']}/{t['files']} files, {t['bytes_transferred'] / 1e9:.1f} GB")
        sleep(poll)


def main(argv=None, client=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", required=True, help="source collection UUID")
    ap.add_argument("--dest", required=True, help="destination collection UUID (your Globus Connect Personal endpoint)")
    ap.add_argument("--source-path", required=True)
    ap.add_argument("--dest-path", required=True)
    ap.add_argument("--label", default="globus-download-nf")
    ap.add_argument("--file", action="store_true", help="the source path is a single file, not a folder")
    args = ap.parse_args(argv)
    try:
        if client is None:
            import auth

            client = auth.transfer_client()
        tid = submit(client, args.source, args.dest, args.source_path, args.dest_path, args.label, recursive=not args.file)
        print(f"submitted transfer task {tid}", flush=True)
        wait(client, tid)
    except Exception as e:
        print(f"{type(e).__name__}: {e}", file=sys.stderr)
        return 1
    print("transfer succeeded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
