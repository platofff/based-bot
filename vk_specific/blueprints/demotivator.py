import functools
import random
from typing import Union

from vkbottle.bot import Blueprint, Message

from common.tagsformatter import TagsFormatter
from vk_specific import utils

bp = Blueprint()


def create_demotivator(args: list, url: Union[str, None]) -> bytes:
    search_results = None

    def kernel_panic():
        _search_results = utils.common.img_search.search('kernel panic')
        return _search_results, random.choice(_search_results)

    if not url:
        search_results = utils.common.img_search.search(args[0])
        if search_results:
            url = random.choice(search_results)
        else:
            search_results, url = kernel_panic()

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
                search_results, url = kernel_panic()


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
        text = await utils.base.random_pair(message.peer_id)
        if text == '':
            return await message.answer('Пока слишком мало сообщений...')
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

    fut = utils.pool.submit(create_demotivator, text.splitlines(), url)
    fut.add_done_callback(functools.partial(utils.photo_callback, message))
