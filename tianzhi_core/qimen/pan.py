"""时家奇门排盘：给定阴阳遁、局数与时干支，布地盘、天盘九星、八门、八神。

═══ 所据 ═══
规则表出自 tianzhi-classics qimen/（本包 data/qimen_*.json 为其逐字节副本）：
  地盘  《遁甲演義》卷三「竒遁佈局法」：本局之宫起甲子戊，陽遁順布六儀逆布三竒，隂遁反之；中五寄坤二。
  直符直使  同篇：「尋本時支落處加以直使，尋本時干落處加以直符」。直符为时旬之首所在宫之星，直使为其门；
        天禽当直符时直使用死门（卷一「時家竒門」：「甲辰在五天禽為直符死門為直使」）。
  九星八门  轉盤（默认，《遁甲演義》卷一「八門九星逐時移宫訣」移輪子）：九星、八门各沿外八宫整体转动，
        天禽随天芮（寄坤）。另备《協紀辨方書》卷三十五「九星飛布九宫，八門順轉八卦」（method="xieji_fei"）。
  八神  《遁甲演義》卷三「天乙直符吉凶神説」：直符、螣蛇、太隂、六合、白虎、玄武、九地、九天，
        自直符所临之宫起，陽遁順、隂遁逆。另一说白虎作勾陈、玄武作朱雀（names="gouchen"）。

两种盘式、两套八神名都有书可据，见 tianzhi-classics qimen/collation.json。
书中排盘算例四十八则见 qimen/examples.json，本包测试逐条回放。

═══ 方位 ═══
外八宫按顺时针（以坎在下、离在上的地图视角）排成环：坎1 艮8 震3 巽4 离9 坤2 兑7 乾6。
阳遁八神沿此环顺行，阴遁逆行（《演義》卷二人遁两例逐宫核过）。
"""
from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources

from ..core import ganzhi

__all__ = ["RING", "STARS", "DOORS", "SHEN", "SHEN_ALT", "Pan", "build", "dipan", "xun_of"]

# 繁简：规则表依原书用字，对外一律简体
T2S = {"天沖": "天冲", "天輔": "天辅", "開": "开", "傷": "伤", "驚": "惊", "太隂": "太阴", "𤣥武": "玄武",
       "勾陳": "勾陈", "螣蛇": "螣蛇", "隂": "阴", "陽": "阳", "離": "离", "兑": "兑"}


def _s(x: str) -> str:
    return T2S.get(x, x)


@lru_cache(maxsize=None)
def _table(name: str) -> dict:
    with resources.files("tianzhi_core.data").joinpath(f"qimen_{name}.json").open(encoding="utf-8") as f:
        return json.load(f)


def _palaces() -> dict[int, dict]:
    return {int(g): v for g, v in _table("jiugong")["palaces"].items()}


#: 外八宫顺时针环
RING: tuple[int, ...] = (1, 8, 3, 4, 9, 2, 7, 6)
#: 宫 → 本宫之星 / 本宫之门
STARS: dict[int, str] = {g: _s(v["star"]) for g, v in _palaces().items()}
DOORS: dict[int, str] = {g: _s(v["door"]) for g, v in _palaces().items() if v["door"]}
SHEN: tuple[str, ...] = tuple(_s(x) for x in _table("buju")["shen"]["default"])
SHEN_ALT: tuple[str, ...] = tuple(_s(x) for x in _table("buju")["shen"]["alt"])
#: 六仪：旬首 → 所隐之仪；布地盘的干序
LIUYI: dict[str, str] = _table("buju")["liuyi"]
ORDER: tuple[str, ...] = tuple(_table("buju")["order"])
JI = 2   # 中五寄坤二

_STAR_HOME = {v: k for k, v in STARS.items()}
_DOOR_HOME = {v: k for k, v in DOORS.items()}


def _step(g: int, n: int) -> int:
    """九宫数顺数 n 步（负为逆），1..9 循环"""
    return (g - 1 + n) % 9 + 1


def _ring_shift(g: int, n: int) -> int:
    """外八宫环上走 n 步；中五按寄宫处理"""
    g = JI if g == 5 else g
    return RING[(RING.index(g) + n) % 8]


def _ring_dist(a: int, b: int) -> int:
    a, b = (JI if a == 5 else a), (JI if b == 5 else b)
    return (RING.index(b) - RING.index(a)) % 8


def dipan(yang: bool, ju: int) -> dict[int, str]:
    """地盘：宫 → 干。本局之宫起戊，阳遁按宫数顺布、阴遁逆布，干序戊己庚辛壬癸丁丙乙"""
    return {_step(ju, i if yang else -i): gan for i, gan in enumerate(ORDER)}


def xun_of(gz: str) -> tuple[str, str]:
    """干支所在之旬：(旬首如「甲子」, 所隐之仪如「戊」)"""
    i = ganzhi.JIAZI.index(gz)
    head = ganzhi.JIAZI[i - i % 10]
    return head, LIUYI[head]


def _gan_on_pan(gan: str, gz: str) -> str:
    """盘上找干：甲不见于盘，以其旬首所隐之仪当之"""
    return xun_of(gz)[1] if gan == "甲" else gan


class Pan(dict):
    """排盘结果。键：dun, ju, hour, xun, xun_yi, zhifu, zhishi, zhifu_gong, zhishi_gong, method, palaces。
    palaces：宫数(1..9) → {di: [干], tian: [干], star: 星|None, stars: [星], door: 门|None, shen: 神|None}。
    中五地盘之干寄坤二，tian/di 两处都列出（di 里中五之干同时记在五宫与二宫）。"""


def build(yang: bool, ju: int, hour_gz: str, *, method: str = "zhuan", names: str = "default") -> Pan:
    """排一个时辰的盘。

    :param yang: 阳遁为 True
    :param ju: 局数 1..9
    :param hour_gz: 时干支，如「丙寅」
    :param method: "zhuan" 转盘（默认，《演義》）/ "xieji_fei" 九星飞布八门转（《協紀》）
    :param names: 八神名号，"default" 白虎玄武 / "gouchen" 勾陈朱雀
    """
    if method not in ("zhuan", "xieji_fei"):
        raise ValueError(f"method 只能是 zhuan 或 xieji_fei：{method!r}")
    if not 1 <= ju <= 9:
        raise ValueError(f"局数应为 1–9：{ju}")
    di = dipan(yang, ju)
    where = {g: p for p, g in di.items()}           # 干 → 地盘宫
    head, yi = xun_of(hour_gz)
    fu_home = where[yi]                              # 旬首之仪所在宫
    zhifu = STARS[fu_home]                           # 中五即天禽
    zhishi = DOORS[JI] if fu_home == 5 else DOORS[fu_home]
    hour_gan = _gan_on_pan(hour_gz[0], hour_gz)
    target = where[hour_gan]                         # 直符所加：时干落处
    # 直使：自旬首宫按九宫数数到时支，阳顺阴逆
    n = ganzhi.JIAZI.index(hour_gz) - ganzhi.JIAZI.index(head)
    door_at = _step(fu_home, n if yang else -n)

    pal = {g: {"di": [di[g]] + ([di[5]] if g == JI else []), "tian": [], "stars": [], "star": None, "door": None, "shen": None}
           for g in range(1, 10)}
    pal[5]["di"] = [di[5]]

    # —— 九星与天盘干 ——
    if method == "zhuan":
        shift = _ring_dist(fu_home, target)
        for home, star in STARS.items():
            if home == 5:
                continue
            to = _ring_shift(home, shift)
            pal[to]["stars"].append(star)
            pal[to]["tian"].append(di[home])
            if home == JI:                          # 天禽随天芮
                pal[to]["stars"].append(STARS[5])
                pal[to]["tian"].append(di[5])
    else:
        off = target - fu_home
        for home, star in STARS.items():
            to = _step(home, off)
            pal[to]["stars"].append(star)
            pal[to]["tian"].append(di[home])

    # —— 八门 ——
    dshift = _ring_dist(_DOOR_HOME[zhishi], door_at)
    for home, door in DOORS.items():
        pal[_ring_shift(home, dshift)]["door"] = door

    # —— 八神 ——
    shen = SHEN_ALT if names == "gouchen" else SHEN
    fu_at = next(g for g, p in pal.items() if zhifu in p["stars"])
    fu_at = JI if fu_at == 5 else fu_at
    for i, name in enumerate(shen):
        pal[_ring_shift(fu_at, i if yang else -i)]["shen"] = name

    for p in pal.values():
        p["star"] = p["stars"][0] if p["stars"] else None
    return Pan(dun="阳" if yang else "阴", ju=ju, hour=hour_gz, xun=head, xun_yi=yi, zhifu=zhifu, zhishi=zhishi,
               zhifu_gong=fu_at if method == "zhuan" else next(g for g, p in pal.items() if zhifu in p["stars"]),
               zhishi_gong=JI if door_at == 5 else door_at, method=method, names=names, palaces=pal)
