import asyncio
import functools
import random
from typing import List

from vkbottle.bot import Blueprint, Message

from common.tagsformatter import TagsFormatter
from vk_specific import utils

bp = Blueprint()
cache_size = 16


async def search_images_ttl(keywords: str) -> List[str]:
    key = f'kw_{keywords}'
    res = await utils.common.chat.db.smembers(key)
    if res:
        return list(res)
    else:
        res = await asyncio.get_running_loop().run_in_executor(None, utils.common.img_search.search, keywords)
        if res:
            await utils.common.chat.db.sadd(key, *res)
            last_img_search = await utils.common.chat.db.get('last_img_search')
            if last_img_search:
                await utils.common.chat.db.expire(last_img_search, 60)
            await utils.common.chat.db.set('last_img_search', key)
        return res


def create_demotivator(args: list, url: str, search_results: List[str], not_found: List[str]) -> bytes:
    while True:
        dem = utils.common.demotivator.create(url, args[0], args[1:])
        if dem:
            return dem
        else:
            if search_results is not None:
                search_results.pop(search_results.index(url))
            if search_results:
                url = random.choice(search_results)
            else:
                search_results = not_found
                url = random.choice(search_results)


@bp.on.message(utils.CommandRule(utils.commands.demotivator))
@utils.command_limit('demotivator', 5)
async def demotivator_handler(message: Message):
    fwd, fwd_photos, _ = await utils.unpack_fwd(message)
    fwd = '\n'.join([*fwd.values()])
    text = utils.get_arguments(message.text)

    url = None
    if not text and not fwd:
        if message.peer_id == message.from_id or not await utils.common.chat.is_storing(message.peer_id):
            return await \
                message.answer('Вызов /демотиватор без текста доступен только в беседах со включённой командой /база!')
        text = TagsFormatter.format(await utils.base.random_pair(message.peer_id))
    else:
        if fwd and text:
            text += f'\n{fwd}'
        elif fwd and not text:
            text = fwd
        text = TagsFormatter.format(text)
    if message.attachments:
        url = await utils.get_photo_url(message)
    elif fwd_photos:
        url = [*fwd_photos.values()][0][0]

    search_results = None
    args = text.splitlines()

    last_img_search = await utils.common.chat.db.get('last_img_search')
    if last_img_search:
        not_found = list(await utils.common.chat.db.smembers(last_img_search))
    else:
        not_found = None

    if not url:
        search_results = await search_images_ttl(args[0])
        if search_results:
            url = random.choice(search_results)
        else:
            search_results = not_found
            url = random.choice(search_results)

    fut = utils.pool.submit(create_demotivator, args, url, search_results, not_found)
    fut.add_done_callback(functools.partial(utils.photo_callback, message))
