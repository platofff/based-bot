from vkbottle.bot import Blueprint, Message

from common.tagsformatter import TagsFormatter
from vk_specific import utils

bp = Blueprint()


@bp.on.message(utils.CommandRule(utils.commands.objection))
@utils.command_limit('objection')
async def objection_handler(message: Message):
    if message.is_cropped:
        if message.from_id != message.peer_id:
            await message.answer('Твоё сообщение слишком большое, попробуй написать мне в ЛС!')
            return
        else:
            message_full = (await bp.api.messages.get_by_id([message.get_message_id()])).items[0]
    else:
        message_full = None

    fwd, fwd_photos, fwd_ids = await utils.unpack_fwd(message_full if message_full else message, photos_max=False)
    if not fwd_ids:
        await message.answer('Прочитай как пользоваться: https://vk.com/@kallinux-objection')
        return
    messages = []
    users = {}
    user_ids, group_ids = [], []
    for _id in [*fwd_ids.values()]:
        if _id > 0:
            user_ids.append(str(_id))
        else:
            group_ids.append(_id)
    users_resp = await bp.api.users.get(user_ids)
    groups_resp = bp.api.groups.get_by_id([str(-x) for x in group_ids])
    for user in users_resp:
        users.update({user.id: f"{user.first_name} {user.last_name[:1]}."})
    groups_resp = await groups_resp
    for group in groups_resp:
        users.update({-group.id: group.name})

    for key, value in fwd_ids.items():
        new_val = []
        if key in fwd.keys():
            new_val.append(TagsFormatter.format(fwd[key]))
        if key in fwd_photos.keys():
            for photo_url in fwd_photos[key]:
                new_val.append({'url': photo_url, 'isIcon': False})
        if new_val:
            messages.append([users[value], new_val])

    result = await utils.common.objection.create(messages, f'vk{message.from_id}')
    if type(result) == bytes:
        await message.answer('Загрузи этот файл на objection.lol/maker',
                             attachment=await utils.docs_uploader.upload(f'Your objection.objection',
                                                                         result,
                                                                         peer_id=message.peer_id))
    else:
        await message.answer(result)
