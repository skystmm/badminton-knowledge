# badminton-knowledge · 羽毛球教学知识库

> 一个 WorkBuddy Skill：把“怎么教羽毛球、怎么分析动作”沉淀成可复用的知识体系——技术要点、常见错误、训练计划模板、13 张教学图解、2 个循环演示动画，以及一整套动作视频分析工具链。

## 这是什么

羽毛球教学与动作分析知识库，覆盖：

- **技术动作要点库**（`references/technique-library.md`）：握拍、发球、高远球、吊球（含劈吊）、杀球、网前技术、步伐、单双打战术的要点与自检；
- **常见错误与纠正库**（`references/common-errors.md`）：按技术分类的错误、原因与纠正练习；
- **训练计划模板**（`references/training-plans.md`）：入门/进阶路线、周期化计划、热身放松流程；
- **动作分析报告模板**（`references/analysis-report-template.md`）：标准化的视频/照片分析输出格式；
- **教学图解库**（`assets/diagrams/`）：13 张自绘 SVG 系列——正手高远球/吊球/劈吊的步关节分解、手部细节、腿部动作、击球瞬间三视图，每张带自检标准；
- **循环演示动画**（`assets/animations/`）：高远球、吊球的完整发力过程动画（HTML，浏览器打开，可 0.5x 慢放、拖动进度、分步跳转）；
- **工具脚本**（`scripts/`）：
  - `extract_frames.py` — 动作视频抽帧（依赖 ffmpeg）
  - `pose_detect.py` — 33 点骨骼检测与关节角度量化（依赖 mediapipe）
  - `annotate_frames.py` — 帧标注：圈问题部位、画理想位置箭头、挥拍轨迹、前后对比
  - `draw_diagram.py` — 教学图示生成器（骨架分解/场地俯视/握拍截面/多图拼接）
- **学员档案**（`references/teaching-archive.md`）：技术介绍五步标准流程 + 已收录技术全要素 + 进度跟踪模板。

## 安装

**方式一：直接下载**

```bash
git clone https://github.com/skystmm/badminton-knowledge.git
mkdir -p ~/.workbuddy/skills
cp -R badminton-knowledge ~/.workbuddy/skills/badminton-knowledge
```

重启 WorkBuddy 后，在技能列表中即可看到「羽毛球教学知识库」。

**方式二：Zip 下载**

在仓库页面下载 ZIP，解压后把 `badminton-knowledge` 目录放入 `~/.workbuddy/skills/`。

## 使用

安装后可直接对 WorkBuddy 说：

- “正手高远球总打不到底线，帮我看看问题在哪”（可上传侧面动作照片/视频）
- “我是零基础，想系统学羽毛球，帮我安排一条入门路线”
- “每周练 3 次、每次 1 小时，帮我制定进阶训练计划”

技能会在讲解技术时自动引用图解库，分析动作时走“抽帧 → 骨骼检测 → 标注 → 跨帧推断”流程。

## 文件结构

```
badminton-knowledge/
├── SKILL.md                        # 技能入口（触发条件与使用原则）
├── manifest.yaml                   # 发布元数据（CSIG Skill 规范）
├── references/                    # 知识库文档
│   ├── technique-library.md        #   技术动作要点库
│   ├── common-errors.md            #   常见错误与纠正库
│   ├── training-plans.md           #   训练计划模板
│   ├── analysis-report-template.md #   动作分析报告模板
│   └── teaching-archive.md         #   学员档案（含空白进度模板）
├── assets/
│   ├── diagrams/                   # 教学图解（13 张自绘 SVG + 5 张程序化 PNG）
│   ├── animations/                 # 循环演示动画（2 个 HTML）
│   └── specs/                      # 图示生成规格 JSON
└── scripts/                        # 工具脚本（抽帧/骨骼/标注/绘图）
```

## 依赖与限制

- 视频分析功能需要 **ffmpeg**（抽帧）与 **mediapipe 姿态模型**（骨骼检测，首次使用按 `SKILL.md` 内命令下载）；
- 缺少依赖时，教学讲解和图解引用功能不受影响；
- 所有图解为「标准动作示意（原理简化）」，对照实际动作时请以实测视频为准。

## 安全说明

- 本技能处理用户上传的动作视频/照片，数据分级 L2，请勿用于处理更高敏感度数据；
- 技能不替代医疗诊断：涉及疼痛、肿胀、旧伤，请就医或找线下教练面诊；
- 仓库内不含任何密钥与个人信息。

## 许可

个人级发布（level: personal）。转载或二次分发请保留作者信息。
