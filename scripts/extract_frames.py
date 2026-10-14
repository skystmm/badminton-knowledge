#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extract_frames.py — 羽毛球动作视频抽帧工具

模型看不了动态视频，但看得懂每一帧。本脚本把动作视频按固定频率
抽成帧序列，供「羽析」逐帧观察、跨帧推断发力链条。

用法示例：
  # 普通视频（30fps），默认每秒 2 帧
  python3 extract_frames.py 高远球.mp4 -o frames/

  # 手机慢动作素材（120fps+），建议每秒 5 帧
  python3 extract_frames.py 杀球慢动作.mov --fps 5

  # 长视频只取某个动作片段（从第 3 秒起，取 4 秒）
  python3 extract_frames.py 全场.mp4 --start 3 --duration 4

依赖：ffmpeg（macOS: brew install ffmpeg）
输出：{输出目录}/frame_0001.jpg ... + frames_manifest.txt（帧清单）
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

# 帧数超过该值给出警告：太多帧逐一细看成本高，建议截取动作片段
MAX_FRAMES_WARN = 150


def check_ffmpeg():
    if shutil.which("ffmpeg") is None:
        print("❌ 未找到 ffmpeg，请先安装（macOS: brew install ffmpeg）", file=sys.stderr)
        sys.exit(1)


def parse_time(value):
    """接受秒（数字）或 HH:MM:SS / MM:SS，原样交给 ffmpeg"""
    if value is None:
        return None
    return str(value)


def main():
    parser = argparse.ArgumentParser(
        description="羽毛球动作视频抽帧：按固定频率抽取帧序列，供逐帧动作分析"
    )
    parser.add_argument("video", help="视频文件路径（mp4/mov/m4v 等）")
    parser.add_argument("-o", "--output", default="frames",
                        help="帧输出目录（默认 ./frames）")
    parser.add_argument("--fps", type=float, default=2.0,
                        help="抽帧频率，帧/秒。普通视频默认 2；慢动作素材建议 5（默认: 2）")
    parser.add_argument("--start", default=None,
                        help="片段起始时间，秒或 HH:MM:SS（默认: 视频开头）")
    parser.add_argument("--duration", default=None,
                        help="片段时长，秒或 HH:MM:SS（默认: 到视频结尾）")
    args = parser.parse_args()

    check_ffmpeg()

    video = Path(args.video).expanduser().resolve()
    if not video.is_file():
        print(f"❌ 视频文件不存在: {video}", file=sys.stderr)
        sys.exit(1)

    out_dir = Path(args.output).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    # 组装 ffmpeg 命令（list 形式，路径含空格/中文也安全）
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(video)]
    if args.start:
        cmd += ["-ss", parse_time(args.start)]
    if args.duration:
        cmd += ["-t", parse_time(args.duration)]
    cmd += ["-vf", f"fps={args.fps}", "-q:v", "3",
            str(out_dir / "frame_%04d.jpg")]

    print(f"🎬 抽帧中: {video.name}（{args.fps} 帧/秒）")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ ffmpeg 抽帧失败:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)

    frames = sorted(out_dir.glob("frame_*.jpg"))
    if not frames:
        print("❌ 未抽到任何帧，请检查视频是否有效", file=sys.stderr)
        sys.exit(1)

    # 写帧清单，方便按顺序引用
    manifest = out_dir / "frames_manifest.txt"
    with manifest.open("w", encoding="utf-8") as f:
        f.write(f"# 帧清单 — 共 {len(frames)} 帧\n")
        f.write(f"# 源视频: {video.name} | 抽帧频率: {args.fps} 帧/秒\n")
        if args.start or args.duration:
            f.write(f"# 片段: start={args.start or '开头'} duration={args.duration or '结尾'}\n")
        for fr in frames:
            f.write(f"{fr.name}\n")

    print(f"✅ 抽帧完成：{len(frames)} 帧 → {out_dir}")
    if len(frames) > MAX_FRAMES_WARN:
        print(f"⚠️ 帧数偏多（>{MAX_FRAMES_WARN}），逐帧细看成本高。")
        print("   建议用 --start/--duration 只截取动作片段（单个动作 3-5 秒即可）。")
    print("📋 下一步：按帧序号顺序观察，覆盖 引拍→倒拍→击球→随挥 全过程；")
    print("   在关键帧上标记观察点，最后跨帧汇总发力链条，输出动作分析报告。")


if __name__ == "__main__":
    main()
