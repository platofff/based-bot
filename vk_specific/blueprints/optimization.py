from vkbottle.bot import Blueprint, Message

from common.optimisation import bash_encode
from vk_specific import utils

bp = Blueprint()


@bp.on.message(utils.CommandRule(utils.commands.optimization))
@utils.command_limit('optimization')
async def optimization_handler(message: Message):
    try:
        await message.answer(bash_encode(utils.get_arguments(message.text)))
    except Exception as e:
        if e.args == (914, 'Message is too long'):
            await message.answer('Слишком длинное выражение')
        else:
            raise e
