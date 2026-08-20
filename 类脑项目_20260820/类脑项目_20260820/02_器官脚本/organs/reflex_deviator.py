#!/usr/bin/env python3
"""
reflex_deviator.py — CoBRA-style deviation analyzer for companion's reflex system.

Reads reflex_events.json, clusters negative events into deviation directions,
and generates calibrated behavior rules.

Step ① of the CoBRA-ZenBrain integration: measurement → direction extraction → rule generation.
"""

import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone, timedelta

# Paths —— 事实源唯一化（2026-08-12）：事件真身只在 hermes-companion-configs 仓库，
# AppData 旧路径已废弃（曾误读废弃副本，见审查 D1）
EVENTS_PATH = os.path.join(os.environ.get("USERPROFILE", os.path.expanduser("~")),
                           "hermes-companion-configs", "reflex_events.json")

# Clustering config
CLUSTER_WINDOW_DAYS = 7  # events within this window form a "current" cluster
MIN_CLUSTER_SCORE = 3     # minimum absolute score sum to warrant a rule


def load_events(path: str) -> dict:
    if not os.path.exists(path):
        return {"version": "1.0", "events": [], "meta": {}}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def cluster_events(events: list) -> dict:
    """Cluster negative events by category, then by tag similarity within category."""
    now = datetime.now(timezone.utc)
    clusters = defaultdict(list)

    for ev in events:
        # Only process active negative events within the window
        if ev.get("status") != "active":
            continue
        if ev.get("score", 0) >= 0:
            continue

        ts = datetime.fromisoformat(ev["timestamp"])
        if (now - ts).days > CLUSTER_WINDOW_DAYS:
            continue

        # Primary cluster key: category
        clusters[ev.get("category", "uncategorized")].append(ev)

    return dict(clusters)


def analyze_cluster(category: str, events: list) -> dict:
    """Analyze a single cluster and generate a calibrated rule."""
    if not events:
        return None

    scores = [ev["score"] for ev in events]
    total_score = sum(scores)
    avg_score = total_score / len(events)

    # Skip if cluster too weak
    if abs(total_score) < MIN_CLUSTER_SCORE:
        return None

    # Extract shared tags — use category as fallback if no common prefix
    tags = [ev.get("tag", "") for ev in events]
    if len(tags) > 1:
        shared_prefix = _longest_common_prefix(tags)
        shared_tag = shared_prefix if shared_prefix else _merge_tags(tags)
    else:
        shared_tag = tags[0] if tags else category

    # Extract key quotes
    quotes = [ev.get("quote", "") for ev in events if ev.get("quote")]

    # Determine severity
    min_score = min(scores)
    if min_score <= -7:
        severity = "红线"
        severity_label = f"🚩 {severity}"
    elif min_score <= -4:
        severity = "中负向"
        severity_label = f"⚠️ {severity}"
    else:
        severity = "低负向"
        severity_label = f"📝 {severity}（累积追踪）"

    # Generate scene summary
    scenes = [ev.get("scene", "") for ev in events]

    return {
        "category": category,
        "tag": shared_tag,
        "severity": severity,
        "severity_label": severity_label,
        "event_count": len(events),
        "total_score": total_score,
        "avg_score": round(avg_score, 1),
        "min_score": min_score,
        "quotes": quotes,
        "scenes": scenes,
        "events": events,
    }


def _longest_common_prefix(strings: list) -> str:
    """Find the longest common prefix among a list of strings."""
    if not strings:
        return ""
    if len(strings) == 1:
        return strings[0]

    prefix = strings[0]
    for s in strings[1:]:
        while not s.startswith(prefix) and prefix:
            prefix = prefix[:-1]
    # D8 修复（2026-08-12）：去掉尾部连接符残留——"过度执行-" → "过度执行"
    return prefix.rstrip("- _·/｜|\t ")


def _merge_tags(tags: list) -> str:
    """Merge multiple dissimilar tags into a short combined label."""
    if len(tags) <= 2:
        return " · ".join(tags)
    return tags[0] + " 等"


def generate_rules_markdown(analyses: list) -> str:
    """Generate REFLEX_RULES markdown from cluster analyses."""
    if not analyses:
        return "<!-- 无活跃偏差方向，暂无需新增规则。 -->"

    blocks = []
    for a in analyses:
        score_range = f"{a['min_score']}"
        if a["event_count"] > 1:
            score_range = f"{a['min_score']} ~ {max(ev['score'] for ev in a['events'])}"

        block = f"""### {a['tag']}（{score_range}分，{a['severity_label']}）

**聚类**：{a['event_count']}条事件 | 总分{a['total_score']} | 均分{a['avg_score']}

**引用**：
"""
        for q in a["quotes"]:
            block += f'- "{q}"\n'

        block += f"\n**场景**：{'；'.join(a['scenes'])}\n"
        block += f"\n**操作**：需人工根据聚类提炼具体行为规则，参照已有规则格式。\n"

        blocks.append(block)

    return "\n\n".join(blocks)


def compute_deviation_directions(analyses: list) -> list:
    """Extract the top deviation directions, sorted by severity."""
    sorted_analyses = sorted(analyses, key=lambda a: a["total_score"])
    directions = []
    for a in sorted_analyses:
        directions.append({
            "direction": a["tag"],
            "category": a["category"],
            "severity": a["severity"],
            "total_score": a["total_score"],
            "event_count": a["event_count"],
        })
    return directions


def main():
    import argparse
    p = argparse.ArgumentParser(description="CoBRA-style 偏差方向分析")
    p.add_argument("--json", action="store_true", help="输出结构化 JSON（程序消费），默认人读文本报告")
    args = p.parse_args()

    data = load_events(EVENTS_PATH)
    events = data.get("events", [])

    if not events:
        print("✅ reflex_events.json 为空，无偏差方向。")
        return

    clusters = cluster_events(events)
    analyses = []
    for category, cat_events in clusters.items():
        a = analyze_cluster(category, cat_events)
        if a:
            analyses.append(a)

    if not analyses:
        print("✅ 无活跃偏差方向达到规则提炼阈值。")
        return

    directions = compute_deviation_directions(analyses)

    # D10 双通道：--json 输出结构化结果供程序消费，默认人读文本报告
    if args.json:
        print(json.dumps(directions, ensure_ascii=False, indent=2))
        return directions

    # Print report
    print("=" * 60)
    print("  CoBRA-style 偏差方向分析")
    print(f"  数据源：{EVENTS_PATH}")
    print(f"  分析时间：{datetime.now().isoformat()}")
    print("=" * 60)

    print(f"\n📊 偏差方向 ({len(directions)}个):\n")
    for i, d in enumerate(directions, 1):
        bar = "█" * min(abs(d["total_score"]), 10)
        print(f"  {i}. [{d['severity']}] {d['direction']} ({d['category']})")
        print(f"     {d['event_count']}条事件 | 总分{d['total_score']} | {bar}")

    print(f"\n{'=' * 60}")
    print("  生成的规则草稿（可直接插入 REFLEX_RULES_START/END 之间）:")
    print("=" * 60)
    print()
    print(generate_rules_markdown(analyses))

    return directions


if __name__ == "__main__":
    main()
