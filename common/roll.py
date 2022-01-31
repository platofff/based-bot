import random


class Roll:
    @staticmethod
    def get(arg: str):
        return f'Ролл на {arg}, выпало {random.randint(1000000, 9999999)}'
