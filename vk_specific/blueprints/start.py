from vkbottle.bot import Blueprint, Message

from vk_specific import utils

bp = Blueprint()


@bp.on.message(utils.CommandRule(utils.commands.start))
@utils.command_limit('start')
async def start_handler(message: Message):
    await message.answer('Команды:\n'
                         '/демотиватор - сгенерировать демотиватор со своей картинкой или из интернета. При вызове без '
                         'аргументов текст берётся из БД Васи Машинки https://vk.com/vasyamashinka\n'
                         '/оптимизация - сгенерировать скрипт оптимизации Ubuntu\n'
                         '/nouveau <уровень шакализации, когда не указан = 93> - рендер картинки с помощью '
                         'проприетарного драйвера nouveau\n'
                         '/objection; /objectionconf - Генерация суда в Ace Attorney из пересланных сообщений. Как '
                         'пользоваться тут: https://vk.com/@kallinux-objection\n'
                         '/жирик - Заставить Жириновского что-то предложить\n'
                         '/пятница - Сколько осталось до ПЯТНИЦЫ\n'
                         '/база <текст> - ответить на вопрос используя мудрость данной беседы. Политика '
                         'конфиденциальности: https://vk.com/@kallinux-base\n'
                         '/btc - Цена биткоина\n'
                         'Для админов бесед:\n'
                         '/чат лимит <команда> <количество вызовов в час на человека>\n'
                         'Например: "/чат лимит /демотиватор 5" сделает команду /демотиватор в беседе доступной 5 раз '
                         'в час для каждого участника.')