import pytest

import globus_transfer

SRC = "00000000-0000-0000-0000-000000000001"
DST = "00000000-0000-0000-0000-000000000002"


class FakeClient:
    """Fake Transfer client: get_task answers from a script of task dicts."""

    def __init__(self, statuses):
        self.statuses = list(statuses)
        self.submitted = None

    def submit_transfer(self, tdata):
        self.submitted = dict(tdata)
        return {"task_id": "task-1"}

    def get_task(self, task_id):
        assert task_id == "task-1"
        return self.statuses.pop(0) if len(self.statuses) > 1 else self.statuses[0]


def task(status, **kw):
    base = {"status": status, "files_transferred": 0, "files": 3, "bytes_transferred": 0, "nice_status": None}
    base.update(kw)
    return base


def test_submit_asks_for_recursive_checksum_verified_transfer():
    c = FakeClient([task("SUCCEEDED")])
    tid = globus_transfer.submit(c, SRC, DST, "/BW_111226_TOFA/", "/data/BW_111226_TOFA/", "label")
    assert tid == "task-1"
    s = c.submitted
    assert s["source_endpoint"] == SRC and s["destination_endpoint"] == DST
    assert s["verify_checksum"] is True
    item = s["DATA"][0]
    assert item["source_path"] == "/BW_111226_TOFA/"
    assert item["destination_path"] == "/data/BW_111226_TOFA/"
    assert item["recursive"] is True


def test_submit_can_send_a_single_file_not_recursive():
    c = FakeClient([task("SUCCEEDED")])
    globus_transfer.submit(c, SRC, DST, "/a/fastq_md5sum.txt", "/d/fastq_md5sum.txt", "l", recursive=False)
    assert c.submitted["DATA"][0]["recursive"] is False


def test_wait_polls_until_succeeded_and_returns_the_task():
    c = FakeClient([task("ACTIVE"), task("ACTIVE"), task("SUCCEEDED", files_transferred=3)])
    naps = []
    out = globus_transfer.wait(c, "task-1", poll=7, sleep=naps.append, log=lambda m: None)
    assert out["status"] == "SUCCEEDED"
    assert naps == [7, 7]


def test_wait_raises_on_failed():
    c = FakeClient([task("FAILED", nice_status="x")])
    with pytest.raises(globus_transfer.TransferFailed, match="FAILED"):
        globus_transfer.wait(c, "task-1", sleep=lambda s: None, log=lambda m: None)


def test_wait_raises_on_inactive_and_says_why():
    c = FakeClient([task("INACTIVE", nice_status="AUTHENTICATION_REQUIRED")])
    with pytest.raises(globus_transfer.TransferFailed, match="AUTHENTICATION_REQUIRED"):
        globus_transfer.wait(c, "task-1", sleep=lambda s: None, log=lambda m: None)


def test_wait_reports_progress():
    c = FakeClient([task("ACTIVE", files_transferred=1, bytes_transferred=2_000_000_000), task("SUCCEEDED")])
    lines = []
    globus_transfer.wait(c, "task-1", sleep=lambda s: None, log=lines.append)
    assert any("1/3" in m and "2.0 GB" in m for m in lines)
