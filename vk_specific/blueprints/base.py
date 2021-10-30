import asyncio

from vkbottle.bot import Blueprint, Message

from vk_specific import utils

bp = Blueprint()


@bp.on.chat_message(utils.CommandRule(utils.commands.base))
@utils.command_limit('base')
async def base_handler(message: Message):
    if not await utils.common.chat.is_storing(message.peer_id):
        await message.answer('Команда /база не включена администратором беседы! Чтобы включить введите /чат база')
        return
    args = utils.get_arguments(message.text)
    fwd, _, _ = await utils.unpack_fwd(message, 0)
    args += ' '.join(fwd.values())
    if not args:
        return await message.answer(await utils.base.random_message(message.peer_id))

    async def callback(text: str) -> None:
        await message.answer(text)

    utils.base.get_answer(message.text, message.peer_id, callback)


@bp.on.chat_message(blocking=False)
async def base_add_handler(message: Message):
    if message.from_id < 0 or not message.text or message.text[0] in ('/', '!') \
            or not await utils.common.chat.is_storing(message.peer_id):
        return
    asyncio.create_task(utils.base.add_message(message))
