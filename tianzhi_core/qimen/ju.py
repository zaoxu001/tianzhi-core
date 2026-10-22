"""时家奇门定局：这一时辰属哪一节气、上中下哪一元、阴阳遁第几局。

═══ 所据 ═══
局数表：《協紀辨方書》卷三十五陽遁歌、隂遁歌（data/qimen_ju.json，经《遁甲演義》诸算例三十二处回核）。
三元：符头为甲己日，符头日支子午夘酉为上元、寅申巳亥为中元、辰戌丑未为下元，五日一元。
上元符头（甲子、己夘、甲午、己酉）每十五日一轮，一轮三元即一节气。

═══ 两法 ═══
method="zhirun"（默认）超神接气置闰：
  每个上元符头起一节气的三元，依次接续下一节气；符头在节前为超神，在节后为接气，同日为正授。
  超神日久，于芒种、大雪一节三元毕后重用该节三元一周，为置闰（《演義》「置閏定在芒種大雪之後」）。
  置闰之限默认「前远后近」（《協紀》按語：前之符首在節前八日、後之符首在節後七日，前逺後近則當置閏），
  以整日计即上元符头早于交节八日以上；《演義》丙戌年芒種之例（初一符頭、初九交節）正是八日即閏。
  rule="days9" 为今人软件（如元亨利贞网旧版、csp）所用的九日之限：两限在百年中约有一成日子给出不同的局，
  因为八日未闰者要再等半年至下一个芒种或大雪才闰，其间整条三元链错开一节。
  接气之时仍用前节之局待符头（《協紀》：「接氣又有拆局補局之法……不可從」）。
method="chaibu" 拆补：交节即换节气，元由当日符头定，永不置闰。今人软件常用，非《演義》《協紀》所主。

置闰法的局与历史有关（何时闰过），本模块自目标时刻前八年起逐节推演至目标：
置闰至多约三年一遇，推演起点若错开一节，过第一个闰即自动对齐，所以起点不影响结果。

═══ 时刻 ═══
入参为北京时间（naive 或带时区）；交节时刻取 calendar.jieqi（紫金山历书口径）。
日以子初（23:00）为界，与本包日柱默认（晚子时作次日）一致：「凡換竒皆子時換也」（《演義》卷一）。
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from functools import lru_cache

from ..calendar.jieqi import as_naive, jieqi_table
from ..core import ganzhi
from .pan import _table

__all__ = ["JIEQI", "ju_of", "day_ganzhi"]

_T2S = {"驚蟄": "惊蛰", "穀雨": "谷雨", "小滿": "小满", "芒種": "芒种", "處暑": "处暑"}
_S2T = {v: k for k, v in _T2S.items()}
#: 二十四节气，自冬至起
JIEQI: tuple[str, ...] = tuple(_T2S.get(n, n) for n in _table("ju")["order"])
_JU = {_T2S.get(k, k): v for k, v in _table("ju")["items"].items()}
_RUN_AT = {_T2S.get(n, n) for n in _table("sanyuan")["zhirun"]["at"]}
_YUAN = "上中下"
_DAY = timedelta(days=1)


def _qday(dt: datetime) -> date:
    """奇门之日：子初（23:00）起算新的一日"""
    return (dt + timedelta(hours=1)).date()


def day_ganzhi(d: date) -> str:
    """某日的日干支（儒略日数推算，与 bazi.chart 同法）"""
    return ganzhi.JIAZI[(d.toordinal() + 1721425 + 49) % 60]


def _day_start(d: date) -> datetime:
    return datetime(d.year, d.month, d.day) - timedelta(hours=1)


def _yuan_of_futou(gz: str) -> int:
    z = gz[1]
    return 0 if z in "子午卯酉" else 1 if z in "寅申巳亥" else 2


def _futou_day(d: date) -> date:
    """d 所属的符头日（最近一个不晚于 d 的甲或己日）"""
    i = ganzhi.JIAZI.index(day_ganzhi(d))
    return d - timedelta(days=i % 5)


@lru_cache(maxsize=64)
def _jieqi_axis(y0: int, y1: int) -> tuple[tuple[datetime, str], ...]:
    out = []
    for y in range(y0, y1 + 1):
        out.extend((t, n) for n, t in jieqi_table(y).items())
    return tuple(sorted(out))


def _ju(jq: str, yuan: int) -> tuple[str, int]:
    it = _JU[jq]
    return ("阳" if it["dun"] == "陽" else "阴"), it["ju"][yuan]


def _run_ok(rule: str, jie_t: datetime, f_start: datetime) -> bool:
    """上元符头之日到交节之日相距 n 日，后一符头距节即 15−n 日。
    前远后近 ⇔ n > 15−n ⇔ n ≥ 8（书中以整日计，不论时刻）；今人软件多取 n ≥ 9"""
    days = (_qday(jie_t) - _qday(f_start)).days
    if rule == "qian_yuan_hou_jin":
        return days >= 8
    if rule == "days9":
        return days >= 9
    raise ValueError(f"置闰之限只能是 qian_yuan_hou_jin / days9：{rule!r}")


def _chaibu(t: datetime, axis) -> dict:
    jt, jq = max((x for x in axis if x[0] <= t), key=lambda x: x[0])
    f = _futou_day(_qday(t))
    yuan = _yuan_of_futou(day_ganzhi(f))
    dun, ju = _ju(jq, yuan)
    return {"jieqi": jq, "jieqi_time": jt, "yuan": _YUAN[yuan], "dun": dun, "ju": ju,
            "futou": day_ganzhi(f), "futou_date": f, "mode": "拆补", "run": False}


def _zhirun(t: datetime, axis, rule: str) -> dict:
    td = _qday(t)
    # 推演起点：目标前约八年的一个上元符头（上元符头即日干支序号为 15 的倍数之日）
    d0 = td - timedelta(days=8 * 365)
    while ganzhi.JIAZI.index(day_ganzhi(d0)) % 15:
        d0 -= _DAY
    f = _day_start(d0)
    # 起点之节：交节时刻离符头最近者
    idx = min(range(len(axis)), key=lambda i: abs((axis[i][0] - f).total_seconds()))
    # 节在轴上的位置对应到二十四节气序
    run = False
    while True:
        nxt = f + timedelta(days=15)
        if nxt > t:
            break
        jt, jq = axis[idx]
        if not run and jq in _RUN_AT and _run_ok(rule, jt, f):
            run = True                          # 下一轮重用本节三元
        else:
            run = False
            idx += 1
        f = nxt
    jt, jq = axis[idx]
    yuan = int((t - f) / timedelta(days=5))
    dun, ju = _ju(jq, yuan)
    fd = _qday(f) + timedelta(days=5 * yuan)
    if run:
        mode = "置闰"
    elif _qday(jt) == _qday(f):
        mode = "正授"
    elif jt > f:
        mode = "超神"
    else:
        mode = "接气"
    return {"jieqi": jq, "jieqi_time": jt, "yuan": _YUAN[yuan], "dun": dun, "ju": ju,
            "futou": day_ganzhi(fd), "futou_date": fd, "shangyuan_date": _qday(f),
            "mode": mode, "run": run}


def ju_of(dt: datetime, *, method: str = "zhirun", rule: str = "qian_yuan_hou_jin") -> dict:
    """这一时刻的局。

    返回 jieqi（所用节气）、jieqi_time（该节气交节时刻）、yuan（上/中/下）、dun（阳/阴）、ju（1–9）、
    futou（本元符头日干支）、futou_date、mode（正授/超神/接气/置闰/拆补）、run（是否闰局）。
    置闰法另返回 shangyuan_date（本节上元符头之日）。
    """
    t = as_naive(dt)
    axis = tuple((tt, _T2S.get(n, n)) for tt, n in _jieqi_axis(t.year - 9, t.year + 1))
    if method == "chaibu":
        return _chaibu(t, axis)
    if method == "zhirun":
        return _zhirun(t, axis, rule)
    raise ValueError(f"method 只能是 zhirun 或 chaibu：{method!r}")
