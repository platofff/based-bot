from vkbottle.bot import Blueprint, Message

from vk_specific import utils

bp = Blueprint()


@bp.on.message(utils.FromBotAdminRule(), text='/redis')
async def redis_stats_handler(message: Message):
    stats = await utils.common.chat.db.info(section='Memory')
    memory_usage = '\n'.join([f'- {k}: {v["keys"]}'
                              for k, v in (await utils.common.chat.db.info(section='Keyspace')).items()])
    await message.answer(f'Выделено памяти: {stats["used_memory_human"]}\n'
                         f'Пиковое потребление памяти: {stats["used_memory_peak_human"]}\n'
                         f'Количество ключей:\n'
                         f'{memory_usage}')
