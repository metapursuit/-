#!/usr/bin/env python3
"""
类脑系统完整性自检
覆盖：JSON格式 | 字段完整性 | CI约束 | 情感权重范围 | 时间戳 | 规则-事件交叉 | meta计数 | 器官导入 | git整洁

用法：
  python self_check.py                          # 自动探测（向上找 reflex_events.json / organs/）
  python self_check.py --events <path>          # 显式指定事件文件（分发/副本场景）
  python self_check.py --organs <dir>           # 显式指定器官目录
  python self_check.py --skill <path>           # 显式指定 reflex skill（SKILL.md 规则交叉检查）
"""

import argparse
import importlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone, timedelta

CN_TZ = timezone(timedelta(hours=8))


def detect_events(start):
    """从 start 向上找第一个含 reflex_events.json 的目录。"""
    d = os.path.abspath(start)
    for _ in range(10):
        cand = os.path.join(d, "reflex_events.json")
        if os.path.exists(cand):
            return cand
        up = os.path.dirname(d)
        if up == d:
            break
        d = up
    return None


def detect_organs(start):
    """从 start 向上找第一个含 organs/ 目录的位置。"""
    d = os.path.abspath(start)
    for _ in range(10):
        cand = os.path.join(d, "organs")
        if os.path.isdir(cand):
            return cand
        up = os.path.dirname(d)
        if up == d:
            break
        d = up
    return None


def main():
    ap = argparse.ArgumentParser(description="类脑系统完整性自检")
    ap.add_argument("--events", default=None, help="reflex_events.json 路径（默认自动探测）")
    ap.add_argument("--organs", default=None, help="organs 目录（默认自动探测）")
    ap.add_argument("--skill", default=None, help="reflex skill 的 SKILL.md 路径（默认按 LOCALAPPDATA 探测）")
    args = ap.parse_args()

    EVENTS = args.events or detect_events(os.path.dirname(os.path.abspath(__file__)))
    ORGANS = args.organs or detect_organs(os.path.dirname(os.path.abspath(__file__)))
    SKILL = args.skill or os.path.join(
        os.environ.get("LOCALAPPDATA", ""), "hermes", "skills",
        "reflex-behavior-calibration", "SKILL.md")

    if EVENTS is None or ORGANS is None:
        print("❌ 未自动定位 reflex_events.json / organs/，请用 --events / --organs 显式指定。")
        sys.exit(1)

    RESULTS = []

    def ok(name, cond, detail=""):
        RESULTS.append((name, cond, detail))
        return cond

    # ── 1. reflex_events.json ──
    print("[1] reflex_events.json")
    with open(EVENTS, encoding="utf-8") as f:
        data = json.load(f)
    events = data["events"]
    meta = data["meta"]
    ok("JSON有效", True)
    ok("version存在", "version" in data)
    ok("events是list", isinstance(events, list))

    for ev in events:
        for field in ["id", "timestamp", "score", "category", "tag", "scene", "quote",
                      "emotional_weight", "confidence_interval", "scene_type", "status"]:
            ok(f"event#{ev['id']}.{field}存在", field in ev)

    ids = [ev["id"] for ev in events]
    ok("无重复ID", len(ids) == len(set(ids)), f"重复:{[i for i in ids if ids.count(i) > 1]}")

    ci_bad = [ev["id"] for ev in events if isinstance(ev["confidence_interval"], str)]
    ok("CI非字符串", len(ci_bad) == 0, f"字符串CI: {ci_bad}")

    for ev in events:
        ci = ev.get("confidence_interval", [0, 0])
        if isinstance(ci, list) and len(ci) == 2:
            ok(f"event#{ev['id']} CI lower≤upper", ci[0] <= ci[1], f"CI={ci}")

    ew_bad = [ev["id"] for ev in events
              if not (0 <= ev.get("emotional_weight", 0.5) <= 1)]
    ok("emotional_weight在[0,1]", len(ew_bad) == 0, f"越界:{ew_bad}")

    now = datetime.now(CN_TZ)
    future = [ev["id"] for ev in events
              if datetime.fromisoformat(ev["timestamp"]) > now]
    ok("无未来时间戳", len(future) == 0, f"未来:{future}")

    actual_pos = sum(1 for e in events if e["score"] > 0)
    actual_neg = sum(1 for e in events if e["score"] < 0)
    ok(f"meta.total_positive={meta['total_positive']} = 实际{actual_pos}", meta["total_positive"] == actual_pos)
    ok(f"meta.total_negative={meta['total_negative']} = 实际{actual_neg}", meta["total_negative"] == actual_neg)

    print(f"  事件:{len(events)} 正向:{actual_pos} 负向:{actual_neg}")

    # ── 2. SKILL.md 规则交叉 ──
    print("[2] SKILL.md 规则交叉引用")
    if not os.path.exists(SKILL):
        # 分发场景无本机 skill 属正常，跳过不算失败
        print(f"  ⚠️ 未找到 SKILL.md（{SKILL}），跳过规则交叉检查")
        ok("SKILL.md存在(跳过)", True, "未配置 --skill，跳过")
    else:
        with open(SKILL, encoding="utf-8") as f:
            skill = f.read()
        rs, re_mark = "<!-- REFLEX_RULES_START -->", "<!-- REFLEX_RULES_END -->"
        ok("含REFLEX_RULES_START", rs in skill)
        ok("含REFLEX_RULES_END", re_mark in skill)

        if rs in skill and re_mark in skill:
            block = skill.split(rs, 1)[1].split(re_mark, 1)[0]
            source_re = re.compile(r"事件#(\d+)")
            all_rule_sources = set(int(x) for x in source_re.findall(block))
            orphans = all_rule_sources - set(ids)
            ok("规则来源事件全存在", len(orphans) == 0, f"孤儿:{sorted(orphans)}")

            active_neg = {ev["id"] for ev in events if ev["score"] < 0 and ev.get("status") == "active"}
            uncovered = active_neg - all_rule_sources
            ok("活跃负向事件全被规则覆盖", len(uncovered) == 0, f"未覆盖:{sorted(uncovered)}")

    # ── 3. 器官导入 ──
    print("[3] 器官导入")
    sys.path.insert(0, ORGANS)
    for name in ["hippocampus", "amygdala", "prefrontal", "bayesian_evaluator",
                 "reflex_deviator", "sleep_consolidator"]:
        try:
            importlib.import_module(name)
            ok(f"{name}.py导入", True)
        except Exception as e:
            ok(f"{name}.py导入", False, str(e)[:100])

    # ── 4. git整洁（仅当事件文件在 git 仓库内时检查） ──
    print("[4] git整洁")
    repo_candidate = os.path.dirname(EVENTS)
    git_dir = os.path.join(repo_candidate, ".git")
    if not os.path.exists(git_dir):
        # 分发场景非 git 仓库属正常
        print("  ⚠️ 非 git 仓库，跳过 git 整洁检查")
        ok("git仓库(跳过)", True, "非 git 仓库")
    else:
        try:
            r = subprocess.run(["git", "status", "--porcelain"], capture_output=True,
                               text=True, cwd=repo_candidate)
            dirty = r.stdout.strip()
            ok("git工作区干净", dirty == "", dirty[:200] if dirty else "")
        except Exception as e:
            ok("git可用", False, str(e)[:100])

    # ── 总览 ──
    print()
    passed = sum(1 for _, c, _ in RESULTS if c)
    failed = sum(1 for _, c, _ in RESULTS if not c)
    for name, cond, detail in RESULTS:
        if not cond:
            print(f"  ❌ {name}  → {detail}")
    print(f"\n  通过:{passed} 失败:{failed}  → {'✅全绿' if failed == 0 else '⚠️有问题'}")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
