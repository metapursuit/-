#!/usr/bin/env python3
"""Bayesian 评估器回归（交付审查 B1 补录——原 16 项为内联验证，现固化）。
对照 bayesian_gold.json（期望值 scipy 实测）+ 边界/先验/零污染。
运行：python run_bayesian_regression.py
"""

import hashlib
import json
import os
import subprocess
import sys
import tempfile

ORGANS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BE = os.path.join(ORGANS, "bayesian_evaluator.py")
TESTS = os.path.dirname(os.path.abspath(__file__))
SYN = os.path.join(TESTS, "data", "synthetic_events.json")
GOLD = os.path.join(TESTS, "bayesian_gold.json")
REAL = os.path.expandvars(r"%USERPROFILE%\hermes-companion-configs\reflex_events.json")


def run(*args, state=None, params=None, index=None, file=None):
    cmd = [sys.executable, BE]
    if file: cmd += ["--file", file]
    if state: cmd += ["--state", state]
    if params: cmd += ["--params", params]
    if index: cmd += ["--index", index]
    r = subprocess.run(cmd + list(args), capture_output=True, text=True, encoding="utf-8")
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def main():
    tmp = tempfile.mkdtemp(prefix="_bayes_test_")
    t_state = os.path.join(tmp, "state.json")
    t_params2 = os.path.join(tmp, "params2.json")
    hp = json.load(open(os.path.join(ORGANS, "hyperparams.json"), encoding="utf-8"))
    hp["bayesian"]["prior_alpha"], hp["bayesian"]["prior_beta"] = 2, 2
    with open(t_params2, "w", encoding="utf-8") as f:
        json.dump(hp, f, ensure_ascii=False)

    results = []

    # 1. 语法
    r = subprocess.run([sys.executable, "-m", "py_compile", BE], capture_output=True, text=True)
    results.append(("语法", r.returncode == 0))

    # 2. status 全类别 + gold 对照
    rc, out, err = run("status", file=SYN, state=t_state)
    cats = json.loads(out)["categories"]
    gold = json.load(open(GOLD, encoding="utf-8"))
    for case in gold["cases"]:
        c = cats.get(case["category"])
        if not c:
            results.append((f"gold[{case['category']}]", False)); continue
        errs = []
        if "mean" in case and abs(c["posterior"]["mean"] - case["mean"]) > 0.005: errs.append("mean")
        if "ci_lo" in case and abs(c["ci_95"][0] - case["ci_lo"]) > 0.005: errs.append("ci_lo")
        if "ci_hi" in case and abs(c["ci_95"][1] - case["ci_hi"]) > 0.005: errs.append("ci_hi")
        if "p_gt" in case and abs(c["p_theta_gt_05"] - case["p_gt"]) > 0.005: errs.append("p_gt")
        if c["status"] != case["status"]: errs.append("status")
        if "level" in case and c.get("suggestion_level") != case["level"]: errs.append("level")
        if "suggestion_prefix" in case and not c.get("suggestion", "").startswith("[弱证据]"): errs.append("prefix")
        if "median_score" in case and c.get("median_score") != case["median_score"]: errs.append("median")
        results.append((f"gold[{case['category']}]", not errs))

    # 3. meta 汇总
    rc, out, err = run("status", file=SYN, state=t_state)
    m = json.loads(out)["meta"]
    results.append(("meta 汇总", m["total_categories"] == 8 and m["ok_count"] == 4 and m["weak_count"] == 3 and m["insufficient_count"] == 1))

    # 4. 先验变更
    r = subprocess.run([sys.executable, BE, "--file", SYN, "--params", t_params2, "--state", t_state, "status"],
                       capture_output=True, text=True, encoding="utf-8")
    mean2 = json.loads(r.stdout)["categories"]["t10k8"]["posterior"]["mean"]
    results.append(("先验(2,2) mean=0.7143", abs(mean2 - 0.7143) < 0.005))

    # 5. analyze 不存在类别
    rc, out, err = run("analyze", "--category", "ghost", file=SYN, state=t_state)
    results.append(("analyze 不存在类别 error", "error" in json.loads(out)))

    # 6. analyze 存在类别
    rc, out, err = run("analyze", "--category", "t10k8", file=SYN, state=t_state)
    a = json.loads(out)
    results.append(("analyze t10k8 完整", len(a.get("events", [])) == 10 and "q25" in a.get("quantiles", {})))

    # 7. 空事件文件
    e_file = os.path.join(tmp, "empty.json")
    with open(e_file, "w", encoding="utf-8") as f:
        json.dump({"version": "1.0", "events": [], "meta": {}}, f)
    r = subprocess.run([sys.executable, BE, "--file", e_file, "--state", t_state, "status"],
                       capture_output=True, text=True, encoding="utf-8")
    se = json.loads(r.stdout)
    results.append(("空事件不崩", r.returncode == 0 and len(se["categories"]) == 0))

    # 8. 真实数据全 insufficient + 零污染
    md5_before = hashlib.md5(open(REAL, "rb").read()).hexdigest()
    r = subprocess.run([sys.executable, BE, "--file", REAL, "--state", t_state, "status"],
                       capture_output=True, text=True, encoding="utf-8")
    sr = json.loads(r.stdout)
    all_insuff = all(c["status"] == "insufficient_data" for c in sr["categories"].values())
    md5_after = hashlib.md5(open(REAL, "rb").read()).hexdigest()
    results.append(("真实数据全 insufficient", all_insuff and len(sr["categories"]) == 5))
    results.append(("真实文件零污染", md5_before == md5_after))

    # 9. 纯 Python 回退 vs scipy
    sys.path.insert(0, ORGANS)
    import importlib
    be_mod = importlib.import_module("bayesian_evaluator")
    from scipy.stats import beta as sp_beta
    worst = 0.0
    for a, b in [(0.5, 0.5), (100, 1), (50, 50), (3, 1), (9, 3), (31, 1)]:
        lo_s, hi_s = sp_beta.interval(0.95, a, b)
        lo_p, hi_p = be_mod._beta_ppf(0.025, a, b), be_mod._beta_ppf(0.975, a, b)
        worst = max(worst, abs(lo_s - lo_p), abs(hi_s - hi_p))
        worst = max(worst, abs((1 - sp_beta.cdf(0.5, a, b)) - (1 - be_mod._betai(a, b, 0.5))))
    results.append((f"回退vs scipy 误差<1e-3 ({worst:.1e})", worst < 1e-3))

    # 10. rule_index 缺失 fallback
    r = subprocess.run([sys.executable, BE, "--file", SYN, "--index", os.path.join(tmp, "no.json"),
                        "--state", t_state, "status"], capture_output=True, text=True, encoding="utf-8")
    all_false = all(c["has_rules"] is False for c in json.loads(r.stdout)["categories"].values())
    results.append(("rule_index 缺失 has_rules=False", r.returncode == 0 and all_false))

    import shutil
    shutil.rmtree(tmp, ignore_errors=True)

    failed = 0
    for name, ok in results:
        print(f"[{'✓' if ok else '✗'}] {name}")
        if not ok: failed += 1
    print(f"\n>>> {len(results) - failed}/{len(results)} 通过")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
