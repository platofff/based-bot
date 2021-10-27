import asyncio
import json
import logging
import re
from datetime import datetime
from os import getenv, listdir
from types import SimpleNamespace
from typing import Callable, Awaitable, List, Union
from collections import Counter
from random import choice, randint

import aiofiles
import aioredis
import pymorphy2
from vkbottle.bot import Message

from common.tagsformatter import TagsFormatter

logger = logging.getLogger(__name__)


class FakeMessage(SimpleNamespace):
    fwd_messages = []
    conversation_message_id = None
    reply_message = None

    def __init__(self, **kwargs):
        SimpleNamespace.__init__(self, **kwargs)


class Base:
    _messages_db: aioredis.Redis
    _keywords_db: aioredis.Redis
    _morph: pymorphy2.MorphAnalyzer
    _keywords_search: str
    _daily_cleanup: str
    _invalid_grammemes = ['INTJ', 'PRCL', 'PREP']
    _unlimited_conversations: List[str]
    _LIMIT: str

    async def _get_keywords(self, text: str) -> List[pymorphy2.analyzer.Parse]:
        return list(filter(
                lambda x: list(x.tag.grammemes)[0] not in self._invalid_grammemes,
                [self._morph.parse(y)[0] for y in
                    [self._morph.parse(x)[0].normal_form for x in re.sub(
                        r'[^\w\s]', '', text).split()]]))

    @classmethod
    async def new(cls, redis_uri: str):
        self = Base()
        self._messages_db = await aioredis.from_url(redis_uri, encoding='utf-8', decode_responses=True, db=4)
        self._keywords_db = await aioredis.from_url(redis_uri, encoding='utf-8', decode_responses=True, db=5)
        async with aiofiles.open('redis_scripts/keyword_search.lua', mode='r') as f:
            self._keywords_search = await self._keywords_db.script_load(await f.read())
        async with aiofiles.open('redis_scripts/daily_cleanup.lua', mode='r') as f:
            self._daily_cleanup = await self._messages_db.script_load(await f.read())
        self._LIMIT = getenv('CONVERSATION_MAX_SIZE') or "8388608"  # 8 MB
        self._unlimited_conversations = getenv('UNLIMITED_CONVERSATIONS')
        if self._unlimited_conversations:
            self._unlimited_conversations = self._unlimited_conversations.split(',')
        else:
            self._unlimited_conversations = []

        self._morph = pymorphy2.MorphAnalyzer()

        try:
            for jf in listdir('predefined_conversations'):
                _id = jf.split('.')[0]
                if not await self._messages_db.exists(_id):
                    logger.info(f'Importing conversation from {jf}...')
                    async with aiofiles.open(f'predefined_conversations/{jf}', mode='r') as f:
                        chat = json.loads(await f.read(), object_hook=lambda d: FakeMessage(**d)).chat
                    _id = int(_id) + 2000000000
                    for msg in reversed(chat):
                        if msg.from_id < 0 or not msg.text or msg.text[0] in ('/', '!'):
                            continue
                        msg.peer_id = _id
                        await self.add_message(msg)
                    logger.info(f'Imported conversation from {jf}.')

        except FileNotFoundError:
            pass
        asyncio.create_task(self._cleanup_scheduler())

        return self

    async def add_message(self, message: Union[Message, FakeMessage]) -> None:
        keywords = await self._get_keywords(message.text)
        if not keywords:
            return
        answers_to = []
        conversation_id = str(message.peer_id - 2000000000)
        for fwd in message.fwd_messages:
            if fwd.text != '' and fwd.conversation_message_id:
                msg = await self._messages_db.zrangebyscore(conversation_id,
                                                            fwd.conversation_message_id,
                                                            fwd.conversation_message_id)
                if msg:
                    answers_to.append(msg[0])
        if message.reply_message and message.reply_message.conversation_message_id and \
                message.reply_message.text != '':
            msg = await self._messages_db.zrangebyscore(conversation_id,
                                                        message.reply_message.conversation_message_id,
                                                        message.reply_message.conversation_message_id)
            if msg:
                answers_to.append(msg[0])

        _id = message.conversation_message_id
        i = await self._messages_db.zcount(conversation_id, '-inf', '+inf')

        async with self._keywords_db.pipeline(transaction=True) as ktr:
            async with self._messages_db.pipeline(transaction=True) as mtr:
                mi = f'{conversation_id}:{i}'
                mtr.hset(mi, 'text', TagsFormatter.format(message.text, True)) \
                    .hset(mi, 'answers', '') \
                    .zadd(conversation_id, {f'{conversation_id}:{i}': int(_id)})
                for kw in keywords:
                    ktr = ktr.sadd(kw.word, f'{conversation_id}:{_id}')
                await asyncio.wait([mtr.execute(), ktr.execute()])

        if answers_to:
            cors = []
            for i, a, x in [(i, self._messages_db.hget(x, 'answers'), x) for i, x in enumerate(answers_to)]:
                a = list(set((await a).split() + [message.conversation_message_id]))
                cors.append(self._messages_db.hset(x, 'answers', ' '.join([str(x) for x in a])))
            await asyncio.wait(cors)

    def get_answer(self, text: str, conversation: int, callback: Callable[[str], Awaitable]) -> None:
        async def _get_answer():
            async def error():
                await callback('Местным оракулам такой вопрос пока не задавали...')

            conversation_id = str(conversation - 2000000000)
            keywords = list(set(await self._get_keywords(text)))
            values = await self._keywords_db.evalsha(self._keywords_search, len(keywords) + 1, conversation_id,
                                                     *[x.word for x in keywords])
            del keywords
            all_ids = Counter(values).most_common()
            if not all_ids:
                return await error()
            most_common = max([x[1] for x in all_ids])
            ids = []
            for _id in all_ids:
                if _id[1] == most_common:
                    ids.append(_id[0])

            while ids:
                chosen = randint(0, len(ids) - 1)
                chosen = ids.pop(chosen)
                chosen = chosen.split(':')[1]
                index = (await self._messages_db.zrangebyscore(conversation_id, chosen, chosen))[0]
                answers = (await self._messages_db.hget(index, 'answers')).split()
                if not answers:
                    if not index:
                        continue
                    res = await self._messages_db.hget(f'{conversation_id}:{int(index.split(":")[1]) + 1}', 'text')
                    if not res:
                        continue
                    return await callback(res)

                chosen = int(choice(answers))
                return await callback(
                        re.sub(r'[*@]', '',
                               TagsFormatter.format(
                                   await self._messages_db.hget(
                                       (await self._messages_db.zrangebyscore(conversation_id,
                                                                              chosen, chosen))[0], 'text'))))
            return await error()

        asyncio.create_task(_get_answer())

    async def _cleanup_scheduler(self):
        while True:
            logger.info('Running cleanup')
            await self._messages_db.evalsha(self._daily_cleanup, len(self._unlimited_conversations) + 1,
                                            self._LIMIT, *self._unlimited_conversations)
            logger.info('Finished cleanup')
            now = datetime.today()
            target = datetime(now.year, now.month, now.day, 4).timestamp()
            if now.hour >= 4:
                target += 86400
            await asyncio.sleep(target - now.timestamp())
