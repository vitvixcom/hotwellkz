#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генерация квадратного логотипа 1200×1200 для Google Ads (business logo).
Повторяет фирменную иконку сайта (site/favicon.svg): жёлтый скруглённый квадрат
#FFC400 + чёрный дом #111 + жёлтая дверь. Рендер с 3× суперсэмплингом и LANCZOS.
Зависимость: Pillow (pip install Pillow). Результат: site/assets/logo-1200.png
"""
import os
from PIL import Image, ImageDraw

S, SS = 1200, 3
W = S * SS
sc = W / 64.0                  # favicon viewBox = 64
YELLOW = (255, 196, 0, 255)    # #FFC400
DARK = (17, 17, 17, 255)       # #111111


def p(x, y):
    return (x * sc, y * sc)


def main():
    img = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, W - 1, W - 1], radius=int(14 * sc), fill=YELLOW)
    house = [p(32, 12), p(55, 33), p(49, 33), p(49, 52), p(15, 52), p(15, 33), p(9, 33)]
    d.polygon(house, fill=DARK)
    d.rounded_rectangle([*p(28, 40), *p(36, 52)], radius=int(1 * sc), fill=YELLOW)
    img = img.resize((S, S), Image.LANCZOS)
    out = os.path.join(os.path.dirname(__file__), "..", "..", "site", "assets", "logo-1200.png")
    out = os.path.abspath(out)
    img.save(out, "PNG")
    print("saved", out, img.size)


if __name__ == "__main__":
    main()
