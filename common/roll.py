import random


class Roll:
    @staticmethod
    def get(arg: str):
        return f'{f"Ролл на {arg}, в" if arg else "В"}ыпало {random.randint(1000000, 9999999)}'
