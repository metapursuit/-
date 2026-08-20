"""冒烟测试模板 — 【AI伙伴】类脑器官落地/改动后使用。

用法：
1. 复制本文件到 organs/ 下（如 _smoke_xxx.py），按需修改 TARGET 和测试项
2. 核心原则：全部操作跑在临时文件副本上，真实文件 md5 必须不变（零污染）
3. 负数参数必须用等号（--score=-8）；--file 是全局参数放子命令前

参考：海马体 10 项 / 杏仁核 14 项 / 前额叶 13 项 / review 回归 15 项
"""
import os
import sys
import json
import hashlib
import shutil
import subprocess

ORGANS = os.path.expandvars(r"%USERPROFILE%\hermes-companion-configs\organs")
REAL = os.path.expandvars(r"%USERPROFILE%\hermes-companion-configs\reflex_events.json")  # 事实源真身
TMP = os.path.join(ORGANS, "_smoke_test.json")
TMP_DRAFTS = os.path.join(ORGANS, "_smoke_drafts.json")  # 前额叶类器官用

TARGET = os.path.join(ORGANS, "hippocampus.py")  # ← 改成被测器官


def run(script, *args):
    """CLI 子进程调用；--file 固定放子命令前。"""
    cmd = [sys.executable, script, "--file", TMP]
    if script.endswith("prefrontal.py"):
        cmd += ["--drafts", TMP_DRAFTS]
    r = subprocess.run(cmd + list(args), capture_output=True, text=True, encoding="utf-8")
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def md5(p):
    with open(p, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


results = []
real_before = md5(REAL)

# 干净环境（防上次残留干扰复现）
for f in [TMP, TMP_DRAFTS, TMP + ".tmp", TMP_DRAFTS + ".tmp"]:
    if os.path.exists(f):
        os.remove(f)

shutil.copy(REAL, TMP)

# 语法检查
r = subprocess.run([sys.executable, "-m", "py_compile", TARGET], capture_output=True, text=True)
results.append(("语法编译", "PASS" if r.returncode == 0 else f"FAIL: {r.stderr}"))

# ===== 在这里添加测试项 =====
# 模式：rc, out, err = run(TARGET, "stats") → data = json.loads(out) → 断言
# 注意：
# - 复现 bug 的测试先确认前置条件能让 bug 真正触发（阈值/状态满足）
# - 区分「断言错」vs「代码 bug」：先看功能输出是否合理再改断言
# - warning 在 stderr（err），stdout 必须是纯 JSON

# 零污染验证（最后一项）
results.append(("真实文件零污染(md5不变)", "PASS" if md5(REAL) == real_before else "FAIL: 真实文件被改了!"))

# 清理
for f in [TMP, TMP_DRAFTS]:
    if os.path.exists(f):
        os.remove(f)
    if os.path.exists(f + ".tmp"):
        os.remove(f + ".tmp")

for name, status in results:
    print(f"[{'✓' if status == 'PASS' else '✗'}] {name}" + ("" if status == "PASS" else f" — {status}"))
print()
print(">>> 全部通过" if all(s == "PASS" for _, s in results) else ">>> 存在失败!")
