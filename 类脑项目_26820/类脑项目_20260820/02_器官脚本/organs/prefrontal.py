#!/usr/bin/env python3
"""
前额叶 (Prefrontal) — 脉冲提炼调度器官
【AI伙伴】类脑系统 V2 · 执行器官之三

职责：数据层三件事——脉冲检测、优先级排序、聚合打包。
不负责语义抽象：工单生成后由【AI伙伴】审阅提炼规则，红线组须【用户】确认。

数据流：
  reflex_events.json → 检测(未提炼≥N) → P_i 排序 → 聚合 → 工单(organs/reflex_drafts.json)
  工单 → 【AI伙伴】审 → (红线组 → 【用户】确认) → 写入 reflex skill（脚本不写 skill）

P_i = 0.25*â + 0.25*e + 0.2*r + 0.3*(1-S/Smax)   [ZenBrain §4.3]
  â: 激活频率 = 同类别事件数 / 全库总数（归一化）
  e: 情绪强度 = 杏仁核校准后的 emotional_weight（组均值）
  r: 检索需求 = 按 scene_type 默认 (work=0.6, chat=0.4, 其他=0.5)
  S: 稳定性   = V1 取 S/Smax=1（该项退化为 0，FSRS 是 V2.4 的活）

CLI 用法：
  python prefrontal.py status [--file events.json]
  python prefrontal.py pulse [--threshold 5] [--dry-run]
  python prefrontal.py drafts [--file drafts.json] [--last N]
  python prefrontal.py reopen --batch P-0001
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hippocampus import Hippocampus

CN_TZ = timezone(timedelta(hours=8))
DEFAULT_DRAFTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reflex_drafts.json")
REDLINE_SCORE = -7          # ≤ -7 为红线级，须【用户】确认（对齐负向分级锚定）
SCENE_R = {"work": 0.6, "chat": 0.4}   # r 检索需求默认


def now_iso():
    return datetime.now(CN_TZ).isoformat(timespec="seconds")


class Prefrontal:
    def __init__(self, path=None, drafts_path=None):
        self.h = Hippocampus(path)
        self.drafts_path = drafts_path or DEFAULT_DRAFTS

    # ---- 基础 ----
    def _unrefined(self, include_suppressed=False):
        """未提炼事件 = id > last_refined 游标。"""
        cursor = self.h.data["meta"].get("last_refined") or 0
        return [e for e in self.h.data["events"]
                if e["id"] > cursor and (include_suppressed or e.get("status") != "suppressed")]

    def _next_batch_id(self):
        batches = self._load_drafts().get("batches", [])
        return f"P-{len(batches) + 1:04d}"

    def _load_drafts(self):
        if not os.path.exists(self.drafts_path):
            return {"batches": []}
        with open(self.drafts_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_drafts(self, data):
        tmp = self.drafts_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.drafts_path)

    # ---- ① 脉冲检测 ----
    def status(self):
        unref = self._unrefined()
        total = len(self.h.data["events"])
        return {
            "total_events": total,
            "unrefined": len(unref),
            "cursor": self.h.data["meta"].get("last_refined") or 0,
            "redline_unrefined": sum(1 for e in unref if e["score"] <= REDLINE_SCORE),
        }

    # ---- ②③ 排序 + 打包 ----
    def pulse(self, threshold=5, dry_run=False):
        unref = self._unrefined()
        if len(unref) < threshold:
            return {"triggered": False, "reason": f"未提炼事件 {len(unref)} < 阈值 {threshold}",
                    "status": self.status()}

        total = len(self.h.data["events"]) or 1

        # 按 category 分组
        groups = {}
        for e in unref:
            cat = e.get("category", "other")
            groups.setdefault(cat, []).append(e)

        # 每组计算 P_i 与统计
        out_groups = []
        for cat, evs in groups.items():
            a_hat = round(len(evs) / total, 3)                    # 激活频率（归一化）
            e_avg = round(sum(e.get("emotional_weight", 0.5) for e in evs) / len(evs), 3)
            scene = max(set(e.get("scene_type", "work") for e in evs),
                        key=lambda s: sum(1 for e in evs if e.get("scene_type") == s))
            r = SCENE_R.get(scene, 0.5)
            # S 项 V1 退化后权重和为 0.7；归一化回 1.0（除以 0.7），保持原比例不变。
            # 修复(2026-08-20)：此前 0.25/0.25/0.2 和为 0.7，数值不可解释（排序方向不受影响）。
            priority = round(0.25 / 0.7 * a_hat + 0.25 / 0.7 * e_avg + 0.2 / 0.7 * r, 3)
            tags = sorted({e.get("tag", "") for e in evs if e.get("tag")})
            has_redline = any(e["score"] <= REDLINE_SCORE for e in evs)
            out_groups.append({
                "category": cat,
                "tags": tags,
                "event_ids": sorted(e["id"] for e in evs),
                "priority": priority,
                "avg_emotional_weight": e_avg,
                "has_redline": has_redline,
                "pattern_hint": f"同类别事件 {len(evs)} 连发" + (f"，疑似行为范式: {'/'.join(tags[:3])}" if tags else ""),
            })

        # 按优先级降序
        out_groups.sort(key=lambda g: g["priority"], reverse=True)

        batch = {
            "batch_id": self._next_batch_id(),
            "triggered_at": now_iso(),
            "event_count": len(unref),
            "threshold": threshold,
            "groups": out_groups,
        }

        if not dry_run:
            drafts = self._load_drafts()
            drafts.setdefault("batches", []).append(batch)
            self._save_drafts(drafts)
            # 游标推进到本轮最大事件 id（幂等；reopen 可回退）
            max_id = max(e["id"] for e in unref)
            self.h.set_cursor(max_id)

        return {"triggered": True, "batch": batch,
                "cursor_advanced": None if dry_run else max(e["id"] for e in unref)}

    # ---- 查看 / 回退 ----
    def drafts(self, last=3):
        batches = self._load_drafts().get("batches", [])
        return batches[-last:]

    def reopen(self, batch_id):
        """回退游标到指定批次之前，使该批事件重新可提炼。"""
        batches = self._load_drafts().get("batches", [])
        idx = next((i for i, b in enumerate(batches) if b["batch_id"] == batch_id), None)
        if idx is None:
            raise KeyError(f"batch {batch_id} not found")
        batch = batches[idx]
        all_ids = [eid for g in batch["groups"] for eid in g["event_ids"]]
        min_id = min(all_ids)
        self.h.set_cursor(min_id - 1)
        return {"reopened": batch_id, "cursor_now": min_id - 1}


def main():
    p = argparse.ArgumentParser(description="前额叶 — 脉冲提炼调度")
    p.add_argument("--file", default=None, help="事件文件路径")
    p.add_argument("--drafts", default=None, help="工单文件路径（默认 organs/reflex_drafts.json）")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("status", help="脉冲状态")
    pu = sub.add_parser("pulse", help="检测+排序+打包")
    pu.add_argument("--threshold", type=int, default=5)
    pu.add_argument("--dry-run", action="store_true", help="只计算不落盘不推游标")

    d = sub.add_parser("drafts", help="查看最近工单")
    d.add_argument("--last", type=int, default=3)

    r = sub.add_parser("reopen", help="回退游标，重新提炼指定批次")
    r.add_argument("--batch", required=True)

    args = p.parse_args()
    pf = Prefrontal(args.file, args.drafts)

    if args.cmd == "status":
        print(json.dumps(pf.status(), ensure_ascii=False, indent=2))
    elif args.cmd == "pulse":
        print(json.dumps(pf.pulse(threshold=args.threshold, dry_run=args.dry_run),
                         ensure_ascii=False, indent=2))
    elif args.cmd == "drafts":
        print(json.dumps(pf.drafts(args.last), ensure_ascii=False, indent=2))
    elif args.cmd == "reopen":
        print(json.dumps(pf.reopen(args.batch), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
