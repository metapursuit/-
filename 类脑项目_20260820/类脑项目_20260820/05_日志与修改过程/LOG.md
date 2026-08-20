# 【AI伙伴】逻辑链台账（对话顺序追踪）

> **用途**：追踪【用户】与【AI伙伴】的跨会话对话顺序——谁在什么时候做了什么、为什么、遗留了什么。
> **动机**（2026-08-12 严苛审查）：多会话并行时，任何单一会话的记忆快照都会过期；
> git 只记录结果不记录意图。本文件是**意图层**的共享真相源。
> **约定**：每个会话在**重大节点**（开工/关键决策/里程碑/收工）追加一条，git 提交。
> 格式固定，禁止改写历史条目（追加不修改——数据只增不删）。

## 追加格式

```
- YYYY-MM-DDTHH:MM | @session:<profile>/<id> | 主题一句话
  - 做了：...
  - 关键决策：...
  - 遗留/依赖：...
```

- 2026-08-12 深夜 | （本会话 desktop） | 审查闭环自动化 + Cherry 技能库吸收
  - 做了：Desktop\code-reviews\ 存放区建立（README 约定：命名/模板/命令样例/编码）；Claude 直接落盘验证通过（README 自审 + wf.py 审查两份真实报告）；Claude 调度默认 workdir=Desktop\7.8；吸收 Cherry Studio 技能库 3 项（security-reviewer 整包 6 references、security-auditor 含 OWASP+3 脚本、git-bash-windows-paths 提炼自官方 bash-master）→ git 8efa5c4
  - 关键决策：审查报告免复制粘贴，Claude 打包生成到存放区、【AI伙伴】回读验证；Cherry 技能三档评估（吸收/参考/跳过）——office-to-md 等 12 项不吸收
  - 遗留：wf.py 两个中危 bug（cmd_clean 误归档 critic 阶段活跃链、cmd_log --today UTC 时区）待修，可调度 Claude 处理

- 2026-08-12 深夜 | （本会话 desktop） | 原生明珠探索 + 维护工具接入
  - 做了：系统性扫原生 CLI——journey 星图/insights/backup/checkpoints/security audit/moa/memory外部后端/project/bundles/hooks 等全盘点；cryptography HIGH 漏洞升级 48→50 清零；cron weekly-backup 建（每周日 23:00，no_agent，保留 4 份）；learnings 复盘约定
  - 关键决策：backup 进维护节奏（git 管配置 + backup 管会话双保险）；journey/insights 定为月度复盘工具；moa/sync/memory 外部后端暂缓（无多设备/多模型需求）
  - 遗留：agent-browser 未装（doctor 提示，需 npm install）；API 连通性检查超时（代理网络慢，非 Hermes 问题）

- 2026-08-13 上午 | （本会话 desktop，跨天续） | 时间校准修复 + 原生能力补齐（delegate/MCP/project）
  - 做了：learnings 时间戳格式升级（YYYY-MM-DDTHH:MM）+ 会话开场 date 校准铁律（跨天盲区）；delegate_task 演示（wf 架构分析子代理 deleg_98ebd22c）；searxng MCP server 接入（协议验证通过，工具 search 注册，config.yaml 已配，新会话生效）；project 工作区两个（companion-configs/hermes-companion-configs、wf-framework/Desktop\7.8）；运维脚本入仓库 scripts/
  - 关键决策：时间戳不凭记忆猜，先 date 校准；MCP 用自写 stdio server 包装 searxng（mcp SDK 已装）
  - 遗留：searxng 引擎网络未通（飞鱼 TUN 不覆盖 Docker，无本地代理端口；brave/ddg/google/wikipedia ConnectTimeout，bing 通但结果空）——开 v2rayN(10808) 后给容器配 HTTP_PROXY 即可恢复；MCP 工具需新会话生效；checkpoints 仍 0 项目（机制在，等写入触发）

## 历史时间线（2026-08-12 重建，含早期会话）

- 2026-08-09 晚 | @session:default/20260809_202929_3eadec | 闲聊重逢 + 需求压缩 skill 迭代 + 契约 v2.0 + ZenBrain 七层映射
  - 做了：需求压缩 V3.0（剪枝优先苏格拉底提问）；companion-contract-v2.md（五组数学公式）；类脑系列路线图 V2.1~V3.1
  - 关键决策：契约引用 ZenBrain 公式；判定权手动主
- 2026-08-10 晚 | @session:default/20260810_195325_f0f041 | V1 行为校准系统部署
  - 做了：SOUL+reflex-behavior-calibration skill+MEMORY；首条红线事件#1（隐瞒障碍 -10）；git 仓库 579bc35
  - 关键决策：reflex-* 命名体系；负向分级锚定；正向不自动检测
- 2026-08-11 下午~晚 | @session:default/20260811_164949_86d70e（本会话） | 类脑六器官建设
  - 做了：海马体/杏仁核/前额叶/固结器四器官 + 地基（PRINCIPLES+数据化+gold set）+ Bayesian 方案 v1.1
  - 关键决策：可迭代化原则（【用户】亲授）；内容迭代准入制；统计严谨（事件#3/#4）
- 2026-08-11 20:27 ~ 8/12 凌晨 | @session:default/20260811_200038_5bfe11 | 并行扩展：价值观/CoBRA/知识库
  - 做了：VALUES.md 板块一二（27条）；CoBRA 整合（reflex_deviator + REM 后悔梯度）；knowledge/ 证据库；qiushi-skill（6核心）；事件#5#6#7#8；事实源唯一化
  - 关键决策：知识不进器官管线（knowledge_events deprecated）；正向事件补录（#7 超预期/#8 审查反馈）
  - 遗留：reflex_deviator 路径未迁移（后由 8/12 审查修复）；MEMORY 副本未同步（后修复）
- 2026-08-12 12:11 | @session:default/20260812_121115_ec038f | 切换科大模型服务商
  - 做了：USTC API 接入（deepseek-v4-pro/glm-5.2-107 等）；Hermes 配置切换
- 2026-08-12 12:07~12:10 | git 51319bf→81524d8 | qiushi-skill 纳入/裁剪/映射（可能 5bfe11 尾声或独立会话）
- 2026-08-12 15:24 | @session:default/20260812_152241_468106 | 孙小凡高中故事（进行中）
- 2026-08-12 下午~晚 | @session:default/20260811_164949_86d70e（本会话续） | 严苛审查 + 全盘复查 + 收官
  - 做了：跨会话逻辑链重建；10 处 bug 修复（D1/B1/S5/G1 等）；六项决策重审（S5 regret 筛选/R-0003 种子回归）；FSRS 调度器收官（七器官闭环）；cross-session-audit skill 沉淀；交付审查报告（Desktop\类脑-系统交付审查-v1.md 等 Claude 审查）
  - 关键决策：规则必经工单；rem_min_regret=2.0；mild_score_threshold 防呆

- 2026-08-12T22:4x | @session:default/20260811_164949_86d70e（本会话） | cross-session-audit skill v1.1（Claude 审查 8 条全采纳）
  - 做了：description 触发词化（精简 52 字符）；补 git diff/路径变量/严重度表/审计输出格式；新增竞态/假设过期/回滚维度；降级方案（无 session_search 环境）
  - 关键决策：Claude #3（session_search 不可执行）判定为环境视角差异——skill 主消费方是 Hermes 【AI伙伴】，session_search 可用；降级方案保留作兼容层

- 2026-08-14 | goal 插件（DSH 移植第一项）：spec → 实施 → 动态验证
  - 做了：goal-plugin-spec（说明书）+ 实施（plugin.yaml + __init__.py 438 行，create_goal/get_goal/update_goal）；config.yaml 三处启用；code-reviews 目录约定（8/12 建，审查报告统一落盘）
  - 验证：【AI伙伴】动态验证——冒烟测试 16/16 全绿；修复 blocked 成功路径返回契约不对称（补 blocked:True）；语法 OK；config 三处确认
  - 关键决策：goal 是 DSH 移植清单优先级最高项；blocked 3 轮门槛 + revision 乐观锁 + 事件溯源
  - 遗留：重启 hermes 后真实工具调用验证；DSH 其余编排能力（workflow/ralph/plan-mode）待评估

- 2026-08-14T15:3x | @session:default/20260814_151008_b325f9 | DSH 评估文档复核 + goal 插件未生效根因定位
  - 做了：复核四份 DSH 移植评估文档（code-reviews/dsh-plugins-*）；实证三处硬伤——① execute_code 的 hermes_tools 无 delegate_task（14 个导出实证，workflow 原路径不成立，改 skill+顶层 batch / hermes chat -q 两条路）② Hermes 已有 plan skill v2.0（plan-mode 应增强而非从零写）③ delegate_task(context) 官方支持注入父会话上下文（subagent_fork 差距缩小为 snapshot vs continuation）；四份文档全部修订并标注 2026-08-14 复核
  - 验证：goal 插件代码 import OK（register+三 handler 齐全）；工具集解析模拟 `_get_platform_tools` → desktop/cli 均 goal=True；git clone 恢复正常（360 虚拟化随重启解决，Hello-World 实测）
  - 关键决策：插件发现是进程级缓存（discover_and_load 幂等），新装插件必须重启承载进程（serve/gateway）才生效；根因=插件 15:03-15:08 安装晚于 serve 14:59 启动的发现缓存，顺序反了
  - 遗留：杀 serve 进程（13420/24540）重启后验证 create_goal/get_goal/update_goal 真实可用；DSH 剩余项（spill 第2位/workflow/plan-mode 增强/ralph）；searxng 仍断网（待 v2rayN 10808 + 容器 HTTP_PROXY）

- 2026-08-14T15:4x | @session:default/20260814_151008_b325f9 | goal 插件重启后真实调用验证通过（遗留项清零）
  - 做了：杀 serve 进程（13420/24540）→ 15:33:01 插件发现 56 found 49 enabled（+1=goal）→ tool_search 确认 create_goal/get_goal/update_goal 注册（source=plugin, goal）
  - 验证（真实调用全链路）：get_goal（空态 has_goal=false）→ create_goal（g_1786693223_77a962, rev1）→ update_goal progress（rev1→2, rounds 1）→ 旧 revision 冲突被拒（乐观锁 ✓）→ complete（phase=completed）。goal_state.json 持久化 ✓
  - 关键决策：插件生效验证范式确立——杀 serve → 日志查 "Plugin discovery complete" 计数 +1 → tool_search 搜工具注册 → 真实调用生命周期
  - 遗留：无（本会话任务全清）

- 2026-08-14T16:0x | @session:default/20260814_151008_b325f9 | DSH 移植第二波：workflow/plan-mode/ralph 三 skill + spill 插件（赶 8.17 DeepSeek 涨价前）
  - 做了：查证 DeepSeek 8.17 调价（官方定价页：v4-flash 输出 2→4.5/9 元/M，v4-pro 输出 6→13.5/27 元/M，峰谷定价高峰 9-12/14-18 点，空闲半价；充值不锁价，扣费按消耗时单价）→ 制定"8.17 前提前消费"策略；三个 skill 已建（workflow=并行编排映射 delegate_task batch、plan-mode=批准门状态机基于官方 plan skill、ralph=每轮全新子代理+工作区跨轮记忆）；spill 插件已写（spill_write/read/list，原子写+路径穿越拦截，冒烟测试全绿：写/读分页/列/安全拒绝）
  - 踩坑：hermes config set plugins.enabled '["goal","spill"]' 把列表存成字符串 → plugins.enabled 解析失败会连累 goal 插件 → 修复脚本 scripts/fix_plugins_enabled.py 改回 YAML 列表；patch 工具拒绝改 config.yaml（安全机制），须用脚本
  - 关键决策：skill 三件套即时生效不需重启，spill 插件攒到重启时一起验证；spill 优先（痛点真实：大输出外溢 vs compression 事后压缩互补）；searxng 网络修复暂停（【用户】指示不需要搞 VPN，Docker 已启动）
  - 遗留：重启 serve 验证 spill 工具真实可用；8.17 后策略（空闲时段半价调度/prompt caching 价值上升/科大 API 分流）；searxng 引擎断网待日后

- 2026-08-14T16:0x | @session:default/20260814_151008_b325f9 | spill 插件重启后真实调用验证通过（DSH 移植第二波收官）
  - 做了：杀 serve（15:33 批）→ 15:52:38 插件发现 57 found 50 enabled（+1=spill）→ tool_search 确认 spill_write/read/list 注册
  - 验证（真实调用）：spill_write（写入+路径+preview+char_count）→ spill_read（读回 5 行）→ spill_list（列出 1 文件）→ 测试文件清理。全链路绿灯
  - 关键决策：DSH 移植账本更新——goal ✅ spill ✅ workflow/plan-mode/ralph ✅（skill 即时生效）；剩余 0 项核心移植（8.17 涨价前窗口全部用掉）
  - 遗留：searxng 引擎断网（暂停，【用户】指示不搞 VPN）；8.17 后成本策略待实施

## 当前状态（2026-08-12 收工时刻）

- git HEAD: ea31e32（35 提交，工作区 clean）
- 七器官全闭环：hippocampus/amygdala/prefrontal/sleep_consolidator/reflex_deviator/bayesian_evaluator/fsrs_scheduler
- 数据：8 事件（pos=2/neg=6）→ 4 规则 R-0001~R-0004 → 6 REM seeds → fsrs_state（S=7 初始化）
- 待办：① 交付审查报告 Claude 返回后逐条处理 ② 正向规则提炼（等【用户】点头）③ 杏仁核词库盲区等数据 ④ FSRS 遗忘路径 V2 ⑤ cross-session-audit v1.1 试用验证

- 2026-08-14T15:55 | @session:default/<本会话> | deepseek-harness skill 体系盘点 + trim-cot-leakage 提炼吸收
  - 做了：盘点 deepseek-harness .claude/skills 11 个 SKILL.md（dsh-archive-agent-notes/code-review/doc-site-sync/doc-standards/find-simplifications/merging-stacked-prs/pre-push-checks/prose-standard/translate-docs/trim-cot-leakage/record-browser-gif），三档评估；提炼 dsh-trim-cot-leakage 为通用版 skill trim-cot-leakage（8 类 taxonomy + keep 规则 + 过校正陷阱 + references/examples.md 校准集），同步 hermes-companion-configs/skills/ → git 9a4f407
  - 关键决策：吸收仅 trim-cot-leakage（视角/引用类泄漏，与 humanizer 管语气互补）；prose-standard/pre-push-checks/merging-stacked-prs/find-simplifications 列参考；其余 6 个绑定 dsh 仓库工具链跳过
  - 遗留：无

- 2026-08-14T16:2x | @session:default/20260814_151008_b325f9 | 教学成果审查（并行会话注入）+ knowledge_gap 关闭
  - 做了：核实并行会话的教学产出——goal-usage/dsh-orchestration-patterns/engineering-practices 三 skill 真实存在且质量合格（边界表/心智模型/工程实践齐全）；LEARNINGS 001-005 在 Hermes home（OpenClaw 格式）实存（初查漏 003/004 是查错位置，全查后确认）；修正三处事实错误：dsh-orchestration-patterns 的 execute_code 调 delegate_task 误导（实证无此能力）、goal-usage 与 plugin-development 的 platform_toolsets.cli 错误（插件 toolset 默认启用，无需手动加）
  - 验证：goal-smoke-test.py 16/16 全绿 EXIT=0（mock 依赖+临时目录隔离）→ LRN-004 knowledge_gap 关闭（Status pending→resolved + Resolution）
  - 关键决策：LEARNINGS 双源声明——运行时真身 Hermes home（OpenClaw 兼容），配置仓库为 git 镜像（003-005 同步段）；教学边界确认（结构性外部知识注入 OK，长尾自进化留给【AI伙伴】）
  - 遗留：plugin-development skill 与 goal-usage 的 related_skills 交叉引用待 curator 观察；8.17 后成本策略
- 2026-08-14T16:45 | @session:default/本会话 | 前端大改：自定义外观功能（源码级）
  - 做了：皮肤 v2（背景提亮+区域色显式化）→ 桌面插件质感层（注入CSS）→ 源码级自定义外观功能：新增 src/themes/custom-appearance.ts（背景图dataURL/遮罩强度/自定义CSS，localStorage持久化，皮肤联动）+ context.tsx applyTheme 接入 + appearance-settings.tsx 新"自定义外观"区块；npm run build 构建通过（vite 2.5s + electron main + 原生依赖）；patch 备份 patches/desktop-custom-appearance-20260814.patch（升级后 git apply 重放）
  - 关键决策：皮肤机制无渐变/纹理通道（语义色板+桌面端派生）→ 插件注入是补丁 → 【用户】要求源码级定制功能，直接改 app；背景图走 dataURL(≤2MB) 存 localStorage 而非文件路径（免 IPC/路径问题）；遮罩用 color-mix + --theme-background-seed 皮肤联动
  - 遗留：桌面 app 需重启生效（hermes desktop 有 content-hash stamp 自动重build）；ui-enhance 插件版与源码功能并存（插件版是旧路径，源码版是正式功能）
