#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
draw_diagram.py — 羽毛球技术教学图示生成器

用于**非分析场景**（技术讲解、要点教学、训练指导）：把文字描述变成标准化示意图。
用户没有标准示范素材，AI 生图解剖结构又不可控，因此走程序化绘制——
关节角度即输入，位置即计算结果，角度标注 100% 可信。

子命令：
  pose    人体骨架图（链式关节，支持多帧横向分解 + 点/圆/箭头/文字标注）
  court   羽毛球场俯视图（标准尺寸比例，支持站位、跑位箭头、区域高亮）
  grip    握拍示意图（拍柄八棱截面 + 虎口朝向，正手/反手对比）
  panel   把多张已有图片拼成带标题的教学图

依赖：Pillow（pip install pillow）

用法示例：
  python3 draw_diagram.py pose clear.json -o clear.png
  python3 draw_diagram.py court footwork.json -o footwork.png
  python3 draw_diagram.py grip -o grip.png
  python3 draw_diagram.py panel a.png b.png -o panel.png --labels "正手,反手"
"""

import argparse
import json
import math
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# ---------------- 基础配置 ----------------

FONT_CANDIDATES = [
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
    "/System/Library/Fonts/Supplemental/Songti.ttc",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
]

COLORS = {
    "red": (193, 60, 40),
    "orange": (217, 119, 87),
    "amber": (201, 154, 46),
    "green": (74, 124, 89),
    "blue": (70, 110, 160),
    "purple": (122, 92, 150),
    "white": (255, 255, 255),
    "paper": (247, 242, 232),
    "court": (58, 106, 96),
    "courtline": (250, 250, 245),
    "dark": (43, 37, 32),
    "grey": (150, 142, 132),
    "bone": (223, 214, 198),
}


def load_font(size, bold=False):
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def color_of(name, default=(193, 60, 40)):
    if isinstance(name, (list, tuple)):
        return tuple(name)
    return COLORS.get(str(name).lower(), default)


def draw_text(draw, xy, text, size=20, color=(255, 255, 255),
              stroke=None, stroke_width=None):
    """文字（可选描边）"""
    font = load_font(size)
    x, y = xy
    if stroke is not None:
        draw.text((x, y), text, font=font, fill=color,
                  stroke_width=stroke_width or max(2, size // 10),
                  stroke_fill=stroke)
    else:
        draw.text((x, y), text, font=font, fill=color)


def text_size(text, size):
    f = load_font(size)
    b = ImageDraw.Draw(Image.new("RGB", (4, 4))).textbbox((0, 0), text, font=f)
    return b[2] - b[0], b[3] - b[1]


# ---------------- pose：人体骨架图 ----------------
# 骨架用「链式关节」描述：每个节点给出 parent / len / ang
#   ang = 绝对角度（度），0°=正右，90°=正上，180°=正左，270°=正下（屏幕坐标已翻转）
# 好处：改一个角度就能改一个环节，标注坐标自动跟着算，不用手填像素。

BONE_LINKS = None  # 由 joints 的 parent 关系自动生成


def resolve_skeleton(sk, root_pos):
    """解析链式骨架，返回 {节点名: (x, y)}"""
    pts = {}
    for name, node in sk.items():
        if "pos" in node:
            pts[name] = tuple(node["pos"])
    # 多次迭代以处理任意书写顺序
    for _ in range(len(sk) + 2):
        done = True
        for name, node in sk.items():
            if name in pts:
                continue
            parent = node.get("parent")
            if parent in pts:
                px, py = pts[parent]
                ang = math.radians(node["ang"])
                L = node["len"]
                pts[name] = (px + math.cos(ang) * L, py - math.sin(ang) * L)
                done = False
        if done:
            break
    return pts


def draw_pose_frame(sk, marks, width, height, bg, title, show_ground=True, mirror=False):
    """绘制单幅骨架图"""
    im = Image.new("RGB", (width, height), color_of(bg))
    d = ImageDraw.Draw(im)

    if mirror:
        # 水平镜像：所有 x 用 width - x
        pass

    if show_ground:
        gy = height - 42
        d.line([(0, gy), (width, gy)], fill=color_of("grey"), width=2)
        for x in range(0, width, 26):
            d.line([(x, gy), (x - 8, gy + 10)], fill=color_of("grey"), width=1)

    pts = resolve_skeleton(sk, None)

    def mirror_pt(p):
        return (width - p[0], p[1]) if mirror else p

    pts = {k: mirror_pt(v) for k, v in pts.items()}

    # 画骨骼：每个非空 parent 节点 → 父节点
    order_low = {"hip": 0, "shoulder": 0}
    for name, node in sk.items():
        parent = node.get("parent")
        if not parent or parent not in pts or name not in pts:
            continue
        p1, p2 = pts[parent], pts[name]
        # 躯干画粗一点
        w = 13 if (parent == "hip" and name == "shoulder") else 9
        c = COLORS["bone"] if node.get("ghost") else color_of(node.get("color", "blue"))
        d.line([p1, p2], fill=c, width=w)
        # 关节点
        d.ellipse([p2[0] - 7, p2[1] - 7, p2[0] + 7, p2[1] + 7], fill=c)

    if "hip" in pts:
        d.ellipse([pts["hip"][0] - 8, pts["hip"][1] - 8,
                   pts["hip"][0] + 8, pts["hip"][1] + 8], fill=color_of("blue"))

    # 头部画成圆
    if "head" in pts:
        hx, hy = pts["head"]
        hr = 17
        d.ellipse([hx - hr, hy - hr, hx + hr, hy + hr],
                  fill=COLORS["bone"], outline=color_of("blue"), width=3)

    # 拍面/球拍加粗
    if "wrist" in pts and "racket" in pts:
        d.line([pts["wrist"], pts["racket"]], fill=color_of("orange"), width=6)
        rx, ry = pts["racket"]
        d.ellipse([rx - 12, ry - 16, rx + 12, ry + 16], outline=color_of("orange"), width=4)

    def _pos(mark, extra=(0, 0)):
        """取标注锚点：优先关节名自动算坐标，其次手填 x/y"""
        at = mark.get("at")
        if at and at in pts:
            x, y = pts[at]
        elif "x" in mark and "y" in mark:
            x, y = mark["x"], mark["y"]
        else:
            return None
        return (x + mark.get("dx", 0) + extra[0], y + mark.get("dy", 0) + extra[1])

    # 标注
    for m in marks:
        t = m.get("type")
        col = color_of(m.get("color", "red"))
        size = m.get("size", 20)
        try:
            if t == "circle":
                p = _pos(m)
                cx, cy = p
                r = m.get("r", 22)
                d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=col, width=m.get("width", 4))
                if m.get("label"):
                    draw_text(d, (cx + r + 8, cy - r - 6), m["label"], size=size,
                              color=col, stroke=im.getpixel((2, 2)), stroke_width=3)
            elif t == "dot":
                cx, cy = _pos(m)
                r = m.get("r", 7)
                d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)
            elif t == "arrow":
                p1 = pts[m["from"]] if m.get("from") in pts else (m["x1"], m["y1"])
                p2 = pts[m["to"]] if m.get("to") in pts else (m["x2"], m["y2"])
                arrow_line(d, p1, p2, col, m.get("width", 4))
                if m.get("label"):
                    draw_text(d, ((p1[0] + p2[0]) / 2 + 8, (p1[1] + p2[1]) / 2 - 30),
                              m["label"], size=size, color=col,
                              stroke=im.getpixel((2, 2)), stroke_width=3)
            elif t == "text":
                p = _pos(m)
                draw_text(d, p, m["text"], size=size, color=col,
                          stroke=im.getpixel((2, 2)), stroke_width=3)
            elif t == "arc":
                draw_angle_arc(d, pts, m, col, size, im.getpixel((2, 2)))
        except Exception as e:
            print(f"   ⚠️ 跳过标注 {t}：{e}")
            continue

    if title:
        tw, _ = text_size(title, 24)
        draw_text(d, ((width - tw) / 2, 10), title, size=24, color=color_of("dark"))
    return im


def draw_angle_arc(d, pts, m, col, size, bg_pixel):
    """角度弧线标注：以 at 为中心，两条边指向 arm1 / arm2。

    arm1/arm2 支持特殊值：
      "vertical"   —— 从该点向上的垂线（用于标躯干倾角 / 后仰角）
      "horizontal" —— 从该点向右的水平线（用于标抬肘高度）
    """
    center_name = m["at"]
    if center_name not in pts:
        print(f"   ⚠️ 跳过 arc：中心点 {center_name} 不存在")
        return
    c = pts[center_name]

    def _ref(v):
        if v == "vertical":
            return (c[0], c[1] - 100)
        if v == "horizontal":
            return (c[0] + 100, c[1])
        if v in pts:
            return pts[v]
        return None

    a = _ref(m.get("arm1"))
    b = _ref(m.get("arm2"))
    if a is None or b is None:
        print(f"   ⚠️ 跳过 arc：参考点 {m.get('arm1')}/{m.get('arm2')} 不存在")
        return

    # 补画参考虚线，让「跟什么比」一目了然
    if m.get("arm1") in ("vertical", "horizontal") and m.get("ref_line", True):
        for i in range(0, 80, 6):
            p1 = (c[0], c[1] - i) if m["arm1"] == "vertical" else (c[0] + i, c[1])
            p2 = (c[0], c[1] - i - 3) if m["arm1"] == "vertical" else (c[0] + i + 3, c[1])
            d.line([p1, p2], fill=col, width=2)

    a1 = math.degrees(math.atan2(-(a[1] - c[1]), a[0] - c[0]))
    a2 = math.degrees(math.atan2(-(b[1] - c[1]), b[0] - c[0]))
    r = m.get("r", 40)
    bb = [c[0] - r, c[1] - r, c[0] + r, c[1] + r]
    # PIL 的 arc 角度是「顺时针、从 3 点方向起」，与数学角相反；且只按 start→end 顺时针画。
    # 因此换算成 PIL 角后，走「劣弧」（差值取 ±180 内），避免画成整圆。
    a1p = (-a1) % 360
    a2p = (-a2) % 360
    delta = (a1p - a2p) % 360
    if delta > 180:
        delta -= 360
    d.arc(bb, start=a2p, end=a2p + delta, fill=col, width=m.get("width", 4))
    # 标签放在劣弧中点方向
    delta_math = ((a1 - a2 + 180) % 360) - 180
    mid = math.radians(a2 + delta_math / 2)
    lx, ly = c[0] + math.cos(mid) * (r + 20), c[1] - math.sin(mid) * (r + 20)
    if m.get("label"):
        draw_text(d, (lx - 14, ly - 10), m["label"], size=size, color=col,
                  stroke=bg_pixel, stroke_width=3)


def arrow_line(d, p1, p2, color, width=4, head=15):
    d.line([p1, p2], fill=color, width=width)
    ang = math.atan2(p2[1] - p1[1], p2[0] - p1[0])
    for dsign in (-0.42, 0.42):
        d.line([p2, (p2[0] - head * math.cos(ang + dsign),
                     p2[1] - head * math.sin(ang + dsign))],
               fill=color, width=width)


def cmd_pose(args):
    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    frames = spec["frames"]
    w = spec.get("width", 420)
    h = spec.get("height", 520)
    bg = spec.get("bg", "paper")
    gap = spec.get("gap", 16)
    pad_top = 54 if spec.get("title") else 0

    ims = []
    for f in frames:
        ims.append(draw_pose_frame(
            f["skeleton"], f.get("marks", []), w, h, bg, f.get("name"),
            show_ground=f.get("ground", True), mirror=f.get("mirror", False)))

    cols = len(ims)
    canvas = Image.new("RGB", (cols * w + (cols - 1) * gap, h + pad_top),
                       color_of(spec.get("canvas_bg", "dark")))
    for i, im in enumerate(ims):
        canvas.paste(im, (i * (w + gap), pad_top))

    if spec.get("title"):
        d = ImageDraw.Draw(canvas)
        tw, _ = text_size(spec["title"], 30)
        draw_text(d, ((canvas.width - tw) / 2, 12), spec["title"], size=30,
                  color=color_of(spec.get("title_color", "white")))

    canvas.save(args.output, quality=95)
    print(f"✅ 骨架图：{args.output}（{canvas.width}×{canvas.height}，{cols} 帧）")


# ---------------- court：场地俯视图 ----------------

COURT_W = 6.10      # 双打场地宽（米）
COURT_L = 13.40     # 全场长（米）
NET_Y = 6.70
FRONT_SERVICE = 1.98
DOUBLE_LONG_SERVICE = 0.76
SINGLES_W = 5.18


def cmd_court(args):
    spec = json.loads(Path(args.spec).read_text(encoding="utf-8")) if args.spec else {}
    scale = spec.get("scale", 84)        # px / m
    margin = spec.get("margin", 60)
    half_only = spec.get("half", False)

    length = NET_Y if half_only else COURT_L
    W = int(COURT_W * scale) + margin * 2
    H = int(length * scale) + margin * 2

    im = Image.new("RGB", (W, H), color_of(spec.get("bg", "dark")))
    d = ImageDraw.Draw(im)
    court_col = color_of(spec.get("court", "court"))
    line_col = color_of(spec.get("line", "courtline"))

    def P(x_m, y_m):
        """米坐标 → 像素。x 从左双打边线起，y 从本方底线起"""
        return (margin + x_m * scale, margin + (length - y_m) * scale)

    p_bl = P(0, 0)                 # 左下角（米坐标原点）
    p_tr = P(COURT_W, length)      # 右上角
    rx0, rx1 = sorted((p_bl[0], p_tr[0]))
    ry0, ry1 = sorted((p_bl[1], p_tr[1]))
    d.rectangle([rx0, ry0, rx1, ry1], fill=court_col)

    lw = 3
    # 外框（双打边线 + 底线）
    d.rectangle([rx0, ry0, rx1, ry1], outline=line_col, width=lw)
    # 单打边线
    sx = (COURT_W - SINGLES_W) / 2
    for xm in (sx, COURT_W - sx):
        ax, ay = P(xm, 0)
        bx, by = P(xm, length)
        d.line([ax, ay, bx, by], fill=line_col, width=lw)
    # 中线（本方半场：从底线到前发球线）
    cx = COURT_W / 2
    for (ya, yb) in ((0, 1.98), (11.42, 13.40)):
        ax, ay = P(cx, ya)
        bx, by = P(cx, yb)
        d.line([ax, ay, bx, by], fill=line_col, width=lw)
    # 前发球线
    for ym in (NET_Y - FRONT_SERVICE, NET_Y + FRONT_SERVICE):
        ax, ay = P(0, ym)
        bx, by = P(COURT_W, ym)
        d.line([ax, ay, bx, by], fill=line_col, width=lw)
    # 双打后发球线
    for ym in (DOUBLE_LONG_SERVICE, COURT_L - DOUBLE_LONG_SERVICE):
        ax, ay = P(0, ym)
        bx, by = P(COURT_W, ym)
        d.line([ax, ay, bx, by], fill=line_col, width=lw)
    # 网
    nx0, ny = P(0, NET_Y)
    nx1, _ = P(COURT_W, NET_Y)
    d.line([nx0, ny, nx1, ny], fill=color_of(spec.get("net", "white")), width=8)

    # 标注
    for m in spec.get("marks", []):
        t = m.get("type")
        col = color_of(m.get("color", "orange"))
        size = m.get("size", 20)
        if t == "zone":
            x1m, y1m, x2m, y2m = m["rect"]
            a = P(x1m, y1m)
            b = P(x2m, y2m)
            overlay = Image.new("RGBA", im.size, (0, 0, 0, 0))
            ImageDraw.Draw(overlay).rectangle([a[0], b[1], b[0], a[1]],
                                              fill=col + (m.get("alpha", 70),))
            im.paste(Image.alpha_composite(im.convert("RGBA"), overlay).convert("RGB"), (0, 0))
            d = ImageDraw.Draw(im)
            if m.get("label"):
                tw, th = text_size(m["label"], size)
                draw_text(d, ((a[0] + b[0] - tw) / 2, (a[1] + b[1] - th) / 2),
                          m["label"], size=size, color=color_of("white"),
                          stroke=color_of("dark"), stroke_width=3)
        elif t == "dot":
            x, y = P(*m["at"])
            r = m.get("r", 13)
            d.ellipse([x - r, y - r, x + r, y + r], fill=col, outline=color_of("white"), width=2)
            if m.get("label"):
                draw_text(d, (x + r + 6, y - 12), m["label"], size=size,
                          color=col, stroke=color_of("dark"), stroke_width=3)
        elif t == "move":
            p1 = P(*m["from"])
            p2 = P(*m["to"])
            arrow_line(d, p1, p2, col, m.get("width", 5), head=m.get("head", 16))
            if m.get("label"):
                tw, th = text_size(m["label"], size)
                draw_text(d, ((p1[0] + p2[0] - tw) / 2, (p1[1] + p2[1] - th) / 2 - 24),
                          m["label"], size=size, color=col,
                          stroke=color_of("dark"), stroke_width=3)
        elif t == "text":
            x, y = m["x"], m["y"]
            draw_text(d, (x, y), m["text"], size=size, color=col,
                      stroke=color_of("dark"), stroke_width=3)

    if spec.get("title"):
        pad = 52
        canvas = Image.new("RGB", (im.width, im.height + pad), color_of("dark"))
        canvas.paste(im, (0, pad))
        dd = ImageDraw.Draw(canvas)
        tw, _ = text_size(spec["title"], 30)
        draw_text(dd, ((canvas.width - tw) / 2, 12), spec["title"], size=30,
                  color=color_of("white"))
        im = canvas

    im.save(args.output, quality=95)
    print(f"✅ 场地图：{args.output}（{im.width}×{im.height}）")


# ---------------- grip：握拍示意 ----------------

def cmd_grip(args):
    spec = json.loads(Path(args.spec).read_text(encoding="utf-8")) if args.spec else {}
    items = spec.get("grips", [
        {"name": "正手握拍（基础）", "thumb": "宽面/大棱面", "index": "食指略分开成“扣扳机”",
         "note": "虎口对准宽棱面\n掌心留空，像握小鸟",
         "v_pos": "left"},
        {"name": "反手握拍", "thumb": "拇指顶住宽面", "index": "拇指斜压在拍柄宽面上",
         "note": "先正手握，再向内旋\n拇指上抬顶住宽面",
         "v_pos": "topleft"},
    ])
    W, H = 560, 560
    panels = []
    for g in items:
        im = Image.new("RGB", (W, H), color_of("paper"))
        d = ImageDraw.Draw(im)
        cx, cy, R = W // 2, H // 2 - 10, 150

        # 八棱截面
        oct_pts = []
        for i in range(8):
            a = math.radians(22.5 + 45 * i)
            oct_pts.append((cx + R * math.cos(a), cy - R * math.sin(a)))
        d.polygon(oct_pts, fill=(226, 214, 190), outline=color_of("dark"), width=3)
        # 标出宽面：顶边 i=1（数学角 67.5°-112.5°）与其对边 i=5
        for i, wd in ((1, 10), (5, 6)):
            a, b = oct_pts[i], oct_pts[(i + 1) % 8]
            d.line([a, b], fill=color_of("orange"), width=wd)
        # 宽面标注统一放底部宽棱旁，顶部留给指位标注
        draw_text(d, (cx - 80, cy + R + 14), "↕ 宽面（大棱面）", size=19,
                  color=color_of("orange"), stroke=color_of("paper"), stroke_width=3)

        # 虎口 V 形 + 拇指/食指位置；标签偏移可由 spec 覆盖
        vp = g.get("v_pos", "left")
        if vp == "left":
            hx, hy = cx - R - 44, cy + 10
            tx, ty = cx - R - 10, cy + 52
            ix, iy = cx - R - 10, cy - 32
            tl, il, hl = (-20, 26), (-20, -52), (-44, 26)
        elif vp == "topleft":
            hx, hy = cx - R - 66, cy - R + 4
            tx, ty = cx - 10, cy - R - 14
            ix, iy = cx - R + 34, cy - R + 16
            tl, il, hl = (24, -44), (-64, -6), (-58, -8)
        else:
            hx, hy = cx, cy - R - 44
            tx, ty = cx + 40, cy - R - 10
            ix, iy = cx - 40, cy - R - 10
            tl, il, hl = (6, -48), (-64, -48), (-30, -70)
        tl = g.get("thumb_label", tl)
        il = g.get("index_label", il)
        hl = g.get("hu_label", hl)
        d.polygon([(hx, hy + 22), (hx + 26, hy - 26), (hx + 52, hy + 22)],
                  fill=color_of("green"))
        draw_text(d, (hx + hl[0], hy + hl[1]), "虎口", size=20, color=color_of("green"),
                  stroke=color_of("paper"), stroke_width=3)
        for (px, py, lb, c, off) in ((tx, ty, "拇指", "red", tl), (ix, iy, "食指", "blue", il)):
            d.ellipse([px - 20, py - 20, px + 20, py + 20], fill=color_of(c),
                      outline=color_of("white"), width=2)
            draw_text(d, (px + off[0], py + off[1]), lb, size=18, color=color_of(c),
                      stroke=color_of("paper"), stroke_width=3)

        # 说明
        y = H - 118
        for line in [g.get("note", ""), "",
                     "拇指位置：" + g.get("thumb", ""),
                     "食指：" + g.get("index", "")]:
            if line:
                draw_text(d, (26, y), line, size=19, color=color_of("dark"))
            y += 30
        draw_text(d, (20, 16), g.get("name", ""), size=26, color=color_of("dark"))
        panels.append(im)

    gap = 16
    canvas = Image.new("RGB", (len(panels) * W + (len(panels) - 1) * gap, H), color_of("dark"))
    for i, p in enumerate(panels):
        canvas.paste(p, (i * (W + gap), 0))
    canvas.save(args.output, quality=95)
    print(f"✅ 握拍图：{args.output}（{canvas.width}×{canvas.height}）")


# ---------------- panel：通用拼图 ----------------

def cmd_panel(args):
    ims = [(Image.open(p).convert("RGB"), Path(p).stem) for p in args.images]
    if args.labels:
        labels = args.labels.split(",")
    else:
        labels = [n for _, n in ims]

    target_h = args.height
    ims_r = []
    for im, _ in ims:
        w = int(im.width * target_h / im.height)
        ims_r.append(im.resize((w, target_h), Image.LANCZOS))

    pad_top = 46 if args.title else 0
    gap = args.gap
    total_w = sum(i.width for i in ims_r) + gap * (len(ims_r) - 1)
    canvas = Image.new("RGB", (total_w, target_h + pad_top), color_of(args.bg))
    d = ImageDraw.Draw(canvas)
    x = 0
    for im, lb in zip(ims_r, labels):
        canvas.paste(im, (x, pad_top))
        tw, _ = text_size(lb, 22)
        draw_text(d, (x + (im.width - tw) / 2, pad_top + 8), lb, size=22,
                  color=color_of("white"), stroke=color_of("dark"), stroke_width=3)
        x += im.width + gap
    if args.title:
        tw, _ = text_size(args.title, 28)
        draw_text(d, ((canvas.width - tw) / 2, 10), args.title, size=28,
                  color=color_of("white"))
    canvas.save(args.output, quality=95)
    print(f"✅ 拼图：{args.output}（{canvas.width}×{canvas.height}）")


# ---------------- CLI ----------------

def main():
    p = argparse.ArgumentParser(description="羽毛球技术教学图示生成器")
    sub = p.add_subparsers(dest="cmd", required=True)

    po = sub.add_parser("pose", help="人体骨架图（多帧分解）")
    po.add_argument("spec", help="JSON 规格文件")
    po.add_argument("-o", "--output", default="pose.png")
    po.set_defaults(func=cmd_pose)

    co = sub.add_parser("court", help="场地俯视图")
    co.add_argument("spec", nargs="?", default=None, help="JSON 规格文件")
    co.add_argument("-o", "--output", default="court.png")
    co.set_defaults(func=cmd_court)

    gr = sub.add_parser("grip", help="握拍示意图")
    gr.add_argument("spec", nargs="?", default=None)
    gr.add_argument("-o", "--output", default="grip.png")
    gr.set_defaults(func=cmd_grip)

    pa = sub.add_parser("panel", help="多图拼接")
    pa.add_argument("images", nargs="+")
    pa.add_argument("-o", "--output", default="panel.png")
    pa.add_argument("--labels", default=None, help="逗号分隔的标签")
    pa.add_argument("--title", default=None)
    pa.add_argument("--height", type=int, default=420)
    pa.add_argument("--gap", type=int, default=16)
    pa.add_argument("--bg", default="dark")
    pa.set_defaults(func=cmd_panel)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
