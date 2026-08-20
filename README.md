# 【AI伙伴】类脑项目 · 全量打包

> 打包时间：2026-08-20（v2，含外部审计修复）
> 打包人：【AI伙伴】（Hermes Agent）
> 内容：脚本器官 + 说明 + 日志 + 修改过程 + 目的 + 将来期望
> 注：本项目为脱敏分发快照，人名已占位符化（【用户】=人类用户、【AI伙伴】=AI）。代码注释中出现的
> hermes-companion-configs 是脱敏后的仓库名占位（原仓库名含拼音名）。

---

## 正确版本：26820

## 一、这是什么（目的）

**类脑系统**是把"人类用户对 AI 伙伴的每次纠正/表扬"沉淀为可追溯、可迭代、可统计行为规则的
七器官 Python 管线——模仿人脑的记忆存储、情绪标记、工单调度、睡眠固结、偏差检测、置信评估与复习调度。

**核心动机（【用户】亲授）**：
- AI 伙伴是诤友，不是工具——行为校准要"有记性、有反思"，不能每次会话从零开始
- 判定权永远在人（【用户】>【AI伙伴】> 脚本）：脚本只量化、建议、调度，不判定
- 可迭代化：数据/词库/参数与代码分离，改内容不动代码，git diff 干净
- 诚实第一（统计版）：能运行 ≠ 有统计效力；样本不足不假装有结论

## 二、架构与数据流

```
事件 → 海马体(存储) → 杏仁核(情绪) → 前额叶(工单) → 固结器(索引/种子/修剪)
     → Bayesian(置信) → FSRS(调度)
     ↘ reflex_deviator（偏差检测，与固结器 REM 后悔梯度集成）
```

| 器官 | 文件 | 职责 |
|---|---|---|
| 海马体 | hippocampus.py | 情景事件存储（reflex_events.json） |
| 杏仁核 | amygdala.py | 情绪强度标记（词库驱动，lexicon 与代码分离） |
| 前额叶 | prefrontal.py | 提炼工单调度（P-XXXX 批次，规则必经工单） |
| 睡眠固结器 | sleep_consolidator.py | SWS/REM/SHY 三阶段固结、种子筛选 |
| 偏差检测器 | reflex_deviator.py | 行为偏差检测（CoBRA 后悔梯度 V2） |
| Bayesian 评估器 | bayesian_evaluator.py | 置信区间校准（min_samples 硬门槛） |
| FSRS 调度器 | fsrs_scheduler.py | Hebbian+Ebbinghaus 自适应复习调度 |

## 三、目录结构

```
├── 01_项目总览/          开发计划 v1 + 架构可视化 HTML
├── 02_器官脚本/          7 个器官 + 词库/状态 JSON + tests/ + self_check.py
├── 03_契约原则与目的/    契约 v2、PRINCIPLES（地基）、VALUES（价值观）、SOUL、knowledge 证据库、reflex_events 数据
├── 04_开发规范与设计参考/ brain-organ-development / reflex-behavior-calibration / companion-agent-architecture 三套 skill
├── 05_日志与修改过程/    LOG 逻辑链台账、learnings 三文件、审查报告五份、git-log.txt
└── 06_将来期望/          未来规划 + 设计参考文档
```

## 四、当前状态（2026-08-20 v2）

- **七器官全部闭环**（2026-08-12 收官）；**69 项测试文件化全绿**（v2 实测：11+10+10+12+5+18+3）
- **reflex_events 8 条事件**（pos=2 / neg=6）；词库盲区排队中（内容迭代准入制）
- **2026-08-20 外部审计修复**（独立 agent 审计 + 人工核验）：
  - 修复 FSRS next_audit 真 bug（此前时间戳是"当前时刻"+天数字符串后缀，现为真正的未来 ISO 时间戳，并补断言 next_audit>now）
  - 修复前额叶优先级权重归一化（此前 0.25+0.25+0.2=0.7，数值不可解释）
  - 修复 Bayesian 中位数标准定义（偶数样本取两中位均值）
  - 测试自包含化：tests/data/reflex_events.json 为脱敏 fixture，测试不再依赖外部真身路径
  - reflex_deviator 支持 --file；器官默认路径支持环境变量 companion_EVENTS + 自动探测
  - self_check.py 支持 --events/--organs/--skill 参数与自动探测

## 五、已知限制（诚实声明）

1. **事件级 confidence_interval 为预留字段**：由录入方填写，当前无器官消费；统计口径以
   Bayesian 评估器输出的类别级 95% CI（bayesian_state.json 的 ci_95/ci_width）为准。
2. **FSRS 难度参数 D 为固定值待标定**：stability_update 只读 D 不更新（无标定数据支撑，遵守内容迭代准入制）。
3. **样本量 8 条，统计层处于 insufficient_data 状态**：Bayesian min_samples=10 硬门槛下，
   所有类别当前只能诚实回答"我不知道"。
4. **reflex_deviator 只分析 7 天窗口内事件**：旧事件偏差检测不参与，规则沉淀走固结器 REM 通道。

## 六、修改过程（时间线摘要）

完整提交记录见 `05_日志与修改过程/git-log.txt`，意图层追踪见 `LOG.md`。关键节点：

- **2026-08-09** 类脑架构可视化；契约 v2.0 五组数学公式
- **2026-08-10** V1 行为校准系统部署；首条红线事件 #1（-10）
- **2026-08-11** 四器官 + 地基；统计严谨事件 #3/#4；VALUES 板块一二；CoBRA 集成；knowledge 证据库
- **2026-08-12** 严苛审查轮（10 处 bug 修复）；FSRS 收官七器官闭环；交付审查 B1（测试固化成文件）；事实源唯一化
- **2026-08-20** 外部 agent 审计（独立视角抓出 4 个真实缺陷）→ 全部修复 + 测试自包含化 + 脱敏分发快照

## 七、如何使用

```bash
# 器官（在 02_器官脚本/organs/ 下，Python 3.10+）
# 默认事件路径自动探测；也可用环境变量 companion_EVENTS 或 --file 显式指定
python organs/hippocampus.py list
python organs/reflex_deviator.py --file ../../03_契约原则与目的/reflex_events.json
python organs/bayesian_evaluator.py --file ../../03_契约原则与目的/reflex_events.json status

# 全系统自检（自动探测；分发场景推荐显式指定）
python 02_器官脚本/self_check.py \
    --events 03_契约原则与目的/reflex_events.json \
    --organs 02_器官脚本/organs

# 跑测试（自包含，fixture 在 tests/data/，无需外部依赖）
cd 02_器官脚本/organs && python tests/test_hippocampus.py
python tests/run_bayesian_regression.py
# ... 全部 7 个测试文件，共 69 项

# 真身运行（本机原仓库）：self_check 自动探测即可
python scripts/self_check.py
