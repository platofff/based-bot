from vkbottle.bot import Blueprint, Message

from vk_specific import utils

bp = Blueprint()


@bp.on.message(utils.CommandRule(utils.commands.objection_conf))
@utils.command_limit('objection_conf')
async def objection_conf_handler(message: Message):
    try:
        async with utils.common.objection.http.get(message.attachments[0].doc.url) as resp:
            await message.answer(
                await utils.common.objection.conf(
                    await resp.text(), f'vk{message.from_id}'))
    except (IndexError, AttributeError):
        await message.answer('Прикрепи .objection файл с objection.lol/maker')
