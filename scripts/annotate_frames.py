#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
annotate_frames.py — 羽毛球动作帧标注工具

把「文字诊断」变成「图上可见」：圈出问题部位、画出理想位置对比、
多帧叠加出挥拍轨迹、放大局部看细节、并排对比两次动作。

子命令：
  grid     画坐标网格（用于精确定位标注坐标）
  crop     裁剪并放大局部（细节图）
  ghost    多帧叠加生成挥拍轨迹图（blend 残影 / trail 差异高亮）
  mark     按 JSON 规格在帧上画标注（圆圈/框/箭头/文字）
  compare  两帧左右并排对比（如改进前 vs 改进后）

用法示例：
  python3 annotate_frames.py grid frames/frame_0030.jpg -o grid.jpg
  python3 annotate_frames.py crop frames/frame_0030.jpg -o zoom.jpg --box 150,110,320,300 --scale 2
  python3 annotate_frames.py ghost frames/ -o trail.jpg --from 26 --to 36 --mode trail
  python3 annotate_frames.py mark frames/frame_0030.jpg -o marked.jpg --spec spec.json
  python3 annotate_frames.py compare a.jpg b.jpg -o cmp.jpg --label-a "改进前" --label-b "改进后"

依赖：Pillow（pip install pillow）
"""

import argparse
import json
import os
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont

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
    "white": (255, 255, 255),
    "dark": (43, 37, 32),
}


def load_font(size):
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def color_of(name, default=(193, 60, 40)):
    return COLORS.get(str(name).lower(), default)


def draw_text(draw, xy, text, size=20, color=(255, 255, 255), stroke=(43, 37, 32)):
    """带描边的中文文字，保证在任何背景上都可读"""
    font = load_font(size)
    x, y = xy
    draw.text((x, y), text, font=font, fill=color,
              stroke_width=max(2, size // 10), stroke_fill=stroke)


def cmd_grid(args):
    im = Image.open(args.image).convert("RGB")
    d = ImageDraw.Draw(im)
    w, h = im.size
    step = args.step
    for x in range(0, w, step):
        d.line([(x, 0), (x, h)], fill=(255, 255, 255, 128), width=1)
        if x % (step * 2) == 0:
            draw_text(d, (x + 3, 3), str(x), size=14, color=(255, 255, 0))
    for y in range(0, h, step):
        d.line([(0, y), (w, y)], fill=(255, 255, 255, 128), width=1)
        if y % (step * 2) == 0:
            draw_text(d, (3, y + 3), str(y), size=14, color=(255, 255, 0))
    im.save(args.output, quality=92)
    print(f"✅ 网格图：{args.output}（尺寸 {w}×{h}，格距 {step}px）")


def cmd_crop(args):
    im = Image.open(args.image).convert("RGB")
    box = tuple(int(v) for v in args.box.split(","))
    crop = im.crop(box)
    if args.scale and args.scale != 1:
        crop = crop.resize((crop.width * args.scale, crop.height * args.scale),
                           Image.LANCZOS)
    if args.label:
        pad = 40
        canvas = Image.new("RGB", (crop.width, crop.height + pad), (43, 37, 32))
        canvas.paste(crop, (0, pad))
        draw_text(ImageDraw.Draw(canvas), (10, 8), args.label, size=22)
        crop = canvas
    crop.save(args.output, quality=94)
    print(f"✅ 细节图：{args.output}（{crop.width}×{crop.height}，放大 {args.scale}×）")


def cmd_ghost(args):
    src = Path(args.frames_dir)
    nums = list(range(args.start, args.end + 1, max(1, args.every)))
    paths = [src / f"frame_{n:04d}.jpg" for n in nums]
    paths = [p for p in paths if p.exists()]
    if len(paths) < 2:
        print("❌ 可用帧不足 2 张，检查 --start/--end 与目录", file=sys.stderr)
        sys.exit(1)

    base = Image.open(paths[0]).convert("RGB")
    if args.box:
        box = tuple(int(v) for v in args.box.split(","))
        paths_scaled = [args.box]  # 记录裁剪区域（沿用同一坐标系）
        base = base.crop(box)
    if args.mode == "blend":
        out = base.convert("RGBA")
        for p in paths[1:]:
            layer = Image.open(p).convert("RGB")
            if args.box:
                layer = layer.crop(box)
            layer = layer.convert("RGBA")
            layer.putalpha(int(255 * args.alpha))
            out = Image.alpha_composite(out, layer)
        result = out.convert("RGB")
    else:  # trail：帧间差异区域染色，高亮运动轨迹
        result = base.copy()
        prev = base
        acc = Image.new("L", base.size, 0)
        for p in paths[1:]:
            cur = Image.open(p).convert("RGB")
            if args.box:
                cur = cur.crop(box)
            diff = ImageChops.difference(prev, cur).convert("L")
            acc = ImageChops.lighter(acc, diff.point(lambda v: 255 if v > args.threshold else 0))
            prev = cur
        result.paste(Image.new("RGB", base.size, COLORS["orange"]), (0, 0), acc)
        result = Image.blend(base, result, 0.62)

    if args.title:
        pad = 46
        canvas = Image.new("RGB", (result.width, result.height + pad), (43, 37, 32))
        canvas.paste(result, (0, pad))
        draw_text(ImageDraw.Draw(canvas), (12, 10), args.title, size=24)
        result = canvas
    result.save(args.output, quality=92)
    print(f"✅ 轨迹图：{args.output}（叠加 {len(paths)} 帧，模式 {args.mode}）")


def cmd_mark(args):
    im = Image.open(args.image).convert("RGB")
    d = ImageDraw.Draw(im)
    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))

    for item in spec:
        t = item.get("type")
        color = color_of(item.get("color", "red"))
        width = item.get("width", 4)
        if t == "circle":
            x, y, r = item["x"], item["y"], item["r"]
            d.ellipse([x - r, y - r, x + r, y + r], outline=color, width=width)
            if item.get("label"):
                draw_text(d, (x + r + 8, y - 12), item["label"],
                          size=item.get("size", 20), color=color)
        elif t == "box":
            x, y, w, h = item["x"], item["y"], item["w"], item["h"]
            d.rectangle([x, y, x + w, y + h], outline=color, width=width)
            if item.get("label"):
                draw_text(d, (x + 4, y - 28), item["label"],
                          size=item.get("size", 20), color=color)
        elif t == "arrow":
            x1, y1, x2, y2 = item["x1"], item["y1"], item["x2"], item["y2"]
            d.line([x1, y1, x2, y2], fill=color, width=width)
            # 箭头头部
            import math
            ang = math.atan2(y2 - y1, x2 - x1)
            L = 14
            d.line([x2, y2, x2 - L * math.cos(ang - 0.42), y2 - L * math.sin(ang - 0.42)],
                   fill=color, width=width)
            d.line([x2, y2, x2 - L * math.cos(ang + 0.42), y2 - L * math.sin(ang + 0.42)],
                   fill=color, width=width)
            if item.get("label"):
                mx, my = (x1 + x2) // 2, (y1 + y2) // 2
                draw_text(d, (mx + 6, my - 26), item["label"],
                          size=item.get("size", 20), color=color)
        elif t == "text":
            draw_text(d, (item["x"], item["y"]), item["text"],
                      size=item.get("size", 22), color=color_of(item.get("color", "white")))

    im.save(args.output, quality=94)
    print(f"✅ 标注图：{args.output}（{len(spec)} 个标注）")


def cmd_compare(args):
    a = Image.open(args.image_a).convert("RGB")
    b = Image.open(args.image_b).convert("RGB")
    pad_top, gap = 46, 12
    h = max(a.height, b.height)
    canvas = Image.new("RGB", (a.width + b.width + gap, h + pad_top), (43, 37, 32))
    canvas.paste(a, (0, pad_top))
    canvas.paste(b, (a.width + gap, pad_top))
    d = ImageDraw.Draw(canvas)
    draw_text(d, (12, 10), args.label_a, size=24, color=COLORS["orange"])
    draw_text(d, (a.width + gap + 12, 10), args.label_b, size=24, color=COLORS["green"])
    canvas.save(args.output, quality=92)
    print(f"✅ 对比图：{args.output}（{canvas.width}×{canvas.height}）")


def main():
    p = argparse.ArgumentParser(description="羽毛球动作帧标注工具")
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("grid", help="画坐标网格（定位用）")
    g.add_argument("image"); g.add_argument("-o", "--output", default="grid.jpg")
    g.add_argument("--step", type=int, default=96, help="网格间距（默认 96px）")
    g.set_defaults(func=cmd_grid)

    c = sub.add_parser("crop", help="裁剪放大局部")
    c.add_argument("image"); c.add_argument("-o", "--output", default="crop.jpg")
    c.add_argument("--box", required=True, help="裁剪区域 x1,y1,x2,y2")
    c.add_argument("--scale", type=int, default=2, help="放大倍数")
    c.add_argument("--label", default=None, help="图片顶部标题")
    c.set_defaults(func=cmd_crop)

    gh = sub.add_parser("ghost", help="多帧叠加轨迹图")
    gh.add_argument("frames_dir"); gh.add_argument("-o", "--output", default="ghost.jpg")
    gh.add_argument("--start", type=int, required=True)
    gh.add_argument("--end", type=int, required=True)
    gh.add_argument("--every", type=int, default=1, help="每隔几帧取一张")
    gh.add_argument("--mode", choices=["blend", "trail"], default="trail")
    gh.add_argument("--alpha", type=float, default=0.35, help="blend 模式不透明度")
    gh.add_argument("--threshold", type=int, default=28, help="trail 模式差异阈值")
    gh.add_argument("--box", default=None, help="只分析该区域 x1,y1,x2,y2（聚焦单人）")
    gh.add_argument("--title", default=None)
    gh.set_defaults(func=cmd_ghost)

    m = sub.add_parser("mark", help="按 JSON 规格画标注")
    m.add_argument("image"); m.add_argument("-o", "--output", default="marked.jpg")
    m.add_argument("--spec", required=True, help="标注规格 JSON 文件")
    m.set_defaults(func=cmd_mark)

    cp = sub.add_parser("compare", help="两帧并排对比")
    cp.add_argument("image_a"); cp.add_argument("image_b")
    cp.add_argument("-o", "--output", default="compare.jpg")
    cp.add_argument("--label-a", default="A"); cp.add_argument("--label-b", default="B")
    cp.set_defaults(func=cmd_compare)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
