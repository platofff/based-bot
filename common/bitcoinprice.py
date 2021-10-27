import json

from urllib import request
from datetime import datetime

import pygal
import cairosvg
from pygal import Config


class BitcoinPrice:
    @classmethod
    def get_price(cls, hours: int) -> bytes:
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
            time = datetime.fromtimestamp(entry['tmsp'])
            if time.hour == 0 and time.day not in marked_days:
                marked_days.append(time.day)
                labels.append(time.strftime('%B, %d'))
            elif i % 6 == 0 and not any(labels[-3:]):
                labels.append(time.strftime('%H:%M'))
            else:
                labels.append('')
        chart.x_labels = labels
        chart.add('USD', [float(entry['price']) for entry in resp])
        return cairosvg.svg2png(bytestring=chart.render(is_unicode=True).encode('utf8'))
