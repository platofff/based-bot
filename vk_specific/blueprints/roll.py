from vkbottle.bot import Blueprint, Message

from common.roll import Roll
from vk_specific import utils

bp = Blueprint()


@bp.on.message(utils.CommandRule(utils.commands.start))
@utils.command_limit('roll')
async def roll_handler(message: Message):
    await message.answer(Roll.get(utils.get_arguments(message.text)))
