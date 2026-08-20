---
name: brain-organ-development
description: 开发或迭代【AI伙伴】类脑器官脚本时使用。含项目结构、编码约定、测试模式、已知坑、迭代准入制。
version: 0.1.0
author: 【AI伙伴】
license: MIT
metadata:
  hermes:
    tags: [companion, brain, organs, python, testing, windows]
---

# 类脑器官开发

【AI伙伴】类脑系统（ZenBrain 架构）的 Python 器官脚本开发规范。数据流：
`事件 → 海马体(存储) → 杏仁核(情绪) → 前额叶(工单) → 固结器(索引/种子/修剪) → Bayesian(置信) → FSRS(调度)`

## 项目快照（2026-08-11）

- git 仓库: `C:\Users\user\hermes-companion-configs`（复制+提交模式，SOUL/USER/MEMORY/器官全在此管理）
- 器官目录: `organs/`（hippocampus.py / amygdala.py / prefrontal.py / sleep_consolidator.py / reflex_deviator.py）
- 运行时数据: `hermes-companion-configs\reflex_events.json`（**事实源唯一真身**，git 管理；AppData 旧路径已废）
- 契约: `Desktop\companion-contract-v2.md`；原则: `PRINCIPLES.md`（git 仓库根，冲突时以文件为准）
- 状态: **7/7 全部完成**（hippocampus/amygdala/prefrontal/sleep_consolidator/reflex_deviator/bayesian_evaluator/fsrs_scheduler，2026-08-12 收官）；杏仁核词库盲区（"咳/重话"等语气词未识别）在 gold set 中排队等数据（内容迭代准入制）

## 流程铁律（2026-08-12 跨会话审查补充）

- **规则入库必经工单**：reflex skill 的 REFLEX_RULES 区块新增规则，必须经过前额叶工单
  （reflex_drafts.json 批次 P-XXXX，【AI伙伴】审 + 红线级【用户】确认），不允许直录。
  直录会断 source_batch 追溯链（2026-08-11 过度执行规则直录，source_batch 全 None）。
- **跨会话接手必做**（git log 全量 + grep 全库引用 + 时间线重建）——详见审查教训。

## 铁律（PRINCIPLES.md 摘要）

1. **判定权层级**：【用户】 > 【AI伙伴】 > 脚本。脚本只量化/建议/调度，不判定；score 永远人工给。
2. **诚实第一（统计版）**：样本不足不假装有结论——"能运行 ≠ 有统计效力"。数据判断必须用统计学原理。
3. **可迭代化**：数据/词库/参数不进代码（JSON 载体分离）；迭代一目了然（diff 干净、可追溯）；无死代码无残留。
4. **内容迭代准入制**：词库/特征迭代需数据支撑（出现频次 + 判别力 P(目标|词)≥0.7 + gold set 回归 + source_event 追溯）。数据不足时结论是"等待"，不是"添加"。gold set 盲区标注 = 待验证需求，不是待执行命令。
5. **数据只增不删**：suppressed 代替删除；全链可追溯（事件→工单→规则→来源）。
6. **红线规则**（score≤-7）写入 reflex skill 必须【用户】确认；正向不自动检测/升级。

## 器官编码约定

- CLI：全局选项（`--file`/`--params`/`--lexicon`/`--drafts`）放**子命令前**；负数参数必须等号（`--score=-8`、`--ci=-8,-6`）
- stdout 只输出 JSON（机器可读）；warning/提示走 stderr（`print(..., file=sys.stderr)`）
- 原子写：写 `.tmp` 再 `os.replace`
- 同目录器官复用：`sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))` + `from hippocampus import Hippocampus`
- 词库/参数默认从 `organs/*.json` 加载（amygdala_lexicon.json / hyperparams.json），CLI 可覆盖（测试用）
- 所有数值参数进 hyperparams.json，不硬编码在函数里；每条规则/事件用统一 ID（rule_index.json 的 R-XXXX）

## 测试模式（每个器官必做）

1. 语法：`python -m py_compile`
2. 冒烟：从 `tests/data/` fixture 复制到临时文件 → 全套操作 → 断言（**绝不直接操作真实数据**；2026-08-20 起 fixture 化：tests/data/reflex_events.json 为脱敏示例数据，测试不再依赖 %USERPROFILE% 真身路径，副本/分发场景可直接跑）
3. 零污染：操作前后 `md5(测试源文件)` 必须不变
4. gold set：`organs/tests/` 固化期望值 + 回归脚本（如 `run_amygdala_regression.py`）
5. 完成后：清理 `__pycache__` 和诊断残留 → `git add organs/ && git commit`

> ⚠️ 测试时间戳用动态生成（如"昨天"），不要写死日期——reflex_deviator 有 7 天窗口，
> 写死时间戳会随日期推移超窗导致测试挂（2026-08-20 实例）。

### ⚠️ 测试必须固化成文件（交付审查 B1 教训，2026-08-12）

**内联 execute_code 跑过的验证 ≠ 测试。不可复现的测试 = 不存在。**
曾把 60+ 项内联验证写进交付报告声称"测试项"，实际可复现仅 8 项，被外部审查抓出虚报。
正确做法：每个器官写完内联验证后，**立刻把断言固化为 `organs/tests/test_<器官>.py`**（自包含、可独立运行、零污染断言内置），然后全量重跑一遍确认固化版真的通过。交付报告里只统计文件化测试。

### 写测试的坑（踩过的，断言前必查）

- **断言前先跑一次看实际输出结构**：pulse 输出是 `{"triggered": true, "batch": {...}}`（batch 嵌套），顶层没有 batch_id——没验证结构就写断言必错
- **CLI 命令名以 argparse 定义为准**：`batches` 是内部方法名，CLI 子命令叫 `drafts`——别凭印象写
- **断言期望值先手算/实测**：arousal 封顶 1.0 需要感叹号+问号+强调词+动作+长度全项组合（0.3+0.3+0.15+0.1+0.1+0.1=1.05→1.0），少一项只有 0.95——断言写错 ≠ 代码错
- **幂等设计会挡测试**：重复 pulse 同一数据不产生新批次（游标已推进）——第 2 次调用要用新数据或直接检查第 1 次产物
- **参数别重复传**：`run("drafts", "--file", t, ...)` 配合 `file=t` 关键字会生成两个 `--file` → unrecognized arguments
- **数据快照会过时**：断言里的类别数/事件数要随数据更新（3 类别 → 8 事件后 5 类别）
- **对称返回检查（goal 插件 bug 实例，2026-08-14）**：拒绝路径返回 `blocked: false`，成功路径却漏了 `blocked: true`——测试断言 `r.get("blocked")` 抓出契约不对称。原则：同一动作的拒绝/成功两条路径，返回字段必须对称；写测试时对照两条路径各查一遍返回键

### 词库单字词过度匹配（lexicon 迭代坑）

单字词进词库会误伤：`"气"` 命中 `"天气"`（中性文本被判负向，测试当场抓出）。
规则：情绪词用**多字词**（"生气"而非"气"），单字词除非语义唯一（如"骗"）否则不入库。测试误报案例 = 词库修正的最强数据依据。

## 已知坑（踩过）

- **argparse 负数**：裸 `-8` 被当 option → 必须等号形式（代码和测试里都是）
- **git-bash 传路径给 Windows python**：`$HOME` 展开的 MSYS 路径会变 `C:\c\Users\...` → 用 `C:\Users\...` 原生格式，或 cygpath
- **测试断言 vs 代码 bug**：断言期望值写错 ≠ 代码错。先确认功能行为（实例：游标回退后未提炼数=2 是正确行为；warning 在 stdout 而非 stderr 是代码问题）
- **测试构造 bug**：追加内容放到了解析标记外（REFLEX_RULES_END 之后）→ 先检查测试数据构造，再怀疑代码
- **全局选项顺序**：`--file` 放子命令后 → `unrecognized arguments`
- **ID 体系**：工单 P-XXXX（面向事件组）≠ 规则 R-XXXX（rule_index.json）≠ skill 人类标题——不可互替
- **规则分值区间正则**：规则标题如"逻辑严谨红线（-6 ~ -5分）"含区间，解析用 `(-?\d+(?:\s*~\s*-?\d+)?)` 而非简单 `(-?\d+)`；提取数值后用 `min(nums)` 取最负端做 score

## 迭代工作流（数据化器官，如杏仁核）

1. 改 lexicon/params JSON（带 note/source_event）
2. `python organs/tests/run_amygdala_regression.py` → 期望 vs 实际对照表
3. `git diff` 应只显示内容变更 → commit
4. 盲区案例 = 待验证迭代需求（等数据积累，不立即加词）

## 外部审查工作流

【用户】会让 Claude Code 复审代码/设计（review 文件放 `Desktop\hermes-code-review.md` / `hermes-design-review-v1.md`）。写代码默认按"会被外部审查"标准；审查意见逐条评估——真 bug 修、误报明确指出（附依据）、设计分歧保留意见并说明理由。review 文件路径要读实际内容验证（Claude 可能基于假设，如"SKILL.md 已有 REFLEX_RULES 标记"——需查证）。

## 统计严谨性纪律（【用户】纠正 2026-08-11，-5 中负向事件；合并自 companion-brain-organs）

【用户】原话："你说话分析要讲求逻辑性，学会用数学（这里是统计学）原理。2条太少了，会有偏差和随机性。"

- **能运行 ≠ 有统计效力**：代码能跑通不构成"可以下结论"的理由。说"X 条数据就能起步跑"之前先问：这样本量下输出有意义吗？
- 涉及样本量/比例/置信度的任何判断，必须用统计学原理（先验、后验、置信区间宽度），不拍脑袋
- 设计数据驱动器官（如 bayesian_evaluator）必须带 **min_samples 硬门槛**（默认 ≥10）：样本不足时输出 `{"status": "insufficient_data", ...}`，**拒绝出结论**
- 参考对照（先验 Beta(1,1)）：n=2 → 95% CI 宽度 0.6~0.8（无信息）；n=10 → ≈0.4（弱）；n=30 → ≈0.25（可用）。详见 `references/statistical-rigor.md`

## 记忆质量纪律（【用户】纠正 2026-08-11，-4 中负向事件；合并自 companion-brain-organs）

- 会过时的状态（练车进度/临时进度）→ 不进 MEMORY，用 session_search 回忆
- 稳定事实（身份/环境/工作流/偏好）→ 才进 MEMORY
- 记忆的价值 = 不再让【用户】重复自己；问了记忆里已有答案的问题 = 双重失职
- 用户纠正本身 → 按校准系统记入 reflex_events.json（负向可自动检测并声明，正向等明确表态）

## 继承资产（2026-08-12 合并自 brain-organ-dev + companion-brain-organs）

- `templates/hippocampus.py` — 完整可运行器官模板（原 brain-organ-dev 独有，写新器官时复制改类名/职责）
- `scripts/self_check.py` — 全系统交叉验证脚本（原 brain-organ-dev 独有，零参数自检）
- `templates/smoke_test_template.py` — 冒烟测试模板（原 companion-brain-organs 独有）
- `references/statistical-rigor.md` — 统计严谨性深度参考（原 companion-brain-organs 独有）
- 合并后本技能为类脑器官开发**唯一入口**（brain-organ-dev / companion-brain-organs 已吸收删除）

## 支持文件

- `references/remaining-organs-design.md` — 剩余器官（Bayesian/FSRS）设计要点与杏仁核迭代方向
- `references/cobra-integration.md` — CoBRA 后悔梯度集成架构（2026-08-11，reflex_deviator + sleep_consolidator V2）
- `references/math-stats-self-review.md` — 数学/统计输出前三步自审查清单（来源：reflex #3, #4）
- `scripts/self_check.py` — 全系统交叉验证（2026-08-20 参数化：`--events/--organs/--skill`，自动探测；非 git 仓库/无本机 skill 时跳过不失败；分发副本用 `--events/--organs` 显式指定）
