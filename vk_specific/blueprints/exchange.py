import asyncio
import concurrent.futures

from vkbottle.bot import Blueprint, Message

from vk_specific import utils

bp = Blueprint()

@bp.on.message(utils.CommandRule(utils.commands.exchange))
@utils.command_limit('exchange')
async def exchange_handler(message: Message):
    def photo_callback(fut: concurrent.futures.Future):
        def callback(_task: asyncio.Task):
            _photo = _task.result()
            asyncio.ensure_future(asyncio.gather(
                utils.exchange.db.set('btcusd_chart', _photo),
                message.answer(attachment=_photo)), loop=utils.loop)
        task = asyncio.ensure_future(utils.photo_uploader.upload(fut.result()), loop=utils.loop)
        task.add_done_callback(callback)

    command = message.text.lower().split()
    try:
        subcommand = command[1]
    except IndexError:
        return await message.answer('Биржа находится на стадии разработки')
    if subcommand in ('инфо', 'info'):
        await message.answer(await utils.exchange.get_info(f'vk{message.from_id}'))
    elif subcommand in ('курс', 'btc', 'биткоин', 'тюльпаны', 'график', 'chart'):
        photo = await utils.exchange.db.get('btcusd_chart')
        if photo:
            await message.answer(attachment=photo)
        else:
            await utils.exchange.get_chart(photo_callback)
    elif subcommand in ('опцион', 'option'):
        if len(command) != 5:
            return await message.answer(utils.exchange.option_usage)
        await message.answer(await utils.exchange.new_option(f'vk{message.from_id}', command[2], command[3], command[4]))
    else:
        await message.answer('Биржа находится на стадии разработки')
