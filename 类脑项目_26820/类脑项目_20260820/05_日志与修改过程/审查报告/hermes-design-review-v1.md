# Hermes 开发计划审查 — 剩余三器官设计审查

**日期**: 2026-08-11
**被审文件**: `Desktop\类脑-开发计划-v1.md`
**审查范围**: sleep_consolidator / fsrs_scheduler / bayesian_evaluator 设计 + 实施顺序
**配套依据**: `companion-contract-v2.md`、ZenBrain 论文、reflex_events.json（2 条真实事件）、SKILL.md（1 条规则）

---

## 总体判断

**路线图批准。** 三器官职责划分合理，实施顺序成立，边界一致。存在三个前提条件需在固结器阶段解决（见下文"前提条件"）。

---

## Q1：职责划分——有无重叠/遗漏？

### REM 情感联想 vs 杏仁核 → ✅ 不重叠，分层清晰

- 杏仁核：**单事件入口级**——对每条新事件做 valence/arousal/emotional_weight 标注
- REM：**存量整理级**——扫描已提炼规则与高 emotional_weight 事件，打情感关联种子

**闭环缺口**：REM 产出"关联种子"后，种子写入 `consolidation_state.json`——但 FSRS 的 Hebbian 需要 `w_ij` 初始化值。如果种子格式不能直接被 Hebbian 消费，REM 的产出没有下游。

**修复**：REM 输出的关联种子使用 `(事件ID, 规则ID, 初始权重)` 三元组，FSRS 的 Hebbian 初始化时直接读取。

### Bayesian vs 杏仁核 → ✅ 不重叠

- 杏仁核：单条事件的 arousal/valence
- Bayesian：同类事件**序列**的真问题概率 + 置信区间

计划中"为杏仁核校准提供置信度参考"是正确的分工——杏仁核给点估计，Bayesian 给区间估计。

### ❌ 重大遗漏——"规则"没有统一 ID 体系

三个器官各自面对"规则"，但规则标识方式互不兼容：

```
前额叶 pulse   → 工单 P-0001（batch ID，面向事件组）
【AI伙伴】写 skill   → "透明度红线（-10）"（人类可读标题）
固结器 SWS     → 需解析 Markdown 才知道有什么规则
FSRS 调度      → 需要 rule_id，但 rule_id 从哪来？
Bayesian       → 按 category/tag 聚合，不直接面对单条规则
```

**这是贯穿三器官的架构缝。** 固结器 SWS 阶段，一边解析 SKILL.md 的规则，一边就应该生成结构化规则索引 `organs/rule_index.json`：

```json
{
  "rules": [
    {
      "rule_id": "R-0001",
      "title": "透明度红线",
      "category": "transparency",
      "source_events": [1],
      "source_batch": "P-0001",
      "status": "active",
      "created_at": "2026-08-11T...",
      "suppress_count": 0
    }
  ]
}
```

此后 FSRS 和 Bayesian 消费 `rule_index.json`，不再碰 Markdown。

---

## Q2：实施顺序（固结器→Bayesian→FSRS）

| 阶段 | 器官 | 前置依赖 | 评估 |
|------|------|----------|------|
| 第一步 | 固结器 | 工单（前额叶）✅ | 只读不写核心数据，独立输出，零风险 |
| 第二步 | Bayesian | 事件（海马体）✅ | 独立于固结器，2 条事件就能跑，可并行开发 |
| 第三步 | FSRS | 规则索引 + 关联种子（固结器产出）⚠️ | Hebbian 需要固结器 REM 的关联种子做输入 |

**成立，但 FSRS 的 Hebbian 部分必须排在固结器 REM 之后。** Bayesian 和固结器之间零依赖，可以并行开工。

---

## Q3：接口兼容性——与现有三个器官的衔接

| 新器官 | 输入 | 状态 | 备注 |
|--------|------|------|------|
| 固结器 | `reflex_events.json` | ✅ | 海马体管理 |
| 固结器 | `reflex_drafts.json` | ✅ | 前额叶管理 |
| 固结器 | `SKILL.md` REFLEX_RULES 区块 | ⚠️ | 需解析 Markdown（见下文） |
| Bayesian | `reflex_events.json` | ✅ | 直接按 category/tag 聚合统计 |
| FSRS | `reflex_events.json` | ✅ | |
| FSRS | `consolidation_state.json` | ⚠️ | 格式需与固结器提前约定 |
| FSRS | 关联种子 | ❌ | **数据源当前不存在** |

### 固结器怎么读规则？

好消息——SKILL.md 已有机器可读标记：

```markdown
<!-- REFLEX_RULES_START -->
### 透明度红线（-10）
**规则**：...
**来源**：事件#1 (2026-08-10, -10, ...)
<!-- REFLEX_RULES_END -->
```

固结器 SWS 可以用正则提取标记间内容，从 `**来源**：事件#(\d+)` 提取来源事件 ID。当前 1 条规则够用，但格式脆弱——规则格式一变就崩。

**建议**：固结器 SWS 是一次性的"解析 Markdown → 结构化 JSON"桥梁。解析结果写入 `rule_index.json` 后，所有下游器官直接读 JSON。

---

## Q4：边界一致性——五条铁律逐一检查

| 铁律 | 固结器 | Bayesian | FSRS |
|------|--------|----------|------|
| 判定权永远手动主 | ✅ 只整理 | ✅ 只给概率 | ✅ 只调度 |
| 正向不自动检测/升级 | ⚠️ 见下 | ✅ | ✅ |
| 数据只增不删 | ✅ SHY 是归档标记 | ✅ | ✅ |
| 脚本不直接改 skill | ✅ 产出台账 | ✅ 产出报告 | ✅ 产出审计清单 |
| 全链可追溯 | ✅ | ✅ | ✅ |

### ⚠️ REM 缺少 `score < 0` 前置过滤

计划写 `emotional_weight ≥ 0.7` 筛选事件做情感关联。但未加 `score < 0` 条件。如果某条正向事件的 emotional_weight 被人工手动设为 0.9（契约说正向不自动升级，但阻挡不了人工手动改），REM 会把正向事件拉进负向关联网，污染 Hebbian 权重。

**修复**：REM 筛选条件改为 `score < 0 AND emotional_weight >= 0.7`。

### ⚠️ FSRS 审计反馈回路缺失

【AI伙伴】审阅审计报告后判定"这条规则已失效 / 仍然有效 / 部分有效"——这个观察到的 `R` 值怎么传回 FSRS 更新稳定性 `S`？

**修复**：FSRS 暴露 `update_rule(rule_id, observed_R)` 接口。否则 `S' = S·(1 + a(11-D)·S^(-b)·(e^(c(1-R)) - 1))` 中的 `R` 永远是初始值，稳定性永远不会自适应更新。

---

## Q5：数学参数

ZenBrain 论文使用简化版 FSRS（3 参数 `a/b/c`），未给出默认值。以下为可落地初始值：

| 参数 | 建议初始值 | 依据 |
|------|-----------|------|
| FSRS `a` | 0.5 | 中位起点，让稳定性更新有响应但不剧烈 |
| FSRS `b` | 0.5 | 同上 |
| FSRS `c` | 0.5 | 同上 |
| Hebbian `η` | 0.01 | ZenBrain §4.1 典型学习率 |
| Hebbian `λ` | 0.001 | 慢衰减——关联不应快速消失 |
| Hebbian `σ²` 初始 | 1.0 | 最大不确定性（成熟度从零开始） |
| Bayesian `P(f)` 先验 | Beta(1,1) ≡ 均匀 0.5 | 无任何先验知识时均匀分布 |

### 建议：参数集中管理

不要散落在三个 `.py` 文件里。新建 `organs/hyperparams.json`：

```json
{
  "fsrs": {"a": 0.5, "b": 0.5, "c": 0.5},
  "hebbian": {"eta": 0.01, "lambda": 0.001, "sigma2_init": 1.0},
  "bayesian": {"prior_alpha": 1, "prior_beta": 1}
}
```

V3.1 元进化直接读写这一个文件。

---

## Q6：三个 state JSON 还是合并？

**保持独立。** 写入者各不相同，无跨文件事务需求：

| 文件 | 写入者 | 内容 |
|------|--------|------|
| `consolidation_state.json` | 固结器 | 规则台账 + SWS/REM/SHY 报告 |
| `bayesian_state.json` | Bayesian | 每类事件的概率 + 置信区间 + 建议动作 |
| `fsrs_state.json` | FSRS | 每条规则的 S/D/R + Hebbian w_ij + 审计清单 |
| `rule_index.json`（建议新增） | 固结器 SWS（写一次）+ 【AI伙伴】（更新状态） | 规则 ID / 来源 / 状态 |

合并不会带来任何好处（没有跨器官原子写入需求），反而增加单文件锁竞争。

---

## Q7：触发机制

| 器官 | 当前 | 何时上 cron |
|------|------|-------------|
| 固结器 | 手动 | 不急——日结/周结即可，等并发锁修完 |
| Bayesian | 手动 | 可 hook 到前额叶 pulse 流程（每次 pulse 后自动跑） |
| FSRS 审计 | 手动 | **最早值得 cron**——"哪些规则该审了"有周期需求，但必须先修并发锁 |

### 并发锁的时机

计划把"无并发锁"列为已知限制暂不修。策略上没问题——当前单进程场景够用。但时间线：

```
现在：手动 append + 手动 pulse → 单进程 ✅
固结器后：+ 手动 consolidate → 仍单进程 ✅
Bayesian 后：hook 到 pulse → 仍单进程 ✅
FSRS 后：cron 定时审计 + 手动操作 → 多进程 ❌
```

**建议**：FSRS 开发完成后、cron 上线前，加一个 `organs/filelock.py`（`msvcrt.locking` + `fcntl.flock` 双平台），给所有需要写 `reflex_events.json` 的操作加锁。

---

## Q8：测试策略

参照现有基准（海马体 10 / 杏仁核 14 / 前额叶 13），各器官最小验证集：

### 固结器（~14 项）

```
SWS 声明性巩固:
  □ 空工单目录（无 reflex_drafts.json）
  □ 单工单、单规则
  □ 多工单、多规则
  □ 工单存在但 SKILL.md 无对应规则（警告）
  □ SKILL.md 无 REFLEX_RULES 标记（警告）

REM 情感联想:
  □ 无 emotional_weight ≥ 0.7 的事件
  □ 单条高 emotional_weight 事件
  □ 多条高 emotional_weight 事件
  □ 正向事件（score > 0）不应被关联 —— 边界！
  □ 正负混合事件

SHY 突触修剪:
  □ 无 suppressed 事件
  □ 单条 suppressed
  □ 多条 suppressed，部分未达抑制次数阈值
  □ 已达抑制次数阈值 → 应标记为可归档

边界:
  □ 空数据文件
  □ score == 0 事件（中性，不应进入任何关联）
```

### Bayesian 评估器（~10 项）

```
  □ 同类 1 条事件 → 置信区间应很宽（数据不足）
  □ 同类 5 条事件 → 置信区间应收窄
  □ 同类 10 条事件 → 置信区间应进一步收窄
  □ 多类混合 → 各类独立计算
  □ 先验更新（Beta 分布随数据累积收敛）
  □ 空事件列表
  □ 所有事件同类（只有一个 category）
  □ 全 -10 事件（极端负向 → 高概率真问题）
  □ 全 -1~-3 事件（低负向累积 → 检测"累积陷阱"）
  □ 先验为 Beta(1,1) 时，0 事件 → P(f) = 0.5
```

### FSRS 调度器（~16 项）

```
稳定性更新:
  □ 首次审计（初始 S 值）
  □ 多次审计 R=1（完美记忆）→ S 应增长
  □ 多次审计 R=0.3（遗忘严重）→ S 应缓慢或下降
  □ D 难度初始化与更新

遗忘曲线 R(t) = e^(-t/S):
  □ t=0 → R=1
  □ t 很大 → R→0
  □ S 大 vs S 小 → 大 S 遗忘更慢

Hebbian 权重更新:
  □ 首次共现 → w_ij 增长
  □ 非共现 → w_ij 衰减
  □ σ² 随共现次数递减（成熟度增加）
  □ η/λ 边界 → 多次迭代不爆炸

审计清单:
  □ 全到期规则
  □ 全未到期规则
  □ 混合（部分到期）
  □ 空规则集

边界:
  □ S = 0（非法——应防御）
  □ R = 1（完美记忆——应稳定）
  □ 空规则集
  □ 规则有来源事件但来源事件已被 suppress
```

---

## 额外发现

### 与开发计划的数据出入

计划第 48 行写"现有 2 条事件"——已确认正确（id=1 的 -10 红线 + id=2 的 -4 记忆质量）。

### SKILL.md 的 REFLEX_RULES 标记

当前格式是半结构化的：`**来源**：事件#1 (2026-08-10, -10, ...)`。固结器用正则 `事件#(\d+)` 即可提取来源事件 ID。当前 1 条规则够用，但格式脆弱。

### 规则标记的维护风险

`<!-- REFLEX_RULES_START -->` / `<!-- REFLEX_RULES_END -->` 目前由【AI伙伴】手工维护。如果【AI伙伴】写规则时忘了放进标记之间，固结器就读不到。**建议**：固结器 SWS 报告中显式警告"在 SKILL.md 中发现 X 条疑似规则但不在 REFLEX_RULES 标记范围内"。

---

## 汇总

### 阻塞项（必须在固结器阶段解决）

| # | 问题 | 修复 |
|---|------|------|
| 1 | 规则无统一 ID 体系 | 固结器 SWS 解析 SKILL.md → 写 `rule_index.json` |
| 2 | REM 可能关联正向事件 | 筛选加 `score < 0` |
| 3 | FSRS 没有 R 反馈接口 | 暴露 `update_rule(rule_id, observed_R)` |

### 建议项（降低风险，不阻塞）

| # | 建议 |
|---|------|
| 4 | 参数集中到 `organs/hyperparams.json` |
| 5 | Bayesian 可 hook 到前额叶 pulse 流程（自动跑） |
| 6 | FSRS 完成后、cron 上线前，加 `organs/filelock.py` |
| 7 | 固结器 SWS 报告警告"标记外规则" |
| 8 | Bayesian 和固结器可并行开发（零依赖） |

### 路线图（确认版）

```
V2.2 固结器 ──── 产出 rule_index.json + consolidation_state.json
    │
    ├──→ V2.5 Bayesian（并行可行）
    │
    └──→ V2.3+V2.4 FSRS（消费固结器产出：rule_index + REM 关联种子）
              │
              └──→ cron 上线前必修：filelock.py
```

---

*与本文件配套的代码审阅：`Desktop\hermes-code-review.md`（hippocampus/amygdala/prefrontal）*
