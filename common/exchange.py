import asyncio
import concurrent.futures
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from multiprocessing import Process
from typing import Callable, Union, List, Tuple

import aiohttp
import aioredis
import cairosvg
from pygal import Config, DateTimeLine

CHART_MAX = 200


class Exchange:
    db: aioredis.Redis
    _pool: ProcessPoolExecutor
    _loop: asyncio.AbstractEventLoop

    @classmethod
    async def new(cls, redis_uri: str, pool: ProcessPoolExecutor):
        self = Exchange()
        self._pool = pool
        self._loop = asyncio.get_running_loop()
        self.db = await aioredis.from_url(redis_uri, encoding='utf-8', decode_responses=True, db=6)
        return self

    class OrderList:
        def __str__(self):
            return 'stub'

    async def _get_balance(self, user: str) -> Union[float, str]:
        return 'stub'

    async def _get_free_margin(self, user: str) -> Union[float, str]:
        return 'stub'

    async def _get_orders(self, user: str) -> OrderList:
        return self.OrderList()

    async def get_info(self, user: str):
        return f'''BTC/USD
Bid: {await self.db.get('btcusd_bid')} USD
Ask: {await self.db.get('btcusd_ask')} USD
Баланс: {await self._get_balance(user)} USD
Свободная маржа: {await self._get_free_margin(user)}
Открытые сделки:
{await self._get_orders(user)}
'''

    @staticmethod
    def _render_chart(data: List[Tuple[str, float]]) -> bytes:
        config = Config()
        config.show_legend = False
        config.fill = True
        config.title = 'BTCUSD (последние 200 сделок на CEX.IO)'
        chart = DateTimeLine(config, x_label_rotation=-20, truncate_label=-1,
                             x_value_formatter=lambda dt: dt.strftime('%H:%M:%S'))
        chart.add(None, [(datetime.fromtimestamp(x[1]), float(x[0])) for x in data])
        return cairosvg.svg2png(bytestring=chart.render(is_unicode=True).encode('utf8'),
                                parent_width=1280, parent_height=1024)

    async def get_chart(self, callback: Callable[[concurrent.futures.Future], None]):
        fut = self._pool.submit(self._render_chart,
                                    await self.db.zrangebyscore('btcusd', '-inf', '+inf', withscores=True))
        fut.add_done_callback(callback)


class ExchangeProcess(Process):
    _db: aioredis.Redis

    def __init__(self, redis_uri: str):
        Process.__init__(self)
        self._redis_uri = redis_uri
        self._loop = asyncio.get_event_loop()

    async def _db_init(self):
        self._db = await aioredis.from_url(self._redis_uri, encoding='utf-8', decode_responses=True, db=6)

    def run(self):
        self._loop.run_until_complete(self._db_init())
        self._loop.run_until_complete(asyncio.gather(
            self._cex_connect('{"e":"subscribe","rooms":["tickers","pair-BTC-USD"]}', self._cex)))

    async def _cex_connect(self, rq: str, func):
        async with aiohttp.ClientSession() as session:
            while True:
                async with session.ws_connect('wss://ws.cex.io/ws') as ws:
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            msg_obj = msg.json()
                            if msg_obj['e'] == 'connected':
                                await ws.send_str(rq)
                            else:
                                await func(msg_obj)
                        elif msg.type == aiohttp.WSMsgType.CLOSED:
                            break
                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            break

    async def _cex(self, msg):
        if msg['e'] == 'md':
            await asyncio.gather(
                self._db.set('btcusd_bid', msg['data']['buy'][0][0]),
                self._db.set('btcusd_ask', msg['data']['sell'][0][0]))
        elif msg['e'] == 'tick' and msg['data']['symbol1'] == 'BTC' and msg['data']['symbol2'] == 'USD':
            await self._db.zadd('btcusd', {msg['data']['price']: time.time()})
            if await self._db.zcount('btcusd', '-inf', '+inf') > CHART_MAX:
                await self._db.zpopmin('btcusd')
            await self._db.delete('btcusd_chart')
