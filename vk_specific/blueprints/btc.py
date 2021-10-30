import functools

from vkbottle.bot import Blueprint, Message

from common.bitcoinprice import BitcoinPrice
from vk_specific import utils

bp = Blueprint()


@bp.on.message(utils.CommandRule(utils.commands.btc))
@utils.command_limit('btc')
async def btcprice_handler(message: Message):
    async def cache_handler(attachment: str):
        await utils.common.chat.db.set(f'btc{hours}', attachment, ex=900)

    hours = utils.get_arguments(message.text)
    if hours:
        try:
            hours = int(hours)
            assert 0 < hours <= 24
        except (ValueError, AssertionError):
            return await message.answer('Использование: /btc <количество часов, не более 24>')
    else:
        hours = 24
    res = await utils.common.chat.db.get(f'btc{hours}')
    if res is None:
        fut = utils.pool.submit(BitcoinPrice.get_price, hours)
        fut.add_done_callback(functools.partial(utils.photo_callback, message, res_callback=cache_handler))
    else:
        await message.answer(attachment=res)
