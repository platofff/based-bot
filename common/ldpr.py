from wand.image import Image


class Zhirinovsky:
    @staticmethod
    def suggested(txt):
        text = f"<span color='#000000' size='38000' font_family='sans'>{txt.upper()}</span>"
        with Image(filename='zhirinovsky.jpeg') as img:
            with Image(width=560, height=360) as img2:
                img2.options['pango:wrap'] = 'word-char'
                img2.options['pango:single-paragraph'] = 'false'
                img2.pseudo(560, 360, pseudo=f"pango:{text}")
                img.composite(image=img2, left=50, top=630)
            img.merge_layers('flatten')
            img.format = 'jpeg'
            return img.make_blob()
