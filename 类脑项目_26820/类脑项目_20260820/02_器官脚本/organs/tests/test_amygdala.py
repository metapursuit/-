#!/usr/bin/env python3
"""杏仁核测试（交付审查 B1 补录——原 14 项内联验证固化核心 10 项）。
覆盖：词库命中/arousal 分解/valence 判定/calibrate 路径/数据化加载/零污染。
运行：python test_amygdala.py
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

ORGANS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AMY = os.path.join(ORGANS, "amygdala.py")
REAL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "reflex_events.json")  # fixture（脱敏示例数据，2026-08-20 自包含化）
DEFAULT_LEX = os.path.join(ORGANS, "amygdala_lexicon.json")
DEFAULT_PARAMS = os.path.join(ORGANS, "hyperparams.json")


def run(*args, file, lex=DEFAULT_LEX, params=DEFAULT_PARAMS):
    r = subprocess.run([sys.executable, AMY, "--file", file, "--lexicon", lex, "--params", params, *args],
                       capture_output=True, text=True, encoding="utf-8")
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def main():
    tmp = tempfile.mkdtemp(prefix="_amy_test_")
    t = os.path.join(tmp, "events.json")
    t_lex = os.path.join(tmp, "lex.json")
    t_params = os.path.join(tmp, "params.json")
    shutil.copy(REAL, t)
    results = []

    # 1. 语法
    r = subprocess.run([sys.executable, "-m", "py_compile", AMY], capture_output=True, text=True)
    results.append(("语法", r.returncode == 0))

    # 2. 显性负向文本
    rc, out, err = run("analyze", "--text", "你竟然撒谎！这太严重了", file=t)
    a = json.loads(out)
    results.append(("负向文本 valence=-1", a["valence"] == -1 and "竟然" in a["clues"]["neg"]))

    # 3. 正向文本
    rc, out, err = run("analyze", "--text", "很好，做得棒", file=t)
    a = json.loads(out)
    results.append(("正向文本 valence=1", a["valence"] == 1))

    # 4. 中性文本
    rc, out, err = run("analyze", "--text", "今天天气不错", file=t)
    a = json.loads(out)
    results.append(("中性文本 valence=0", a["valence"] == 0))

    # 5. arousal 公式（感叹号/强调词/长度）
    rc, out, err = run("analyze", "--text", "非常严重！！！！！！？？？叹气" + "长" * 80, file=t)
    a = json.loads(out)
    results.append(("arousal 封顶 1.0", a["arousal"] == 1.0))

    # 6. 自定义词库生效
    with open(t_lex, "w", encoding="utf-8") as f:
        json.dump({"neg": [{"word": "竟然"}], "pos": [], "arousal": [], "action_neg": []}, f, ensure_ascii=False)
    rc, out, err = run("analyze", "--text", "你竟然撒谎", file=t, lex=t_lex)
    a = json.loads(out)
    results.append(("自定义词库", a["clues"]["neg"] == ["竟然"]))

    # 7. 空词库不崩
    with open(t_lex, "w", encoding="utf-8") as f:
        json.dump({}, f)
    rc, out, err = run("analyze", "--text", "测试文本", file=t, lex=t_lex)
    results.append(("空词库不崩", json.loads(out)["valence"] == 0))

    # 8. calibrate 红线事件（人工 0.95 维持）
    with open(t_lex, "w", encoding="utf-8") as f:
        json.dump(json.load(open(DEFAULT_LEX, encoding="utf-8")), f, ensure_ascii=False)
    rc, out, err = run("calibrate", "--id", "1", file=t)
    row = json.loads(out)
    results.append(("calibrate #1 维持0.95", row["suggested_weight"] == 0.95))

    # 9. report 汇总结构
    rc, out, err = run("report", file=t)
    rep = json.loads(out)
    results.append(("report 结构", rep["summary"]["total"] == 8 and "valence_dist" in rep["summary"]))

    # 10. 真实文件零污染
    md5_before = hashlib.md5(open(REAL, "rb").read()).hexdigest()
    run("report", file=t)
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
