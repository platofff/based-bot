import re

from wand.image import Image
from wand.font import Font

class Zhirinovsky:
    def __init__(self):
        with open('zhirinovsky.jpeg', 'rb') as f:
            self._pattern = f.read()

    def suggested(self, txt):
        txt = re.sub('^(ЕСТЬ ИДЕЯ|МБ|МОЖЕТ БЫТЬ|ПРЕДЛАГАЮ|А МОЖЕТ|МОЖЕТ|ДАВАЙТЕ|ДАВАЙ) ', '', txt.upper())
        with Image(blob=self._pattern) as img:
            with Image(width=560, height=360) as img2:
                img2.options['pango:wrap'] = 'word-char'
                img2.options['pango:single-paragraph'] = 'false'
                img2.font = Font('OswaldRegular')
                img2.font_color = '#000000'
                img2.font_size = 44
                img2.pseudo(560, 360, pseudo=f"pango:{txt}")
                img2.sharpen(radius=8, sigma=4)
                img.composite(image=img2, left=50, top=630)
            img.merge_layers('flatten')
            img.format = 'jpeg'
            return img.make_blob()
