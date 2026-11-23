import hashlib
import json

import md5_verify


def md5(b):
    return hashlib.md5(b).hexdigest()


def make(tmp_path, folder, files, md5_lines):
    d = tmp_path / folder
    d.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        (d / name).write_bytes(data)
    (d / "fastq_md5sum.txt").write_text("\n".join(md5_lines) + "\n")
    return d / "fastq_md5sum.txt"


def test_matching_files_ok(tmp_path):
    m = make(tmp_path, "A", {"x.gz": b"one", "y.gz": b"two"},
             [f"{md5(b'one')}  x.gz", f"{md5(b'two')}  y.gz"])
    res = md5_verify.verify_folder(str(m))
    assert [r["ok"] for r in res] == [True, True]


def test_binary_marker_and_dot_slash_prefix(tmp_path):
    m = make(tmp_path, "A", {"x.gz": b"one"}, [f"{md5(b'one')} *./x.gz"])
    assert md5_verify.verify_folder(str(m))[0]["ok"] is True


def test_mismatch_reported_and_exit_nonzero(tmp_path):
    make(tmp_path, "A", {"x.gz": b"one"}, [f"{md5(b'WRONG')}  x.gz"])
    out = tmp_path / "r.json"
    rc = md5_verify.main(["--root", str(tmp_path), "--out", str(out)])
    assert rc != 0
    rep = json.loads(out.read_text())
    assert rep[0]["ok"] is False and rep[0]["actual"] == md5(b"one")


def test_missing_file_reported_and_exit_nonzero(tmp_path):
    make(tmp_path, "A", {}, [f"{md5(b'one')}  gone.gz"])
    out = tmp_path / "r.json"
    assert md5_verify.main(["--root", str(tmp_path), "--out", str(out)]) != 0
    assert json.loads(out.read_text())[0]["actual"] is None


def test_malformed_line_fails_not_skipped(tmp_path):
    make(tmp_path, "A", {"x.gz": b"one"}, ["this is not an md5 line"])
    out = tmp_path / "r.json"
    assert md5_verify.main(["--root", str(tmp_path), "--out", str(out)]) != 0


def test_folder_without_md5_file_is_skipped(tmp_path):
    (tmp_path / "B").mkdir()
    (tmp_path / "B" / "x.gz").write_bytes(b"one")
    out = tmp_path / "r.json"
    assert md5_verify.main(["--root", str(tmp_path), "--out", str(out)]) == 0
    assert json.loads(out.read_text()) == []
