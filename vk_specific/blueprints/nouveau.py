import functools
import itertools

from vkbottle.bot import Blueprint, Message

from common.nouveau import Nouveau
from vk_specific import utils

bp = Blueprint()


@bp.on.message(utils.CommandRule(utils.commands.nouveau))
@utils.command_limit('nouveau')
async def nouveau_handler(message: Message):
    if message.is_cropped:
        if message.from_id != message.peer_id:
            return await message.answer('Слишком много картинок, попробуй написать мне в ЛС!')
        else:
            message = (await bp.api.messages.get_by_id([message.get_message_id()])).items[0]

    if not message.attachments:
        _, photos, _ = await utils.unpack_fwd(message, photos_max=10)
        try:
            photos = list(itertools.chain.from_iterable(photos.values()))
        except IndexError:
            await message.answer('Прикрепи или перешли изображение.')
            return
    else:
        photos = await utils.get_photo_url(message, True)
    try:
        q = int(utils.get_arguments(message.text))
        if not 1 <= q <= 100:
            raise ValueError
    except ValueError:
        await message.answer('Качество картинки должно быть целым числом от 1 до 100.')
        return
    except TypeError:  # text == None
        q = 93

    q = 101 - q

    fut = utils.pool.submit(Nouveau.create, photos, q)
    fut.add_done_callback(functools.partial(utils.photo_callback, message, _list=True))
