import random


class Roll:
    @staticmethod
    def get():
        return f'Выпало {random.randint(1000000, 9999999)}'
