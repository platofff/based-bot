import asyncio
from os import getenv
from typing import List, Dict

import aioredis


class OnlineDetect:
    _db: aioredis.Redis
    _db2: aioredis.Redis

    @staticmethod
    async def new(redis_uri: str):
        self = OnlineDetect()
        self._db = await aioredis.from_url(redis_uri, encoding='utf-8', decode_responses=True, db=4)
        self._db2 = await aioredis.from_url(redis_uri, encoding='utf-8', decode_responses=True, db=5)
        self.peer = 2000000000 + int(getenv('STATS_CHAT'))
        return self

    async def update_uid(self, uid: int) -> None:
        uid = str(uid)
        async with self._db.pipeline(transaction=True) as tr:
            c = [tr.set(uid, 1).expire(uid, 300).execute()]
        c.append(self._db2.incr(uid))
        await asyncio.wait(c)

    async def get_online(self) -> List[int]:
        return [int(x) for x in await self._db.keys('*')]

    async def get_active(self) -> Dict[int, int]:
        uids = [int(x) for x in await self._db2.keys('*')]
        try:
            values = [int(x) for x in await self._db2.mget(*tuple(uids))]
        except (IndexError, TypeError):
            values = []
        return dict(zip(uids, values))
