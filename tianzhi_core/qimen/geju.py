"""奇门吉凶诸格：在排好的盘上逐宫判定。

规则表 data/qimen_geju.json 出自 tianzhi-classics（《遁甲演義》卷二），provenance 为 modeled：
cond 是同一宫内须同时成立的条件，表示本包如何读原文，不等同原书论述。另有八格不按一宫天地盘判
（五不遇时、六仪击刑、伏吟、反吟、门迫、时干入墓、天网四张、三奇受制），在此专门实现，判法写在各处。

只给「哪一宫成何格、出自哪一句」，不给吉凶断语的发挥——那是书中原文与下游解读的事。
"""
from __future__ import annotations

from ..core import ganzhi, wuxing
from .pan import JI, STARS, _table, _s, xun_of

__all__ = ["find", "GEJU"]

GEJU: list[dict] = _table("geju")["items"]
_SPECIAL = {it["name"]: it for it in _table("geju")["special"]}
_GONG_WX = {int(g): v["wuxing"] for g, v in _table("jiugong")["palaces"].items()}
_DOOR_HOME = {_s(v["door"]): int(g) for g, v in _table("jiugong")["palaces"].items() if v["door"]}
_OPPOSITE = {1: 9, 9: 1, 2: 8, 8: 2, 3: 7, 7: 3, 4: 6, 6: 4}
#: 六仪击刑：旬首 → 所刑之宫（《演義》引王璋）
_JIXING = {"甲子": 3, "甲戌": 2, "甲申": 8, "甲午": 9, "甲辰": 4, "甲寅": 4}
_RUMU_HOUR = {"丙戌", "壬辰", "丁丑", "癸未", "戊戌", "己丑"}


def _gan(gz: str | None) -> str | None:
    """取干；甲不见于盘，以其旬首所隐之仪当之"""
    if not gz:
        return None
    return xun_of(gz)[1] if gz[0] == "甲" else gz[0]


def _vals(v, env) -> set:
    vs = v if isinstance(v, list) else [v]
    out = set()
    for x in vs:
        x = env.get(x[1:]) if isinstance(x, str) and x.startswith("$") else x
        if x:
            out.add(_s(x) if isinstance(x, str) else x)
    return out


def _match(cond: dict, p: dict, g: int, env: dict) -> bool:
    for k, v in cond.items():
        want = _vals(v, env)
        if not want:
            return False
        if k == "tian" and not (want & set(p["tian"])):
            return False
        if k == "di" and not (want & set(p["di"])):
            return False
        if k == "men" and p["door"] not in want:
            return False
        if k == "shen" and p["shen"] not in want:
            return False
        if k == "gong" and g not in want:
            return False
    return True


def find(pan: dict, *, day: str | None = None, month: str | None = None, year: str | None = None) -> list[dict]:
    """这一盘成哪些格。day/month/year 为日、月、年干支（判伏干、飞干、岁月格与五不遇时要用；缺则跳过相关格）。

    返回 [{name, verdict, gong, cite, quote}]；gong 为 None 表示整盘之格（如五不遇时、伏吟）。
    """
    pal = pan["palaces"]
    env = {"xun": pan["xun_yi"], "hour": _gan(pan["hour"]), "day": _gan(day), "month": _gan(month), "year": _gan(year),
           "zhishi": pan["zhishi"]}
    out = []

    def hit(name, verdict, gong, src):
        out.append({"name": name, "verdict": verdict, "gong": gong, "cite": src["cite"], "quote": src["quote"]})

    for it in GEJU:
        for g in range(1, 10):
            if g == 5:
                continue
            p = pal[g]
            if _match(it["cond"], p, g, env) or any(_match(v["cond"], p, g, env) for v in it.get("variants", [])):
                hit(it["name"], it["verdict"], g, it)
    sp = _SPECIAL
    # 五不遇时：时干克日干，阳克阳、阴克阴
    if day:
        hg, dg = pan["hour"][0], day[0]
        if wuxing.relation(ganzhi.GAN_WUXING[hg], ganzhi.GAN_WUXING[dg]) == "官杀" and (hg in ganzhi.GAN_YANG) == (dg in ganzhi.GAN_YANG):
            hit("五不遇時", "凶", None, sp["五不遇時"])
    # 六仪击刑：直符（时旬首）加其所刑之宫
    if pan["zhifu_gong"] == _JIXING[pan["xun"]]:
        hit("六儀擊刑", "凶", pan["zhifu_gong"], sp["六儀擊刑"])
    # 伏吟、反吟：直符之星仍在本宫 / 在对冲之宫
    home = next(g for g, st in STARS.items() if st == pan["zhifu"])
    home = JI if home == 5 else home
    if pan["zhifu_gong"] == home:
        hit("伏吟", "凶", None, sp["伏吟"])
    elif _OPPOSITE.get(home) == pan["zhifu_gong"]:
        hit("反吟", "凶", None, sp["反吟"])
    # 门迫：门之五行克宫之五行
    for g, p in pal.items():
        if p["door"] and g != 5:
            dw = _GONG_WX[_DOOR_HOME[p["door"]]]
            if wuxing.relation(_GONG_WX[g], dw) == "财":
                hit("門迫", "凶", g, sp["門迫"])
    if pan["hour"] in _RUMU_HOUR:
        hit("時干入墓", "凶", None, sp["時干入墓"])
    if pan["hour"][0] == "癸":
        hit("天網四張", "凶", None, sp["天網四張"])
    for g, p in pal.items():
        if ("乙" in p["tian"] and g in (6, 7)) or ("丙" in p["tian"] and g == 1):
            hit("三竒受制", "凶", g, sp["三竒受制"])
    return out
