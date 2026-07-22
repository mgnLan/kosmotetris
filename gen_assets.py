# -*- coding: utf-8 -*-
"""
Генератор графических ассетов VK Mini App «Звездопад».
Палитра: бирюза #00d4ff, золото #ffd54f, глубокий индиго.
Рендер в 2x (суперсэмплинг) -> даунскейл LANCZOS.
"""
import math
import os
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(ROOT, "assets")
os.makedirs(ASSETS, exist_ok=True)

FONT_BOLD = r"C:\Windows\Fonts\segoeuib.ttf"
FONT_REG = r"C:\Windows\Fonts\segoeui.ttf"

TURQ = (0, 212, 255)
GOLD = (255, 213, 79)
INDIGO = (16, 12, 54)
INDIGO_DEEP = (7, 6, 28)
VIOLET = (124, 77, 255)
PINK = (255, 79, 216)
WHITE = (240, 248, 255)
NAVY = (6, 10, 34)

SS = 2  # supersampling factor


# ---------------------------------------------------------------- helpers
def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def vgrad(w, h, stops):
    """Вертикальный градиент. stops: [(pos0..1, (r,g,b)), ...]"""
    arr = np.zeros((h, w, 3), dtype=np.float32)
    ys = np.linspace(0.0, 1.0, h)
    for yi, t in enumerate(ys):
        c = stops[-1][1]
        for i in range(len(stops) - 1):
            p0, c0 = stops[i]
            p1, c1 = stops[i + 1]
            if p0 <= t <= p1:
                tt = 0.0 if p1 == p0 else (t - p0) / (p1 - p0)
                c = lerp(c0, c1, tt)
                break
        arr[yi, :, :] = c
    return Image.fromarray(arr.astype(np.uint8), "RGB").convert("RGBA")


def add_nebula(img, blobs, blur=None):
    """Мягкие цветные пятна туманности. blobs: (cx, cy, r, color, alpha)"""
    W, H = img.size
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for (cx, cy, r, color, alpha) in blobs:
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color + (alpha,))
    layer = layer.filter(ImageFilter.GaussianBlur(blur or W // 9))
    img.alpha_composite(layer)


def add_stars(img, count, seed=2, flare_every=14, ymax=None):
    rng = random.Random(seed)
    W, H = img.size
    ymax = ymax or H
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for i in range(count):
        x = rng.uniform(0, W)
        y = rng.uniform(0, ymax)
        b = rng.randint(130, 255)
        r = rng.uniform(0.6, 2.1) * SS
        d.ellipse([x - r, y - r, x + r, y + r],
                  fill=(b, b, min(255, b + 18), rng.randint(120, 255)))
        if i % flare_every == 0:  # крестообразный блик
            fl = r * 5.5
            a = rng.randint(50, 100)
            wd = max(1, SS // 2)
            d.line([x - fl, y, x + fl, y], fill=(190, 225, 255, a), width=wd)
            d.line([x, y - fl, x, y + fl], fill=(190, 225, 255, a), width=wd)
    img.alpha_composite(layer)


def vignette(img, strength=110):
    W, H = img.size
    y, x = np.ogrid[:H, :W]
    dist = np.sqrt(((x - W / 2) / (W / 2)) ** 2 + ((y - H / 2) / (H / 2)) ** 2)
    mask = (np.clip((dist - 0.62) / 0.75, 0, 1) * strength).astype(np.uint8)
    black = Image.new("RGBA", img.size, (0, 0, 0, 255))
    img.paste(black, (0, 0), Image.fromarray(mask, "L"))


def glass_panel(img, box, rad, fill=(200, 225, 255, 20),
                border=(150, 220, 255, 70)):
    x0, y0, x1, y1 = box
    # мягкое свечение рамки
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.rounded_rectangle(box, radius=rad, outline=TURQ + (36,), width=SS * 2)
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(SS * 4)))
    # стекло рисуем в отдельный слой и блендим (ImageDraw заменяет пиксели!)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle(box, radius=rad, fill=fill, outline=border, width=SS)
    d.line([x0 + rad, y0 + SS, x1 - rad, y0 + SS],
           fill=(255, 255, 255, 60), width=SS)
    img.alpha_composite(layer)


def make_text_layer(text, font, tracking=0, pad=None):
    pad = pad if pad is not None else font.size // 2
    tmp = ImageDraw.Draw(Image.new("RGBA", (8, 8)))
    widths = [tmp.textlength(ch, font=font) for ch in text]
    asc, desc = font.getmetrics()
    w = int(sum(widths) + tracking * max(0, len(text) - 1)) + pad * 2
    h = asc + desc + pad * 2
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    x = pad
    for ch, cw in zip(text, widths):
        ld.text((x, pad), ch, font=font, fill=(255, 255, 255, 255))
        x += cw + tracking
    return layer


def paste_neon(img, layer, center, fill, glow, glow_alpha=220, radii=None):
    """Вставка слоя текста с неоновым свечением. center=(cx,cy)."""
    alpha = layer.split()[3]

    def tinted(color, scale):
        t = Image.new("RGBA", layer.size, color + (0,))
        t.putalpha(alpha.point(lambda v: int(v * scale)))
        return t

    x = int(center[0] - layer.size[0] / 2)
    y = int(center[1] - layer.size[1] / 2)
    if radii is None:
        radii = [(SS * 16, 0.30), (SS * 8, 0.55), (SS * 3, 0.95)]
    for r, s in radii:
        g = tinted(glow, s * glow_alpha / 255)
        img.alpha_composite(g.filter(ImageFilter.GaussianBlur(r)), (x, y))
    img.alpha_composite(tinted(fill, 1.0), (x, y))


def rounded_gradient(size_wh, rad, c0, c1, horizontal=True):
    w, h = size_wh
    if horizontal:
        t = np.linspace(0, 1, w)[None, :]
        t = np.repeat(t, h, axis=0)
    else:
        t = np.linspace(0, 1, h)[:, None]
        t = np.repeat(t, w, axis=1)
    g = np.zeros((h, w, 3), dtype=np.uint8)
    for i in range(3):
        g[..., i] = (c0[i] * (1 - t) + c1[i] * t).astype(np.uint8)
    im = Image.fromarray(g, "RGB").convert("RGBA")
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1],
                                           radius=rad, fill=255)
    im.putalpha(mask)
    return im


def star4(cx, cy, r_out, r_in, rot=-math.pi / 2):
    pts = []
    for i in range(8):
        ang = rot + i * math.pi / 4
        r = r_out if i % 2 == 0 else r_in
        pts.append((cx + math.cos(ang) * r, cy + math.sin(ang) * r))
    return pts


# ---------------------------------------------------------------- star cube
def draw_star_cube(size, trail=True):
    """Падающий светящийся «звёздный куб». Возвращает RGBA size x size."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    cube = int(size * 0.52)
    cx = size // 2 + int(size * 0.05)
    cy = size // 2 + int(size * 0.07)
    x0, y0 = cx - cube // 2, cy - cube // 2
    rad = int(cube * 0.24)

    # --- хвост кометы (вверх-влево) ---
    if trail:
        tl, th = int(size * 0.85), int(size * 0.24)
        xs = np.linspace(0, 1, tl)
        a_col = ((1 - xs) ** 1.6 * 215).astype(np.uint8)
        ys = np.linspace(0, 1, th)
        a_row = (np.sin(ys * math.pi) ** 0.7)[:, None]
        alpha = (a_col[None, :] * a_row).astype(np.uint8)
        grad = np.zeros((th, tl, 4), dtype=np.uint8)
        grad[..., 0], grad[..., 1], grad[..., 2] = 80, 225, 255
        grad[..., 3] = alpha
        tr = Image.fromarray(grad, "RGBA").rotate(135, expand=True,
                                                  resample=Image.BICUBIC)
        tr = tr.filter(ImageFilter.GaussianBlur(size * 0.008))
        # яркий конец — в центре куба
        px = cx - tr.size[0] + int(size * 0.10)
        py = cy - tr.size[1] + int(size * 0.10)
        img.alpha_composite(tr, (px, py))

    # --- внешнее свечение куба ---
    glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.rounded_rectangle([x0, y0, x0 + cube, y0 + cube], radius=rad,
                         fill=TURQ + (150,))
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(size * 0.05)))
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(size * 0.018)))

    # --- тело куба: диагональный градиент бирюза -> индиго/фиолет ---
    body = rounded_gradient((cube, cube), rad, (20, 190, 235), (60, 40, 160),
                            horizontal=False)
    img.alpha_composite(body, (x0, y0))
    d = ImageDraw.Draw(img)
    # верхняя глянцевая кромка
    d.rounded_rectangle([x0, y0, x0 + cube, y0 + cube], radius=rad,
                        outline=(190, 240, 255, 170), width=max(2, size // 256))
    d.arc([x0 + cube * 0.08, y0 + cube * 0.04, x0 + cube * 0.92, y0 + cube * 0.6],
          start=200, end=340, fill=(255, 255, 255, 130),
          width=max(2, size // 200))

    # --- золотая звезда с свечением ---
    sg = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(sg).polygon(
        star4(cx, cy, cube * 0.34, cube * 0.13), fill=GOLD + (230,))
    img.alpha_composite(sg.filter(ImageFilter.GaussianBlur(size * 0.03)))
    d.polygon(star4(cx, cy, cube * 0.30, cube * 0.115), fill=GOLD + (255,))
    d.polygon(star4(cx, cy, cube * 0.14, cube * 0.055),
              fill=(255, 250, 225, 255))
    return img


def paste_cube(img, size, center, angle=0):
    cube = draw_star_cube(size)
    if angle:
        cube = cube.rotate(angle, expand=True, resample=Image.BICUBIC)
    x = int(center[0] - cube.size[0] / 2)
    y = int(center[1] - cube.size[1] / 2)
    img.alpha_composite(cube, (x, y))


def base_space(w, h, seed, blobs, star_count):
    img = vgrad(w, h, [(0.0, (26, 18, 72)), (0.45, INDIGO),
                       (1.0, INDIGO_DEEP)])
    add_nebula(img, blobs)
    add_stars(img, star_count, seed=seed)
    return img


def downscale(img, w, h):
    return img.resize((w, h), Image.LANCZOS)


# ---------------------------------------------------------------- 1. icons
def gen_icon():
    S = 1152
    img = vgrad(S, S, [(0.0, (30, 20, 84)), (0.5, (14, 11, 48)),
                       (1.0, (6, 5, 24))])
    add_nebula(img, [
        (S * 0.25, S * 0.22, S * 0.34, VIOLET, 60),
        (S * 0.85, S * 0.80, S * 0.36, (0, 120, 190), 70),
        (S * 0.70, S * 0.15, S * 0.22, (0, 90, 160), 45),
    ])
    add_stars(img, 170, seed=7)
    paste_cube(img, int(S * 0.92), (S * 0.50, S * 0.52), angle=-8)
    vignette(img, 90)

    for side in (576, 278, 150, 32):
        out = downscale(img, side, side).convert("RGBA")
        out.save(os.path.join(ASSETS, f"icon_{side}.png"))
    print("icons ok")


# ---------------------------------------------------------------- 2. cover
def gen_cover():
    W, H = 1120 * SS, 360 * SS
    img = base_space(W, H, seed=21, blobs=[
        (W * 0.16, H * 0.30, W * 0.22, VIOLET, 55),
        (W * 0.05, H * 0.95, W * 0.20, (0, 110, 190), 60),
        (W * 0.78, H * 0.15, W * 0.24, (0, 90, 170), 65),
        (W * 0.95, H * 0.85, W * 0.18, (150, 60, 160), 45),
    ], star_count=320)

    # --- заголовок ---
    f_title = ImageFont.truetype(FONT_BOLD, 84 * SS)
    f_slogan = ImageFont.truetype(FONT_BOLD, 24 * SS)
    left = 64 * SS
    layer = make_text_layer("ЗВЕЗДОПАД", f_title, tracking=4 * SS)
    paste_neon(img, layer, (left + layer.size[0] / 2, H * 0.40),
               fill=WHITE, glow=TURQ, glow_alpha=235)

    layer2 = make_text_layer("КОСМИЧЕСКАЯ АРКАДА", f_slogan, tracking=10 * SS)
    paste_neon(img, layer2, (left + layer2.size[0] / 2, H * 0.66),
               fill=GOLD, glow=(200, 130, 20), glow_alpha=170,
               radii=[(SS * 10, 0.30), (SS * 5, 0.55), (SS * 2, 0.9)])

    # золотая линия-подчёркивание
    d = ImageDraw.Draw(img)
    ly = int(H * 0.565)
    lg = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(lg).line([left, ly, left + layer.size[0] * 0.62, ly],
                            fill=GOLD + (200,), width=SS * 2)
    img.alpha_composite(lg.filter(ImageFilter.GaussianBlur(SS * 2)))
    ul = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(ul).line([left, ly, left + layer.size[0] * 0.62, ly],
                            fill=(255, 235, 170, 230), width=SS)
    img.alpha_composite(ul)

    # --- падающие кубы справа ---
    paste_cube(img, 200 * SS, (W * 0.795, H * 0.44), angle=-14)
    paste_cube(img, 115 * SS, (W * 0.635, H * 0.72), angle=11)
    paste_cube(img, 82 * SS, (W * 0.925, H * 0.76), angle=-28)
    paste_cube(img, 54 * SS, (W * 0.660, H * 0.20), angle=24)

    vignette(img, 100)
    downscale(img, 1120, 360).convert("RGB").save(
        os.path.join(ASSETS, "cover_1120x360.png"))
    print("cover ok")


# ---------------------------------------------------------------- tetromino
PALETTE = [TURQ, GOLD, VIOLET, PINK, (64, 255, 176)]


def draw_block_cell(img, x, y, cell, color):
    """Один светящийся блок в клетке (x,y — верхний левый угол клетки)."""
    m = max(2, cell // 12)
    box = [x + m, y + m, x + cell - m, y + cell - m]
    rad = max(2, cell // 6)
    c_top = lerp(color, (255, 255, 255), 0.35)
    body = rounded_gradient((cell - 2 * m, cell - 2 * m), rad,
                            c_top, lerp(color, (0, 0, 0), 0.35),
                            horizontal=False)
    img.alpha_composite(body, (box[0], box[1]))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle(box, radius=rad,
                        outline=lerp(color, (255, 255, 255), 0.55) + (160,),
                        width=max(1, SS))
    d.line([box[0] + rad, box[1] + SS, box[2] - rad, box[1] + SS],
           fill=(255, 255, 255, 120), width=max(1, SS))


def field_glow(img, cells_draw_fn):
    """Свечение для набора блоков: рисуем копию в слой, блюрим."""
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    cells_draw_fn(layer, glow_pass=True)
    img.alpha_composite(layer.filter(ImageFilter.GaussianBlur(SS * 7)))


# ---------------------------------------------------------------- 3a. start
def gen_screenshot_start():
    W, H = 800 * SS, 1200 * SS
    img = base_space(W, H, seed=33, blobs=[
        (W * 0.20, H * 0.12, W * 0.30, VIOLET, 55),
        (W * 0.90, H * 0.35, W * 0.26, (0, 110, 190), 60),
        (W * 0.10, H * 0.85, W * 0.28, (0, 90, 170), 50),
        (W * 0.85, H * 0.92, W * 0.24, (150, 60, 160), 42),
    ], star_count=380)

    # логотип-куб
    paste_cube(img, 200 * SS, (W * 0.5, H * 0.175), angle=-8)

    # название
    f_title = ImageFont.truetype(FONT_BOLD, 64 * SS)
    layer = make_text_layer("ЗВЕЗДОПАД", f_title, tracking=3 * SS)
    paste_neon(img, layer, (W * 0.5, H * 0.315), fill=WHITE, glow=TURQ,
               glow_alpha=235)

    f_slogan = ImageFont.truetype(FONT_BOLD, 19 * SS)
    layer2 = make_text_layer("КОСМИЧЕСКАЯ АРКАДА", f_slogan, tracking=8 * SS)
    paste_neon(img, layer2, (W * 0.5, H * 0.362), fill=GOLD,
               glow=(200, 130, 20), glow_alpha=160,
               radii=[(SS * 8, 0.30), (SS * 4, 0.55), (SS * 2, 0.9)])

    # --- кнопка ИГРАТЬ ---
    bw, bh = 340 * SS, 76 * SS
    bx0, by0 = int(W * 0.5 - bw / 2), int(H * 0.425)
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow).rounded_rectangle(
        [bx0, by0, bx0 + bw, by0 + bh], radius=bh // 2, fill=TURQ + (160,))
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(SS * 14)))
    btn = rounded_gradient((bw, bh), bh // 2, (40, 225, 255), (0, 150, 235))
    img.alpha_composite(btn, (bx0, by0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([bx0, by0, bx0 + bw, by0 + bh], radius=bh // 2,
                        outline=(200, 245, 255, 190), width=SS)
    f_btn = ImageFont.truetype(FONT_BOLD, 30 * SS)
    bl = make_text_layer("ИГРАТЬ", f_btn, tracking=6 * SS)
    paste_neon(img, bl, (W * 0.5, by0 + bh / 2), fill=NAVY,
               glow=(255, 255, 255), glow_alpha=90,
               radii=[(SS * 3, 0.5)])

    # --- карточки режимов 2x2 ---
    modes = [
        ("КЛАССИКА", "бесконечная игра", TURQ),
        ("СПРИНТ", "40 линий на скорость", GOLD),
        ("МАРАФОН", "15 уровней скорости", VIOLET),
        ("КОМБО", "серии и множители", PINK),
    ]
    cw, chh = 344 * SS, 128 * SS
    gap = 24 * SS
    gx0 = int(W * 0.5 - cw - gap / 2)
    gy0 = int(H * 0.545)
    f_mt = ImageFont.truetype(FONT_BOLD, 22 * SS)
    f_ms = ImageFont.truetype(FONT_REG, 15 * SS)
    for i, (title, sub, accent) in enumerate(modes):
        x0 = gx0 + (i % 2) * (cw + gap)
        y0 = gy0 + (i // 2) * (chh + gap)
        glass_panel(img, [x0, y0, x0 + cw, y0 + chh], rad=18 * SS)
        # мини-кубик-акцент
        draw_block_cell(img, x0 + 16 * SS, y0 + chh // 2 - 14 * SS,
                        28 * SS, accent)
        d = ImageDraw.Draw(img)
        d.text((x0 + 58 * SS, y0 + 26 * SS), title, font=f_mt,
               fill=WHITE + (255,))
        d.text((x0 + 58 * SS, y0 + 66 * SS), sub, font=f_ms,
               fill=(170, 195, 225, 255))
        d.line([x0 + 58 * SS, y0 + 58 * SS, x0 + cw - 20 * SS, y0 + 58 * SS],
               fill=accent + (70,), width=SS)

    # нижняя строка
    f_small = ImageFont.truetype(FONT_REG, 13 * SS)
    sl = make_text_layer("РЕКОРД: 48 210   ·   УРОВЕНЬ 12", f_small,
                         tracking=2 * SS)
    paste_neon(img, sl, (W * 0.5, gy0 + 2 * chh + gap + 44 * SS),
               fill=(160, 185, 215), glow=(60, 90, 140), glow_alpha=110,
               radii=[(SS * 4, 0.5)])

    vignette(img, 105)
    downscale(img, 800, 1200).convert("RGB").save(
        os.path.join(ASSETS, "screenshot_start.png"))
    print("screenshot_start ok")


# ---------------------------------------------------------------- 3b. game
def gen_screenshot_game():
    W, H = 800 * SS, 1200 * SS
    img = base_space(W, H, seed=44, blobs=[
        (W * 0.12, H * 0.08, W * 0.26, VIOLET, 40),
        (W * 0.95, H * 0.5, W * 0.24, (0, 100, 180), 45),
        (W * 0.08, H * 0.95, W * 0.26, (0, 90, 160), 40),
    ], star_count=260)

    d = ImageDraw.Draw(img)
    f_lab = ImageFont.truetype(FONT_BOLD, 13 * SS)
    f_val = ImageFont.truetype(FONT_BOLD, 26 * SS)

    # --- верхняя HUD-панель: счёт / уровень / линии ---
    hx0, hy0, hx1, hy1 = 40 * SS, 44 * SS, W - 40 * SS, 132 * SS
    glass_panel(img, [hx0, hy0, hx1, hy1], rad=16 * SS)
    stats = [("СЧЁТ", "12 480"), ("УРОВЕНЬ", "3"), ("ЛИНИИ", "27")]
    for i, (lab, val) in enumerate(stats):
        cx = hx0 + (hx1 - hx0) * (i + 0.5) / 3
        ll = make_text_layer(lab, f_lab, tracking=4 * SS)
        paste_neon(img, ll, (cx, hy0 + 26 * SS), fill=GOLD,
                   glow=(180, 120, 20), glow_alpha=120, radii=[(SS * 3, 0.5)])
        vl = make_text_layer(val, f_val, tracking=1 * SS)
        paste_neon(img, vl, (cx, hy0 + 60 * SS), fill=WHITE, glow=TURQ,
                   glow_alpha=150, radii=[(SS * 5, 0.4), (SS * 2, 0.8)])

    # --- панель «СЛЕДУЮЩАЯ» (слева) и «РЕКОРД» (справа) ---
    py0, py1 = 156 * SS, 268 * SS
    nx0, nx1 = 40 * SS, 300 * SS
    glass_panel(img, [nx0, py0, nx1, py1], rad=16 * SS)
    nl = make_text_layer("СЛЕДУЮЩАЯ", f_lab, tracking=4 * SS)
    paste_neon(img, nl, ((nx0 + nx1) / 2, py0 + 22 * SS), fill=GOLD,
               glow=(180, 120, 20), glow_alpha=120, radii=[(SS * 3, 0.5)])
    # T-фигура из мини-блоков
    mb = 22 * SS
    tcx, tcy = (nx0 + nx1) // 2, py0 + 70 * SS
    for dx, dy in [(-1, 0), (0, 0), (1, 0), (0, 1)]:
        draw_block_cell(img, tcx + dx * mb - mb // 2, tcy + dy * mb - mb // 2,
                        mb, VIOLET)

    rx0, rx1 = W - 300 * SS, W - 40 * SS
    glass_panel(img, [rx0, py0, rx1, py1], rad=16 * SS)
    rl = make_text_layer("РЕКОРД", f_lab, tracking=4 * SS)
    paste_neon(img, rl, ((rx0 + rx1) / 2, py0 + 22 * SS), fill=GOLD,
               glow=(180, 120, 20), glow_alpha=120, radii=[(SS * 3, 0.5)])
    rv = make_text_layer("48 210", f_val, tracking=1 * SS)
    paste_neon(img, rv, ((rx0 + rx1) / 2, py0 + 66 * SS), fill=WHITE,
               glow=TURQ, glow_alpha=140, radii=[(SS * 5, 0.4), (SS * 2, 0.8)])

    # --- игровое поле 10x20 ---
    cell = 33 * SS
    fw, fh = 10 * cell, 20 * cell
    fx0 = (W - fw) // 2
    fy0 = 296 * SS
    # стеклянная рамка вокруг поля
    pad = 10 * SS
    glass_panel(img, [fx0 - pad, fy0 - pad, fx0 + fw + pad, fy0 + fh + pad],
                rad=14 * SS, fill=(8, 10, 30, 120))
    # сетка (через слой — для корректного блендинга альфы)
    grid = Image.new("RGBA", img.size, (0, 0, 0, 0))
    gdr = ImageDraw.Draw(grid)
    for i in range(11):
        x = fx0 + i * cell
        gdr.line([x, fy0, x, fy0 + fh], fill=(120, 180, 255, 22), width=1)
    for j in range(21):
        y = fy0 + j * cell
        gdr.line([fx0, y, fx0 + fw, y], fill=(120, 180, 255, 22), width=1)
    img.alpha_composite(grid)

    # --- стек блоков внизу (детерминированный) ---
    rng = random.Random(99)
    heights = [4, 6, 5, 7, 8, 6, 5, 3, 1, 2]  # «колодец» в 9-й колонке
    stack = {}  # (col,row_from_bottom) -> color
    for c in range(10):
        h = heights[c]
        for r in range(h):
            # цвет кластерами
            color = PALETTE[(c // 2 + r // 2 + rng.randint(0, 1)) % len(PALETTE)]
            stack[(c, r)] = color
    # вырезаем пару дыр для естественности
    for hole in [(2, 1), (5, 0), (7, 2), (0, 2)]:
        stack.pop(hole, None)

    def draw_stack(target, glow_pass=False):
        for (c, r), color in stack.items():
            x = fx0 + c * cell
            y = fy0 + fh - (r + 1) * cell
            if glow_pass:
                m = max(2, cell // 12)
                ImageDraw.Draw(target).rounded_rectangle(
                    [x + m, y + m, x + cell - m, y + cell - m],
                    radius=max(2, cell // 6), fill=color + (170,))
            else:
                draw_block_cell(target, x, y, cell, color)

    field_glow(img, draw_stack)
    draw_stack(img)

    # --- активная фигура: I-тетрамино падает ---
    piece = [(4, 2), (4, 3), (4, 4), (4, 5)]  # col,row from top
    def draw_piece(target, glow_pass=False):
        for c, r in piece:
            x, y = fx0 + c * cell, fy0 + r * cell
            if glow_pass:
                m = max(2, cell // 12)
                ImageDraw.Draw(target).rounded_rectangle(
                    [x + m, y + m, x + cell - m, y + cell - m],
                    radius=max(2, cell // 6), fill=TURQ + (200,))
            else:
                draw_block_cell(target, x, y, cell, TURQ)
    field_glow(img, draw_piece)
    draw_piece(img)
    # призрак фигуры (контур внизу)
    ghost_r = 20 - 1 - 8  # приземление на стек высоты 8 -> строка 11 сверху? вычислим: высота колонки 4 = 8, значит верхний блок фигуры на строке 20-8-4
    gr = 20 - heights[4] - 4
    for c, r in [(4, gr), (4, gr + 1), (4, gr + 2), (4, gr + 3)]:
        x, y = fx0 + c * cell, fy0 + r * cell
        m = max(2, cell // 12)
        d.rounded_rectangle([x + m, y + m, x + cell - m, y + cell - m],
                            radius=max(2, cell // 6),
                            outline=TURQ + (70,), width=SS)

    # --- нижняя панель управления ---
    by0 = fy0 + fh + pad + 18 * SS
    bw2, bh2 = 200 * SS, 52 * SS
    glass_panel(img, [W // 2 - bw2 // 2, by0, W // 2 + bw2 // 2, by0 + bh2],
                rad=bh2 // 2)
    pl = make_text_layer("ПАУЗА", f_lab, tracking=6 * SS)
    paste_neon(img, pl, (W // 2, by0 + bh2 // 2), fill=(190, 210, 235),
               glow=TURQ, glow_alpha=110, radii=[(SS * 3, 0.5)])

    vignette(img, 100)
    downscale(img, 800, 1200).convert("RGB").save(
        os.path.join(ASSETS, "screenshot_game.png"))
    print("screenshot_game ok")


if __name__ == "__main__":
    gen_icon()
    gen_cover()
    gen_screenshot_start()
    gen_screenshot_game()
    print("ALL DONE ->", ASSETS)
