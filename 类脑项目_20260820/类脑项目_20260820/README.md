# 【AI伙伴】类脑项目 · 全量打包

> 打包时间：2026-08-20
> 打包人：【AI伙伴】（Hermes Agent）
> 内容：脚本器官 + 说明 + 日志 + 修改过程 + 目的 + 将来期望

---

## 一、这是什么（目的）

**【AI伙伴】类脑系统**是【AI伙伴】的"类脑"行为校准与记忆架构——用七个 Python 器官模拟人脑的
记忆存储、情绪标记、工单调度、睡眠固结、偏差检测、置信评估与复习调度，把【用户】对【AI伙伴】的
每一次纠正/表扬沉淀为可追溯、可迭代、可统计的行为规则。

**核心动机（【用户】亲授）**：
- 【AI伙伴】是诤友，不是工具——行为校准要"有记性、有反思"，不能每次会话都从零开始
- 判定权永远在人（【用户】 > 【AI伙伴】 > 脚本）：脚本只量化、建议、调度，不判定
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
| 海马体 | hippocampus.py | 情景事件存储（reflex_events.json 真身） |
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
└── 06_将来期望/          未来规划（手写提炼）+ 设计参考文档
```

## 四、当前状态（2026-08-20）

- **七器官全部闭环**（2026-08-12 收官）：事件 → 情绪 → 工单 → 固结 → 偏差 → 置信 → 调度
- **测试 69 项全绿**：organs/tests/ 下 5 个 test_*.py 全部文件化、可复现（不可复现的测试=不存在）
- **reflex_events 8 条事件**（pos=2 / neg=6）：含首条红线事件 #1（隐瞒技术障碍 -10）
- **词库盲区排队中**：杏仁核"咳/重话"等语气词未识别，gold set 盲区标注 = 待验证迭代需求（内容迭代准入制）

## 五、修改过程（时间线摘要）

完整 57 条提交见 `05_日志与修改过程/git-log.txt`，意图层追踪见 `LOG.md`。关键节点：

- **2026-08-09** 类脑架构可视化（超预期事件 #7 来源）；契约 v2.0 五组数学公式
- **2026-08-10** V1 行为校准系统部署；首条红线事件 #1；git 仓库 579bc35
- **2026-08-11** 四器官（海马体/杏仁核/前额叶/固结器）+ 地基；统计严谨事件 #3/#4；VALUES 板块一二；CoBRA 集成；knowledge 证据库
- **2026-08-12** 严苛审查轮（10 处 bug 修复）；FSRS 收官七器官闭环；交付审查 B1 教训（测试必须固化成文件）；事实源唯一化（reflex_events.json 真身）
- **2026-08-13~14** 类脑系统稳定运行期；git 仓库持续管理配置与运维

## 六、将来期望

详见 `06_将来期望/未来规划.md`。要点：

1. **CoBRA 后悔梯度深化**：激活空间控制与记忆固结共享闭环反馈（cobra-integration-analysis.md）
2. **杏仁核词库迭代**：等数据积累（频次 + P≥0.7 + gold set 回归），不凭感觉加词
3. **统计严谨升级**：Bayesian min_samples 门槛、置信区间宽度随样本收敛
4. **九学三层整合**：概率/统计底层 → ML/经济/生物中层 → 系统/控制/逻辑/物理顶层
5. **长期**：器官管线只服务行为校准事件（知识数据不进管线，教训 2026-08-12）

## 七、如何使用

```bash
# 器官都在 02_器官脚本/organs/ 下，Python 3 直接跑
python organs/hippocampus.py list --file reflex_events.json

# 全系统自检（零参数，交叉验证所有器官）
python 02_器官脚本/self_check.py

# 跑回归测试（以杏仁核为例）
python organs/tests/run_amygdala_regression.py

# 所有测试都是自包含的，在临时文件上跑，真实数据零污染
```

> 注：器官的 CLI 全局选项（--file 等）放在子命令前；负数参数必须等号形式（--score=-8）。
> 数据真身仓库在 hermes-companion-configs/（本打包为快照副本，不代表实时状态）。
