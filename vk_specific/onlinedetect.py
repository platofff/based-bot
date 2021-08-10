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
        async with self._db.pipeline(transaction=True) as tr:
            await tr.set(str(uid), 1).expire(str(uid), 300).incr(str(uid)).execute()

    async def get_online(self) -> List[int]:
        return [int(x) for x in await self._db.keys('*')]

    async def get_active(self) -> Dict[int, int]:
        uids = [int(x) for x in await self._db2.keys('*')]
        try:
            values = [int(x) for x in await self._db2.mget(*tuple(uids))]
        except (IndexError, TypeError):
            values = []
        return dict(zip(uids, values))
