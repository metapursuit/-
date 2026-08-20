# CoBRA 整合分析

> 基于 2026-08-11 会话中对 CoBRA 仓库的完整审查。
> 仓库路径：`D:\360安全浏览器下载\CoBRA-master\CoBRA-master`
> 论文：CHI 2026 Best Paper, arXiv 2509.13588

## 项目概要

CoBRA（Cognitive Bias Regulator for Social Agents）— UCSD AISmithLab。MIT 开源。

核心命题：**将认知偏差变成可连续调控的变量**，用经典社会科学实验（米尔格拉姆服从、阿希从众、沃森选择、亚洲疾病问题）做测量基准。

## 三层控制架构

| 层 | 方法 | 粒度 | 实现 |
|---|---|---|---|
| 输入空间 | Prompt Engineering | 粗 | `prompt_experiment.py` |
| **激活空间** | **Representation Engineering** | **精** | `repe/rep_control_pipeline.py` |
| 参数空间 | Fine-tuning | 永久 | finetuning 分支 |

## 激活空间控制机制（核心创新）

### 原理

1. 用经典实验跑模型，读特定层的隐藏状态
2. 提取偏差对应的**方向向量**（如"权威效应方向"）
3. 推理时在指定层注入：`hidden_state += coeff × direction_vector`
4. 系数正调→偏差增强，负调→偏差抑制
5. 再度量→验证偏差移到目标刻度

### 关键代码路径

- `control/repe/rep_control_reading_vec.py` — `WrappedBlock` 拦截 transformer block 的 forward，注入控制信号
- `control/repe/rep_control_pipeline.py` — `RepControlPipeline` 继承 HuggingFace TextGenerationPipeline
- `control/repe_experiment.py` — `find_dynamic_control_coeffs()` 两阶段自适应采样器
- `control/base.py` — `ControlExperiment` 基类，含概率计算、李克特评分、绘图

### 算子

```python
# linear_comb（加法）：直接加控制向量
modified = current + controller

# projection（投影）：投影到控制方向
proj = (unit_current · unit_controller) × unit_controller
modified = current - proj + |weight| × controller × 10 × current_norm

# orthogonalize（正交化）：移除控制方向分量后加回
eliminated = current - weight × current_norm × unit_controller
modified = eliminated + controller
```

### 自适应采样算法（Phase 1 + Phase 2）

```python
# Phase 1：粗网格找边界
max_coeff = _probe_one_direction(0.0, +1, adaptive_threshold)
min_coeff = _probe_one_direction(0.0, -1, adaptive_threshold)
initial_coeffs = {min, max, 0} ∪ linspace(min, max, 15)

# Phase 2：在 Likert 分数变化最大的区间加密采样
for i in range(n_adaptive_samples):
    max_gap, best_midpoint = find_largest_likert_gap(probed_results)
    new_result = probe(best_midpoint)
    probed_results[best_midpoint] = new_result
```

## 与 ZenBrain 的对称性

```
CoBRA:    测量偏差 → 施加控制向量 → 再测量 → 调系数
ZenBrain: 记录后悔 → 睡眠固结回放 → 更新先验 → 下一次行为改变
```

同一个闭环结构，两套算子。CoBRA 是**空间控制**（激活向量），ZenBrain 是**时间控制**（记忆衰减/固结）。

## 三层整合路径

### 第 0 层（已就位）：行为数据采集

hippocampus.py + amygdala.py + reflex_events.json + reflex-behavior-calibration skill。
对应 CoBRA 的"认知偏差指数"——用经典实验测偏差。

### 第 1 层（可建）：控制信号映射

从 reflex_events.json 提取"当前主要偏差方向" → 生成校准后的行为约束 prompt → 注入 SOUL.md 或 reflex skill 规则权重。在 prompt 层做 CoBRA 的测量-控制循环（因为当前用 API 而非本地模型）。脚本：

```
输入：reflex_events.json（最近 N 条红线 + 正向）
输出：一条行为规则字符串，带强度权重
```

### 第 2 层（可建）：睡前固结闭环

改 `sleep_consolidator.py` 的回放采样逻辑：

```python
# 原来：按情绪权重均匀回放
replay_priority = amygdala_score

# 改成：按后悔梯度加权采样（CoBRA 风格）
replay_priority = |expected_confidence - actual_outcome|
```

白天在线轻度控制 + 夜晚离线深度重加权。这是 CoBRA 的 Phase 2 自适应采样在记忆固结中的直接迁移。

### 远期：本地模型 + 激活空间控制

当本地跑模型时，CoBRA 的 `WrappedBlock` + `rep_control_pipeline` 可以直接使用——在隐藏层做真正的向量注入，控制粒度从 prompt 升级到激活空间。Mistral-7B 已验证通过。

## CoBRA 没做的事（恰好是我们该做的）

1. **单轴控制**：只调单一偏差轴（权威/从众/确认/框架），无多轴联调
2. **外部基准**：经验来自社会科学实验，不是 Agent 自己的后悔日志
3. **无记忆系统**：不关心上次调完的效果是否被遗忘
4. **无代价函数**：不关心调偏差花了多少 token

这四条空缺对应 ZenBrain + reflex 已有或待建的模块：多维度校准、后悔日志、艾宾浩斯衰减、代价敏感。

## 验证状态

- CHI 2026 Best Paper：经过同行评议
- 代码可运行：Mistral-7B / LLaMA 已验证
- 自适应采样：有完整的数学推导和实验验证
- 绘图输出：scatter plot + Likert 曲线 + 概率分布
