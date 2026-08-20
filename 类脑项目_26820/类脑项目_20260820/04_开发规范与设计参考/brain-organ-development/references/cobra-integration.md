# CoBRA 后悔梯度集成 (2026-08-11)

## 源起

【用户】提出"用科学理论规范 Agent 行为"，我们建立了九学科三层框架。随后下载 CoBRA（CHI 2026 Best Paper, UCSD, MIT 开源）——一个用经典社会科学实验精确调控 LLM 认知偏差的研究项目。

## CoBRA 核心机制（与我们系统的映射）

| CoBRA | 我们的系统 | 映射关系 |
|---|---|---|
| 认知偏差指数（经典实验测量） | reflex_events.json（【用户】 ±10 评分） | 测量层 |
| Representation Engineering 控制向量 | reflex skill 行为规则（prompt 层） | 控制层 |
| 动态系数搜索（自适应采样） | regret 梯度加权 + 自适应优先级 | 校准层 |
| 闭环：测量→施加→再测量 | 白天采集→夜晚固结→下次行为改变 | 闭环结构 |

## 后悔梯度公式

```
regret = |score| × emotional_weight
```

- 高后悔 = 大偏差 × 高在乎 = 最值得回放巩固
- 低后悔 = 小偏差 × 不太在乎 = 常规处理即可
- 与 CoBRA Phase 2 "最大 gap 处加密采样" 数学同构

## 已实现的器官（CoBRA V2）

### reflex_deviator.py（偏差方向分析器）

CLI 脚本。读取 reflex_events.json → 按 category 聚类 → 生成规则草稿。

- 窗口期：7 天内的 active 负向事件
- 最低阈值：总分 ≥ |3| 才生成规则建议
- 多事件聚类：tag 合并（如"统计逻辑 · 数学严谨"）
- 输出：偏差方向排序 + 规则草稿 Markdown

### sleep_consolidator.py（CoBRA V2 REM）

REM 阶段从二元阈值过滤改造为后悔梯度加权：

1. `_regret_score(event)`: 计算 regret
2. `_rem()`: 按 regret 降序排列种子，输出 regret_distribution
3. `_adaptive_prioritize()`: 按 category 聚合后悔，输出优先级建议（high/medium/low）
4. `consolidate()`: 新增 `adaptive` 输出 → 告诉 downstream "哪个类别最需要加密提炼"

关键效果：即使 transparency 单条后悔最高 (9.5)，logic 类别累计 2 条事件总后悔反超 (9.7) → 系统自动判断 logic 需要优先加密。

## 集成架构（三步）

```
① reflex_deviator.py  → 偏差方向分析 → 生成规则草稿
② sleep_consolidator.py (CoBRA V2) → 后悔梯度加权 + 自适应优先级
③ (远期) 本地模型 + 激活空间控制 → CoBRA 原生 RepE 直接可用
```

①② 已完成，③ 待本地模型条件成熟。
