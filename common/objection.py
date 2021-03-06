import base64
import json
import random
from string import ascii_letters

from typing import List, Dict, Union

import aiohttp
import aioredis


class Objection:
    http: aiohttp.ClientSession
    _usage: str
    _db: aioredis.Redis
    _jsonPattern: Dict[str, Union[int, bool, str]]

    @staticmethod
    async def new(redis_uri: str):
        self = Objection()
        self._jsonPattern = {
            "id": -1,
            "text": "",
            "poseId": 1,
            "poseAnimation": True,
            "flipped": False,
            "bubbleType": "0",
            "goNext": False,
            "mergeNext": False,
            "doNotTalk": False,
            "username": ""
        }
        self._usage = 'Использование только с пересланными сообщениями.'
        self._db = await aioredis.from_url(redis_uri, encoding='utf-8', decode_responses=True, db=2)
        self.http = aiohttp.ClientSession()
        return self

    async def create(self, messages: List[List[Union[str, List[Union[str, Dict[str, Union[str, bool]]]]]]],
                     user_id: str) -> Union[bytes, str]:
        result = []

        async with self._db.pipeline(transaction=True) as tr:
            for author in messages:
                tr = tr.get(f'{user_id}_{author[0]}')
            poses = await tr.execute()
        for i in range(len(poses)):
            phrase = self._jsonPattern.copy()
            phrase['username'] = messages[i][0]
            for content in messages[i][1]:
                if type(content) == str:
                    phrase['text'] = content
                else:
                    content.update({'name': ''.join([random.choice(ascii_letters) for _ in range(8)])})
                    async with self.http.post('https://api.objection.lol/api/assets/evidence/add',
                                              data=json.dumps(content, ensure_ascii=False),
                                              headers={
                                                  'Content-type': 'application/json',
                                                  'Referer': 'https://objection.lol/',
                                                  'Origin': 'https://objection.lol/',
                                                  'Authorization': 'Bearer undefined',
                                                  'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:87.0) '
                                                                'Gecko/20100101 Firefox/87.0'
                                              }) as resp:
                        phrase['text'] += f'[#evd{await resp.text()}][#p1000][#evdh]'
            if poses[i]:
                text = phrase['text']
                phrase = json.loads(poses[i])
                phrase['text'] = text
                phrase.pop('iid', None)
            result.append(phrase)
        return base64.b64encode(bytes(json.dumps(result, ensure_ascii=False), 'utf8'))

    async def conf(self, data: str, user_id: str):
        objection = json.loads(base64.b64decode(data))
        print(objection)
        processed = {}
        async with self._db.pipeline(transaction=True) as tr:
            for phrase in objection['groups'][0]['frames']:
                if not phrase['username'] in processed:
                    phrase.pop('text', None)
                    tr = tr.set(f'{user_id}_{phrase["username"]}', json.dumps(phrase))
                    processed.update({phrase['username']: phrase['poseId']})
            await tr.execute()
        return '\n'.join([f'Персонажу {key} назначается поза {value}' for key, value in processed.items()])
