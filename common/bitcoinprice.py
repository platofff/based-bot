import json
from time import time
from urllib import request
from datetime import datetime

import pygal
import cairosvg
from pygal import Config


class BitcoinPrice:
    def __init__(self):
        self._cache = {}

    def get_price(self, hours: int) -> bytes:
        if hours not in self._cache.keys() or time() - self._cache[hours][0] > 900:
            resp = json.load(request.urlopen(
                request.Request('https://cex.io/api/price_stats/BTC/USD',
                                data=json.dumps({'lastHours': hours, 'maxRespArrSize': hours * 4}).encode('ascii'),
                                headers={'Content-type': 'application/json', 'User-agent': 'curl/7.79.1'})))
            config = Config()
            config.show_legend = False
            config.fill = True
            config.title = 'Цена биткоина на CEX.IO'
            config.y_title = 'USD'
            chart = pygal.Line(config, x_label_rotation=-20)
            marked_days = []
            labels = []
            for i, entry in enumerate(resp):
                _time = datetime.fromtimestamp(entry['tmsp'])
                if _time.hour == 0 and _time.day not in marked_days:
                    marked_days.append(_time.day)
                    for j in range(-3, 0):
                        try:
                            labels[j] = ''
                        except IndexError:
                            pass
                    labels.append(_time.strftime('%B, %d'))
                elif i % 6 == 0 and not any(labels[-3:]):
                    labels.append(_time.strftime('%H:%M'))
                else:
                    labels.append('')
            chart.x_labels = labels
            chart.add('USD', [float(entry['price']) for entry in resp])
            self._cache.update({hours: [time(),
                                        cairosvg.svg2png(bytestring=chart.render(is_unicode=True).encode('utf8'))]})
        for e in self._cache.keys():
            if time() - self._cache[e][0] > 900:
                self._cache.pop(e)
        return self._cache[hours][1]
