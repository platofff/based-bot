import asyncio
import concurrent.futures
import functools
import itertools
import sys
import threading
import traceback
from collections import OrderedDict
from concurrent.futures import ProcessPoolExecutor
from os import getenv
import logging
import random
from typing import Optional, Tuple, List, Union
import re
from multiprocessing import cpu_count

import typing
from vkbottle import Bot, DocMessagesUploader
from vkbottle.bot import Message, rules
from vkbottle.tools.dev_tools.uploader import PhotoMessageUploader
from vkbottle_types.objects import MessagesMessageAttachmentType, PhotosPhotoSizesType, MessagesForeignMessage, \
    MessagesMessage, MessagesMessageAttachment

from common.bitcoinprice import BitcoinPrice
from common.chat import Chat
from common.demotivator import Demotivator
from common.nouveau import Nouveau
from common.objection import Objection
from common.optimisation import bash_encode
from common.searchimages import ImgSearch
from common.tagsformatter import TagsFormatter
from common.vasyacache import Vasya
from common.ratelimit import RateLimit
from common.ldpr import Zhirinovsky
from vk_specific.base import Base
from vk_specific.friday import Friday

log_level = logging.DEBUG if getenv('DEBUG') else logging.INFO
logging.basicConfig(level=log_level)
logger = logging.getLogger('MAIN')

bot = Bot(getenv('VK_BOT_TOKEN'))
redis_uri = getenv('REDIS_URI')
photo_uploader = PhotoMessageUploader(bot.api, generate_attachment_strings=True)
docs_uploader = DocMessagesUploader(bot.api, generate_attachment_strings=True)
pool = ProcessPoolExecutor(max_workers=cpu_count() // 2)
demotivator = Demotivator()
img_search = ImgSearch()
rate_limit = RateLimit(5)
objection: Objection
vasya_caching: Vasya
chat: Chat
base: Base
bitcoin_price: BitcoinPrice


def excepthook(exctype, value, tb):
    logging.debug(f'Thread {threading.get_ident()} raised {exctype}: {value}\nTraceback:\n{traceback.format_tb(tb)}')


sys.ecxepthook = excepthook


def command_limit(command: str):
    def decorator(func: typing.Callable):
        async def wrapper(message: Message, *args, **kwargs):
            if await chat.get_limit(f'vk{message.chat_id}', command, str(message.from_id)) != 0:
                return await func(message, *args, **kwargs)

        return wrapper

    return decorator


def get_arguments(text: str) -> str:
    return re.sub(r'^[\S]*\s?', '', text, 1)


class CommandRule(rules.ABCMessageRule):
    def __init__(self, command: List[str]):
        rules.ABCMessageRule.__init__(self)
        self._command = command

    async def check(self, message: Message) -> bool:
        return any(message.text.lower().startswith(x) for x in self._command)


commands = {'start': ['/начать', '/start', '/команды', '/commands', '/помощь', '/help'],
            'demotivator': ['/демотиватор', '/demotivator'],
            'nouveau': ['/nouveau', '/нуво', '/ноувеау'],
            'optimization': ['/оптимизация', '/optimization'],
            'objection': ['/обжекшон', '/objection'],
            'objection_conf': ['/обжекшонконф', '/objectionconf'],
            'zhirinovskysuggested': ['/жириновский', '/жирик', '/zhirinovsky'],
            'friday': ['/friday', '/пятница'],
            'base': ['/base', '/база'],
            'btc': ['/btc', '/бтц', '/bitcoin', '/биткоин', '/тюльпаны']}


@bot.on.message(CommandRule(commands['start']))
@command_limit('start')
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
                         'Для админов бесед:\n'
                         '/чат лимит <команда> <количество вызовов в час на человека>\n'
                         'Например: "/чат лимит /демотиватор 5" сделает команду /демотиватор в беседе доступной 5 раз '
                         'в час для каждого участника.')


async def get_photo_url(message: Union[Message, MessagesForeignMessage], _all=False) -> Union[str, List[str]]:
    async def process(attachment: MessagesMessageAttachment) -> str:
        url = None
        if attachment.type == MessagesMessageAttachmentType.PHOTO:
            # If possible get proportional image
            for size in reversed(attachment.photo.sizes):
                if size.type not in (PhotosPhotoSizesType.R, PhotosPhotoSizesType.Q, PhotosPhotoSizesType.P,
                                     PhotosPhotoSizesType.O):
                    url = size.url
                    break
            if not url:
                url = attachment.photo.sizes[-1].url
        return url

    if _all:
        return list(await asyncio.gather(*[process(a) for a in message.attachments if 'photo' in dir(a)]))
    return await process(message.attachments[0])


async def unpack_fwd(message: Union[Message, MessagesMessage], photos_max: Optional[Union[int, bool]] = 1) -> \
        Tuple[typing.OrderedDict[int, str], typing.OrderedDict[int, List[str]], typing.OrderedDict[int, int]]:
    fwd = OrderedDict()
    fwd_ids = OrderedDict()
    fwd_msgs = []
    fwd_photos = OrderedDict()
    if photos_max is False:
        photos_max = 100

    async def _unpack_fwd(msgs: List[MessagesForeignMessage]):
        for x in msgs:
            if x and x.conversation_message_id not in fwd_msgs:
                fwd_ids.update({x.conversation_message_id: x.from_id})
                if x.text:
                    fwd.update({x.conversation_message_id: x.text})
                if x.fwd_messages:
                    await _unpack_fwd(x.fwd_messages)
                if x.attachments and (not photos_max or len(fwd_photos) < photos_max):
                    photos = await get_photo_url(x, True)
                    for photo in photos:
                        if len(fwd_photos) == photos_max:
                            break
                        if x.conversation_message_id not in fwd_photos.keys():
                            fwd_photos[x.conversation_message_id] = [photo]
                        else:
                            fwd_photos[x.conversation_message_id].append(photo)
                fwd_msgs.append(x.conversation_message_id)

    await _unpack_fwd([message.reply_message] + message.fwd_messages)
    return fwd, fwd_photos, fwd_ids


def create_demotivator(args: list, url: Optional[str] = None) -> bytes:
    search_results = None

    def kernel_panic():
        _search_results = img_search.search('kernel panic')
        return _search_results, random.choice(_search_results)

    if not url:
        search_results = img_search.search(args[0])
        if search_results:
            url = random.choice(search_results)
        else:
            search_results, url = kernel_panic()

    while True:
        dem = demotivator.create(url, args[0], args[1:])
        if dem:
            return dem
        else:
            if search_results is not None:
                search_results.pop(search_results.index(url))
            if search_results:
                url = random.choice(search_results)
            else:
                search_results, url = kernel_panic()


def photo_callback(message: Message, _fut: concurrent.futures.Future, _list: bool = False):
    async def _callback(result: Union[bytes, List[bytes]]):
        if _list:
            attachment = ','.join(await asyncio.gather(*[photo_uploader.upload(r) for r in result]))
        else:
            attachment = await photo_uploader.upload(result)
        await message.answer(attachment=attachment)

    asyncio.ensure_future(_callback(_fut.result()), loop=bot.loop)


@bot.on.message(CommandRule(commands['demotivator']))
@command_limit('demotivator')
async def demotivator_handler(message: Message):
    r = await rate_limit.ratecounter(f'vk{message.from_id}')
    if type(r) != bool:
        await message.answer(r)
        return None

    fwd, fwd_photos, _ = await unpack_fwd(message)
    fwd = '\n'.join([*fwd.values()])
    text = get_arguments(message.text)

    if not text and not fwd:
        await message.answer(attachment=await photo_uploader.upload(await vasya_caching.get_demotivator()))
    else:
        if fwd and text:
            text += f'\n{fwd}'
        elif fwd and not text:
            text = fwd
        text = TagsFormatter.format(text)
        url = None
        if message.attachments:
            url = await get_photo_url(message)
        elif fwd_photos:
            url = [*fwd_photos.values()][0][0]

        fut = pool.submit(create_demotivator, text.splitlines(), url)
        fut.add_done_callback(functools.partial(photo_callback, message))


@bot.on.message(CommandRule(commands['nouveau']))
@command_limit('nouveau')
async def nouveau_handler(message: Message):
    if not message.attachments:
        _, photos, _ = await unpack_fwd(message, photos_max=10)
        try:
            photos = list(itertools.chain.from_iterable(photos.values()))
        except IndexError:
            await message.answer('Прикрепи или перешли изображение.')
            return
    else:
        photos = await get_photo_url(message, True)
    try:
        q = int(get_arguments(message.text))
        if not 1 <= q <= 100:
            raise ValueError
    except ValueError:
        await message.answer('Качество картинки должно быть целым числом от 1 до 100.')
        return
    except TypeError:  # text == None
        q = 93

    q = 101 - q

    fut = pool.submit(Nouveau.create, photos, q)
    fut.add_done_callback(functools.partial(photo_callback, message, _list=True))


@bot.on.message(CommandRule(commands['zhirinovskysuggested']))
@command_limit('zhirinovskysuggested')
async def zhirinovsky_suggested_handler(message: Message):
    text = get_arguments(message.text)
    fwd, _, _ = await unpack_fwd(message)
    fwd = '\n'.join([*fwd.values()])
    if not text and not fwd:
        await message.answer('А чё предлагать-то...')
        return
    if text:
        if fwd:
            text = fwd + '\n' + text
    elif fwd:
        text = fwd

    fut = pool.submit(Zhirinovsky.suggested, text)
    fut.add_done_callback(functools.partial(photo_callback, message))


@bot.on.message(CommandRule(commands['optimization']))
@command_limit('optimization')
async def optimization_handler(message: Message):
    try:
        await message.answer(bash_encode(get_arguments(message.text)))
    except Exception as e:
        if e.args == (914, 'Message is too long'):
            await message.answer('Слишком длинное выражение')
        else:
            raise e


@bot.on.message(CommandRule(commands['friday']))
@command_limit('friday')
async def friday_handler(message: Message):
    res = Friday.get()
    if res.startswith('photo'):
        await message.answer(attachment=res)
    else:
        await message.answer(res)


@bot.on.message(CommandRule(commands['objection']))
@command_limit('objection')
async def objection_handler(message: Message):
    if message.is_cropped:
        if message.from_id != message.peer_id:
            await message.answer('Твоё сообщение слишком большое, попробуй написать мне в ЛС!')
            return
        else:
            message_full = (await bot.api.messages.get_by_id([message.get_message_id()])).items[0]
    else:
        message_full = None

    fwd, fwd_photos, fwd_ids = await unpack_fwd(message_full if message_full else message, photos_max=False)
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
    users_resp = await bot.api.users.get(user_ids)
    groups_resp = bot.api.groups.get_by_id([str(-x) for x in group_ids])
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

    result = await objection.create(messages, f'vk{message.from_id}')
    if type(result) == bytes:
        await message.answer('Загрузи этот файл на objection.lol/maker',
                             attachment=await docs_uploader.upload(f'Your objection.objection',
                                                                   result,
                                                                   peer_id=message.peer_id))
    else:
        await message.answer(result)


@bot.on.message(CommandRule(commands['objection_conf']))
@command_limit('objection_conf')
async def objection_conf_handler(message: Message):
    try:
        async with objection.http.get(message.attachments[0].doc.url) as resp:
            await message.answer(
                await objection.conf(
                    await resp.text(), f'vk{message.from_id}'))
    except (IndexError, AttributeError):
        await message.answer('Прикрепи .objection файл с objection.lol/maker')


async def is_admin(_id: int, peer: int):
    if _id < 0:
        return False
    members = (await bot.api.messages.get_conversation_members(peer)).items
    for member in members:
        if member.member_id == _id and member.is_admin:
            return True
    return False


@bot.on.chat_message(text=['/чат лимит <command> <limit>', '/chat limit <command> <limit>'])
async def chat_limit_handler(message: Message, command: str, limit: str):
    if not await is_admin(message.from_id, message.peer_id):
        return await message.answer('Ты не админ')
    await message.answer(await chat.set_limit(f'vk{message.chat_id}', command, limit))


@bot.on.chat_message(text=['/чат база', '/chat base'])
async def chat_base_handler(message: Message):
    if not await is_admin(message.from_id, message.peer_id):
        return await message.answer('Ты не админ')
    if await chat.toggle_messages_store_state(message.peer_id):
        await message.answer('Команда "/база" включена в этой беседе. История чата будет обезличенно сохраняться.')
    else:
        await message.answer('Команда "/база" отключена в этой беседе. История чата стёрта из базы данных.')


@bot.on.chat_message(CommandRule(commands['btc']))
@command_limit('btc')
async def btcprice_handler(message: Message):
    await message.answer(await bitcoin_price.get_price())


@bot.on.chat_message(CommandRule(commands['base']))
@command_limit('base')
async def base_handler(message: Message):
    if not await chat.is_storing(message.peer_id):
        await message.answer('Команда /база не включена администратором беседы! Чтобы включить введите /чат база')
        return
    args = get_arguments(message.text)
    if not args:
        await message.answer('Использование: /база <текст>')
        return

    async def callback(text: str) -> None:
        await message.answer(text)

    base.get_answer(message.text, message.peer_id, callback)


@bot.on.chat_message(blocking=False)
async def base_add_handler(message: Message):
    if message.from_id < 0 or message.text[0] in ('/', '!') or not await chat.is_storing(message.peer_id):
        return
    asyncio.create_task(base.add_message(message))


async def main():
    global objection, vasya_caching, chat, base, bitcoin_price
    objection = await Objection.new(redis_uri)
    vasya_caching = await Vasya.new(demotivator, img_search, pool, redis_uri)
    chat = await Chat.new(redis_uri, commands)
    base = await Base.new(redis_uri)
    bitcoin_price = BitcoinPrice(chat.db)
    bot.loop.create_task(vasya_caching.run())

if __name__ == '__main__':
    bot.loop_wrapper.add_task(main())
    bot.run_forever()
