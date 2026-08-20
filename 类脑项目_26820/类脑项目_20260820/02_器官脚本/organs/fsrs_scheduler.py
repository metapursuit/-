#!/usr/bin/env python3
"""
FSRS 调度器 (FSRS Scheduler) — 自适应审计调度器官
【AI伙伴】类脑系统 V2 · 执行器官之七（收官）

定位：调度器，不是判定器。基于规则的稳定性 S 计算审计时间点，
审计后观测恢复率反馈更新 S——"恢复率低的规则审计更频繁"（契约 V2.4）。

数学（契约 companion-contract-v2.md，FSRS 变体）：
  S' = S · (1 + a(11-D) · S^{-b} · (e^{c(1-R)} - 1))
  自审查（2026-08-12，教训 #3/#4）：
  - R=1 → e^0-1=0 → S'=S（完美回忆不增长）✓
  - 0.7≤R<1 → 增长随 (1-R) 增大——越难的回忆成功提升越大（desirable difficulty）✓
  - R<0.7 → 契约公式不适用（成功路径公式），V1 标记失效风险不更新 S（不发明公式）
  next_audit: R(t)=e^{-t/S} 降到 audit_r_target → t = -S·ln(audit_r_target)

Hebbian 初始化：从固结器 REM seeds 聚合规则激活权重（mean weights），
记录 max regret——FSRS 审计优先级 = 调度时间 + 后悔强度提示。

输入：rule_index.json / consolidation_state.json（REM seeds）/ hyperparams.json（fsrs/hebbian 段）
输出：fsrs_state.json（每规则 S/D/R/next_audit/hebbian，全链可追溯）

边界：只计算调度与反馈更新，不触发任何动作；规则失效风险仅报告，判定权在【用户】/【AI伙伴】。

CLI:
  python fsrs_scheduler.py schedule                  # 初始化/更新全部规则调度
  python fsrs_scheduler.py status                    # 查看调度状态
  python fsrs_scheduler.py audit --rule R-0001 --observed-r 0.8   # 审计反馈
  python fsrs_scheduler.py hebbian                   # 查看 Hebbian 初始化
"""

import argparse
import json
import math
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hippocampus import Hippocampus, DEFAULT_PATH

ORGANS = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PARAMS = os.path.join(ORGANS, "hyperparams.json")
DEFAULT_INDEX = os.path.join(ORGANS, "rule_index.json")
DEFAULT_STATE = os.path.join(ORGANS, "fsrs_state.json")
DEFAULT_CONSOL = os.path.join(ORGANS, "consolidation_state.json")

CN_TZ = timezone(timedelta(hours=8))


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


def now_iso():
    return datetime.now(CN_TZ).isoformat(timespec="seconds")


class FSRSScheduler:
    def __init__(self, params_path=None, index_path=None, state_path=None, consol_path=None):
        self.params = _load_json(params_path or DEFAULT_PARAMS, {})
        self.fp = self.params.get("fsrs", {})
        self.hp = self.params.get("hebbian", {})
        self.index_path = index_path or DEFAULT_INDEX
        self.state_path = state_path or DEFAULT_STATE
        self.consol_path = consol_path or DEFAULT_CONSOL

    # ---- 数学核心 ----
    def stability_update(self, s, d, observed_r):
        """契约公式：成功回忆路径（observed_r ≥ audit_r_target）。"""
        a = self.fp.get("a", 0.5)
        b = self.fp.get("b", 0.5)
        c = self.fp.get("c", 0.5)
        growth = a * (11 - d) * (s ** -b) * (math.exp(c * (1 - observed_r)) - 1)
        return s * (1 + growth)

    def next_audit_days(self, s):
        """R(t)=e^{-t/S} 降到 audit_r_target 的时刻。"""
        target = self.fp.get("audit_r_target", 0.7)
        if s <= 0:
            return 1.0
        return -s * math.log(target) if target < 1 else s

    # ---- Hebbian 聚合（从 REM seeds） ----
    def _hebbian_from_seeds(self):
        cons = _load_json(self.consol_path, {})
        seeds = cons.get("rem", {}).get("seeds", [])
        by_rule = {}
        for s in seeds:
            rid = s["rule_id"]
            b = by_rule.setdefault(rid, {"weights": [], "regrets": []})
            b["weights"].append(s.get("weight", 0.5))
            b["regrets"].append(s.get("regret_score", 0))
        return {
            rid: {
                "weight": round(sum(v["weights"]) / len(v["weights"]), 3),
                "max_regret": round(max(v["regrets"]), 2),
                "seed_count": len(v["weights"]),
            }
            for rid, v in by_rule.items()
        }

    # ---- 调度 ----
    def schedule(self):
        index = _load_json(self.index_path, {"rules": []})
        active = [r for r in index["rules"] if r.get("status") == "active"]
        hebb = self._hebbian_from_seeds()
        state = _load_json(self.state_path, {"rules": {}})
        now = now_iso()

        for r in active:
            rid = r["rule_id"]
            cur = state["rules"].get(rid, {})
            if not cur:  # 新规则初始化：S=7（原固定7天基线）、D=5（中等）、R=1.0
                         # 注(2026-08-20): D 目前为固定值待标定——stability_update 只读 D 不更新，
                         # 属已知限制（无标定数据支撑，遵守内容迭代准入制）。
                cur = {
                    "rule_id": rid, "title": r["title"], "category": r.get("category"),
                    "S": self.fp.get("init_s", 7.0), "D": self.fp.get("init_d", 5.0),
                    "R": 1.0, "last_audit": None,
                    "source_events": r.get("source_events", []),
                    "created_at": now,
                }
            days = round(self.next_audit_days(cur["S"]), 2)
            # 修复(2026-08-20): next_audit 必须是真正的未来时刻（ISO 时间戳），
            # 此前把 now 当时间戳、天数只作字符串后缀，调度器从未输出未来审计时间。
            cur["next_audit"] = (datetime.fromisoformat(now) + timedelta(days=days)).isoformat(timespec="seconds")
            cur["next_audit_days"] = days
            cur["hebbian"] = hebb.get(rid, {"weight": None, "max_regret": None, "seed_count": 0})
            state["rules"][rid] = cur

        state["last_scheduled"] = now
        state["meta"] = {
            "active_rules": len(active),
            "avg_S": round(sum(r2["S"] for r2 in state["rules"].values()) / len(state["rules"]), 2) if state["rules"] else 0,
        }
        _save_json(self.state_path, state)
        return state

    # ---- 审计反馈 ----
    def audit(self, rule_id, observed_r):
        state = _load_json(self.state_path, {"rules": {}})
        if rule_id not in state["rules"]:
            # 尝试从索引自动初始化（未 schedule 直接 audit 的场景）
            index = _load_json(self.index_path, {"rules": []})
            hit = next((r for r in index["rules"] if r["rule_id"] == rule_id), None)
            if not hit:
                return {"error": f"规则 {rule_id} 不存在于调度状态与规则索引"}
            self.schedule()
            state = _load_json(self.state_path, {"rules": {}})

        cur = state["rules"][rule_id]
        threshold = self.fp.get("audit_r_target", 0.7)
        result = {
            "rule_id": rule_id, "observed_r": observed_r, "threshold": threshold,
            "S_before": cur["S"], "D": cur["D"],
        }
        if observed_r >= threshold:
            new_s = self.stability_update(cur["S"], cur["D"], observed_r)
            cur["S"] = round(new_s, 3)
            cur["R"] = round(observed_r, 3)
            cur["last_audit"] = now_iso()
            cur["next_audit_days"] = round(self.next_audit_days(cur["S"]), 2)
            cur["next_audit"] = now_iso() + " (approx " + str(cur["next_audit_days"]) + "d)"
            result.update({"S_after": cur["S"], "status": "stable",
                           "note": "契约公式成功路径：恢复良好，稳定性更新"})
        else:
            result.update({"S_after": cur["S"], "status": "at_risk",
                           "note": "恢复率低于阈值——契约公式仅覆盖成功路径，S 不更新；建议人工复核规则是否仍适用（判定权在【用户】/【AI伙伴】）"})
        state["rules"][rule_id] = cur
        state["last_audit"] = now_iso()
        _save_json(self.state_path, state)
        return result

    def hebbian(self):
        return {"hebbian": self._hebbian_from_seeds(),
                "source": "consolidation_state.json REM seeds"}


def main():
    p = argparse.ArgumentParser(description="FSRS 调度器 — 自适应审计调度")
    p.add_argument("--params", default=None, help="超参数文件路径")
    p.add_argument("--index", default=None, help="规则索引路径")
    p.add_argument("--state", default=None, help="调度状态输出路径")
    p.add_argument("--consol", default=None, help="固结状态路径（REM seeds 来源）")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("schedule", help="初始化/更新全部规则调度")
    t = sub.add_parser("status", help="查看调度状态")
    a = sub.add_parser("audit", help="审计反馈（更新稳定性）")
    a.add_argument("--rule", required=True)
    a.add_argument("--observed-r", type=float, required=True)
    h = sub.add_parser("hebbian", help="查看 Hebbian 初始化")

    args = p.parse_args()
    fs = FSRSScheduler(args.params, args.index, args.state, args.consol)

    if args.cmd == "schedule":
        print(json.dumps(fs.schedule(), ensure_ascii=False, indent=2))
    elif args.cmd == "status":
        st = _load_json(fs.state_path, {"rules": {}})
        print(json.dumps(st, ensure_ascii=False, indent=2))
    elif args.cmd == "audit":
        print(json.dumps(fs.audit(args.rule, args.observed_r), ensure_ascii=False, indent=2))
    elif args.cmd == "hebbian":
        print(json.dumps(fs.hebbian(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
