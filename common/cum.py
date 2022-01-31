from urllib import request

from wand.image import Image


class Cum:
    def __init__(self):
        with open('pictures/cum.png', 'rb') as overlay:
            self._overlay = overlay.read()

    def overlay(self, url: str):
        image = request.urlopen(url)
        with Image(file=image) as img1:
            with Image(blob=self._overlay) as img2:
                img2.transform(resize=f'{img1.size[0]}x{img1.size[1]}')
                img1.composite(img2, left=0, bottom=0)
                img1.format = 'jpeg'
                res = img1.make_blob()
        image.close()
        return res


