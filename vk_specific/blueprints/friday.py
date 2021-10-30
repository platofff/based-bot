from vkbottle.bot import Blueprint, Message

from vk_specific import utils
from common.friday import Friday

bp = Blueprint()


@bp.on.message(utils.CommandRule(utils.commands.friday))
@utils.command_limit('friday')
async def friday_handler(message: Message):
    res = Friday.get()
    if res == 'ПЯТНИЦА':
        await message.answer(attachment='photo-197443814_457247468')
    else:
        await message.answer(res)
