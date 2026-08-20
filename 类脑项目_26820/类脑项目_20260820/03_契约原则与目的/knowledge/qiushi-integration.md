# qiushi-skill 集成映射（求是方法论 × 【AI伙伴】现有体系）

> 2026-08-11 建立。来源：qiushi-skill v1.4.1（HughYau，MIT，npm 官方 registry，安装前已逐行审查安装逻辑）。
> 定位：**思维工具库，不是信仰体系**。方法论当工具用，不当真理用。

## 决策记录

| 日期 | 决策 | commit |
|---|---|---|
| 2026-08-11 | 安装 v1.4.1（11 skills），审查通过 | — |
| 2026-08-11 | 纳入配置仓库（完整镜像） | `51319bf` |
| 2026-08-11 | 精选裁剪至 6 核心（【用户】拍板，方案A） | `a43d716` |

**回滚方式**：`git checkout 51319bf -- skills/qiushi-skill/<skill>` 或整体恢复该 commit 的目录。

## 保留的 6 核心：与现有体系的边界

| skill | 触发时机 | 与现有体系的边界（谁管什么） |
|---|---|---|
| **arming-thought** | 新会话开始：建立"实事求是"总原则，路由下游 | SOUL 已有破除幻觉/诚实第一精神。本 skill 是**方法论路由层**，不覆盖 SOUL；宿主已有更强约束时以宿主为准 |
| **contradiction-analysis** | 复杂问题、多冲突因素、优先级不清 | `systematic-debugging` 管技术根因链；本 skill 管**主次取舍/问题排序**。正确姿势：先矛盾分析定主攻，再调试追根因 |
| **investigation-first** | 信息不足要下判断时 | `honest-execution` 管"诚实报告缺口"；本 skill 管"**如何补缺口**"；`grounded-citations` 管引用规范。三者职责互补不冲突 |
| **practice-cognition** | 方案需实践验证/迭代时 | `brain-organ-development` 管器官开发的具体迭代流程；本 skill 管**通用验证-复盘循环**（假设→实验→修正） |
| **criticism-self-criticism** | 交付后复盘、收到批评反馈 | `reflex-behavior-calibration` 管行为事件评分（±10 奖惩）；本 skill 管**工作质量审查方法**（review-checklist）。职能不同：reflex 管"我做得对不对"，csc 管"活儿干得好不好" |
| **workflows** | 多方法串联时 | 编排层。使用纪律：**一次最多串联 2 个**，不机械调用 |

## 使用纪律

1. **优先级**：用户明确指示 > 宿主平台规则 / SOUL > qiushi 方法论
2. 一次只选一个主 skill，确有必要再串联第二个；不为了"形式完整"机械调用
3. 命中 skill 的"不适用场景"列表时，直接跳过
4. **意识形态注意**：原文引用仅作溯源，方法论用于问题分析，不用于政治话语；不因引用经典而免于批判性审查
5. 冲突裁决：qiushi 方法论的任何规则与 SOUL/VALUES 冲突时，SOUL 胜

## 裁剪记录（去芜）

已删 5 个低触发率 skill（完整内容在 `51319bf` 可恢复）：

| 已删 | 理由 |
|---|---|
| mass-line | 【AI伙伴】执行场景几乎无多方意见收集；对【用户】个人用途可恢复 |
| concentrate-forces | todo 工具天然承担优先级排序 |
| overall-planning | 触发率低，多目标平衡多由用户直接裁决 |
| protracted-strategy | cronjob 承担长期任务；现阶段无长周期项目 |
| spark-prairie-fire | MVP 思路已由 coding-discipline/最小化原则覆盖 |

## 观察项（2-4 周后评估，2026-08-25 前后）

- [ ] 6 核心中实际被触发的有几个？触发率低者考虑再裁
- [ ] investigation-first 与 honest-execution 是否造成调用歧义？→ 决定是否融合
- [ ] workflows 是否被滥用（机械串联）？→ 决定是否删除
- [ ] 【AI伙伴】之外，【用户】个人是否用到已删 skill？→ 决定是否单独恢复

## 升级策略

上游发布新版本时：`git checkout 51319bf` 对比 → 审查 changelog → 决定是否吸收 → 重新走"镜像→裁剪→映射"流程。
