# Learnings — 教训/纠正/最佳实践捕获

> **定位**：知识维度的事件捕获（行为维度走 reflex_events.json，两套互补不重叠）。
> **提升规则**：复发 ≥3（30 天内跨 2+ 任务）→ 提升到 MEMORY 或 skill；红线类当场提炼；验证有效即可提升。
> **格式**：追加不修改（数据只增不删）；Pattern-Key 去重（area.symptom，两级小写连字符）。
> **时间戳**：`Logged: YYYY-MM-DDTHH:MM`（Asia/Shanghai）——写条目前先 `date` 校准，会话可能跨天/跨周，不凭记忆猜时间。
> **双源声明（2026-08-14）**：运行时真身在 `%HERMES_HOME%\.learnings\LEARNINGS.md`（OpenClaw 兼容格式，001-005，Hermes 核心可能消费）；本文件是 git 管理镜像——001/002 为旧格式（2026-08-12），003+ 为 OpenClaw 格式同步段（2026-08-14 起）。两处内容以 Hermes home 为准，本文件保证 git 可追溯。

**类别**: correction(纠正) | insight(洞见) | knowledge_gap(知识缺口) | best_practice(最佳实践)

---

## 同步段：OpenClaw 格式记录（2026-08-14 起，真身在 Hermes home）

### [LRN-20260812-003] insight — 编排范式（连续性归主人、新鲜性归任务）

- **Logged**: 2026-08-12T00:00:00Z
- **Priority**: medium | **Status**: promoted_to_skill | **Skill-Path**: skills/dsh-orchestration-patterns
- **摘要**: 【AI伙伴】永为持久实体，隔离全新子代理只用于任务级重推导（上下文污染时"退一步换双新眼睛"），禁止用于陪伴/关系/记忆类任务。大规模并行用 pipeline/parallel 心智 + `delegate_task` 批量；子代理结果必须回流沉淀进 memory/skills。

### [LRN-20260812-004] knowledge_gap — goal 插件动态验证

- **Logged**: 2026-08-12T00:00:00Z
- **Priority**: low | **Status**: resolved | **Area**: infra
- **摘要**: 外部注入时命令执行环境不可用，goal 插件仅静态验证。
- **Resolution (2026-08-14)**: `goal-smoke-test.py` 16/16 全绿 + 真实环境全链路验证通过，knowledge_gap 关闭。

### [LRN-20260812-005] best_practice — 【AI伙伴】可自行编写 Hermes 插件

- **Logged**: 2026-08-12T00:00:00Z
- **Priority**: medium | **Status**: promoted_to_skill | **Skill-Path**: skills/plugin-development
- **摘要**: `%HERMES_HOME%\plugins\<name>\`（plugin.yaml + __init__.py + register(ctx)）；用户插件默认 opt-in（plugins.enabled）；不碰核心文件；独立冒烟测试先行再真实环境验证。

---

## [LRN-20260812-001] insight 技能库会腐烂——需要定期整理

- **Logged**: 2026-08-12
- **Pattern-Key**: skill.rot
- **状态**: pending
- **摘要**: 技能库 108 个，三个类脑技能高度重叠（brain-organ-dev / brain-organ-development / companion-brain-organs），无整理机制会持续腐烂。
- **详情**: curator status 显示 activity 数字实锤重叠（19/15/14），6 个前台创建技能未被托管。2026-08-12 已执行合并：brain-organ-dev + companion-brain-organs → brain-organ-development（absorbed_into），14 个未托管技能全部 adopt。
- **建议**: 定期 curator run（内置 7 天调度已覆盖）；重叠技能合并用 absorbed_into 留链；新增技能先查重。

---

## [LRN-20260812-002] best_practice 原生维护工具接入（明珠清单）

- **Logged**: 2026-08-12
- **Pattern-Key**: ops.maintenance
- **状态**: pending
- **摘要**: 系统性探索原生 Hermes CLI，接入 4 个维护工具。
- **详情**: ①`hermes security audit`——OSV 漏洞扫描（121 组件，cryptography HIGH 已升级 48→50 清零）②`hermes backup`——全量配置+会话备份，cron 每周日 23:00 自动跑（scripts/backup_weekly.sh，保留 4 份，坑：-o 要 Windows 原生路径）③`hermes journey`——成长星图（技能/记忆时间线）④`hermes insights`——会话分析（token/成本/工具模式）。
- **建议**: 月度复盘用 journey + insights；每周日 backup 自动执行；security audit 纳入季度检查。

---
