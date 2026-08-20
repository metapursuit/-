#!/usr/bin/env python3
"""
杏仁核 (Amygdala) — 情绪强度标记器官
【AI伙伴】类脑系统 V2 · 执行器官之二 · 数据化版 2.1

职责：对已录入事件做情绪量化——极性标注 (valence)、激活度测量 (arousal)、
强度校准建议 (suggested_weight)。产出睡眠优先度公式 P_i 中的 e_i。

数据化（PRINCIPLES 可迭代化原则）：
- 词库 → organs/amygdala_lexicon.json（加词不改代码，带 note/source_event）
- 参数 → organs/hyperparams.json 的 amygdala 段
- 期望值 → organs/tests/amygdala_gold.json（回归验证）

边界（对齐 V1 契约）：
- 不做事件检测——不判定"这是夸奖/批评"，判定权永远手动主
- 正向不自动升级——校准只增强负向线索，正向维持人工值
- 默认只报告不写回；--apply 才通过海马体 update 写回

CLI 用法：
  python amygdala.py analyze --text "你竟然撒谎！这太严重了"
  python amygdala.py report [--file events.json] [--apply]
  python amygdala.py calibrate --id 1 [--apply]
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hippocampus import Hippocampus, DEFAULT_PATH

ORGANS = os.path.dirname(os.path.abspath(__file__))
DEFAULT_LEXICON = os.path.join(ORGANS, "amygdala_lexicon.json")
DEFAULT_PARAMS = os.path.join(ORGANS, "hyperparams.json")


def _load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


class Amygdala:
    def __init__(self, path=None, lexicon_path=None, params_path=None):
        self.h = Hippocampus(path)
        self.lexicon_path = lexicon_path or DEFAULT_LEXICON
        self.params = _load_json(params_path or DEFAULT_PARAMS, {})
        self.lexicon = self._load_lexicon()
        self.ap = self.params.get("amygdala", {})

    def _load_lexicon(self):
        """从 JSON 加载词库（数据与代码分离，加词不改代码）。"""
        lex = _load_json(self.lexicon_path, {})
        return {
            "neg": [x["word"] for x in lex.get("neg", [])],
            "pos": [x["word"] for x in lex.get("pos", [])],
            "arousal": [x["word"] for x in lex.get("arousal", [])],
            "action_neg": [x["word"] for x in lex.get("action_neg", [])],
        }

    def analyze_text(self, text):
        """情绪特征分析：极性 + 激活度 + 线索明细。纯信息，不判定事件。"""
        if not text:
            return {"valence": 0, "arousal": 0.0, "clues": {"neg": [], "pos": [], "action_neg": [], "exclamations": 0, "questions": 0}}
        neg_hits = [w for w in self.lexicon["neg"] if w in text]
        pos_hits = [w for w in self.lexicon["pos"] if w in text]
        action_hits = [w for w in self.lexicon["action_neg"] if w in text]
        n_excl = text.count("！") + text.count("!")
        n_q = text.count("？") + text.count("?")

        # 激活度：基础 + 标点 + 强调词 + 动作 + 长度（参数全部来自 hyperparams.json）
        arousal = self.ap.get("arousal_base", 0.3)
        arousal += min(self.ap.get("excl_cap", 0.3), self.ap.get("excl_rate", 0.12) * n_excl)
        arousal += min(self.ap.get("q_cap", 0.15), self.ap.get("q_rate", 0.08) * n_q)
        if any(w in text for w in self.lexicon["arousal"]):
            arousal += self.ap.get("arousal_word_bonus", 0.1)
        if action_hits:
            arousal += self.ap.get("action_bonus", 0.1)
        if len(text) > self.ap.get("long_text_len", 80):
            arousal += self.ap.get("long_text_bonus", 0.1)
        arousal = round(min(1.0, arousal), 2)

        # 极性：线索主导；正负同时存在=矛盾，需人工
        if neg_hits or action_hits:
            valence = -1 if not pos_hits else 0
        elif pos_hits:
            valence = 1
        else:
            valence = 0

        return {"valence": valence, "arousal": arousal,
                "clues": {"neg": neg_hits, "pos": pos_hits, "action_neg": action_hits,
                          "exclamations": n_excl, "questions": n_q}}

    def calibrate(self, event):
        """单事件校准：只给建议，不写回（除非调用方 update）。"""
        manual = event.get("emotional_weight", 0.5)
        text = f"{event.get('quote', '')}\n{event.get('scene', '')}"
        a = self.analyze_text(text)
        score = event.get("score", 0)
        suggested, reasons = manual, []

        if score < 0 and a["valence"] == -1 and a["arousal"] >= self.ap.get("calibrate_min_arousal", 0.45) and manual < self.ap.get("calibrate_max_manual", 0.85):
            boost = 0.1 + 0.15 * a["arousal"]
            suggested = min(self.ap.get("calibrate_up_cap", 0.95), round(manual + boost, 2))
            reasons.append(f"负向线索强(arousal={a['arousal']}, 词:{'/'.join(a['clues']['neg'][:3]) or '动作'})，建议上调")
        elif score < 0 and manual > self.ap.get("calibrate_high_manual", 0.9):
            reasons.append("负向事件人工值已高，维持")
        elif score > 0:
            reasons.append("正向事件：按 V1 契约不自动升级，维持人工值")
        else:
            reasons.append("中性事件，维持默认")

        return {"id": event["id"], "score": score, "valence": a["valence"],
                "arousal": a["arousal"], "original_weight": manual,
                "suggested_weight": suggested, "delta": round(suggested - manual, 2),
                "reasons": reasons, "clues": a["clues"]}

    def report(self):
        rows = [self.calibrate(e) for e in self.h.data["events"]]
        summary = {
            "total": len(rows),
            "valence_dist": {"pos": sum(1 for r in rows if r["valence"] == 1),
                             "neg": sum(1 for r in rows if r["valence"] == -1),
                             "neutral": sum(1 for r in rows if r["valence"] == 0)},
            "avg_arousal": round(sum(r["arousal"] for r in rows) / len(rows), 2) if rows else 0,
            "upgrade_suggested": sum(1 for r in rows if r["delta"] > 0),
        }
        return {"summary": summary, "rows": rows}


def main():
    p = argparse.ArgumentParser(description="杏仁核 — 情绪强度标记")
    p.add_argument("--file", default=None, help="事件文件路径")
    p.add_argument("--lexicon", default=None, help="词库文件路径（默认 amygdala_lexicon.json）")
    p.add_argument("--params", default=None, help="超参数文件路径（默认 hyperparams.json）")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("analyze", help="分析文本情绪特征")
    a.add_argument("--text", required=True)

    r = sub.add_parser("report", help="全量情绪报告")
    r.add_argument("--apply", action="store_true", help="将建议写回事件（calibrate 默认只报告）")

    c = sub.add_parser("calibrate", help="校准单条事件")
    c.add_argument("--id", type=int, required=True)
    c.add_argument("--apply", action="store_true", help="写回建议值")

    args = p.parse_args()
    am = Amygdala(args.file, args.lexicon, args.params)

    if args.cmd == "analyze":
        print(json.dumps(am.analyze_text(args.text), ensure_ascii=False, indent=2))
    elif args.cmd == "report":
        rep = am.report()
        if args.apply:
            for row in rep["rows"]:
                if row["suggested_weight"] != row["original_weight"] and am.h.get(row["id"]) is not None:
                    am.h.update(row["id"], emotional_weight=row["suggested_weight"],
                                valence=row["valence"], arousal=row["arousal"])
        print(json.dumps(rep, ensure_ascii=False, indent=2))
    elif args.cmd == "calibrate":
        e = am.h.get(args.id)
        if not e:
            print(f"NOT FOUND: event {args.id}")
            return 1
        row = am.calibrate(e)
        if args.apply and row["suggested_weight"] != row["original_weight"]:
            am.h.update(args.id, emotional_weight=row["suggested_weight"],
                        valence=row["valence"], arousal=row["arousal"])
            row["applied"] = True
        print(json.dumps(row, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
