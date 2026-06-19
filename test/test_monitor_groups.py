from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

try:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
except ModuleNotFoundError as exc:
    raise unittest.SkipTest("SQLAlchemy 未安装，跳过监控群组数据库测试") from exc

from database import crud
from database.models import Base, MonitoredGroup


class MonitorGroupCrudTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.engine = create_async_engine(f"sqlite+aiosqlite:///{Path(self.tmp.name) / 'test.db'}")
        self.sessionmaker = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def asyncTearDown(self):
        await self.engine.dispose()
        self.tmp.cleanup()

    async def test_add_group_reactivates_inactive_existing_group(self):
        async with self.sessionmaker() as session:
            session.add(MonitoredGroup(chat_id=1001, title="old", is_active=False))
            await session.commit()

            group = await crud.add_group(session, chat_id=1001, title="new")
            groups = await crud.get_active_groups(session)

        self.assertTrue(group.is_active)
        self.assertEqual(group.title, "new")
        self.assertEqual([item.chat_id for item in groups], [1001])

    async def test_add_group_rejects_active_existing_group(self):
        async with self.sessionmaker() as session:
            await crud.add_group(session, chat_id=1001, title="group")

            with self.assertRaises(crud.GroupAlreadyMonitoredError):
                await crud.add_group(session, chat_id=1001, title="group")

    async def test_all_groups_includes_inactive_groups(self):
        async with self.sessionmaker() as session:
            session.add(MonitoredGroup(chat_id=1001, title="disabled", is_active=False))
            await crud.add_group(session, chat_id=1002, title="enabled")
            all_groups = await crud.get_all_groups(session)
            active_groups = await crud.get_active_groups(session)

        self.assertEqual({item.chat_id for item in all_groups}, {1001, 1002})
        self.assertEqual([item.chat_id for item in active_groups], [1002])


if __name__ == "__main__":
    unittest.main()
