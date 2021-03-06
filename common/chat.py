from typing import Dict, List

import aioredis


class Chat:
    db: aioredis.Redis
    commands: Dict[str, List[str]]

    @staticmethod
    async def new(redis_uri: str, commands: Dict[str, List[str]]):
        self = Chat()
        self.db = await aioredis.from_url(redis_uri, encoding='utf-8', decode_responses=True, db=3)
        self.commands = {}
        for x, y in commands.items():
            for c in y:
                if ' ' in c:
                    y.remove(c)
            self.commands.update({x: y})
        return self

    async def set_limit(self, chat: str, _command: str, hour_limit: str) -> str:
        try:
            hour_limit = int(hour_limit)
        except (ValueError, TypeError):
            return 'Некорректное использование!'
        command = None
        for c, j in self.commands.items():
            if _command in j:
                command = c
                break
        if not command:
            return 'Нет такой команды!'
        if hour_limit == -1:
            await self.db.delete(f'{chat}_limit_{command}')
            return f'Лимит команды {command} для данного чата снят.'
        await self.db.set(f'{chat}_limit_{command}', hour_limit)
        return f'Лимит команды {command} для данного чата установлен на {hour_limit} вызовов на человека в час. ' \
               f'Чтобы убрать лимит установите -1.'

    async def get_limit(self, chat: str, command: str, user: str) -> int:
        configured_limit = await self.db.get(f'{chat}_limit_{command}')
        if not configured_limit:
            return -1
        configured_limit = int(configured_limit)
        key = f'{chat}_limit_{command}_{user}'
        user_limit = await self.db.get(key)
        if user_limit is not None:
            user_limit = int(user_limit)
            lim = max(0, user_limit - 1)
            ttl = await self.db.ttl(key)
            await self.db.set(key, lim, ex=ttl)
        else:
            lim = configured_limit
            await self.db.set(key, lim, ex=3600)
        return lim

    async def toggle_messages_store_state(self, conversation_id: int) -> bool:
        if await self.db.sismember('mstore', conversation_id):
            await self.db.srem('mstore', conversation_id)
            return False
        else:
            await self.db.sadd('mstore', conversation_id)
            return True

    async def is_storing(self, conversation_id: int) -> bool:
        return await self.db.sismember('mstore', conversation_id)

    async def rate_limit(self, user: str, interval: int) -> int:
        key = f'rl_{user}'
        ttl = await self.db.pttl(key)
        if ttl == -2:
            await self.db.set(key, '0', px=interval)
            return 0
        else:
            ttl += interval
            val = await self.db.get(key)
            if val == '1':
                await self.db.pexpire(key, ttl)
                return -1
            await self.db.set(key, '1', px=ttl)
            return ttl
