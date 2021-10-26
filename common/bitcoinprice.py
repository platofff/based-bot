import aiohttp
import aioredis


class BitcoinPrice:
    _lastPrice: str = None

    def __init__(self, db: aioredis.Redis):
        self.db = db

    async def get_price(self) -> str:
        if not await self.db.exists('btcprice') or self._lastPrice is None:
            price = None
            async with aiohttp.ClientSession() as session:
                async with session.get('http://api.bitcoincharts.com/v1/markets.json') as resp:
                    for entry in await resp.json(content_type='text/html'):
                        if entry['currency'] == 'USD' and entry['symbol'] == 'cexUSD':
                            price = entry['avg']
            await self.db.set('btcprice', 1, ex=900)
            self._lastPrice = f'На CEX биткоин стоит {int(price // 1)} USD'
        return self._lastPrice
