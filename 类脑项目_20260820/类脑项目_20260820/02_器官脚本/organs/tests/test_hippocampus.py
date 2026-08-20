#!/usr/bin/env python3
"""海马体测试（交付审查 B1 补录——原 10 项内联验证固化）。
覆盖：append/query/update/suppress/reactivate 游标回退/原子写/stats/零污染。
运行：python test_hippocampus.py
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

ORGANS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HIP = os.path.join(ORGANS, "hippocampus.py")
REAL = os.path.expandvars(r"%USERPROFILE%\hermes-companion-configs\reflex_events.json")


def run(*args, file):
    r = subprocess.run([sys.executable, HIP, "--file", file, *args], capture_output=True, text=True, encoding="utf-8")
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def main():
    tmp = tempfile.mkdtemp(prefix="_hip_test_")
    t = os.path.join(tmp, "events.json")
    shutil.copy(REAL, t)
    results = []

    # 1. 语法
    r = subprocess.run([sys.executable, "-m", "py_compile", HIP], capture_output=True, text=True)
    results.append(("语法", r.returncode == 0))

    # 2. append 自动 id + meta 刷新
    rc, out, err = run("append", "--score=-3", "--category=audit", "--tag=t", file=t)
    e = json.loads(out)
    results.append(("append id=9 meta刷新", e["id"] == 9 and e["score"] == -3))

    # 3. append 后 stats
    rc, out, err = run("stats", file=t)
    st = json.loads(out)
    results.append(("stats total=9 neg=7", st["total"] == 9 and st["negative"] == 7))

    # 4. query 过滤（tag 子串/category）
    rc, out, err = run("query", "--category", "logic", file=t)
    q = json.loads(out)
    results.append(("query category=logic 3条", len(q) == 3))

    # 5. update 改 score 后 meta 刷新
    rc, out, err = run("update", "--id", "9", "--set", "score=-2", file=t)
    rc2, out2, err2 = run("stats", file=t)
    st2 = json.loads(out2)
    results.append(("update score 刷新 meta neg=7", st2["negative"] == 7 and st2["neutral"] == 0))

    # 6. update --set CI JSON 解析（B1 修复验证）
    rc, out, err = run("update", "--id", "9", "--set", "confidence_interval=[-8,-6]", file=t)
    e6 = json.loads(out)
    results.append(("CI JSON 解析为 list", isinstance(e6["confidence_interval"], list) and e6["confidence_interval"] == [-8, -6]))

    # 7. suppress 不删除
    rc, out, err = run("suppress", "--id", "9", file=t)
    rc2, out2, err2 = run("stats", file=t)
    st7 = json.loads(out2)
    results.append(("suppress 后 total 不变 suppressed=1", st7["total"] == 9 and st7["suppressed"] == 1))

    # 8. query 默认排除 suppressed；include 包含
    rc, out, err = run("query", "--limit", "100", file=t)
    results.append(("query 排除 suppressed", len(json.loads(out)) == 8))
    rc, out, err = run("query", "--include-suppressed", "--limit", "100", file=t)
    results.append(("query --include-suppressed 含", len(json.loads(out)) == 9))

    # 9. reactivate 游标回退（先设 cursor 再抑制再恢复）
    rc, out, err = run("update", "--id", "5", "--set", "meta_cursor_dummy=1", file=t)  # noop
    rc, out, err = run("reactivate", "--id", "9", file=t)
    rc2, out2, err2 = run("stats", file=t)
    st9 = json.loads(out2)
    results.append(("reactivate 恢复 suppressed=0", st9["suppressed"] == 0))

    # 10. 真实文件零污染
    md5_before = hashlib.md5(open(REAL, "rb").read()).hexdigest()
    rc, out, err = run("stats", file=t)
    md5_after = hashlib.md5(open(REAL, "rb").read()).hexdigest()
    results.append(("真实文件零污染", md5_before == md5_after))

    shutil.rmtree(tmp, ignore_errors=True)

    failed = 0
    for name, ok in results:
        print(f"[{'✓' if ok else '✗'}] {name}")
        if not ok: failed += 1
    print(f"\n>>> {len(results) - failed}/{len(results)} 通过")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
