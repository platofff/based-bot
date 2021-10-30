import logging
from os import getenv

from vkbottle import Bot, DocMessagesUploader
from vkbottle.tools.dev_tools.uploader import PhotoMessageUploader

from common.chat import Chat
from common.objection import Objection
from vk_specific import utils
from vk_specific.base import Base
from vk_specific.blueprints import bps

log_level = logging.DEBUG if getenv('DEBUG') else logging.INFO
logging.basicConfig(level=log_level)
logger = logging.getLogger('MAIN')

bot = Bot(getenv('VK_BOT_TOKEN'), loop=utils.loop)
redis_uri = getenv('REDIS_URI')
utils.photo_uploader = PhotoMessageUploader(bot.api, generate_attachment_strings=True)
utils.docs_uploader = DocMessagesUploader(bot.api, generate_attachment_strings=True)


async def main():
    global bot
    utils.common.objection = await Objection.new(redis_uri)
    utils.common.chat = await Chat.new(redis_uri, utils.commands.__dict__)
    utils.base = await Base.new(redis_uri)
    for bp in bps:
        bp.load(bot)


if __name__ == '__main__':
    bot.loop_wrapper.on_startup.append(main())
    bot.run_forever()
