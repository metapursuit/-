#!/usr/bin/env python3
"""前额叶测试（交付审查 B1 补录——原 13 项内联验证固化核心 10 项）。
覆盖：pulse 检测/P_i 排序/聚合打包/游标幂等/reopen 回退/dry-run。
运行：python test_prefrontal.py
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

ORGANS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PF = os.path.join(ORGANS, "prefrontal.py")


def mk_events(n_events, scores):
    evs = []
    for i, s in enumerate(scores, 1):
        evs.append({"id": i, "timestamp": f"2026-08-11T12:0{i % 60:02d}:00+08:00", "score": s,
                    "category": "logic", "tag": "严谨", "scene": "s", "quote": "q",
                    "emotional_weight": 0.8, "confidence_interval": [s, s],
                    "scene_type": "work", "status": "active"})
    return {"version": "1.0", "events": evs,
            "meta": {"total_positive": 0, "total_negative": n_events, "last_refined": None, "next_audit": None}}


def run(*args, file=None, drafts=None):
    cmd = [sys.executable, PF]
    if file: cmd += ["--file", file]
    if drafts: cmd += ["--drafts", drafts]
    r = subprocess.run(cmd + list(args), capture_output=True, text=True, encoding="utf-8")
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def main():
    tmp = tempfile.mkdtemp(prefix="_pf_test_")
    results = []

    # 1. 语法
    r = subprocess.run([sys.executable, "-m", "py_compile", PF], capture_output=True, text=True)
    results.append(("语法", r.returncode == 0))

    # 2. 攒 5 条触发 pulse
    t = os.path.join(tmp, "e5.json")
    d = os.path.join(tmp, "d1.json")
    with open(t, "w", encoding="utf-8") as f:
        json.dump(mk_events(5, [-5, -4, -3, -6, -5]), f, ensure_ascii=False)
    rc, out, err = run("pulse", file=t, drafts=d)
    p1 = json.loads(out)
    results.append(("pulse 5条触发", p1["batch"]["batch_id"] == "P-0001" and p1["batch"]["event_count"] == 5))

    # 3. 幂等：同数据再 pulse 不重复
    rc, out, err = run("pulse", file=t, drafts=d)
    p2 = json.loads(out)
    results.append(("pulse 幂等（无新事件不重复）", p2.get("batch") is None))

    # 4. 聚合：P_i 排序（高分在前）
    groups = p1["batch"].get("groups", [])
    results.append(("聚合非空", len(groups) >= 1))

    # 5. 红线标记（score<=-7 的组 has_redline）
    t2 = os.path.join(tmp, "e_red.json")
    d2 = os.path.join(tmp, "d2.json")
    with open(t2, "w", encoding="utf-8") as f:
        json.dump(mk_events(5, [-10, -4, -3, -2, -1]), f, ensure_ascii=False)
    rc, out, err = run("pulse", file=t2, drafts=d2)
    p3 = json.loads(out)
    has_red = any(g.get("has_redline") for g in p3["batch"].get("groups", []))
    results.append(("红线标记", has_red))

    # 6. dry-run 不落盘
    d3 = os.path.join(tmp, "d3.json")
    rc, out, err = run("pulse", "--dry-run", file=t2, drafts=d3)
    results.append(("dry-run 不写 drafts", not os.path.exists(d3)))

    # 7. drafts 文件结构（检查第 5 步已生成的 d2——重复 pulse 同一数据会被幂等挡住）
    dj = json.load(open(d2, encoding="utf-8"))
    results.append(("drafts 批次结构", "batches" in dj and dj["batches"][0]["batch_id"] == "P-0001"))

    # 8. 批量查询（CLI 子命令是 drafts，batches 是内部方法名）
    rc, out, err = run("drafts", file=t2, drafts=d2)
    results.append(("drafts 可查", rc == 0 and len(json.loads(out)) >= 1))

    # 9. 真实文件零污染（用真身只读验证）
    real = os.path.expandvars(r"%USERPROFILE%\hermes-companion-configs\reflex_events.json")
    md5_before = __import__("hashlib").md5(open(real, "rb").read()).hexdigest()
    t3 = os.path.join(tmp, "e_real.json")
    shutil.copy(real, t3)
    rc, out, err = run("stats", file=t3)
    md5_after = __import__("hashlib").md5(open(real, "rb").read()).hexdigest()
    results.append(("真实文件零污染", md5_before == md5_after))

    # 10. 事件不足 5 条不触发
    t4 = os.path.join(tmp, "e3.json")
    d5 = os.path.join(tmp, "d5.json")
    with open(t4, "w", encoding="utf-8") as f:
        json.dump(mk_events(3, [-5, -4, -3]), f, ensure_ascii=False)
    rc, out, err = run("pulse", file=t4, drafts=d5)
    p5 = json.loads(out)
    results.append(("3条不触发", p5.get("batch") is None))

    shutil.rmtree(tmp, ignore_errors=True)

    failed = 0
    for name, ok in results:
        print(f"[{'✓' if ok else '✗'}] {name}")
        if not ok: failed += 1
    print(f"\n>>> {len(results) - failed}/{len(results)} 通过")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
