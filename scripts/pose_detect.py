#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pose_detect.py — 羽毛球动作骨骼关键点检测与关节角度量化

基于 MediaPipe Pose Landmarker（tasks API），检测画面中最多 N 人的 33 个
骨骼关键点，输出像素坐标、关键关节角度，并生成骨架叠加图。

用法：
  python3 pose_detect.py frame.jpg -o skeleton.jpg --json pose.json [--num-poses 4]
  python3 pose_detect.py frames/ --start 26 --end 36 -o out_dir/ --json pose.json

角度定义：
  肘角   = 肩-肘-腕 夹角（180=完全伸直）
  肩角   = 髋-肩-肘 夹角（手臂上举程度，180=手臂与躯干同向伸直）
  膝角   = 髋-膝-踝 夹角（起跳蓄力时越小蹲得越深）
  躯干倾角 = 肩中点-髋中点 连线与竖直方向夹角（后仰程度）

依赖：mediapipe>=1.0, opencv-python-headless, pillow
模型：pose_landmarker_full.task
  https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/1/pose_landmarker_full.task
"""

import argparse
import json
import math
import sys
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

# 关键连接（MediaPipe Pose 33 点索引）
CONNECTIONS = [
    (11, 12), (11, 13), (13, 15), (12, 14), (14, 16),          # 肩肘腕
    (11, 23), (12, 24), (23, 24),                               # 躯干
    (23, 25), (25, 27), (24, 26), (26, 28),                     # 髋膝踝
    (27, 31), (28, 32),                                         # 脚
]
JOINT_NAMES = {
    0: "鼻", 11: "左肩", 12: "右肩", 13: "左肘", 14: "右肘",
    15: "左腕", 16: "右腕", 23: "左髋", 24: "右髋",
    25: "左膝", 26: "右膝", 27: "左踝", 28: "右踝",
}


def angle(a, b, c):
    """三点夹角（b 为顶点），单位度"""
    va = np.array([a[0] - b[0], a[1] - b[1]])
    vc = np.array([c[0] - b[0], c[1] - b[1]])
    na, nc = np.linalg.norm(va), np.linalg.norm(vc)
    if na < 1e-6 or nc < 1e-6:
        return None
    cos = np.clip(np.dot(va, vc) / (na * nc), -1.0, 1.0)
    return round(math.degrees(math.acos(cos)), 1)


def analyze_person(lms, w, h):
    """把归一化关键点转为像素坐标并计算角度"""
    px = {i: (lm.x * w, lm.y * h, lm.visibility) for i, lm in enumerate(lms)}
    have = lambda i: i in px and px[i][2] > 0.5

    angles = {}
    if all(have(i) for i in (11, 13, 15)):
        angles["左肘角"] = angle(px[11][:2], px[13][:2], px[15][:2])
    if all(have(i) for i in (12, 14, 16)):
        angles["右肘角"] = angle(px[12][:2], px[14][:2], px[16][:2])
    if all(have(i) for i in (23, 11, 13)):
        angles["左肩角"] = angle(px[23][:2], px[11][:2], px[13][:2])
    if all(have(i) for i in (24, 12, 16)):
        angles["右肩角"] = angle(px[24][:2], px[12][:2], px[16][:2])
    if all(have(i) for i in (23, 25, 27)):
        angles["左膝角"] = angle(px[23][:2], px[25][:2], px[27][:2])
    if all(have(i) for i in (24, 26, 28)):
        angles["右膝角"] = angle(px[24][:2], px[26][:2], px[28][:2])
    if all(have(i) for i in (11, 12, 23, 24)):
        sm = ((px[11][0] + px[12][0]) / 2, (px[11][1] + px[12][1]) / 2)
        hm = ((px[23][0] + px[24][0]) / 2, (px[23][1] + px[24][1]) / 2)
        lean = math.degrees(math.atan2(abs(sm[0] - hm[0]), abs(sm[1] - hm[1])))
        angles["躯干倾角(后仰)"] = round(lean, 1)

    points = {JOINT_NAMES.get(i, str(i)): {"x": round(v[0]), "y": round(v[1]),
                                           "vis": round(v[2], 2)}
              for i, v in px.items() if v[2] > 0.4}
    return points, angles


def draw_skeleton(img_bgr, lms, color=(60, 160, 90), person_tag=""):
    h, w = img_bgr.shape[:2]
    pts = [(int(lm.x * w), int(lm.y * h)) for lm in lms]
    for a, b in CONNECTIONS:
        if a < len(pts) and b < len(pts):
            cv2.line(img_bgr, pts[a], pts[b], color, 2, cv2.LINE_AA)
    for i, p in enumerate(pts):
        if i in JOINT_NAMES:
            cv2.circle(img_bgr, p, 4, (0, 90, 200), -1, cv2.LINE_AA)
    if person_tag and pts:
        cv2.putText(img_bgr, person_tag, (pts[0][0] - 40, max(20, pts[0][1] - 34)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 4, cv2.LINE_AA)
        cv2.putText(img_bgr, person_tag, (pts[0][0] - 40, max(20, pts[0][1] - 34)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (40, 60, 200), 2, cv2.LINE_AA)
    return img_bgr


def detect_image(detector, path, num_poses):
    img = cv2.imread(str(path))
    if img is None:
        return None
    h, w = img.shape[:2]
    mp_img = mp.Image(image_format=mp.ImageFormat.SRGB,
                      data=cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    res = detector.detect(mp_img)

    people = []
    for idx, lms in enumerate(res.pose_landmarks):
        points, angles = analyze_person(lms, w, h)
        xs = [lm.x for lm in lms]
        person = {
            "id": idx,
            "bbox_x": [round(min(xs) * w), round(max(xs) * w)],
            "points": points,
            "angles": angles,
        }
        people.append(person)
        img = draw_skeleton(img, lms, person_tag=f"P{idx}")
    return img, people


def main():
    p = argparse.ArgumentParser(description="羽毛球动作骨骼检测与角度量化")
    p.add_argument("input", help="单帧图片或帧目录")
    p.add_argument("-o", "--output", default="skeleton.jpg", help="骨架叠加图（目录输入时为输出目录）")
    p.add_argument("--json", default=None, help="关键点与角度输出 JSON 路径")
    p.add_argument("--model", required=True, help="pose_landmarker_full.task 路径")
    p.add_argument("--num-poses", type=int, default=4, help="画面最多检测人数")
    p.add_argument("--start", type=int, default=None)
    p.add_argument("--end", type=int, default=None)
    p.add_argument("--every", type=int, default=1)
    args = p.parse_args()

    options = vision.PoseLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=args.model),
        running_mode=vision.RunningMode.IMAGE,
        num_poses=args.num_poses,
        min_pose_detection_confidence=0.3,
        min_pose_presence_confidence=0.3,
    )
    detector = vision.PoseLandmarker.create_from_options(options)

    src = Path(args.input)
    out = Path(args.output)
    if src.is_dir():
        out.mkdir(parents=True, exist_ok=True)
        nums = list(range(args.start, args.end + 1, max(1, args.every)))
        targets = [src / f"frame_{n:04d}.jpg" for n in nums]
        targets = [t for t in targets if t.exists()]
    else:
        out.parent.mkdir(parents=True, exist_ok=True)
        targets = [src]

    all_results = {}
    for t in targets:
        r = detect_image(detector, t, args.num_poses)
        if r is None:
            print(f"⚠️ 跳过无效图 {t}")
            continue
        img, people = r
        save_path = out if src.is_file() else out / t.name
        cv2.imwrite(str(save_path), img)
        all_results[t.name] = people
        print(f"✅ {t.name}: 检测到 {len(people)} 人 → {save_path}")

    detector.close()

    if args.json:
        Path(args.json).write_text(
            json.dumps(all_results, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"✅ 数据：{args.json}")


if __name__ == "__main__":
    main()
