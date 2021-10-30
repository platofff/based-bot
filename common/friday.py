from datetime import datetime


class Friday:
    @staticmethod
    def get() -> str:
        now = datetime.now()
        weekday = datetime.weekday(now)
        if weekday == 4:
            return 'ПЯТНИЦА'
        timestamp = now.timestamp()
        while True:
            timestamp += 86400
            date = datetime.fromtimestamp(timestamp)
            if date.weekday() == 4:
                return 'До ПЯТНИЦЫ осталось ' +\
                    str(datetime.fromtimestamp(datetime(date.year, date.month, date.day).timestamp()) - now)\
                    .replace('-1 day, ', '')[:-7].replace('1 day', '1 день').replace('2 days', '2 дня')\
                    .replace('3 days', '3 дня').replace('4 days', '4 дня').replace('days', 'дней') + '!'