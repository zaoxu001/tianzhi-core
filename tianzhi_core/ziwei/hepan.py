"""合盘：两张紫微命盘之间的结构化指标。

只给指标，不给文案。《紫微斗数全书》没有专论合盘的一节，这里取后世通行的三条看法：

1. 四化互飞：甲的生年四化星在乙的盘上落在哪一宫（反过来同理）；
2. 命宫互看：两人命宫地支的合冲刑害，判定走 :mod:`tianzhi_core.core.ganzhi`；甲命宫的主星落在乙盘哪一宫；
3. 夫妻宫对照：甲夫妻宫里的主星，是不是正好坐在乙的命宫。

另给一个 0 到 100 的相对分与一个档位标签。权重全部为本包取值，不出典籍。
分数两个方向各算一遍再相加，所以 ``relation(a, b)`` 与 ``relation(b, a)`` 的分数、档位、
命宫关系必然一致；``ab`` / ``ba`` 两半随顺序互换。
"""
from __future__ import annotations

from ..core import ganzhi
from .chart import at

# ── 权重表（全部为本包取值，可调）────────────────────────────────
BASE: float = 50.0
#: 四化落进对方哪一宫，按宫的分量折算：命、夫妻、福德最贴身
PALACE_W: dict[str, float] = {"命宫": 1.0, "夫妻": 1.0, "福德": 1.0, "财帛": .6, "官禄": .6, "迁移": .6}
PALACE_W_REST: float = .3
HUA_PT: dict[str, float] = {"禄": 8.0, "权": 3.0, "科": 4.0, "忌": -8.0}
#: 两人命宫地支之间每种关系的分值
MING_ZHI_PT: dict[str, float] = {"六合": 8.0, "三合": 6.0, "冲": -6.0, "刑": -3.0, "害": -3.0}
#: 甲夫妻宫的主星坐在乙命宫，每个方向各算一次
FUQI_MATCH_PT: float = 6.0
#: 甲命宫主星落在乙的命、夫妻、福德，每个方向各算一次
MING_IN_KEY_PT: float = 3.0
KEY_PALACES: tuple[str, ...] = ("命宫", "夫妻", "福德")
#: 档位标签，与 bazi.hepan 同一套。只是分段标签，不是断语
GRADE_BANDS: tuple[tuple[float, str], ...] = ((75.0, "相契"), (55.0, "相合"), (40.0, "平"), (0.0, "相冲"))
HUA_ORDER: tuple[str, ...] = ("禄", "权", "科", "忌")


def _where(chart: dict) -> dict:
    return {s["name"]: p["name"] for p in chart["palaces"] for s in p["stars"]}


def _palace(chart: dict, name: str) -> dict:
    return next(p for p in chart["palaces"] if p["name"] == name)


def _mains(p: dict) -> list:
    return [s["name"] for s in p["stars"] if s["kind"] == "main"]


def _ming_mains(chart: dict) -> tuple[list, bool]:
    """命宫主星；命宫无主星照书借对宫。返回 (星名, 是否借来的)"""
    ming = _palace(chart, "命宫")
    if _mains(ming):
        return _mains(ming), False
    opp = next(p for p in chart["palaces"] if p["zhi"] == at(ming["zhi"], 6))
    return _mains(opp), True


def _sihua(chart: dict) -> list:
    got = {s["hua"]: s["name"] for p in chart["palaces"] for s in p["stars"] if s.get("hua")}
    return [(h, got[h]) for h in HUA_ORDER if h in got]


def ming_kinds(a_zhi: str, b_zhi: str) -> list[str]:
    """两个命宫地支之间的关系：六合、三合、冲、刑、害（可多项）"""
    kinds = []
    for r in ganzhi.zhi_relation(a_zhi, b_zhi):
        k = "六合" if r.kind == "合" else r.kind
        if k in MING_ZHI_PT and k not in kinds:
            kinds.append(k)
    if a_zhi != b_zhi and any(a_zhi in g and b_zhi in g for g in ganzhi.ZHI_SANHE):
        kinds.append("三合")
    return kinds


def _direction(src: dict, dst: dict) -> dict:
    where = _where(dst)
    fei = [{"hua": h, "star": n, "palace": where[n]} for h, n in _sihua(src) if n in where]
    stars, borrowed = _ming_mains(src)
    return {"fei": fei, "ming_stars": stars, "ming_borrowed": borrowed,
            "ming_in": where.get(stars[0]) if stars else None,
            "fuqi_match": [n for n in _mains(_palace(src, "夫妻")) if n in _mains(_palace(dst, "命宫"))]}


def _score_dir(d: dict) -> tuple[float, list]:
    pts, why = 0.0, []
    for f in d["fei"]:
        v = HUA_PT[f["hua"]] * PALACE_W.get(f["palace"], PALACE_W_REST)
        pts += v
        why.append((f"化{f['hua']}入{f['palace']}", round(v, 1)))
    if d["ming_in"] in KEY_PALACES:
        pts += MING_IN_KEY_PT
        why.append((f"命宫主星落{d['ming_in']}", MING_IN_KEY_PT))
    if d["fuqi_match"]:
        pts += FUQI_MATCH_PT
        why.append(("夫妻宫星坐对方命宫", FUQI_MATCH_PT))
    return pts, why


def relation(a: dict, b: dict) -> dict:
    """两张紫微命盘（build_chart 的结果，或带同样 palaces 结构的 dict）之间的关系指标。

    返回 score（0–100）、grade、ming（两人命宫地支与关系）、ab / ba（一方落到另一方盘上：
    fei 四化飞入各宫、ming_stars 命宫主星、ming_in 主星所落之宫、fuqi_match 夫妻宫星坐对方命宫者）
    与 breakdown（每一项加减了多少分）。"""
    ab, ba = _direction(a, b), _direction(b, a)
    kinds = ming_kinds(a["ming"], b["ming"])
    s_ab, w_ab = _score_dir(ab)
    s_ba, w_ba = _score_dir(ba)
    score = round(max(0.0, min(100.0, BASE + s_ab + s_ba + sum(MING_ZHI_PT[k] for k in kinds))))
    return {"score": score, "grade": next(g for lo, g in GRADE_BANDS if score >= lo), "ab": ab, "ba": ba,
            "ming": {"a": a["ming"], "b": b["ming"], "kinds": kinds},
            "breakdown": {"ab": w_ab, "ba": w_ba, "ming_zhi": [(f"命宫{k}", MING_ZHI_PT[k]) for k in kinds]}}
