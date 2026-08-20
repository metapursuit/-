#!/usr/bin/env python3
"""
海马体 (Hippocampus) — 情景事件存储器官
【AI伙伴】类脑系统 V2 · 执行器官之一

职责：reflex_events.json 的读写入口——事件录入、查询、抑制。
原则：只追加、不删除（旧事件抑制而非抹除）；原子写防损坏。

CLI 用法：
  python hippocampus.py append --score -8 --category transparency --tag "语气" --scene "..." --quote "..."
  注：负数参数必须用等号传（--ci=-8,-6），argparse 会把裸 -8 当成选项
  python hippocampus.py query [--tag T] [--category C] [--scene-type W] [--limit N]
  python hippocampus.py get --id 1
  python hippocampus.py suppress --id 2
  python hippocampus.py reactivate --id 2
  python hippocampus.py stats
  注：--file 是全局选项，必须放子命令前：python hippocampus.py --file F stats

库用法：
  from hippocampus import Hippocampus
  h = Hippocampus()                       # 默认 hermes-companion-configs/reflex_events.json
  h.append(score=-8, tag="语气", scene="...")
  rows = h.query(category="transparency")
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone

DEFAULT_PATH = os.path.join(
    os.environ.get("USERPROFILE", os.path.expanduser("~")),
    "hermes-companion-configs", "reflex_events.json")  # 2026-08-12: 真身唯一(仓库), AppData旧默认已废

CN_TZ = timezone(timedelta(hours=8))  # Asia/Shanghai，与现有数据一致


def now_iso():
    return datetime.now(CN_TZ).isoformat(timespec="microseconds")


class Hippocampus:
    def __init__(self, path=None):
        self.path = path or DEFAULT_PATH
        self.data = self._load()

    def _load(self):
        if not os.path.exists(self.path):
            return {"version": "1.0", "events": [],
                    "meta": {"total_positive": 0, "total_negative": 0,
                             "last_refined": None, "next_audit": None}}
        with open(self.path, "r", encoding="utf-8") as f:
            return json.load(f)

    def save(self):
        """原子写：先写临时文件再替换，写一半不会损坏数据。"""
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.path)

    # ---- 写入 ----
    def append(self, score, category=None, tag=None, scene=None, quote=None,
               emotional_weight=None, confidence_interval=None,
               scene_type="work", timestamp=None, status="active"):
        events = self.data["events"]
        eid = max((e["id"] for e in events), default=0) + 1
        event = {
            "id": eid,
            "timestamp": timestamp or now_iso(),
            "score": score,
            "category": category or "other",
            "tag": tag or "",
            "scene": scene or "",
            "quote": quote or "",
            "emotional_weight": emotional_weight if emotional_weight is not None else 0.5,
            "confidence_interval": confidence_interval or [score, score],
            "scene_type": scene_type,
            "status": status,
        }
        events.append(event)
        self._refresh_meta()
        self.save()
        return event

    def set_status(self, eid, status):
        """抑制/恢复事件——抑制非删除。"""
        for e in self.data["events"]:
            if e["id"] == eid:
                e["status"] = status
                self.save()
                return e
        raise KeyError(f"event {eid} not found")

    def _refresh_meta(self):
        m = self.data["meta"]
        m["total_positive"] = sum(1 for e in self.data["events"] if e["score"] > 0)
        m["total_negative"] = sum(1 for e in self.data["events"] if e["score"] < 0)

    # ---- 读取 ----
    def get(self, eid):
        for e in self.data["events"]:
            if e["id"] == eid:
                return e
        return None

    def query(self, tag=None, category=None, scene_type=None,
              min_score=None, max_score=None, include_suppressed=False, limit=None):
        out = []
        for e in self.data["events"]:
            if not include_suppressed and e.get("status") == "suppressed":
                continue
            if tag and tag not in (e.get("tag") or ""):
                continue
            if category and e.get("category") != category:
                continue
            if scene_type and e.get("scene_type") != scene_type:
                continue
            if min_score is not None and e["score"] < min_score:
                continue
            if max_score is not None and e["score"] > max_score:
                continue
            out.append(e)
        # 双键排序：同秒连续事件也保证最新在前
        out.sort(key=lambda e: (e["timestamp"], e["id"]), reverse=True)
        return out[:limit] if limit else out

    def stats(self):
        m = self.data["meta"]
        events = self.data["events"]
        by_cat = {}
        for e in events:
            by_cat[e.get("category", "other")] = by_cat.get(e.get("category", "other"), 0) + 1
        return {
            "path": self.path,
            "total": len(events),
            "active": sum(1 for e in events if e.get("status") != "suppressed"),
            "suppressed": sum(1 for e in events if e.get("status") == "suppressed"),
            "positive": m["total_positive"],
            "negative": m["total_negative"],
            "by_category": by_cat,
            "last_refined": m.get("last_refined"),
            "next_audit": m.get("next_audit"),
        }


def _parse_ci(s):
    if not s:
        return None
    lo, hi = s.split(",")
    return [int(lo.strip()), int(hi.strip())]


def main():
    p = argparse.ArgumentParser(description="海马体 — 情景事件存储")
    p.add_argument("--file", default=None, help="数据文件路径（默认 hermes-companion-configs/reflex_events.json）")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("append", help="录入事件")
    a.add_argument("--score", type=int, required=True)
    a.add_argument("--category")
    a.add_argument("--tag")
    a.add_argument("--scene")
    a.add_argument("--quote")
    a.add_argument("--emotional-weight", type=float)
    a.add_argument("--ci", help="置信区间 lo,hi（负值用等号：--ci=-8,-6）")
    a.add_argument("--scene-type", default="work")
    a.add_argument("--timestamp")
    a.add_argument("--status", default="active")

    q = sub.add_parser("query", help="查询事件")
    q.add_argument("--tag")
    q.add_argument("--category")
    q.add_argument("--scene-type")
    q.add_argument("--min-score", type=int)
    q.add_argument("--max-score", type=int)
    q.add_argument("--include-suppressed", action="store_true")
    q.add_argument("--limit", type=int)

    g = sub.add_parser("get", help="按 id 查询")
    g.add_argument("--id", type=int, required=True)

    s = sub.add_parser("suppress", help="抑制事件（不删除）")
    s.add_argument("--id", type=int, required=True)

    r = sub.add_parser("reactivate", help="恢复被抑制的事件")
    r.add_argument("--id", type=int, required=True)

    st = sub.add_parser("stats", help="统计")

    args = p.parse_args()
    h = Hippocampus(args.file)

    if args.cmd == "append":
        e = h.append(score=args.score, category=args.category, tag=args.tag,
                     scene=args.scene, quote=args.quote,
                     emotional_weight=args.emotional_weight,
                     confidence_interval=_parse_ci(args.ci),
                     scene_type=args.scene_type, timestamp=args.timestamp,
                     status=args.status)
        print(json.dumps(e, ensure_ascii=False, indent=2))
    elif args.cmd == "query":
        rows = h.query(tag=args.tag, category=args.category, scene_type=args.scene_type,
                       min_score=args.min_score, max_score=args.max_score,
                       include_suppressed=args.include_suppressed, limit=args.limit)
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    elif args.cmd == "get":
        e = h.get(args.id)
        print(json.dumps(e, ensure_ascii=False, indent=2) if e else "NOT FOUND")
    elif args.cmd == "suppress":
        e = h.set_status(args.id, "suppressed")
        print(json.dumps(e, ensure_ascii=False, indent=2))
    elif args.cmd == "reactivate":
        e = h.set_status(args.id, "active")
        print(json.dumps(e, ensure_ascii=False, indent=2))
    elif args.cmd == "stats":
        print(json.dumps(h.stats(), ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
