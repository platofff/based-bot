import asyncio
import time
from math import ceil
from os import getenv
from threading import Thread
from typing import List, Dict, Tuple, Union

import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
from vkbottle import Bot

from vk_specific.onlinedetect import OnlineDetect


class FirebaseStatsThread(Thread):
    def __init__(self, bot: Bot, online_detect: OnlineDetect):
        Thread.__init__(self)
        cred = credentials.Certificate('/firebase-adminsdk.json')
        self._app = firebase_admin.initialize_app(cred, {'databaseURL': getenv('FIREBASE_DB_URL')})
        self._ref = db.reference('/')
        self._online_history_ref = db.reference('/online_history')
        self._members_active_ref = db.reference('/members_active')
        self._chat = 2000000000 + int(getenv('STATS_CHAT'))
        self._admins = {}
        self._bot = bot
        self._update_interval = int(getenv('STATS_UPDATE_INTERVAL') or 120)
        self._online_detect = online_detect
        self._online_history = None
        self._running = True

    async def _get_stats(self) -> Tuple[Dict[str, Union[Union[Dict[int, List[str]], float, int]]], Dict[str, int],
                                        Dict[int, List[Union[str, int]]]]:
        chat = (await self._bot.api.request('messages.getConversationsById',
                                            {'peer_ids': self._chat}))['response']['items'][0]

        async def ids_prepare(ids_list: List[int]) -> Dict[int, List[str]]:
            result, user_ids, group_ids = {}, [], []
            for _id in ids_list:
                if _id > 0:
                    user_ids.append(str(_id))
                else:
                    group_ids.append(_id)
            users_resp = await self._bot.api.users.get(user_ids, fields=['photo_100'])
            groups_resp = self._bot.api.groups.get_by_id([str(-x) for x in group_ids], fields=['photo_100'])
            for admin in users_resp:
                result.update({admin.id: [f'{admin.first_name} {admin.last_name}', admin.photo_100]})
            groups_resp = await groups_resp
            for admin in groups_resp:
                result.update({-admin.id: [admin.name, admin.photo_100]})
            return result

        if list(self._admins.keys()) != chat:
            self._admins = await ids_prepare(chat['chat_settings']['admin_ids'])
        members_active = await self._online_detect.get_active()
        online, members_active_profiles = await asyncio.gather(ids_prepare(await self._online_detect.get_online()),
                                                               ids_prepare(list(members_active.keys())))
        for _id, val in members_active.items():
            members_active_profiles[_id].append(val)
        timestamp = ceil(time.time())
        online_history = {str(timestamp): len(online)}
        return {'members_count': chat['chat_settings']['members_count'],
                'online': online,
                'admins': self._admins,
                'updated': timestamp}, online_history, members_active_profiles

    def _update_stats(self):
        res = asyncio.run_coroutine_threadsafe(self._get_stats(), self._bot.loop).result()
        self._ref.update(res[0])
        self._online_history = self._online_history or self._online_history_ref.get() or {}
        while len(self._online_history) > 1440:
            earliest = str(min([int(x) for x in self._online_history.keys()]))
            self._online_history.pop(earliest)
        self._online_history.update(res[1])
        self._online_history_ref.set(self._online_history)
        self._members_active_ref.set(res[2])

    def run(self):
        while self._running:
            self._update_stats()
            time.sleep(self._update_interval)

    def stop(self):
        self._running = False
        firebase_admin.delete_app(self._app)

