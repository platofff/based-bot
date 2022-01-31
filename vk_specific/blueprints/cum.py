import functools

from vkbottle.bot import Blueprint, Message

from vk_specific import utils

bp = Blueprint()


@bp.on.message(utils.CommandRule(utils.commands.cum))
@utils.command_limit('cum')
async def cum_handler(message: Message):
    photo = await utils.get_photo_url(message)
    if photo is None:
        _, photos, _ = await utils.unpack_fwd(message, photos_max=1)
        if not photos:
            return await message.answer('Прикрепи или перешли изображение.')
        photo = photos[0]
    fut = utils.pool.submit(utils.common.cum.overlay, photo)
    fut.add_done_callback(functools.partial(utils.photo_callback, message))
