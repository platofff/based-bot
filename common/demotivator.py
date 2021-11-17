import logging
import re
from math import floor, ceil
from typing import Union, List
from urllib import request

from wand.color import Color
from wand.drawing import Drawing
from wand.font import Font
from wand.image import Image

logger = logging.getLogger(__name__)


class Demotivator:
    BIG_FONT_SIZE = 0.052
    SM_FONT_SIZE = 0.036

    @classmethod
    def _dem_text(cls, img: Image, txt: str, font_k: float, font: str) -> Image:
        dem = Image(width=floor(img.width * 1.1), height=1000)
        dem.options['gravity'] = 'center'
        dem.options['pango:wrap'] = 'word-char'
        dem.options['trim:edges'] = 'south'
        dem.font = Font(font)
        dem.font_size = floor(font_k * dem.width)
        dem.font_color = '#ffffff'
        dem.background_color = Color('black')
        dem.pseudo(dem.width, dem.height, pseudo=f'pango:{txt}')
        dem.trim(color=Color('black'))
        return dem

    def create(self, url: str, text1: str, text2: List[str]) -> Union[bytes, None]:
        text1 = re.sub(r'[<>]', '', text1)
        text2 = re.sub(r'[<>]', '', r'\n'.join(text2))
        draw = Drawing()
        draw.stroke_color = Color('white')
        try:
            r = request.urlopen(url, timeout=3).read()
            img = Image(blob=r)
        except BaseException as e:
            logger.debug('Image download error:', e)
            return None
        img.transform(resize='1500x1500>')
        img.transform(resize='300x300<')

        dem1 = self._dem_text(img, text1, self.BIG_FONT_SIZE, 'serif')
        dem2 = self._dem_text(img, text2, self.SM_FONT_SIZE, 'sans')

        output = Image(width=dem1.width,
                       height=dem1.height + dem2.height + img.height + floor(0.12 * img.width),
                       background=Color('black'))
        img_left = floor(0.05 * img.width)
        img_top = floor(0.05 * img.width)
        draw.stroke_width = ceil(img.width / 500)
        k = draw.stroke_width * 4
        draw.polygon([(img_left - k, img_top - k),
                      (img_left + img.width + k, img_top - k),
                      (img_left + img.width + k, img_top + img.height + k),
                      (img_left - k, img_top + img.height + k)])  # Square polygon around image
        draw(output)
        output.composite(image=img, left=img_left, top=img_top)
        img_height = floor(0.07 * img.width + img.height)
        output.composite(image=dem1, left=0, top=img_height)
        output.composite(image=dem2, left=0, top=img_height + dem1.height)
        output.format = 'jpeg'
        return output.make_blob()
