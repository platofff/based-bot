from vkbottle.bot import Blueprint, Message

from vk_specific import utils

bp = Blueprint()


@bp.on.chat_message(text=['/чат лимит <command> <limit>', '/chat limit <command> <limit>'])
async def chat_limit_handler(message: Message, command: str, limit: str):
    if not await utils.is_admin(message.from_id, message.peer_id):
        return await message.answer('Ты не админ')
    await message.answer(await utils.common.chat.set_limit(f'vk{message.chat_id}', command, limit))


@bp.on.chat_message(text=['/чат база', '/chat base'])
async def chat_base_handler(message: Message):
    if not await utils.is_admin(message.from_id, message.peer_id):
        return await message.answer('Ты не админ')
    if await utils.common.chat.toggle_messages_store_state(message.peer_id):
        await message.answer('Команда "/база" включена в этой беседе. Политика конфиденциальности: '
                             'https://vk.com/@kallinux-base')
    else:
        await message.answer('Команда "/база" отключена в этой беседе.')
