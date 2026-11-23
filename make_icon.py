# -*- coding: utf-8 -*-
"""生成程序图标 app.ico（羊皮纸底 + 暗红四角星）。"""
import math
import os

from PIL import Image, ImageDraw

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "app.ico")

PAPER = (243, 238, 228, 255)
EDGE = (214, 201, 176, 255)
RED = (168, 38, 30, 255)
GOLD = (154, 123, 63, 255)


def star_points(cx, cy, r_out, r_in, n=4, rot=-math.pi / 2):
    pts = []
    for i in range(n * 2):
        r = r_out if i % 2 == 0 else r_in
        a = rot + i * math.pi / n
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def make(size):
    S = 8
    img = Image.new("RGBA", (size * S, size * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    W = size * S
    r = int(W * 0.22)
    d.rounded_rectangle([0, 0, W - 1, W - 1], radius=r, fill=PAPER, outline=EDGE, width=max(1, W // 64))
    # 内圈细线
    m = int(W * 0.10)
    d.rounded_rectangle([m, m, W - 1 - m, W - 1 - m], radius=int(r * 0.7),
                        outline=(226, 216, 198, 255), width=max(1, W // 90))
    # 四角星
    d.polygon(star_points(W / 2, W / 2, W * 0.30, W * 0.085), fill=RED)
    d.ellipse([W / 2 - W * 0.035, W / 2 - W * 0.035, W / 2 + W * 0.035, W / 2 + W * 0.035], fill=GOLD)
    return img.resize((size, size), Image.LANCZOS)


sizes = [16, 24, 32, 48, 64, 128, 256]
imgs = [make(s) for s in sizes]
imgs[-1].save(OUT, format="ICO", sizes=[(s, s) for s in sizes])
print("wrote", OUT, os.path.getsize(OUT), "bytes")
