"""Verify files against every fastq_md5sum.txt found under a folder.

Writes a JSON report (a list of {folder, file, expected, actual, ok}) and exits
non-zero if anything does not match, is missing, or cannot be read. Never deletes data.
"""
import argparse
import hashlib
import json
import os
import re
import sys

MD5_NAME = "fastq_md5sum.txt"
LINE = re.compile(r"^([0-9a-fA-F]{32})\s+\*?(.+)$")


def _md5_of(path: str):
    if not os.path.isfile(path):
        return None
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_folder(md5_file: str) -> list:
    folder = os.path.dirname(md5_file)
    results = []
    with open(md5_file) as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            m = LINE.match(line)
            if not m:
                results.append({"folder": folder, "file": line, "expected": None,
                                "actual": None, "ok": False, "error": "malformed line"})
                continue
            expected, name = m.group(1).lower(), m.group(2)
            if name.startswith("./"):
                name = name[2:]
            actual = _md5_of(os.path.join(folder, name))
            results.append({"folder": folder, "file": name, "expected": expected,
                            "actual": actual, "ok": actual == expected})
    return results


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", required=True)
    ap.add_argument("--out", default="md5_report.json")
    args = ap.parse_args(argv)
    report = []
    for dirpath, _, names in os.walk(args.root):
        if MD5_NAME in names:
            report.extend(verify_folder(os.path.join(dirpath, MD5_NAME)))
    with open(args.out, "w") as fh:
        json.dump(report, fh, indent=1)
    bad = [r for r in report if not r["ok"]]
    for r in bad:
        print(f"MD5 problem: {r['folder']}/{r['file']}", file=sys.stderr)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
