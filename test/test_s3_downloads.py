from __future__ import annotations

import sys
import tempfile
import types
import unittest
from pathlib import Path

from bot.downloads import DownloadSettings, _join_s3_key, _s3_object_url, _upload_s3_file


class S3DownloadUnitTest(unittest.TestCase):
    def test_join_s3_key_cleans_filename_and_prefix(self) -> None:
        key = _join_s3_key("/local/tg/", 'a:b?.mp4')

        self.assertEqual(key, "local/tg/a_b_.mp4")

    def test_s3_object_url_uses_endpoint_bucket_and_key(self) -> None:
        url = _s3_object_url(
            DownloadSettings(
                s3_endpoint_url="https://r2.example.test",
                s3_bucket="media",
            ),
            "local/tg/a b.mp4",
        )

        self.assertEqual(url, "https://r2.example.test/media/local/tg/a%20b.mp4")

    def test_upload_uses_multipart_config_and_progress_callback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "video.mp4"
            path.write_bytes(b"x" * 100)
            progress_values: list[int] = []
            calls = {}

            class FakeConfig:
                def __init__(self, **kwargs):
                    calls["client_config"] = kwargs

            class FakeTransferConfig:
                def __init__(self, **kwargs):
                    calls["transfer_config"] = kwargs

            class FakeS3Transfer:
                def __init__(self, client, config):
                    calls["transfer_client"] = client
                    calls["transfer_config_obj"] = config

                def upload_file(self, filename, bucket, key, extra_args=None, callback=None):
                    calls["upload"] = (filename, bucket, key)
                    calls["extra_args"] = extra_args
                    callback(40)
                    callback(60)

            class FakeNotFound(Exception):
                response = {"Error": {"Code": "404"}, "ResponseMetadata": {"HTTPStatusCode": 404}}

            class FakeClient:
                def head_object(self, Bucket, Key):
                    calls["head"] = (Bucket, Key)
                    raise FakeNotFound()

            fake_client = FakeClient()
            fake_boto3 = types.SimpleNamespace(
                client=lambda service, **kwargs: calls.setdefault("client", (service, kwargs)) and fake_client,
            )
            fake_botocore_client = types.SimpleNamespace(Config=FakeConfig)
            fake_boto3_transfer = types.SimpleNamespace(
                S3Transfer=FakeS3Transfer,
                TransferConfig=FakeTransferConfig,
            )

            originals = {
                "boto3": sys.modules.get("boto3"),
                "boto3.s3": sys.modules.get("boto3.s3"),
                "boto3.s3.transfer": sys.modules.get("boto3.s3.transfer"),
                "botocore": sys.modules.get("botocore"),
                "botocore.client": sys.modules.get("botocore.client"),
            }
            sys.modules["boto3"] = fake_boto3
            sys.modules["boto3.s3"] = types.SimpleNamespace()
            sys.modules["boto3.s3.transfer"] = fake_boto3_transfer
            sys.modules["botocore"] = types.SimpleNamespace()
            sys.modules["botocore.client"] = fake_botocore_client
            try:
                target = _upload_s3_file(
                    path,
                    DownloadSettings(
                        s3_endpoint_url="https://s3.example.test",
                        s3_region="us-east-1",
                        s3_bucket="media",
                        s3_access_key_id="ak",
                        s3_secret_access_key="sk",
                        s3_prefix="local/tg",
                        s3_addressing_style="path",
                        s3_multipart_chunk_mb=16,
                        s3_max_concurrency=12,
                    ),
                    progress_values.append,
                )
            finally:
                for name, module in originals.items():
                    if module is None:
                        sys.modules.pop(name, None)
                    else:
                        sys.modules[name] = module

        self.assertEqual(target, "https://s3.example.test/media/local/tg/video.mp4")
        self.assertEqual(calls["client"][0], "s3")
        self.assertEqual(calls["client"][1]["endpoint_url"], "https://s3.example.test")
        self.assertEqual(calls["client"][1]["aws_access_key_id"], "ak")
        self.assertEqual(calls["client_config"], {"s3": {"addressing_style": "path"}})
        self.assertEqual(calls["head"], ("media", "local/tg/video.mp4"))
        self.assertEqual(calls["transfer_config"]["multipart_chunksize"], 16 * 1024 * 1024)
        self.assertEqual(calls["transfer_config"]["max_concurrency"], 12)
        self.assertEqual(calls["upload"][1:], ("media", "local/tg/video.mp4"))
        self.assertEqual(calls["extra_args"], {"ContentType": "video/mp4"})
        self.assertEqual(progress_values, [40, 100])

    def test_upload_skips_when_s3_object_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "video.mp4"
            path.write_bytes(b"x" * 100)
            calls = {}

            class FakeConfig:
                def __init__(self, **kwargs):
                    calls["client_config"] = kwargs

            class FakeTransferConfig:
                def __init__(self, **kwargs):
                    calls["transfer_config"] = kwargs

            class FakeS3Transfer:
                def __init__(self, client, config):
                    calls["transfer_created"] = True

                def upload_file(self, *args, **kwargs):
                    calls["upload"] = True

            class FakeClient:
                def head_object(self, Bucket, Key):
                    calls["head"] = (Bucket, Key)
                    return {}

            fake_client = FakeClient()
            fake_boto3 = types.SimpleNamespace(
                client=lambda service, **kwargs: calls.setdefault("client", (service, kwargs)) and fake_client,
            )
            fake_botocore_client = types.SimpleNamespace(Config=FakeConfig)
            fake_boto3_transfer = types.SimpleNamespace(
                S3Transfer=FakeS3Transfer,
                TransferConfig=FakeTransferConfig,
            )

            originals = {
                "boto3": sys.modules.get("boto3"),
                "boto3.s3": sys.modules.get("boto3.s3"),
                "boto3.s3.transfer": sys.modules.get("boto3.s3.transfer"),
                "botocore": sys.modules.get("botocore"),
                "botocore.client": sys.modules.get("botocore.client"),
            }
            sys.modules["boto3"] = fake_boto3
            sys.modules["boto3.s3"] = types.SimpleNamespace()
            sys.modules["boto3.s3.transfer"] = fake_boto3_transfer
            sys.modules["botocore"] = types.SimpleNamespace()
            sys.modules["botocore.client"] = fake_botocore_client
            try:
                target = _upload_s3_file(
                    path,
                    DownloadSettings(
                        s3_endpoint_url="https://s3.example.test",
                        s3_region="us-east-1",
                        s3_bucket="media",
                        s3_access_key_id="ak",
                        s3_secret_access_key="sk",
                        s3_prefix="local/tg",
                        s3_addressing_style="path",
                    ),
                )
            finally:
                for name, module in originals.items():
                    if module is None:
                        sys.modules.pop(name, None)
                    else:
                        sys.modules[name] = module

        self.assertEqual(target, "https://s3.example.test/media/local/tg/video.mp4")
        self.assertTrue(getattr(target, "existed", False))
        self.assertEqual(calls["head"], ("media", "local/tg/video.mp4"))
        self.assertNotIn("upload", calls)


if __name__ == "__main__":
    unittest.main()
