import json

import globus_sdk
import pytest

import globus_list

COLL = "00000000-0000-0000-0000-000000000000"


def f(name, size=1):
    return {"name": name, "type": "file", "size": size}


def d(name):
    return {"name": name, "type": "dir", "size": 0}


class FakeClient:
    """Fake Transfer client. Serves at most `page` entries per call, like the real API's cap."""

    def __init__(self, tree, page=1000, fail_on=None, https_server="https://example.test"):
        self.tree, self.page, self.fail_on = tree, page, fail_on
        self.https_server = https_server
        self.orderby_seen = []

    def get_endpoint(self, collection):
        return {"https_server": self.https_server}

    def operation_ls(self, collection, path="/", limit=1000, offset=0, **kw):
        key = path.strip("/")
        self.orderby_seen.append(kw.get("orderby"))
        if key == self.fail_on:
            raise globus_sdk.GlobusError("boom")
        entries = self.tree[key]
        n = min(limit, self.page)
        return {"DATA": entries[offset : offset + n], "total": len(entries)}


TREE = {
    "": [d("Keiji"), d("LAPO"), f("top.csv", 5)],
    "Keiji": [f("a.fastq.gz", 10), f("b c.fastq.gz", 20)],
    "LAPO": [d("sub"), f("m.txt", 3)],
    "LAPO/sub": [f("deep.txt", 7)],
}


def test_normalize_path():
    for p in ("Keiji", "/Keiji", "/Keiji/", "Keiji/"):
        assert globus_list.normalize_path(p) == "Keiji"
    assert globus_list.normalize_path("/") == ""
    assert globus_list.normalize_path("") == ""


def test_lists_nested_files_with_relative_paths():
    out = globus_list.list_files(FakeClient(TREE), COLL, "LAPO")
    assert sorted(out, key=lambda x: x["path"]) == [
        {"path": "LAPO/m.txt", "size": 3},
        {"path": "LAPO/sub/deep.txt", "size": 7},
    ]


def test_root_listing_has_no_leading_slash():
    out = globus_list.list_files(FakeClient(TREE), COLL, "/")
    assert "top.csv" in [x["path"] for x in out]
    assert all(not x["path"].startswith("/") for x in out)
    assert len(out) == 5


def test_pages_through_more_than_one_page():
    tree = {"": [f(f"f{i}.txt", i) for i in range(5)]}
    out = globus_list.list_files(FakeClient(tree, page=2), COLL, "/")
    assert sorted(x["path"] for x in out) == [f"f{i}.txt" for i in range(5)]


def test_empty_path_gives_empty_files_list():
    assert globus_list.list_files(FakeClient({"": []}), COLL, "/") == []


def test_listing_error_exits_nonzero_and_writes_no_partial_json(tmp_path):
    out = tmp_path / "listing.json"
    rc = globus_list.main(
        ["--collection", COLL, "--paths", "LAPO", "--out", str(out)],
        client=FakeClient(TREE, fail_on="LAPO/sub"),
    )
    assert rc != 0
    assert not out.exists()


def test_main_writes_listing_json_and_dedupes_overlapping_paths(tmp_path):
    out = tmp_path / "listing.json"
    rc = globus_list.main(
        ["--collection", COLL, "--paths", "/,/Keiji", "--out", str(out)],
        client=FakeClient(TREE),
    )
    assert rc == 0
    data = json.loads(out.read_text())
    assert data["collection"] == COLL
    assert data["https_server"] == "https://example.test"
    paths = [x["path"] for x in data["files"]]
    assert len(paths) == len(set(paths)) == 5


def test_paging_uses_a_fixed_order():
    client = FakeClient({"": [f(f"f{i}.txt") for i in range(3)]}, page=2)
    globus_list.list_files(client, COLL, "/")
    assert client.orderby_seen and all(o == "name" for o in client.orderby_seen)


def test_collection_without_https_fails_with_clear_message(tmp_path, capsys):
    out = tmp_path / "listing.json"
    rc = globus_list.main(
        ["--collection", COLL, "--out", str(out)],
        client=FakeClient(TREE, https_server=None),
    )
    assert rc != 0
    assert not out.exists()
    assert "HTTPS" in capsys.readouterr().err
