#!/usr/bin/env python3
"""
hermes-companion-configs 系统完整性自检
覆盖：JSON格式 | 字段完整性 | CI约束 | 情感权重范围 | 时间戳 | 规则-事件交叉 | meta计数 | 器官导入 | git整洁

用法：python scripts/self_check.py
零参数，自动定位 C:/Users/<user>/hermes-companion-configs
"""

import json, os, sys, re, importlib, subprocess
from datetime import datetime, timezone, timedelta

CN_TZ = timezone(timedelta(hours=8))
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORGANS = os.path.join(REPO, "organs")
EVENTS = os.path.join(REPO, "reflex_events.json")
SKILL = os.path.join(os.environ.get("LOCALAPPDATA", ""), "hermes", "skills",
                     "reflex-behavior-calibration", "SKILL.md")

RESULTS = []
def ok(name, cond, detail=""):
    RESULTS.append((name, cond, detail))
    return cond

# ── 1. reflex_events.json ──
print("[1] reflex_events.json")
with open(EVENTS, encoding="utf-8") as f:
    data = json.load(f)
events = data["events"]; meta = data["meta"]
ok("JSON有效", True)
ok("version存在", "version" in data)
ok("events是list", isinstance(events, list))

for ev in events:
    for field in ["id","timestamp","score","category","tag","scene","quote",
                  "emotional_weight","confidence_interval","scene_type","status"]:
        ok(f"event#{ev['id']}.{field}存在", field in ev)

ids = [ev["id"] for ev in events]
ok("无重复ID", len(ids) == len(set(ids)), f"重复:{[i for i in ids if ids.count(i)>1]}")

ci_bad = [ev["id"] for ev in events if isinstance(ev["confidence_interval"], str)]
ok("CI非字符串", len(ci_bad)==0, f"字符串CI: {ci_bad}")

for ev in events:
    ci = ev.get("confidence_interval", [0,0])
    if isinstance(ci, list) and len(ci)==2:
        ok(f"event#{ev['id']} CI lower≤upper", ci[0]<=ci[1], f"CI={ci}")

ew_bad = [ev["id"] for ev in events
          if not (0 <= ev.get("emotional_weight", 0.5) <= 1)]
ok("emotional_weight在[0,1]", len(ew_bad)==0, f"越界:{ew_bad}")

now = datetime.now(CN_TZ)
future = [ev["id"] for ev in events
          if datetime.fromisoformat(ev["timestamp"]) > now]
ok("无未来时间戳", len(future)==0, f"未来:{future}")

actual_pos = sum(1 for e in events if e["score"]>0)
actual_neg = sum(1 for e in events if e["score"]<0)
ok(f"meta.total_positive={meta['total_positive']} = 实际{actual_pos}", meta["total_positive"]==actual_pos)
ok(f"meta.total_negative={meta['total_negative']} = 实际{actual_neg}", meta["total_negative"]==actual_neg)

print(f"  事件:{len(events)} 正向:{actual_pos} 负向:{actual_neg}")

# ── 2. SKILL.md 规则交叉 ──
print("[2] SKILL.md 规则交叉引用")
if not os.path.exists(SKILL):
    ok("SKILL.md存在", False, SKILL)
else:
    with open(SKILL, encoding="utf-8") as f:
        skill = f.read()
    rs, re_mark = "<!-- REFLEX_RULES_START -->", "<!-- REFLEX_RULES_END -->"
    ok("含REFLEX_RULES_START", rs in skill)
    ok("含REFLEX_RULES_END", re_mark in skill)

    if rs in skill and re_mark in skill:
        block = skill.split(rs,1)[1].split(re_mark,1)[0]
        source_re = re.compile(r"事件#(\d+)")
        all_rule_sources = set(int(x) for x in source_re.findall(block))
        orphans = all_rule_sources - set(ids)
        ok("规则来源事件全存在", len(orphans)==0, f"孤儿:{sorted(orphans)}")

        active_neg = {ev["id"] for ev in events if ev["score"]<0 and ev.get("status")=="active"}
        uncovered = active_neg - all_rule_sources
        ok("活跃负向事件全被规则覆盖", len(uncovered)==0, f"未覆盖:{sorted(uncovered)}")

# ── 3. 器官导入 ──
print("[3] 器官导入")
sys.path.insert(0, ORGANS)
for name in ["hippocampus","amygdala","prefrontal","bayesian_evaluator",
             "reflex_deviator","sleep_consolidator"]:
    try:
        importlib.import_module(name)
        ok(f"{name}.py导入", True)
    except Exception as e:
        ok(f"{name}.py导入", False, str(e)[:100])

# ── 4. git整洁 ──
print("[4] git整洁")
try:
    r = subprocess.run(["git","status","--porcelain"], capture_output=True, text=True, cwd=REPO)
    dirty = r.stdout.strip()
    ok("git工作区干净", dirty=="", dirty[:200] if dirty else "")
except Exception as e:
    ok("git可用", False, str(e)[:100])

# ── 总览 ──
print()
passed = sum(1 for _,c,_ in RESULTS if c)
failed = sum(1 for _,c,_ in RESULTS if not c)
for name, cond, detail in RESULTS:
    if not cond:
        print(f"  ❌ {name}  → {detail}")
print(f"\n  通过:{passed} 失败:{failed}  → {'✅全绿' if failed==0 else '⚠️有问题'}")
sys.exit(0 if failed==0 else 1)
