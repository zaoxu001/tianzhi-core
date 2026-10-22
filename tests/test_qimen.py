"""奇门：书中算例逐条回放；定局与开源排盘程序 csp、元亨利贞网交叉核过的时刻；格局、空亡马星。

书中算例在 tianzhi-classics qimen/examples.json（需与本仓同级），没有则跳过。
"""
import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from tianzhi_core.qimen import qiju, ju_of, build_pan, find_geju, xun_kong
from tianzhi_core.qimen.ju import _run_ok, JIEQI
from tianzhi_core.qimen.pan import _s as s, dipan

EXAMPLES = Path(__file__).resolve().parents[2] / "tianzhi-classics" / "qimen" / "examples.json"


def _examples():
    if not EXAMPLES.exists():
        pytest.skip("需要 tianzhi-classics 与本仓库同级")
    return json.loads(EXAMPLES.read_text(encoding="utf-8"))


def test_book_cases_replay():
    """《遁甲演義》卷二卷三、《協紀》卷三十五的排盘算例：原文点明的每一处落宫都要对上"""
    ex = _examples()
    n = 0
    for c in ex["cases"]:
        if c.get("status") == "unclear":
            continue
        p = build_pan(c["dun"] == "陽", c["ju"], c["hour"], method=c["method"])
        pal, e = p["palaces"], c["expect"]
        if "zhifu" in e:
            assert p["zhifu"] == s(e["zhifu"]), c["id"]
        if "zhishi" in e:
            assert p["zhishi"] == s(e["zhishi"]), c["id"]
        for key, field in (("star", "stars"), ("tian", "tian"), ("di", "di")):
            for name, g in e.get(key, {}).items():
                assert s(name) in pal[g][field], (c["id"], key, name, g)
        for name, g in e.get("men", {}).items():
            assert pal[g]["door"] == s(name), (c["id"], name, g)
        for name, g in e.get("shen", {}).items():
            assert pal[g]["shen"] == s(name), (c["id"], name, g)
        n += 1
    assert n >= 45


def test_book_cases_geju():
    """算例所举之格，判格都要判得出"""
    alias = {"螣蛇跃蹻": "螣蛇夭矯"}
    for c in _examples()["cases"]:
        if c.get("status") == "unclear" or not c.get("geju"):
            continue
        p = build_pan(c["dun"] == "陽", c["ju"], c["hour"])
        names = {g["name"] for g in find_geju(p, day=c.get("day"))}
        assert alias.get(c["geju"], c["geju"]) in names, c["id"]


def test_book_runqi_rule():
    """书中置闰判例：芒种、大雪之后，符头早节八日以上即闰（前远后近），七日不闰"""
    for r in _examples()["runqi"]:
        if r["verdict"] not in ("置閏", "超神") or r["diff"] <= 0:
            continue
        f = datetime(2000, 1, 1) - timedelta(hours=1)   # 符头日子初
        jt = f + timedelta(days=r["diff"], hours=13)       # 交节在第 diff 日午时
        if r["verdict"] == "置閏":
            assert _run_ok("qian_yuan_hou_jin", jt, f), r["id"]
        elif r["jieqi"] in ("大雪", "芒種"):
            assert not _run_ok("qian_yuan_hou_jin", jt, f), r["id"]


# 与 csp（taynpg/csp，-t1 置闰九日之限 / -t3 拆补）及元亨利贞网交叉核过的时刻
CROSS = [
    ("2026-10-19 08:25", ("阴", 5), ("阴", 6), "天冲", "伤"),
    ("2024-12-15 12:00", ("阴", 4), ("阴", 4), None, None),
    ("2024-12-23 12:00", ("阴", 1), ("阳", 4), "天柱", "惊"),
    ("2025-06-21 12:00", ("阳", 9), ("阴", 6), "天冲", "伤"),
    ("2026-06-20 12:00", ("阴", 9), ("阳", 6), None, None),
    ("2004-09-01 12:00", ("阴", 9), ("阴", 1), "天辅", "杜"),
    ("1986-05-29 12:00", ("阳", 2), ("阳", 2), "天柱", "惊"),
]


@pytest.mark.parametrize("ts,zr,cb,zhifu,zhishi", CROSS)
def test_cross_checked(ts, zr, cb, zhifu, zhishi):
    t = datetime.strptime(ts, "%Y-%m-%d %H:%M")
    a = ju_of(t, rule="days9")
    assert (a["dun"], a["ju"]) == zr
    assert (lambda b: (b["dun"], b["ju"]))(ju_of(t, method="chaibu")) == cb
    if zhifu:
        r = qiju(t, rule="days9")
        assert (r["pan"]["zhifu"], r["pan"]["zhishi"]) == (zhifu, zhishi)


def test_csp_full_plate():
    """2026-10-19 08:25 一盘逐宫与 csp 相同（星、门、神、天盘、地盘）"""
    p = qiju(datetime(2026, 10, 19, 8, 25), rule="days9")["pan"]["palaces"]
    want = {6: ("天任", "惊", "螣蛇", "丁", "乙"), 7: ("天蓬", "死", "太阴", "壬", "丙"), 2: ("天心", "景", "六合", "乙", "辛"),
            9: ("天柱", "杜", "白虎", "丙", "癸"), 4: ("天芮", "伤", "玄武", "辛", "己"), 3: ("天英", "生", "九地", "癸", "庚"),
            8: ("天辅", "休", "九天", "己", "丁"), 1: ("天冲", "开", "直符", "庚", "壬")}
    for g, (st, dr, sh, tg, dg) in want.items():
        assert (p[g]["star"], p[g]["door"], p[g]["shen"], p[g]["tian"][0], p[g]["di"][0]) == (st, dr, sh, tg, dg), g
    assert p[4]["tian"] == ["辛", "戊"]          # 天禽随天芮，带中五之戊


def test_run_marks_and_modes():
    j = ju_of(datetime(2024, 12, 15, 12))
    assert j["run"] and j["mode"] == "置闰" and j["jieqi"] == "大雪"
    assert ju_of(datetime(2026, 10, 19, 8, 25))["mode"] == "超神"


def test_zi_hour_switch():
    """换局在子初（「凡換竒皆子時換也」）：2024-12-16 为中元符头，15 日 23 点即入中元"""
    assert ju_of(datetime(2024, 12, 15, 22, 30))["yuan"] == "上"
    assert ju_of(datetime(2024, 12, 15, 23, 30))["yuan"] == "中"
    assert ju_of(datetime(2024, 12, 16, 0, 30))["yuan"] == "中"


def test_dipan_and_jieqi_table():
    assert dipan(True, 1) == {1: "戊", 2: "己", 3: "庚", 4: "辛", 5: "壬", 6: "癸", 7: "丁", 8: "丙", 9: "乙"}
    assert dipan(False, 9) == {9: "戊", 8: "己", 7: "庚", 6: "辛", 5: "壬", 4: "癸", 3: "丁", 2: "丙", 1: "乙"}
    assert len(JIEQI) == 24 and JIEQI[0] == "冬至"


def test_kong_ma():
    r = qiju(datetime(2026, 10, 19, 8, 25))
    assert xun_kong("壬辰") == "午未" and r["kong"]["gong"] == [2, 9]
    assert r["ma"] == {"zhi": "寅", "gong": 8}


def test_options_validated():
    with pytest.raises(ValueError):
        ju_of(datetime(2026, 1, 1), method="maoshan")
    with pytest.raises(ValueError):
        build_pan(True, 10, "甲子")
