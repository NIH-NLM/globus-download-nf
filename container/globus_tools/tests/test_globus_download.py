import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote

import pytest

import globus_download

TOKEN = "TOKEN_SECRET_XYZ"


class Auth:
    def get_authorization_header(self):
        return f"Bearer {TOKEN}"


class Server:
    def __init__(self, files):
        self.files = files  # path -> bytes
        self.ranges = []  # Range headers seen
        self.requests = 0
        self.fail_first = 0  # answer 500 this many times first
        self.status = None  # force a status for every request
        self.truncate_to = None  # serve fewer bytes than the file has
        outer = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                outer.requests += 1
                if outer.status:
                    self.send_response(outer.status)
                    self.end_headers()
                    return
                if outer.fail_first > 0:
                    outer.fail_first -= 1
                    self.send_response(500)
                    self.end_headers()
                    return
                if self.headers.get("Authorization") != f"Bearer {TOKEN}":
                    self.send_response(401)
                    self.end_headers()
                    return
                data = outer.files[unquote(self.path.lstrip("/"))]
                rng = self.headers.get("Range")
                start = 0
                if rng:
                    outer.ranges.append(rng)
                    start = int(rng.split("=")[1].rstrip("-"))
                body = data[start:]
                if outer.truncate_to is not None:
                    body = data[: outer.truncate_to][start:]
                self.send_response(206 if rng else 200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self):
        self.httpd.shutdown()


@pytest.fixture
def server():
    made = []

    def make(files):
        s = Server(files)
        made.append(s)
        return s

    yield make
    for s in made:
        s.close()


def dl(srv, path, data, out, **kw):
    return globus_download.download_file(
        srv.url, path, len(data), str(out), Auth(), backoff=0, **kw
    )


def test_downloads_file_with_folder_structure(server, tmp_path):
    data = b"hello world"
    srv = server({"Keiji/a.fastq.gz": data})
    got = dl(srv, "Keiji/a.fastq.gz", data, tmp_path)
    assert got == str(tmp_path / "Keiji" / "a.fastq.gz")
    assert open(got, "rb").read() == data
    assert not os.path.exists(got + ".part")


def test_same_name_in_two_folders_not_overwritten(server, tmp_path):
    srv = server({"A/fastq_md5sum.txt": b"aaa", "B/fastq_md5sum.txt": b"bbbb"})
    dl(srv, "A/fastq_md5sum.txt", b"aaa", tmp_path)
    dl(srv, "B/fastq_md5sum.txt", b"bbbb", tmp_path)
    assert (tmp_path / "A" / "fastq_md5sum.txt").read_bytes() == b"aaa"
    assert (tmp_path / "B" / "fastq_md5sum.txt").read_bytes() == b"bbbb"


def test_name_with_spaces_and_unicode(server, tmp_path):
    p = "dir one/naïve file #1.txt"
    srv = server({p: b"xyz"})
    dl(srv, p, b"xyz", tmp_path)
    assert (tmp_path / p).read_bytes() == b"xyz"


def test_resume_from_part_file(server, tmp_path):
    data = b"0123456789"
    srv = server({"f.bin": data})
    part = tmp_path / "f.bin.part"
    part.write_bytes(data[:4])
    dl(srv, "f.bin", data, tmp_path)
    assert srv.ranges == ["bytes=4-"]
    assert (tmp_path / "f.bin").read_bytes() == data
    assert not part.exists()


def test_final_file_never_exists_when_size_wrong(server, tmp_path):
    data = b"0123456789"
    srv = server({"f.bin": data})
    srv.truncate_to = 6
    with pytest.raises(globus_download.DownloadError):
        dl(srv, "f.bin", data, tmp_path)
    assert not (tmp_path / "f.bin").exists()


def test_retries_then_raises_after_three_failures(server, tmp_path):
    srv = server({"f.bin": b"x"})
    srv.status = 500
    with pytest.raises(globus_download.DownloadError):
        dl(srv, "f.bin", b"x", tmp_path)
    assert srv.requests == 3


def test_recovers_after_a_transient_failure(server, tmp_path):
    srv = server({"f.bin": b"data"})
    srv.fail_first = 1
    dl(srv, "f.bin", b"data", tmp_path)
    assert (tmp_path / "f.bin").read_bytes() == b"data"


def test_token_not_in_error_output(server, tmp_path):
    srv = server({"f.bin": b"x"})
    srv.status = 401
    with pytest.raises(globus_download.DownloadError) as e:
        dl(srv, "f.bin", b"x", tmp_path)
    assert TOKEN not in str(e.value)


def test_rejects_path_traversal(server, tmp_path):
    srv = server({"../evil": b"x"})
    with pytest.raises(globus_download.DownloadError):
        dl(srv, "../evil", b"x", tmp_path)
    assert srv.requests == 0


def test_zero_byte_file_downloads(server, tmp_path):
    srv = server({"empty.txt": b""})
    got = dl(srv, "empty.txt", b"", tmp_path)
    assert os.path.getsize(got) == 0
    assert not os.path.exists(got + ".part")
