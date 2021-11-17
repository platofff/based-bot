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
        await utils.common.chat.db.sadd(key, *res)
        await utils.common.chat.db.expire(key, 60)
        return res


def create_demotivator(args: list, url: str, search_results: List[str]) -> bytes:
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
                search_results = utils.common.img_search.search('kernel panic')  # TODO caching
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

    async def kernel_panic():
        _search_results = await search_images_ttl('kernel panic')
        return _search_results, random.choice(_search_results)

    if not url:
        search_results = await search_images_ttl(args[0])
        if search_results:
            url = random.choice(search_results)
        else:
            search_results, url = await kernel_panic()

    fut = utils.pool.submit(create_demotivator, args, url, search_results)
    fut.add_done_callback(functools.partial(utils.photo_callback, message))
