from __future__ import annotations

import base64
import os
import tempfile
import unittest
from pathlib import Path

from urllib.request import Request

from bot.downloads import (
    DownloadSettings,
    WEBDAV_UPLOAD_BLOCK_SIZE,
    _add_webdav_auth,
    _ensure_webdav_collections,
    _join_webdav_url,
    _upload_webdav_file,
)


class FakeOpener:
    def __init__(self, fail_first_put: bool = False) -> None:
        self.fail_first_put = fail_first_put
        self.requests: list[Request] = []
        self.put_attempts = 0
        self.put_body_chunks: list[int] = []

    def open(self, req: Request, timeout: int = 0):
        self.requests.append(req)
        if req.get_method() == "PUT":
            self.put_attempts += 1
            if self.fail_first_put and self.put_attempts == 1:
                raise BrokenPipeError("simulated broken pipe")
            while True:
                chunk = req.data.read(WEBDAV_UPLOAD_BLOCK_SIZE * 2)
                if not chunk:
                    break
                self.put_body_chunks.append(len(chunk))
        return object()


class WebDavDownloadUnitTest(unittest.TestCase):
    def test_join_webdav_url_quotes_path_parts(self) -> None:
        url = _join_webdav_url(
            "http://example.test/dav",
            "/local/tg space/",
            "a b.mp4",
        )
        self.assertEqual(url, "http://example.test/dav/local/tg%20space/a%20b.mp4")

    def test_add_webdav_auth_uses_basic_header(self) -> None:
        req = Request("http://example.test/dav/file.txt", method="PUT")
        settings = DownloadSettings(webdav_username="...", webdav_password="......")

        _add_webdav_auth(req, settings)

        expected = "Basic " + base64.b64encode(b"...:......").decode()
        self.assertEqual(req.get_header("Authorization"), expected)

    def test_ensure_collections_creates_each_remote_path_part(self) -> None:
        opener = FakeOpener()
        settings = DownloadSettings(
            webdav_url="http://example.test/dav",
            webdav_username="user",
            webdav_password="pass",
            webdav_remote_path="/local/tg",
        )

        _ensure_webdav_collections(opener, settings)

        methods = [req.get_method() for req in opener.requests]
        urls = [req.full_url for req in opener.requests]
        self.assertEqual(methods, ["MKCOL", "MKCOL"])
        self.assertEqual(urls, ["http://example.test/dav/local/", "http://example.test/dav/local/tg/"])
        self.assertTrue(all(req.get_header("Authorization") for req in opener.requests))

    def test_upload_retries_put_after_broken_pipe(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.txt"
            path.write_text("hello", encoding="utf-8")
            settings = DownloadSettings(
                webdav_url="http://example.test/dav",
                webdav_username="user",
                webdav_password="pass",
                webdav_remote_path="/local/tg",
            )

            opener = FakeOpener(fail_first_put=True)
            import bot.downloads as downloads

            original = downloads._make_webdav_opener
            downloads._make_webdav_opener = lambda _: opener
            try:
                target = _upload_webdav_file(path, settings)
            finally:
                downloads._make_webdav_opener = original

        self.assertEqual(target, "http://example.test/dav/local/tg/sample.txt")
        self.assertEqual(opener.put_attempts, 2)

    def test_upload_uses_large_block_reader_and_progress_callback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.bin"
            path.write_bytes(b"a" * (WEBDAV_UPLOAD_BLOCK_SIZE + 123))
            settings = DownloadSettings(
                webdav_url="http://example.test/dav",
                webdav_username="user",
                webdav_password="pass",
                webdav_remote_path="/local/tg",
            )

            opener = FakeOpener()
            progress_values: list[int] = []
            import bot.downloads as downloads

            original = downloads._make_webdav_opener
            downloads._make_webdav_opener = lambda _: opener
            try:
                target = _upload_webdav_file(path, settings, progress_values.append)
            finally:
                downloads._make_webdav_opener = original

        put_requests = [req for req in opener.requests if req.get_method() == "PUT"]
        self.assertEqual(target, "http://example.test/dav/local/tg/sample.bin")
        self.assertEqual(len(put_requests), 1)
        self.assertEqual(opener.put_body_chunks, [WEBDAV_UPLOAD_BLOCK_SIZE, 123])
        self.assertEqual(progress_values, [WEBDAV_UPLOAD_BLOCK_SIZE, WEBDAV_UPLOAD_BLOCK_SIZE + 123])


class WebDavSmokeTest(unittest.TestCase):
    def test_real_webdav_upload_when_env_enabled(self) -> None:
        url = os.getenv("WEBDAV_SMOKE_URL")
        username = os.getenv("WEBDAV_SMOKE_USERNAME")
        password = os.getenv("WEBDAV_SMOKE_PASSWORD")
        remote_path = os.getenv("WEBDAV_SMOKE_REMOTE_PATH", "/local/tg")
        if not all([url, username, password]):
            self.skipTest("set WEBDAV_SMOKE_URL/USERNAME/PASSWORD to run real WebDAV smoke test")

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tg-userbot-smoke.txt"
            path.write_text("tg-userbot webdav smoke\n", encoding="utf-8")
            target = _upload_webdav_file(
                path,
                DownloadSettings(
                    webdav_url=url,
                    webdav_username=username,
                    webdav_password=password,
                    webdav_remote_path=remote_path,
                ),
            )

        self.assertTrue(target.endswith("/tg-userbot-smoke.txt"))


if __name__ == "__main__":
    unittest.main()
