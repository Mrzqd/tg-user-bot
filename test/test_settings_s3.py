from __future__ import annotations

import unittest

try:
    from fastapi import HTTPException

    from api.models import DownloadSettingsIn
    from api.routes import settings as settings_route
    from bot.downloads import DownloadSettings
except ModuleNotFoundError as exc:
    raise unittest.SkipTest("FastAPI/Pydantic Settings 未安装，跳过 S3 设置接口测试") from exc


class S3SettingsRouteTest(unittest.IsolatedAsyncioTestCase):
    async def test_webdav_test_reuses_saved_password_when_body_password_empty(self) -> None:
        tested: list[DownloadSettings] = []

        async def fake_get_download_settings():
            return DownloadSettings(webdav_password="old-pass")

        def fake_test_webdav_settings(new_settings):
            tested.append(new_settings)
            return "http://example.test/dav/local/tg/.tg-userbot-webdav-test-1.txt"

        original_get = settings_route.get_download_settings
        original_test = settings_route.test_webdav_settings
        settings_route.get_download_settings = fake_get_download_settings
        settings_route.test_webdav_settings = fake_test_webdav_settings
        try:
            result = await settings_route.test_webdav_config(
                DownloadSettingsIn(
                    target_type="webdav",
                    webdav_url="http://example.test/dav",
                    webdav_username="user",
                    webdav_password="",
                    webdav_remote_path="/local/tg",
                )
            )
        finally:
            settings_route.get_download_settings = original_get
            settings_route.test_webdav_settings = original_test

        self.assertEqual(tested[0].webdav_password, "old-pass")
        self.assertTrue(result.ok)
        self.assertEqual(result.message, "WebDAV 测试成功")

    async def test_s3_secret_kept_when_body_secret_empty(self) -> None:
        saved: list[DownloadSettings] = []

        async def fake_get_download_settings():
            return DownloadSettings(
                target_type="s3",
                s3_bucket="old-bucket",
                s3_access_key_id="old-ak",
                s3_secret_access_key="old-secret",
            )

        async def fake_save_download_settings(new_settings):
            saved.append(new_settings)

        original_get = settings_route.get_download_settings
        original_save = settings_route.save_download_settings
        settings_route.get_download_settings = fake_get_download_settings
        settings_route.save_download_settings = fake_save_download_settings
        try:
            result = await settings_route.update_download_config(
                DownloadSettingsIn(
                    target_type="s3",
                    s3_bucket="media",
                    s3_access_key_id="ak",
                    s3_secret_access_key="",
                    s3_endpoint_url="https://s3.example.test",
                    s3_prefix="local/tg",
                    s3_multipart_chunk_mb=16,
                    s3_max_concurrency=8,
                )
            )
        finally:
            settings_route.get_download_settings = original_get
            settings_route.save_download_settings = original_save

        self.assertEqual(saved[0].s3_secret_access_key, "old-secret")
        self.assertEqual(saved[0].s3_bucket, "media")
        self.assertTrue(result.has_s3_secret_access_key)

    async def test_s3_secret_required_when_not_previously_configured(self) -> None:
        async def fake_get_download_settings():
            return DownloadSettings()

        original_get = settings_route.get_download_settings
        settings_route.get_download_settings = fake_get_download_settings
        try:
            with self.assertRaises(HTTPException) as ctx:
                await settings_route.update_download_config(
                    DownloadSettingsIn(
                        target_type="s3",
                        s3_bucket="media",
                        s3_access_key_id="ak",
                        s3_secret_access_key="",
                    )
                )
        finally:
            settings_route.get_download_settings = original_get

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertEqual(ctx.exception.detail, "S3 Secret Key 不能为空")


if __name__ == "__main__":
    unittest.main()
