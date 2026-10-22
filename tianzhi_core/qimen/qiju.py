"""起局：输入一个时刻，一步给出四柱、定局、九宫、成格、旬空、马星。"""
from __future__ import annotations

from datetime import datetime

from ..bazi.chart import build_chart
from ..calendar.jieqi import as_naive
from ..core import ganzhi
from .geju import find as find_geju
from .ju import ju_of
from .pan import build as build_pan

__all__ = ["qiju", "xun_kong", "ma_xing"]

#: 驿马：时支三合局之冲（申子辰马在寅……）
_MA = {"申": "寅", "子": "寅", "辰": "寅", "寅": "申", "午": "申", "戌": "申",
       "巳": "亥", "酉": "亥", "丑": "亥", "亥": "巳", "卯": "巳", "未": "巳"}
_ZHI_GONG = {"子": 1, "丑": 8, "寅": 8, "卯": 3, "辰": 4, "巳": 4, "午": 9, "未": 2, "申": 2, "酉": 7, "戌": 6, "亥": 6}


def xun_kong(gz: str) -> str:
    """旬空二支：本旬十干用尽所余之二支"""
    i = ganzhi.JIAZI.index(gz)
    start = ganzhi.ZHI.index(ganzhi.JIAZI[i - i % 10][1])
    return ganzhi.ZHI[(start + 10) % 12] + ganzhi.ZHI[(start + 11) % 12]


def ma_xing(gz: str) -> str:
    return _MA[gz[1]]


def qiju(dt: datetime, *, method: str = "zhirun", rule: str = "qian_yuan_hou_jin", pan_method: str = "zhuan",
         names: str = "default") -> dict:
    """为这一时刻起一局时家奇门。

    :param dt: 起局时刻，北京时间（naive 按东八区理解）。用真太阳时的话由调用方先换算好再传入。
    返回 {sizhu, ju, pan, geju, kong, ma, options}：
      sizhu  年月日时四柱（日以子初换，与本包八字默认一致）
      ju     定局结果（节气、元、遁、局、符头、正授/超神/接气/置闰）
      pan    九宫（见 pan.build）
      geju   成格（见 geju.find）
      kong   时旬空亡之二支及其所落之宫；ma 时支驿马及其宫
    """
    t = as_naive(dt)
    sz = build_chart(t).bazi.split()
    j = ju_of(t, method=method, rule=rule)
    p = build_pan(j["dun"] == "阳", j["ju"], sz[3], method=pan_method, names=names)
    kong = xun_kong(sz[3])
    ma = ma_xing(sz[3])
    return {
        "sizhu": {"year": sz[0], "month": sz[1], "day": sz[2], "hour": sz[3]},
        "ju": j,
        "pan": p,
        "geju": find_geju(p, day=sz[2], month=sz[1], year=sz[0]),
        "kong": {"zhi": kong, "gong": sorted({_ZHI_GONG[z] for z in kong})},
        "ma": {"zhi": ma, "gong": _ZHI_GONG[ma]},
        "options": {"method": method, "rule": rule, "pan_method": pan_method, "names": names},
    }
