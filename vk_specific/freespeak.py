import asyncio
import itertools
import json
import logging
import re
from typing import Callable, Awaitable, List
from collections import OrderedDict, Counter
from random import choice

import aiofiles
import aioredis
import pymorphy2
from vkbottle.bot import Message

logger = logging.getLogger(__name__)


class Freespeak:
    _messages_db: aioredis.Redis
    _keywords_db: aioredis.Redis
    _loop: asyncio.AbstractEventLoop
    _morph: pymorphy2.MorphAnalyzer
    _valid_grammemes = ['NOUN', 'ADVB', 'ADJF' 'NPRO', 'INFN', 'NUMR', 'INTJ', 'CONJ']

    async def _get_keywords(self, text: str) -> List[pymorphy2.analyzer.Parse]:
        return [self._morph.parse(y)[0] for y in
                [self._morph.parse(x)[0].normal_form for x in re.sub(
                    r'[^\w\s]', '', text).split()]]

    @classmethod
    async def new(cls, redis_uri: str, loop: asyncio.AbstractEventLoop):
        self = Freespeak()
        self._messages_db = await aioredis.from_url(redis_uri, encoding='utf-8', decode_responses=True, db=6)
        self._keywords_db = await aioredis.from_url(redis_uri, encoding='utf-8', decode_responses=True, db=7)
        self._morph = pymorphy2.MorphAnalyzer()
        self._loop = loop
        if not await self._messages_db.keys('m'):
            logger.info('Freespeak DB is empty! Loading data from json...')
            async with aiofiles.open('freespeak.json') as f:
                initial = json.loads(await f.read(), object_pairs_hook=OrderedDict)
            async with self._keywords_db.pipeline(transaction=True) as ktr:
                async with self._messages_db.pipeline(transaction=True) as mtr:
                    for i, _id in enumerate(initial.keys()):
                        mi = f'm:{i}'
                        mtr = mtr.hset(mi, 'text', initial[_id]['text']) \
                            .hset(mi, 'answers', ' '.join([str(x) for x in initial[_id]['answers']])
                                  if initial[_id]['answers'] is not None else '').zadd('m', {f'm:{i}': int(_id)})
                        all_keywords = await self._get_keywords(initial[_id]['text'])

                        for kw in all_keywords:
                            if any(x in list(kw.tag.grammemes) for x in self._valid_grammemes):
                                ktr = ktr.sadd(kw.word, _id)

                    await asyncio.wait([mtr.execute(), ktr.execute()])
            del initial
            logger.info('Freespeak DB successfully loaded!')
        return self

    def get_answer(self, text: str, callback: Callable[[str], Awaitable]) -> None:
        async def _get_answer():
            async def error():
                await callback('Оракулам фриспика такой вопрос пока не задавали...')

            keywords = []
            for key in await self._get_keywords(text):
                if any(x in list(key.tag.grammemes) for x in self._valid_grammemes):
                    keywords.append(key)
            keywords = list(set(keywords))
            values = await self._keywords_db.eval(
                "local r = {}; for k,v in pairs(KEYS) do table.insert(r, redis.call('smembers', v)) end; return r",
                len(keywords), *[x.word for x in keywords])
            del keywords
            all_ids = Counter(list(itertools.chain.from_iterable(values))).most_common()
            if not all_ids:
                return await error()
            most_common = max([x[1] for x in all_ids])
            ids = []
            for _id in all_ids:
                if _id[1] == most_common:
                    ids.append(_id[0])
            chosen = choice(ids)
            index = int((await self._messages_db.zrangebyscore('m', chosen, chosen))[0][2:])
            answers = (await self._messages_db.hget(f'm:{index}', 'answers')).split()
            if not answers:
                if index == 0:
                    return await error()
                await callback(await self._messages_db.hget(f'm:{index - 1}', 'text'))
            else:
                chosen = int(choice(answers))
                await callback(
                    await self._messages_db.hget(
                        (await self._messages_db.zrangebyscore('m', chosen, chosen))[0], 'text'))

        asyncio.ensure_future(_get_answer(), loop=self._loop)

    def add_message(self, message: Message) -> None:
        async def _add_message():
            all_keywords = await self._get_keywords(message.text)
            if not all_keywords:
                return
            _id = message.conversation_message_id
            i = await self._messages_db.zcount('m', '-inf', '+inf')
            answers_to = []
            for fwd in message.fwd_messages:
                if fwd.text != '' and fwd.conversation_message_id:
                    msg = await self._messages_db.zrangebyscore('m', fwd.conversation_message_id,
                                                                fwd.conversation_message_id)
                    if msg:
                        answers_to.append(msg[0])
            if message.reply_message and message.reply_message.conversation_message_id and \
                    message.reply_message.text != '':
                msg = await self._messages_db.zrangebyscore('m', message.reply_message.conversation_message_id,
                                                            message.reply_message.conversation_message_id)
                if msg:
                    answers_to.append(msg[0])

            async with self._keywords_db.pipeline(transaction=True) as ktr:
                async with self._messages_db.pipeline(transaction=True) as mtr:
                    mi = f'm:{i}'
                    mtr.hset(mi, 'text', message.text) \
                        .hset(mi, 'answers', '') \
                        .zadd('m', {f'm:{i}': int(_id)})
                    for kw in all_keywords:
                        if any(x in list(kw.tag.grammemes) for x in self._valid_grammemes):
                            ktr = ktr.sadd(kw.word, _id)
                    await asyncio.wait([mtr.execute(), ktr.execute()])

            if answers_to:
                cors = []
                for i, a, x in [(i, self._messages_db.hget(x, 'answers'), x) for i, x in enumerate(answers_to)]:
                    a = list(set((await a).split() + [message.conversation_message_id]))
                    cors.append(self._messages_db.hset(x, 'answers', ' '.join([str(x) for x in a])))
                await asyncio.wait(cors)

        asyncio.ensure_future(_add_message(), loop=self._loop)
