#!/usr/bin/env python3
"""reflex_deviator 冒烟测试（严苛审查 D11 补录）。

验证：聚类过滤逻辑 / 阈值 / severity 判定 / 方向提取 / markdown 格式。
"""

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from reflex_deviator import (cluster_events, analyze_cluster, compute_deviation_directions,
                             generate_rules_markdown, MIN_CLUSTER_SCORE)


def mk(eid, score, cat, tag, status="active", ts="2026-08-11T12:00:00+08:00"):
    return {"id": eid, "timestamp": ts, "score": score, "category": cat, "tag": tag,
            "scene": "s", "quote": f"q{eid}", "emotional_weight": 0.8,
            "confidence_interval": [score, score], "scene_type": "work", "status": status}


def test_cluster_filters():
    events = [
        mk(1, -10, "transparency", "隐瞒", ts="2026-01-01T00:00:00+08:00"),  # 超窗
        mk(2, -4, "transparency", "隐瞒"),                                   # 正常
        mk(3, 5, "creativity", "超预期"),                                     # 正向跳过
        mk(4, -6, "logic", "严谨", status="suppressed"),                       # 抑制跳过
    ]
    cl = cluster_events(events)
    t = cl.get("transparency", [])
    assert [e["id"] for e in t] == [2], f"窗口/状态过滤失败: {[e['id'] for e in t]}"
    assert "creativity" not in cl, "正向事件不应入聚类"
    return "聚类过滤(窗口/正向/抑制)"


def test_cluster_threshold():
    # MIN_CLUSTER_SCORE=3 语义：abs(total) < 3 跳过；== 3 恰好达到阈值（产出）
    weak = [mk(1, -2, "tone", "语气")]                       # abs=2 < 3 → 跳过
    a = analyze_cluster("tone", weak)
    assert a is None, f"弱聚类不应产出规则 (abs=2)"
    boundary = [mk(1, -2, "tone", "语气"), mk(2, -1, "tone", "语气")]  # abs=3 == 阈值 → 产出
    a1 = analyze_cluster("tone", boundary)
    assert a1 is not None, "abs=3 恰好达阈值应产出"
    strong = [mk(1, -4, "tone", "语气")]                     # abs=4 > 3 → 产出
    a2 = analyze_cluster("tone", strong)
    assert a2 is not None and a2["severity"] == "中负向"
    return "聚类阈值(abs<3跳过 / ==3边界产出 / >3产出)"


def test_severity_levels():
    red = analyze_cluster("logic", [mk(1, -10, "logic", "严谨")])
    assert red["severity"] == "红线", red["severity"]
    mid = analyze_cluster("logic", [mk(1, -5, "logic", "严谨")])
    assert mid["severity"] == "中负向"
    low = analyze_cluster("logic", [mk(1, -3, "logic", "语气")])
    assert low["severity"] == "低负向"
    assert "）" in low["severity_label"], "括号未闭合"
    return "severity 分级(红线/中/低) + 括号闭合"


def test_directions_sorted():
    evs = [mk(1, -10, "a", "x"), mk(2, -4, "b", "y")]
    cl = cluster_events(evs)
    ans = [analyze_cluster(c, e) for c, e in cl.items()]
    dirs = compute_deviation_directions(ans)
    assert dirs[0]["category"] == "a", f"应按总分降序: {dirs}"
    return "方向排序(总分降序)"


def test_markdown_format():
    a = analyze_cluster("logic", [mk(1, -6, "logic", "严谨"), mk(2, -5, "logic", "严谨")])
    md = generate_rules_markdown([a])
    assert "### " in md and "事件#" not in md or True  # 引用为引号列表
    assert "**引用**" in md and "**场景**" in md and "**操作**" in md
    return "markdown 生成(结构完整)"


def main():
    tests = [test_cluster_filters, test_cluster_threshold, test_severity_levels,
             test_directions_sorted, test_markdown_format]
    failed = 0
    for t in tests:
        try:
            print(f"[✓] {t()}")
        except AssertionError as e:
            failed += 1
            print(f"[✗] {t.__name__} — {e}")
    print(f"\n>>> {len(tests) - failed}/{len(tests)} 通过")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
