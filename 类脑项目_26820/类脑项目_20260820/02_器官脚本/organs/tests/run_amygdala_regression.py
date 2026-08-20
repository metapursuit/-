#!/usr/bin/env python3
"""
杏仁核回归验证（gold set 驱动）
用法: python run_amygdala_regression.py [--events reflex_events.json] [--gold amygdala_gold.json]
输出: 每条 case 期望 vs 实际，全量 PASS/FAIL 对照表。
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from amygdala import Amygdala
from hippocampus import DEFAULT_PATH

ORGANS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_GOLD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "amygdala_gold.json")


def main():
    p = argparse.ArgumentParser(description="杏仁核 gold set 回归")
    p.add_argument("--events", default=DEFAULT_PATH)
    p.add_argument("--gold", default=DEFAULT_GOLD)
    args = p.parse_args()

    am = Amygdala(args.events)
    gold = json.load(open(args.gold, encoding="utf-8"))
    events = {e["id"]: e for e in am.h.data["events"]}

    results = []
    for case in gold["cases"]:
        e = events.get(case["event_id"])
        if e is None:
            results.append((case["event_id"], "SKIP", f"事件不存在"))
            continue
        text = f"{e.get('quote', '')}\n{e.get('scene', '')}"
        actual = am.analyze_text(text)
        ok = (actual["valence"] == case["expected_valence"]
              and actual["arousal"] == case["expected_arousal"])
        results.append((case["event_id"], "PASS" if ok else "FAIL",
                        f"期望 v={case['expected_valence']}/a={case['expected_arousal']} "
                        f"实际 v={actual['valence']}/a={actual['arousal']} | {case['note']}"))

    for eid, status, note in results:
        print(f"[{'✓' if status == 'PASS' else '✗' if status == 'FAIL' else '·'}] 事件#{eid} {status} — {note}")
    failed = sum(1 for _, s, _ in results if s == "FAIL")
    print(f"\n>>> {len(results) - failed}/{len(results)} 通过" + ("，有失败（盲区=迭代输入）" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
