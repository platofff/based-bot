import functools

from vkbottle.bot import Blueprint, Message

from common.ldpr import Zhirinovsky
from vk_specific import utils

bp = Blueprint()


@bp.on.message(utils.CommandRule(utils.commands.zhirinovskysuggested))
@utils.command_limit('zhirinovskysuggested')
async def zhirinovsky_suggested_handler(message: Message):
    text = utils.get_arguments(message.text)
    fwd, _, _ = await utils.unpack_fwd(message, 0)
    fwd = '\n'.join([*fwd.values()])
    if not text and not fwd:
        return await message.answer('А чё предлагать-то...')
    if text:
        if fwd:
            text = fwd + '\n' + text
    elif fwd:
        text = fwd

    fut = utils.pool.submit(Zhirinovsky.suggested, text)
    fut.add_done_callback(functools.partial(utils.photo_callback, message))
