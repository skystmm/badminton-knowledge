---
name: badminton-knowledge
description: 羽毛球教学与动作分析知识库：技术动作要点、常见错误与纠正、训练计划模板、动作分析报告模板、教学图示库、动作视频抽帧脚本。当需要讲解羽毛球技术、诊断动作问题、分析上传的动作视频、制定训练计划或生成动作分析报告时加载本知识库。
agent_created: true
---

# 羽毛球知识库

本知识库是「羽析」的配套资料，回答羽毛球技术教学、动作纠错、训练计划类问题前，先查阅对应参考文件，保证内容成体系、口径一致。

## 参考文件索引

| 文件 | 内容 | 使用场景 |
|------|------|---------|
| `references/technique-library.md` | 握拍、发球、后场球（高远/吊/杀）、网前球、步伐、单双打战术的要点与自检 | 技术教学、标准参考 |
| `references/common-errors.md` | 按技术分类的常见错误、原因与纠正练习 | 动作诊断、纠错方案 |
| `references/training-plans.md` | 入门/进阶路线、周期化计划模板、热身与放松流程 | 制定训练计划 |
| `references/analysis-report-template.md` | 动作分析报告标准模板与素材角度要求 | 生成动作分析报告 |
| `references/teaching-archive.md` | 学员档案：五步教学标准流程、已入库技术（高远球/吊球）全要素、进度与待办 | **每次教学前先查**，保持口径与进度一致 |
| `scripts/extract_frames.py` | 动作视频抽帧脚本（依赖 ffmpeg） | 用户上传视频分析时先运行，生成帧序列 |
| `scripts/annotate_frames.py` | 帧标注工具：grid 定位 / crop 放大 / mark 圈注 / ghost 轨迹 / compare 对比（依赖 Pillow） | 生成标注图与挥拍轨迹图 |
| `scripts/pose_detect.py` | 骨骼关键点检测与关节角度量化，33 点、支持多人（依赖 mediapipe；模型需另下，见脚本 docstring） | 量化肘角/膝角/躯干后仰角，骨架叠加图 |
| `scripts/draw_diagram.py` | 教学图示生成器：pose 骨架分解 / court 场地俯视 / grip 握拍截面 / panel 拼图（依赖 Pillow） | **技术教学配图（必用）**、步伐路线、站位、发力链条 |
| `assets/specs/*.json` | 图示规格：clear-high（高远球四步）/ contact-point（击球点正误）/ footwork-net（网前步伐）/ doubles-serve（双打发球） | 直接复用生成现成图 |
| `assets/diagrams/*.png` | 已生成的示范图（高远球分解、击球点对比、握拍、步伐、双打发球） | 回答对应问题时**直接引用** |
| `assets/diagrams/02~20-*.svg` | 自绘教学系列：高远球/吊球/劈吊/杀球的四步关节分解、手部细节（含反握与触球发力）、腿部动作、击球瞬间三视图 | 对应技术讲解时**直接引用**，每张图带自检标准；新技术收录时编号从 22 起接续，命名 `NN-技术名-类型.svg` |
| `assets/animations/07~08、21-*.html` | 循环演示动画（正手高远球、吊球、杀球）：真实时间轴插值，可 0.5x 慢放、拖动进度、跳步 | 讲解完整发力过程时与静态图配套给出，浏览器直接打开 |

**模型下载**（pose_detect.py 首次使用前）：
`curl -L -o pose_landmarker_full.task "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/1/pose_landmarker_full.task"`

**标注工作流**（远距小人像必读）：全画幅直接检测常漏掉远处主角 → 先 `crop` 放大主角区域 3× → 再 `pose_detect` → 用检测到的真实关键点坐标写 `mark` 的 JSON 规格 → 输出标注图；改进复盘用 `compare` 并排。

## 使用原则

1. **先查后答**：涉及具体技术细节、纠正练习、计划编排时，先读对应文件再作答；
2. **口径一致**：同一技术问题的表述以知识库为准，不凭印象发挥；
3. **按需裁剪**：知识内容是完整版，回答用户时按用户水平和问题聚焦点裁剪，不整篇倾倒；
4. **安全优先**：涉及疼痛与损伤的内容，以「建议就医/找线下教练」收口；
5. **视频先抽帧**：用户上传视频时，先运行 `scripts/extract_frames.py` 生成帧序列（普通视频每秒 2 帧、慢动作每秒 5 帧），再按报告模板逐帧分析、跨帧汇总。
6. **教学必配图**：讲解任何技术动作（握拍、发力、击球点、步伐、站位）时，**必须配图**，不许只发文字。优先级：① 库里有现成图（`assets/diagrams/`）直接引用；② 库里没有但改几行 spec JSON 就能出的，用 `scripts/draw_diagram.py` 生成；③ 都不行才用纯文字，并说明"建议提供 XX 视频后可给你标注实测图"。规格 JSON 写法见 `assets/specs/` 示例——骨架用链式关节（parent/len/ang），标注挂关节名自动定位，角度即输入即所标。
7. **教学先查档案**：给这位学员讲技术前，先读 `references/teaching-archive.md`——按里面的五步标准流程走，遵守五件套配图规则（步关节分解 + 手部细节×2 + 腿部动作 + 击球三视图）和前置关铁律，引用学员的当前进度，不重复考级、不跳步。
8. **新技术先搜后录**：库里没有的技术，按 Agent MD「新技术收录流程」执行——先查库确认 → 联网检索（≥2-3 来源交叉，不编造）→ 过前置关 → 生成五件套图解（编号从 11 起接续）→ 自动收录（assets + 学员档案）→ 汇报。搜不到可靠资料就明说，不硬凑。
