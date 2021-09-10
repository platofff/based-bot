from datetime import datetime


class Friday:
    _photo = 'photo-197443814_457247468'

    @classmethod
    def get(cls) -> str:
        now = datetime.now()
        weekday = datetime.weekday(now)
        if weekday == 4:
            return cls._photo
        timestamp = now.timestamp()
        while True:
            timestamp += 86400
            date = datetime.fromtimestamp(timestamp)
            if date.weekday() == 4:
                return 'До ПЯТНИЦЫ осталось ' +\
                    str(datetime.fromtimestamp(datetime(date.year, date.month, date.day).timestamp()) - now)\
                    .replace('-1 day, ', '')[:-7].replace('1 day', '1 день').replace('2 days', '2 дня')\
                    .replace('3 days', '3 дня').replace('4 days', '4 дня').replace('days', 'дней') + '!'



