#!/usr/bin/env python3
"""FSRS 调度器测试（交付审查 B1 补录——原 12 项为内联验证，现固化为可复现文件）。
覆盖：数学公式手算对照 / 边界 / Hebbian 聚合 / 错误路径 / 零污染。
运行：python test_fsrs_scheduler.py
"""

import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile

ORGANS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FSRS = os.path.join(ORGANS, "fsrs_scheduler.py")
REAL_IDX = os.path.join(ORGANS, "rule_index.json")
REAL_CONS = os.path.join(ORGANS, "consolidation_state.json")


def mk_tmp():
    d = tempfile.mkdtemp(prefix="_fsrs_test_")
    return d


def run(*args, state=None, params=None, index=None):
    cmd = [sys.executable, FSRS]
    if state: cmd += ["--state", state]
    if params: cmd += ["--params", params]
    if index: cmd += ["--index", index]
    r = subprocess.run(cmd + list(args), capture_output=True, text=True, encoding="utf-8")
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def main():
    tmp = mk_tmp()
    t_state = os.path.join(tmp, "fsrs_state.json")
    t_params = os.path.join(tmp, "params.json")
    hp = json.load(open(os.path.join(ORGANS, "hyperparams.json"), encoding="utf-8"))
    with open(t_params, "w", encoding="utf-8") as f:
        json.dump(hp, f, ensure_ascii=False)

    results = []

    # 1. 语法
    r = subprocess.run([sys.executable, "-m", "py_compile", FSRS], capture_output=True, text=True)
    results.append(("语法", r.returncode == 0))

    # 2. schedule 初始化：4 规则 S=7 D=5 next=2.5d
    rc, out, err = run("schedule", state=t_state, params=t_params, index=REAL_IDX)
    st = json.loads(out)
    exp_next = round(-7 * math.log(0.7), 2)
    ok = len(st["rules"]) == 4 and all(r2["S"] == 7.0 for r2 in st["rules"].values()) \
         and all(abs(r2["next_audit_days"] - exp_next) < 0.01 for r2 in st["rules"].values())
    results.append((f"schedule: 4规则 S=7 next={exp_next}d", ok))

    # 3. R=1 → S'=S
    rc, out, err = run("audit", "--rule", "R-0001", "--observed-r", "1.0", state=t_state, params=t_params, index=REAL_IDX)
    a1 = json.loads(out)
    results.append(("audit R=1: S不变", a1["S_after"] == a1["S_before"]))

    # 4. R=0.8 → 手算对照
    rc, out, err = run("audit", "--rule", "R-0002", "--observed-r", "0.8", state=t_state, params=t_params, index=REAL_IDX)
    a2 = json.loads(out)
    exp_s = 7 * (1 + 0.5 * (11 - 5) * (7 ** -0.5) * (math.exp(0.5 * 0.2) - 1))
    results.append((f"audit R=0.8: S→{a2['S_after']} vs 手算{round(exp_s,3)}", abs(a2["S_after"] - exp_s) < 0.01))

    # 5. R=0.5 → at_risk S不变
    rc, out, err = run("audit", "--rule", "R-0003", "--observed-r", "0.5", state=t_state, params=t_params, index=REAL_IDX)
    a3 = json.loads(out)
    results.append(("audit R=0.5: at_risk S不变", a3["status"] == "at_risk" and a3["S_after"] == a3["S_before"]))

    # 6. Hebbian 聚合
    rc, out, err = run("hebbian", state=t_state, params=t_params, index=REAL_IDX)
    h = json.loads(out)["hebbian"]
    exp_h = {"R-0001": 0.95, "R-0002": 0.875, "R-0003": 0.6, "R-0004": 0.775}
    results.append(("hebbian 聚合", all(abs(h[k]["weight"] - v) < 0.01 for k, v in exp_h.items())))

    # 7. 未知规则
    rc, out, err = run("audit", "--rule", "R-9999", "--observed-r", "0.8", state=t_state, params=t_params, index=REAL_IDX)
    results.append(("未知规则 error", "error" in json.loads(out)))

    # 8. 空索引 + 全新 state
    e_idx = os.path.join(tmp, "empty.json")
    with open(e_idx, "w", encoding="utf-8") as f:
        json.dump({"rules": []}, f)
    f_state = os.path.join(tmp, "fresh.json")
    r = subprocess.run([sys.executable, FSRS, "--state", f_state, "--index", e_idx, "schedule"],
                       capture_output=True, text=True, encoding="utf-8")
    se = json.loads(r.stdout)
    results.append(("空索引+全新state", r.returncode == 0 and len(se["rules"]) == 0))

    # 9. 零污染
    m1 = hashlib.md5(open(REAL_IDX, "rb").read()).hexdigest()
    m2 = hashlib.md5(open(REAL_CONS, "rb").read()).hexdigest()
    run("schedule", state=t_state, params=t_params, index=REAL_IDX)
    m1b = hashlib.md5(open(REAL_IDX, "rb").read()).hexdigest()
    m2b = hashlib.md5(open(REAL_CONS, "rb").read()).hexdigest()
    results.append(("真实文件零污染", m1 == m1b and m2 == m2b))

    # 10. 超参覆盖
    p2 = os.path.join(tmp, "params2.json")
    hp2 = json.load(open(t_params, encoding="utf-8"))
    hp2["fsrs"]["a"] = 1.0
    with open(p2, "w", encoding="utf-8") as f:
        json.dump(hp2, f, ensure_ascii=False)
    rc, out, err = run("audit", "--rule", "R-0004", "--observed-r", "0.8", state=t_state, params=p2, index=REAL_IDX)
    a4 = json.loads(out)
    exp_s2 = 7 * (1 + 1.0 * (11 - 5) * (7 ** -0.5) * (math.exp(0.5 * 0.2) - 1))
    results.append(("超参a=1.0 生效", abs(a4["S_after"] - exp_s2) < 0.01))

    # 11. 序列 audit S 递增
    rc, out, err = run("audit", "--rule", "R-0001", "--observed-r", "0.9", state=t_state, params=t_params, index=REAL_IDX)
    s1 = json.loads(out)["S_after"]
    rc, out, err = run("audit", "--rule", "R-0001", "--observed-r", "0.9", state=t_state, params=t_params, index=REAL_IDX)
    s2 = json.loads(out)["S_after"]
    results.append(("序列 audit 递增", s2 > s1))

    # 12. 报告字段完整性（next_audit/source_events/hebbian）
    rc, out, err = run("status", state=t_state, params=t_params, index=REAL_IDX)
    st2 = json.loads(out)
    r0 = list(st2["rules"].values())[0]
    results.append(("status 字段完整", all(k in r0 for k in ["S", "D", "R", "next_audit", "next_audit_days", "hebbian", "source_events"])))

    shutil.rmtree(tmp, ignore_errors=True)

    failed = 0
    for name, ok in results:
        print(f"[{'✓' if ok else '✗'}] {name}")
        if not ok: failed += 1
    print(f"\n>>> {len(results) - failed}/{len(results)} 通过")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
