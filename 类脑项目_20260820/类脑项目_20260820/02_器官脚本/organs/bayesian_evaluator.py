#!/usr/bin/env python3
"""
Bayesian 评估器 (Bayesian Evaluator) — 置信区间校准器官
【AI伙伴】类脑系统 V2 · 执行器官之五 · v1.1（方案审查修订版）

定位：不是"算分器"，是"敢说不知道的区间估计器"。
对每个 category 独立做贝叶斯推断（Beta-Binomial 共轭），
样本不足拒绝给结论；语义存疑（低分累积 vs 真问题）诚实标注。

设计依据：Desktop\bayesian-框架方案-v1.md（v1.1，审查通过版）
- 后验: Beta(a0+k, b0+n-k)，均值 = (a0+k)/(a0+b0+n)
- 95% CI: Beta 分位数（scipy 优先，纯 Python 连分数回退）
- 门槛: min_samples=10 / weak_n=30 / ci_width=0.4（hyperparams 可配）
- 低分累积分支: P>=0.9 但中位分>-4 → "低分累积提醒"而非"真问题"

CLI:
  python bayesian_evaluator.py status                  # 全类别总览
  python bayesian_evaluator.py analyze --category X    # 单类别深入
  python bayesian_evaluator.py state                   # 查看 state
"""

import argparse
import json
import math
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hippocampus import Hippocampus, DEFAULT_PATH

ORGANS = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PARAMS = os.path.join(ORGANS, "hyperparams.json")
DEFAULT_INDEX = os.path.join(ORGANS, "rule_index.json")
DEFAULT_STATE = os.path.join(ORGANS, "bayesian_state.json")

CN_TZ = timezone(timedelta(hours=8))

# ---- scipy（优先）----
try:
    from scipy.stats import beta as _scipy_beta
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


def _load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def now_iso():
    return datetime.now(CN_TZ).isoformat(timespec="seconds")


# ================= 纯 Python 回退：不完全 Beta + 分位数 =================
def _betacf(a, b, x, itmax=200, eps=3e-12):
    """不完全 Beta 连分数展开（Numerical Recipes betacf）。"""
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < 1e-30:
        d = 1e-30
    d = 1.0 / d
    h = d
    for m in range(1, itmax + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return h


def _betai(a, b, x):
    """正则不完全 Beta I_x(a,b)，x 的兼容区间为 [0,1]。"""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lnbt = (math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
            + a * math.log(x) + b * math.log1p(-x))
    bt = math.exp(lnbt)
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def _beta_ppf(p, a, b, tol=1e-9):
    """Beta 分位数（二分法反 CDF），用于 95% 区间与 P(theta>0.5)。"""
    lo, hi = 1e-12, 1.0 - 1e-12
    for _ in range(200):
        mid = (lo + hi) / 2.0
        if _betai(a, b, mid) < p:
            lo = mid
        else:
            hi = mid
        if hi - lo < tol:
            break
    return (lo + hi) / 2.0


def beta_interval(alpha, beta_, prob=0.95):
    """统一入口：scipy 优先，纯 Python 回退。返回 (lo, hi)。"""
    if HAS_SCIPY:
        lo, hi = _scipy_beta.interval(prob, alpha, beta_)
        return float(lo), float(hi)
    tail = (1.0 - prob) / 2.0
    return _beta_ppf(tail, alpha, beta_), _beta_ppf(1.0 - tail, alpha, beta_)


def beta_cdf(x, alpha, beta_):
    """统一入口：scipy 优先，纯 Python 回退。"""
    if HAS_SCIPY:
        return float(_scipy_beta.cdf(x, alpha, beta_))
    return _betai(alpha, beta_, x)


# ================= 评估器 =================
class BayesianEvaluator:
    def __init__(self, events_path=None, params_path=None, index_path=None, state_path=None):
        self.h = Hippocampus(events_path)
        self.params = _load_json(params_path or DEFAULT_PARAMS, {}).get("bayesian", {})
        self.index_path = index_path or DEFAULT_INDEX
        self.state_path = state_path or DEFAULT_STATE

    def _aggregate(self):
        """按 category 聚合：n / k(负向数) / scores。"""
        agg = {}
        for e in self.h.data["events"]:
            cat = e.get("category", "other")
            a = agg.setdefault(cat, {"n": 0, "k": 0, "scores": []})
            a["n"] += 1
            if e["score"] < 0:
                a["k"] += 1
            a["scores"].append(e["score"])
        return agg

    def _evaluate_category(self, cat, agg):
        """单类别贝叶斯推断（含门槛、低分累积分支、建议）。"""
        a0 = self.params.get("prior_alpha", 1)
        b0 = self.params.get("prior_beta", 1)
        min_samples = self.params.get("min_samples", 10)
        weak_n = self.params.get("weak_n_threshold", 30)
        weak_w = self.params.get("weak_ci_width", 0.4)
        hi_t = self.params.get("suggestion_threshold_high", 0.9)
        mid_t = self.params.get("suggestion_threshold_mid", 0.6)
        # mild_score_threshold 比较方向（负数陷阱，勿改）：
        #   median_score > 阈值（如 -1 > -4）→ mild/低分累积
        #   median_score <= 阈值（如 -10 <= -4）→ 严重/真问题
        # 负数下 > 与 >= 直觉相反，禁止凭直觉修改此行。
        mild_t = self.params.get("mild_score_threshold", -4)

        n, k = agg["n"], agg["k"]
        scores = sorted(agg["scores"])
        median_score = scores[len(scores) // 2] if scores else None

        # 后验参数
        a, b = a0 + k, b0 + n - k
        mean = a / (a + b)
        lo, hi = beta_interval(a, b)
        p_gt = 1.0 - beta_cdf(0.5, a, b)
        ci_width = hi - lo

        # 门槛
        if n < min_samples:
            status = "insufficient_data"
        elif n < weak_n or ci_width > weak_w:
            status = "weak_evidence"
        else:
            status = "ok"

        # 建议（仅 weak/ok；insufficient 不给）
        suggestion, level = None, None
        if status != "insufficient_data":
            if p_gt >= hi_t:
                is_severe = median_score is not None and median_score <= mild_t  # ≤-4 才严重
                if is_severe:
                    level, suggestion = "high_confidence", "真问题概率高（建议触发提炼/提醒）"
                else:
                    level, suggestion = "low_score_accumulation", "低分累积提醒（同类低负向反复出现，建议关注）"
            elif p_gt >= mid_t:
                level, suggestion = "moderate", "倾向真问题（建议继续观察）"
            else:
                level, suggestion = "low", "疑似随机波动（建议不提醒）"
            if status == "weak_evidence":
                suggestion = f"[弱证据] {suggestion}"

        return {
            "n": n, "k": k,
            "posterior": {"alpha": a, "beta": b, "mean": round(mean, 4)},
            "ci_95": [round(lo, 4), round(hi, 4)], "ci_width": round(ci_width, 4),
            "p_theta_gt_05": round(p_gt, 4),
            "median_score": median_score,
            "has_rules": self._has_rules(cat),
            "status": status,
            "suggestion": suggestion, "suggestion_level": level,
            "previous_status": None, "status_changed_at": None,
        }

    def _has_rules(self, cat):
        # fallback：rule_index.json 不存在时默认 False（器官可独立启动，不依赖固结器先跑）
        index = _load_json(self.index_path, {"rules": []})
        return any(r.get("category") == cat and r.get("status") == "active" for r in index.get("rules", []))

    def evaluate(self):
        """全类别评估 + state 持久化（含趋势字段占位）。"""
        agg = self._aggregate()
        old_state = _load_json(self.state_path, {"categories": {}})
        old_cats = old_state.get("categories", {})
        cats = {}
        for cat, a in agg.items():
            cur = self._evaluate_category(cat, a)
            prev = old_cats.get(cat, {})
            if prev.get("status") and prev.get("status") != cur["status"]:
                cur["previous_status"] = prev.get("status")
                cur["status_changed_at"] = now_iso()
            cats[cat] = cur

        state = {
            "last_evaluated": now_iso(),
            "categories": cats,
            "meta": {
                "total_categories": len(cats),
                "ok_count": sum(1 for c in cats.values() if c["status"] == "ok"),
                "weak_count": sum(1 for c in cats.values() if c["status"] == "weak_evidence"),
                "insufficient_count": sum(1 for c in cats.values() if c["status"] == "insufficient_data"),
            },
        }
        _save_json(self.state_path, state)
        return state

    def analyze_category(self, cat):
        """单类别深入：事件清单 + 分位数 + 状态对比。"""
        state = _load_json(self.state_path, None)
        if state is None:
            return {"error": "尚无评估记录——先运行 status"}
        if cat not in state["categories"]:
            return {"error": f"类别 {cat} 不在评估记录中", "categories": list(state["categories"])}
        events = [{"id": e["id"], "score": e["score"], "tag": e.get("tag"), "scene_type": e.get("scene_type")}
                  for e in self.h.data["events"] if e.get("category") == cat]
        a = state["categories"][cat]["posterior"]["alpha"]
        b = state["categories"][cat]["posterior"]["beta"]
        quantiles = {"q25": round(beta_ppf_q(0.25, a, b), 4),
                     "q50": round(beta_ppf_q(0.5, a, b), 4),
                     "q75": round(beta_ppf_q(0.75, a, b), 4)}
        return {"category": cat, "events": events, "quantiles": quantiles, "summary": state["categories"][cat]}


def beta_ppf_q(p, a, b):
    if HAS_SCIPY:
        return float(_scipy_beta.ppf(p, a, b))
    return _beta_ppf(p, a, b)


def main():
    p = argparse.ArgumentParser(description="Bayesian 评估器 — 置信区间校准")
    p.add_argument("--file", default=None, help="事件文件路径")
    p.add_argument("--params", default=None, help="超参数文件路径")
    p.add_argument("--index", default=None, help="规则索引路径")
    p.add_argument("--state", default=None, help="state 输出路径")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("status", help="全类别总览并持久化 state")
    a = sub.add_parser("analyze", help="单类别深入")
    a.add_argument("--category", required=True)
    st = sub.add_parser("state", help="查看 bayesian_state.json")

    args = p.parse_args()
    be = BayesianEvaluator(args.file, args.params, args.index, args.state)

    if args.cmd == "status":
        print(json.dumps(be.evaluate(), ensure_ascii=False, indent=2))
    elif args.cmd == "analyze":
        print(json.dumps(be.analyze_category(args.category), ensure_ascii=False, indent=2))
    elif args.cmd == "state":
        state = _load_json(be.state_path, None)
        print(json.dumps(state if state is not None else {"error": "无 state 文件"}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
