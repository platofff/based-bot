from typing import List
from urllib import request

from wand.image import Image


class Nouveau:
    @staticmethod
    def create(urls: List[str], quality: int) -> List[bytes]:
        result = []
        for url in urls:
            img = Image(blob=request.urlopen(url).read())
            img.transform(resize='500x500>')
            img.transform(resize='500x500<')
            img.format = 'jpeg'
            img.compression_quality = quality
            result.append(img.make_blob())
        return result
