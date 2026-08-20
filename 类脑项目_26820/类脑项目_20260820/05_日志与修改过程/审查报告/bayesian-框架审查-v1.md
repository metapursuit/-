# Bayesian 评估器 — 框架方案审查报告

**日期**: 2026-08-11
**被审文件**: `Desktop\bayesian-框架方案-v1.md`
**审查标准**: PRINCIPLES.md（六条原则）、数学正确性、接口衔接、测试覆盖
**配套上下文**: `hyperparams.json`（bayesian 段仅有 prior）、`consolidation_state.json`（固结器已跑）、`rule_index.json`（R-0001 已存在）、`reflex_events.json`（2 条事件）

---

## 总体判断

**框架方向正确，三个高优问题必须先修再动手实现。** Beta-Binomial 建模、三级门槛制、scipy→纯Python→拒绝正态近似的回退策略都是对的。但数学公式有笔误、边界行为有定义缺口、诚实原则有漏洞。

---

## 逐项审查

### ❌ 问题 1：均值公式写错（line 38）

```
后验均值 E[θ] = (α₀+k)/(α₀+n+k+β₀-1) 校正为 (α₀+k)/(α₀+β₀+n)
```

第一个表达式 `(α₀+k)/(α₀+n+k+β₀-1)` 是错误的——分母不应包含额外的一个 `n` 和一个 `-1`。Beta(α₀+k, β₀+n-k) 的均值恒为：

```
E[θ|data] = (α₀+k) / (α₀+β₀+n)
```

不存在"第一种写法再校正为第二种"的中间形式。**错误公式不应出现在设计文档中**——无论是叙事手法还是笔误，它都会误导后续读文档的人。

---

### ❌ 问题 2：二值化丢弃分数强度，诚实声明不充分

提案：V1 只看正负（score < 0），-10 和 -3 同权重。V2.6 再引入加权。

设计取舍本身可以接受。但**诚实声明不到位**。PRINCIPLES.md 原则三：

> "统计版：样本不足不假装有结论——'能运行 ≠ 有统计效力'"

同理应有一条：**"统计显著 ≠ 语义正确"。** 伯努利模型在以下场景会静默撒谎：

```
场景 A：10 条事件，全 -1（【用户】轻微不满） → θ=1.0 → "真问题概率高" → 建议提炼
场景 B：10 条事件，全 -10（【用户】暴怒）    → θ=1.0 → 完全相同的结论
```

模型把"轻微皱眉 10 次"和"红线暴怒 10 次"视作等同。按诚实原则，**必须在输出中显式区分**。

**修复方案**：在建议生成时加一层判断——若 P(θ>0.5) ≥ 0.9 但中位分数 > -4（全低负向），建议文变为"低分累积提醒（同类低负向反复出现，建议关注）"而非"真问题概率高（建议触发提炼）"。这与契约中"负向累积陷阱（-1~-3 同类累计 N 条自动提醒）"完全一致——Bayesian 正是这个机制的统计基础，不应把低负向累积和严重红线混为一谈。

**额外**：方案中应新增一节"已知限制"，明确列出：
- V1 不区分分数强度（-1 和 -10 在伯努利模型中同权重）
- 高分数强度信息将在 V2.6 情感调节中通过加权似然引入
- 当前缓解措施：低分累积警告 vs 真问题警告的文本区分

---

### ❌ 问题 3：weak_evidence 状态下的建议行为未定义

门槛表定义了三状态，但只有 `ok` 给了建议动作映射：

| 状态 | 计算 P(θ>0.5)？ | 输出建议？ | 文档是否定义？ |
|------|----------------|-----------|--------------|
| `insufficient_data` | 否 | 否（拒给结论） | ✅ 明确 |
| `weak_evidence` | **？** | **？** | ❌ 未定义 |
| `ok` | 是 | 三级建议 | ✅ 明确 |

两种合理设计：

**A) weak_evidence 仍给建议，但打标签：**
```
建议：真问题概率高 [弱证据，仅供观察]
```
优点：信息密度高，用户能看到"模型在猜什么"。缺点：可能被误读为可靠结论。

**B) weak_evidence 不给建议，只给数值：**
```
状态：弱证据（n=12, CI 宽度 0.48）
建议：数据不足，继续积累
```
优点：更保守，符合"敢说不知道"的定位。缺点：浪费了已有信号。

**建议选 A**——符合 PRINCIPLES.md 原则三的精神（"不知为不知"不意味着"有弱信号也要装瞎"，而是"告诉你信号弱"）。但建议文本强制加 `[弱证据]` 前缀，输出中明确区分于 ok 的建议。

---

### ⚠️ 问题 4：事件数量错误（line 17）

"当前仅 **3** 条事件"。reflex_events.json 实际只有 **2 条**：
- id=1: -10 transparency
- id=2: -4 memory

git log 中也无第三条。改为 2。

---

### ⚠️ 问题 5：hyperparams.json 键名清单缺失

提案说阈值全部在 `hyperparams.json → bayesian` 段，并标注"已存在，追加"。但实际文件只有：

```json
"bayesian": {
    "prior_alpha": 1,
    "prior_beta": 1
}
```

**缺少的键**（提案依赖但未列出）：

| 键名 | 用途 | 建议默认值 |
|------|------|-----------|
| `min_samples` | insufficient_data 门槛 | 10 |
| `weak_n_threshold` | weak → ok 的 n 分界 | 30 |
| `weak_ci_width` | CI 宽度超此值 → weak | 0.4 |
| `suggestion_threshold_high` | P(θ>0.5) ≥ 此值 → "真问题概率高" | 0.9 |
| `suggestion_threshold_mid` | P(θ>0.5) ≥ 此值 → "倾向真问题" | 0.6 |

**修复**：方案中新增一节"hyperparams.json bayesian 段完整 schema"，或在文件设计表中列出键名。

---

### ⚠️ 问题 6：测试计划缺 6 个边界过渡用例

现有 10 项测试覆盖核心路径。缺失的边界：

| # | 用例 | 期望 | 为什么重要 |
|---|------|------|-----------|
| 11 | n = 9, k = 5 (min_samples-1) | insufficient_data | 差 1 条事件结论天壤之别——过渡边界必须正确 |
| 12 | n = 10, k = 5 (恰好在门槛) | weak_evidence | 准入边界 |
| 13 | n = 29 → n = 30, 同 k 比例 | weak → ok 过渡 | 分类切换边界 |
| 14 | P(θ>0.5) = 0.899 vs 0.901 | 建议等级不同 | 差 0.002 概率就换建议——边界必须精确 |
| 15 | 某 category 在数据中不存在 | insufficient_data, 输出先验 | 空类别不应崩也不应假装有数据 |
| 16 | prior 从 Beta(1,1) 改为 Beta(2,2)（改 hyperparams） | 后验变化可验证 | 原则一："改内容=改 JSON，不改 .py"——必须可测 |

---

### ⚠️ 问题 7：bayesian_state.json schema 未定义

提案只说含"n/k/后验均值/CI/建议/时间戳/status"。未给结构。参考 consolidation_state.json 现有格式，建议：

```json
{
  "last_evaluated": "2026-08-11T18:50:00+08:00",
  "categories": {
    "transparency": {
      "n": 2,
      "k": 2,
      "posterior": {"alpha": 3, "beta": 1, "mean": 0.75},
      "ci_95": [0.30, 0.97],
      "ci_width": 0.67,
      "p_theta_gt_05": 0.86,
      "status": "insufficient_data",
      "suggestion": null,
      "suggestion_level": null,
      "previous_status": null,
      "status_changed_at": null
    },
    "memory": {
      "n": 1,
      "k": 1,
      "posterior": {"alpha": 2, "beta": 1, "mean": 0.667},
      "ci_95": [0.16, 0.99],
      "ci_width": 0.83,
      "p_theta_gt_05": 0.75,
      "status": "insufficient_data",
      "suggestion": null,
      "suggestion_level": null,
      "previous_status": null,
      "status_changed_at": null
    }
  },
  "meta": {
    "total_categories": 2,
    "ok_count": 0,
    "weak_count": 0,
    "insufficient_count": 2
  }
}
```

注意 `previous_status` + `status_changed_at`——为 Q7（趋势检测）预埋字段。

---

### ⚠️ 问题 8："category" 的定义域未明确

Bayesian 按 category 分组。category 来自哪里？

| 选项 | 来源 | 效果 |
|------|------|------|
| A | `reflex_events.json` 的 `category` 字段 | 动态出现新类别；memory（1 条事件但无规则）也会出现 |
| B | `rule_index.json` 的 `category` 字段 | 静态，只有已提炼规则的类别；memory 不会出现 |

当前数据：events 有 transparency + memory。rule_index 只有 transparency（R-0001）。

**影响 FSRS 衔接**（审查问题 Q6）。如果 Bayesian 结论要喂给 FSRS（按类别调整审计优先级），则需要 category 与 rule_index 对齐。但如果 Bayesian 也要覆盖"未提炼但已有事件的类别"（预警功能），则需要 events 维度。

**建议**：以 events 的 category 为准（选项 A），但在 bayesian_state 每个类别下加 `has_rules` 布尔字段（查 rule_index）。FSRS 消费时自行过滤。

---

### ⚠️ 问题 9：Beta 分位数回退的验证范围不足

"误差 < 1e-3" 是对的，但未指定验证的参数范围。连分数展开在极端参数下可能振荡或收敛极慢。

**需增加的验证参数**：
- 极端小：α=0.5, β=0.5（Jeffreys prior）
- 极端偏斜：α=100, β=1（大量事件全负向）
- 极端平衡：α=50, β=50（大量事件正负各半）
- 当前真实参数：α=3, β=1（n=2, k=2 with Beta(1,1) prior）

在以上四种参数下验证纯 Python 回退与 scipy 的误差均 < 1e-3。

---

### ⚠️ 问题 10：`analyze` 与 `status` 子命令区别未定义

```
python bayesian_evaluator.py status                    # 全类别总览
python bayesian_evaluator.py analyze --category X      # 单类别深入
```

`status` = 汇总表，那 `analyze` 深入什么？

至少应明确是否包含：
- 该类所有事件的 id/score/tag 列表
- 后验分布关键分位数（中位数 / 25% / 75%）
- 与前次评估的对比（如果 `previous_status` 存在）
- 低分累积警告（如果触发问题 2 的条件）

---

### ✅ 做得正确的地方

- **Beta-Binomial 共轭建模**正确，θ = P(负向) 的定义清晰
- **scipy → 纯 Python 回退 → 拒绝正态近似**的优先级正确——正态近似在 n<30 时误差不可接受
- **三级门槛 + 参数外置**符合 PRINCIPLES.md 原则一（数据不进代码）
- **三步实施计划**每步可验证：手算对照 → 10 项测试 → 真实数据 insufficient_data
- **"敢说不知道"的定位**正确对齐原则三——n<10 拒给结论
- **黄金集回归**（bayesian_gold.json + run_bayesian_regression.py）符合原则七
- **与 consolidation_state.json 解耦**——Bayesian 只读 events，不依赖固结器
- **建议动作不触发执行**——"只输出建议文本"，判定权在【用户】/【AI伙伴】，符合原则二

---

### 审查问题逐答

**Q1: θ = P(负向) 的伯努利模型是否合适？**
合适。Beta-Binomial 是比例推断的标准共轭模型。"真问题"操作化定义为"该类负向比例显著高"是可接受的——它与契约"负向累积陷阱"直接对应。但需补问题 2 的分数强度诚实声明。

**Q2: min_samples=10 / n=30 分级是否合理？**
n=10 作为 insufficient 门槛合理——Beta(1,1) 下 n=2 CI 宽度 ~0.8（无信息），n=10 CI 宽度在 0.40~0.55（开始有信息但弱）。n=30 作为 ok 门槛也合理——CI 宽度 ≤0.4 在 Beta(1,1) 下需要 n≥30（平衡数据 ~0.37，偏斜数据更窄）。但文档中"n≥30 约 0.25"只对偏斜数据成立，平衡数据在 n=30 时宽度约 0.37。建议修正措辞。

**Q3: 建议阈值 0.9 / 0.6 是否合理？**
0.9 意味着"90% 把握该类是问题高发区"——需要 k/n ≥ ~0.63（约 19/30）。合理的保守门槛。0.6 作为"倾向真问题"底线——略高于 0.5（完全不确定），提供最低限度的区分度。合理。

**Q4: scipy vs 纯 Python 回退优先序？**
正确。先试 scipy（如果有），再纯 Python（连分数+二分），拒绝正态近似。优先级不改变。

**Q5: 10 项测试有无遗漏？**
有遗漏——见问题 6，缺 6 项边界过渡测试。

**Q6: bayesian_state 是否应被 FSRS 消费？**
应该。FSRS 审计规则时，Bayesian 的类别级 P(θ>0.5) 可以作为审计优先级的附加信号——"transparency 类别问题概率高 → 该类别规则审计更频繁"。但需要 Bayesian 先完成、FSRS 读 bayesian_state.json。当前实施顺序（Bayesian → FSRS）支持这一点。

**Q7: 是否需要记录"上次结论变化"（趋势检测）？**
需要。已在 bayesian_state schema 中预埋 `previous_status` 和 `status_changed_at`。V1 不实现趋势分析，但字段先占位。

**Q8: 伯努利丢分数强度——V1 可接受吗？**
可接受，但有条件——见问题 2。必须加"低分累积"的文本区分 + 已知限制章节。

---

## 修改清单（实现前必须完成）

| # | 严重度 | 修改项 | 位置 |
|---|--------|--------|------|
| 1 | **高** | 删除错误均值公式，只保留 `(α₀+k)/(α₀+β₀+n)` | §2 line 38 |
| 2 | **高** | 新增"已知限制"节：声明二值化丢分数强度 + 低分累积 vs 真问题的文本区分 | 新增 §2 末 |
| 3 | **高** | 定义 weak_evidence 下的建议行为（给建议但打 `[弱证据]` 标签） | §3-§4 |
| 4 | **中** | 事件数量 3 → 2 | §0 line 17 |
| 5 | **中** | hyperparams.json bayesian 段补充 5 个缺失键名及默认值 | §5 或新增 |
| 6 | **中** | 测试计划追加 6 项边界过渡用例（n=9/10/29/30, P≈0.9/0.6 边界, 空类别, prior 可配） | §6 |
| 7 | **中** | 定义 bayesian_state.json 完整 schema | §5 |
| 8 | **低** | 明确 category 来源（events 字段），加 `has_rules` 布尔 | §2 或 §5 |
| 9 | **低** | Beta 分位数回退验证指定四种参数范围 | §6-§7 |
| 10 | **低** | 定义 `analyze --category X` 输出内容清单 | §5 CLI 段 |

---

## 结论

**批准框架方向，三个高优问题必须先修。** 修完后可以直接进三步实施计划——数学核心是确定的，剩下的工程问题都是已知的。最危险的不是代码写错，而是伯努利模型静默把低负向累积和红线暴怒混为一谈——这是原则性违规，必须在方案里补上诚实声明和文本区分逻辑。

---

*配套审查文件：`Desktop\hermes-code-review.md`（三器官代码审阅）、`Desktop\hermes-design-review-v1.md`（三器官设计审查）、`Desktop\类脑-开发计划-v1.md`（总计划）*
