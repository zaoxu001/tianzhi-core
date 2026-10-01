"""紫微合盘：分数与调用顺序无关；四化落宫与星的实际位置一致；命宫关系判定。"""
import random
from datetime import datetime

from tianzhi_core.ziwei import build_chart
from tianzhi_core.ziwei.hepan import ming_kinds, relation


def _pairs(n, seed):
    rnd = random.Random(seed)
    dt = lambda: datetime(rnd.randint(1950, 2010), rnd.randint(1, 12), rnd.randint(1, 28), rnd.randint(0, 23), rnd.choice((0, 30)))
    for _ in range(n):
        yield build_chart(dt(), rnd.randint(0, 1)), build_chart(dt(), rnd.randint(0, 1))


def test_symmetric_and_bounded():
    for a, b in _pairs(150, 7):
        r1, r2 = relation(a, b), relation(b, a)
        assert (r1["score"], r1["grade"]) == (r2["score"], r2["grade"])
        assert 0 <= r1["score"] <= 100
        assert r1["ab"] == r2["ba"] and r1["ba"] == r2["ab"]


def test_fei_lands_where_star_sits():
    for a, b in _pairs(40, 3):
        rel = relation(a, b)
        where = {s["name"]: p["name"] for p in b["palaces"] for s in p["stars"]}
        assert len(rel["ab"]["fei"]) == 4
        for f in rel["ab"]["fei"]:
            assert where[f["star"]] == f["palace"]


def test_ming_kinds():
    assert ming_kinds("子", "丑") == ["六合"]
    assert ming_kinds("子", "午") == ["冲"]
    assert ming_kinds("申", "子") == ["三合"]
    assert set(ming_kinds("寅", "巳")) == {"刑", "害"}
    assert ming_kinds("子", "子") == []
