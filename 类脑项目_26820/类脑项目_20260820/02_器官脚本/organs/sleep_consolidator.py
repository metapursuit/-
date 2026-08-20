#!/usr/bin/env python3
"""
睡眠固结器 (Sleep Consolidator) — SWS/REM/SHY 三阶段巩固器官
【AI伙伴】类脑系统 V2 · 执行器官之四

定位：存量整理器。把"已提炼的规则和事件"周期性巩固压缩，不是新数据入口。

三阶段（对齐 ZenBrain §4.3, Alg.4）：
  SWS 声明性巩固  解析 SKILL.md REFLEX_RULES 区块 → 生成结构化规则索引 rule_index.json
                  （下游 FSRS/Bayesian 只消费 JSON，不碰 Markdown）
  REM 情感联想    CoBRA V2: 后悔梯度加权（regret = |score| × emotional_weight）
                  高后悔事件 → 更高种子权重 → FSRS 优先回放
                  + 自适应优先级：后悔最高的类别建议加密规则提炼
  SHY 突触修剪    同 tag suppressed 事件达阈值 → 标记"模式已替代"归档候选 + 存储压缩统计

边界（铁律）：
  - 只标记不删除；不自动改 SKILL.md / reflex_events.json
  - REM 只关联负向事件（score<0），正向/中性永不进入关联（Claude review 阻塞项#2）
  - 全链可追溯：报告含来源事件 ID

CLI 用法：
  python sleep_consolidator.py consolidate [--file events.json] [--drafts drafts.json]
      [--skill SKILL.md] [--state state.json] [--index rule_index.json] [--params hyperparams.json]
  python sleep_consolidator.py report [--state state.json]
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hippocampus import Hippocampus, DEFAULT_PATH

CN_TZ = timezone(timedelta(hours=8))
ORGANS = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DRAFTS = os.path.join(ORGANS, "reflex_drafts.json")
DEFAULT_SKILL = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
                             "hermes", "skills", "reflex-behavior-calibration", "SKILL.md")
DEFAULT_STATE = os.path.join(ORGANS, "consolidation_state.json")
DEFAULT_INDEX = os.path.join(ORGANS, "rule_index.json")
DEFAULT_PARAMS = os.path.join(ORGANS, "hyperparams.json")

RULES_START = "<!-- REFLEX_RULES_START -->"
RULES_END = "<!-- REFLEX_RULES_END -->"
RULE_BLOCK_RE = re.compile(r"### (.+?)（(-?\d+(?:\s*~\s*-?\d+)?)(?:分)?）\n(.*?)(?=\n### |\Z)", re.S)
SOURCE_RE = re.compile(r"事件#(\d+)")


def now_iso():
    return datetime.now(CN_TZ).isoformat(timespec="seconds")


def _load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


class SleepConsolidator:
    def __init__(self, events_path=None, drafts_path=None, skill_path=None,
                 state_path=None, index_path=None, params_path=None):
        self.h = Hippocampus(events_path)
        self.drafts_path = drafts_path or DEFAULT_DRAFTS
        self.skill_path = skill_path or DEFAULT_SKILL
        self.state_path = state_path or DEFAULT_STATE
        self.index_path = index_path or DEFAULT_INDEX
        self.params = _load_json(params_path or DEFAULT_PARAMS, {})
        self.cons_p = self.params.get("consolidator", {})

    # ================= SWS 声明性巩固 =================
    def _parse_skill_rules(self):
        """解析 SKILL.md REFLEX_RULES 区块 → [{title, score, source_events}]"""
        if not os.path.exists(self.skill_path):
            return [], ["SKILL.md 不存在，无法解析规则"]
        with open(self.skill_path, "r", encoding="utf-8") as f:
            text = f.read()
        if RULES_START not in text or RULES_END not in text:
            return [], ["SKILL.md 缺少 REFLEX_RULES 标记（规则无法定位）"]
        block = text.split(RULES_START, 1)[1].split(RULES_END, 1)[0]
        rules = []
        for m in RULE_BLOCK_RE.finditer(block):
            title, score_str = m.group(1).strip(), m.group(2)
            body = m.group(3)
            # 支持 "（-10）" 和 "（-6 ~ -5分）" 两种格式
            nums = [int(x) for x in re.findall(r"-?\d+", score_str)]
            score = min(nums) if nums else 0
            rules.append({
                "title": title,
                "score": score,
                "source_events": sorted(int(x) for x in SOURCE_RE.findall(body)),
            })
        # 标记外疑似规则警告（Claude 建议#7）——列出具体标题供人工判断
        outside = text.split(RULES_END, 1)[1] if RULES_END in text else ""
        outside_hits = re.findall(r"^### (.+)$", outside, re.M)
        return rules, ([f"REFLEX_RULES 标记外疑似规则: {', '.join(outside_hits)}"] if outside_hits else [])

    def _sws(self):
        """SWS：解析规则 → 合并进 rule_index.json"""
        rules, warnings = self._parse_skill_rules()
        index = _load_json(self.index_path, {"rules": []})
        by_title = {r["title"]: r for r in index["rules"]}

        # 事件表：取来源事件的 category（第一个匹配）
        events_by_id = {e["id"]: e for e in self.h.data["events"]}
        # 工单表：事件 → 所属 batch
        drafts = _load_json(self.drafts_path, {"batches": []})
        batch_of_event = {}
        for b in drafts.get("batches", []):
            for g in b.get("groups", []):
                for eid in g.get("event_ids", []):
                    batch_of_event.setdefault(eid, b["batch_id"])

        next_num = max((int(r["rule_id"][2:]) for r in index["rules"]), default=0) + 1
        now = now_iso()
        indexed_ids = []
        for rule in rules:
            title = rule["title"]
            srcs = [eid for eid in rule["source_events"] if eid in events_by_id]
            cat = events_by_id[srcs[0]].get("category", "other") if srcs else "unknown"
            batch = next((batch_of_event[eid] for eid in srcs if eid in batch_of_event), None)

            if title in by_title:
                existing = by_title[title]
                existing.update({"score": rule["score"], "source_events": rule["source_events"],
                                 "category": cat, "source_batch": batch or existing.get("source_batch"),
                                 "status": "active"})
                rid = existing["rule_id"]
            else:
                rid = f"R-{next_num:04d}"
                next_num += 1
                by_title[title] = {"rule_id": rid, "title": title, "category": cat,
                                   "source_events": rule["source_events"], "source_batch": batch,
                                   "status": "active", "created_at": now, "suppress_count": 0}
            indexed_ids.append(rid)

        # 旧规则不在新解析列表 → 标记 removed（保留历史，不删除）
        for r in index["rules"]:
            if r["title"] not in {x["title"] for x in rules} and r.get("status") != "removed":
                r["status"] = "removed"
                warnings.append(f"规则 {r['rule_id']} ({r['title']}) 已不在 SKILL.md 中，标记 removed")

        index["rules"] = list(by_title.values())
        index["last_synced"] = now
        _save_json(self.index_path, index)
        return {"rules_found": len(rules), "rules_indexed": indexed_ids, "warnings": warnings}

    # ================= REM 情感联想 (CoBRA V2: 后悔梯度加权) =================
    def _regret_score(self, event):
        """CoBRA regret: |score| × emotional_weight.
        高后悔 = 大偏差 × 高在乎 = 最值得回放巩固。"""
        return abs(event["score"]) * event.get("emotional_weight", 0.5)

    def _rem(self, index):
        """REM：后悔梯度加权 → 与同类别 active 规则打关联种子。
        CoBRA V2 改进：①按 regret 降序排列（高后悔事件优先被 FSRS 调度回放）
                      ②种子 weight 保持 emotional_weight（0-1，Hebbian 初始权重语义），
                        regret_score 作为附加排序字段（不替代 weight——regret 可 >1，
                        直接作权重会破坏 0-1 契约；审查 S1 修正文档与实现一致）
        S5 修复（2026-08-12 重审）：筛选指标从 weight≥0.7 改为 regret≥rem_min_regret——
        weight 门槛会筛掉"高严重度低情绪"事件（如 -4×0.6=2.4），导致 R-0003 记忆质量规则
        无种子。regret=|score|×weight 已编码两者，用它筛选与排序指标一致。"""
        min_regret = self.cons_p.get("rem_min_regret", 2.0)
        events = [e for e in self.h.data["events"]
                  if e["score"] < 0 and self._regret_score(e) >= min_regret
                  and e.get("status") != "suppressed"]

        # 计算后悔并排序 —— 与 CoBRA Phase 2 "最大 gap 处加密采样" 同构
        scored = [(self._regret_score(e), e) for e in events]
        scored.sort(key=lambda x: x[0], reverse=True)

        rules = [r for r in index["rules"] if r.get("status") == "active"]
        seeds, unmatched = [], []
        for regret, e in scored:
            match = next((r for r in rules if r["category"] == e.get("category")), None)
            if match:
                seeds.append({
                    "event_id": e["id"],
                    "rule_id": match["rule_id"],
                    "weight": e.get("emotional_weight", 0.5),
                    "regret_score": round(regret, 2),
                })
            else:
                unmatched.append({
                    "event_id": e["id"],
                    "category": e.get("category"),
                    "regret_score": round(regret, 2),
                    "reason": "无同类别 active 规则",
                })

        # 后悔分布统计
        regrets = [s["regret_score"] for s in seeds]
        return {
            "seeds": seeds,
            "unmatched": unmatched,
            "min_regret": min_regret,
            "regret_distribution": {
                "max": max(regrets) if regrets else 0,
                "min": min(regrets) if regrets else 0,
                "mean": round(sum(regrets) / len(regrets), 2) if regrets else 0,
                "count": len(regrets),
            },
        }

    # ================= CoBRA 自适应优先级 (V2 新增) =================
    def _adaptive_prioritize(self, rem_result):
        """CoBRA Phase 2 映射：在后悔梯度最大的类别上建议加密提炼。

        不是直接修改规则，而是输出一份优先级建议——
        告诉 downstream（前额叶/人工）"这个类别后悔最高，该加密回放"。"""
        seeds = rem_result.get("seeds", [])
        if not seeds:
            return {"recommendations": [], "top_category": None, "top_regret": 0}

        # 按 category 聚合后悔
        index = _load_json(self.index_path, {"rules": []})
        rule_cat = {r["rule_id"]: r.get("category", "unknown") for r in index["rules"]}
        by_cat = {}
        for s in seeds:
            cat = rule_cat.get(s["rule_id"], "unknown")
            by_cat.setdefault(cat, []).append(s["regret_score"])

        cat_stats = {}
        for cat, regrets in by_cat.items():
            cat_stats[cat] = {
                "avg_regret": round(sum(regrets) / len(regrets), 2),
                "max_regret": max(regrets),
                "seed_count": len(regrets),
                "total_regret": round(sum(regrets), 2),
            }

        # 按总后悔降序 → CoBRA 的 "最大 gap 优先"
        ranked = sorted(cat_stats.items(), key=lambda x: x[1]["total_regret"], reverse=True)

        recommendations = []
        for i, (cat, stats) in enumerate(ranked):
            priority = "high" if i == 0 else ("medium" if i < 3 else "low")
            recommendations.append({
                "category": cat,
                "priority": priority,
                "action": f"建议加密 {cat} 类别规则提炼" if priority == "high" else "",
                **stats,
            })

        return {
            "recommendations": recommendations,
            "top_category": ranked[0][0] if ranked else None,
            "top_regret": ranked[0][1]["total_regret"] if ranked else 0,
        }

    # ================= SHY 突触修剪 =================
    def _shy(self):
        """SHY：同 tag suppressed 事件达阈值 → 归档候选 + 存储压缩估计"""
        threshold = self.cons_p.get("shy_suppress_threshold", 3)
        suppressed = [e for e in self.h.data["events"] if e.get("status") == "suppressed"]
        by_tag = {}
        for e in suppressed:
            by_tag.setdefault(e.get("tag") or "untagged", []).append(e["id"])

        candidates = [{"tag": t, "event_ids": ids, "suppressed_count": len(ids)}
                      for t, ids in by_tag.items() if len(ids) >= threshold]

        # 存储估计：可归档候选的 JSON 字节量（粗估）
        est = 0
        for e in self.h.data["events"]:
            if any(e["id"] in c["event_ids"] for c in candidates):
                est += len(json.dumps(e, ensure_ascii=False))
        total = len(json.dumps(self.h.data, ensure_ascii=False))
        return {"suppressed_events": len(suppressed), "archive_candidates": candidates,
                "storage_est_bytes": est, "storage_total_bytes": total,
                "storage_pct": round(est / total * 100, 1) if total else 0.0}

    # ================= 主流程 =================
    def consolidate(self):
        sws = self._sws()
        index = _load_json(self.index_path, {"rules": []})
        rem = self._rem(index)
        adaptive = self._adaptive_prioritize(rem)
        shy = self._shy()

        state = {
            "last_consolidated": now_iso(),
            "run_count": (_load_json(self.state_path, {}).get("run_count", 0) or 0) + 1,
            "sws": sws,
            "rem": rem,
            "adaptive": adaptive,
            "shy": shy,
        }
        _save_json(self.state_path, state)
        return state

    def report(self):
        state = _load_json(self.state_path, None)
        if state is None:
            return {"error": "尚无固结记录——先运行 consolidate"}
        return state


def main():
    p = argparse.ArgumentParser(description="睡眠固结器 — SWS/REM/SHY 三阶段巩固")
    p.add_argument("--file", default=None, help="事件文件路径")
    p.add_argument("--drafts", default=None, help="工单文件路径")
    p.add_argument("--skill", default=None, help="SKILL.md 路径")
    p.add_argument("--state", default=None, help="固结状态输出路径")
    p.add_argument("--index", default=None, help="规则索引输出路径")
    p.add_argument("--params", default=None, help="超参数文件路径")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("consolidate", help="执行三阶段巩固")
    r = sub.add_parser("report", help="查看最近固结报告")

    args = p.parse_args()
    sc = SleepConsolidator(args.file, args.drafts, args.skill, args.state, args.index, args.params)

    if args.cmd == "consolidate":
        print(json.dumps(sc.consolidate(), ensure_ascii=False, indent=2))
    elif args.cmd == "report":
        print(json.dumps(sc.report(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
