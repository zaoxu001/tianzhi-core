"""六壬取传与天将布位的回归测试，依据《六壬大全》（四库全书本）。

每条都带底本原文或课例出处。算法改了而与书对不上，这里会先报出来。
"""
from tianzhi_core.liuren import pan as L


def _chuan(gz, yue_jiang, zhan_shi):
    tdp = L.build_tian_di_pan(yue_jiang, zhan_shi)
    c = L.get_three_chuan(L.build_four_classes(gz[0], gz[1], tdp), tdp, gz[0], gz[1])
    return c["chu"] + c["zhong"] + c["mo"]


# 卷五伏吟课「杜傳」所列课例（伏吟：月将同占时）
FUYIN = {
    "壬辰": "亥辰戌", "壬午": "亥午子", "乙亥": "辰亥巳", "乙酉": "辰酉卯",
    "丁卯": "卯子午", "己卯": "卯子午", "辛卯": "卯子午",  # 子卯兩刑不復再傳，以子冲午為末傳
    "壬申": "亥申寅", "壬戌": "亥戌未", "壬子": "亥子卯", "壬寅": "亥寅巳",
    "乙丑": "辰丑戌", "乙未": "辰未丑", "乙巳": "辰巳申", "乙卯": "辰卯子",
    "丁酉": "酉未丑", "己酉": "酉未丑", "辛酉": "酉戌未",
    "丁亥": "亥未丑", "己亥": "亥未丑", "辛亥": "亥戌未",
    "癸巳": "丑戌未", "丙辰": "巳申寅", "丁丑": "丑戌未", "丁巳": "巳申寅", "丁未": "未丑戌",
}


def test_fuyin_dujuan_matches_daquan():
    for gz, want in FUYIN.items():
        assert _chuan(gz, "子", "子") == want, gz


# 卷五涉害课与订讹中的数克实例：(上神, 所临地盘宫, 是否下贼上, 书中重数)。临位不计，寄宫干计入。
SHEHAI_DEPTH = [
    ("亥", "丑", True, 5),   # 亥加丑前行歷辰戊未己戌土五重
    ("丑", "卯", True, 1),   # 丑加卯前行只歷辰中乙木一重
    ("辰", "寅", True, 1),   # 辰加寅卯木一重
    ("申", "午", True, 1),   # 申加午歷丁火一重
    ("午", "申", False, 2),  # 午加庚（寄申）金前行歷酉辛金二重
    ("戌", "子", False, 1),  # 戌加子水前行歷癸水一重
]


def test_shehai_depth_counts_like_daquan():
    for upper, gong, victim, want in SHEHAI_DEPTH:
        assert L._shehai_depth(upper, gong, victim) == want, (upper, gong)


# 课经诸卷的起例课：(日干支, 月将, 占时, 书中三传)
EXAMPLES = [
    ("丁卯", "亥", "丑", "亥酉未"),  # 涉害
    ("庚子", "申", "戌", "午辰寅"),  # 见机
    ("庚戌", "申", "辰", "辰申子"),  # 察微
    ("甲午", "午", "辰", "辰午申"),  # 缀瑕
    ("乙卯", "子", "寅", "亥酉未"),  # 比用
    ("戊寅", "午", "寅", "丑午酉"),  # 昴星；底本作「午時寅將」，与所列课式不合，按课式改正
]


def test_worked_examples():
    for gz, yj, zs, want in EXAMPLES:
        assert _chuan(gz, yj, zs) == want, (gz, yj, zs)


def test_palace_tian_jiang_follows_sky_branch():
    """天将乘天盘支。课式里每一宫的天将，须与三传所标的天将一致。"""
    r = L.qike(2026, 1, 1, 3, 0)  # 乙亥日 丑将加寅时，夜贵，贵人乘申
    palaces = r["plate"]["palaces"]
    for key in ("chu", "zhong", "mo"):
        t = r["three_chuan"][key]
        earth = next(z for z, p in palaces.items() if p["sky"] == t["zhi"])
        assert palaces[earth]["tian_jiang"] == t["tian_jiang"], key


def test_day_night_by_sunrise_sunset():
    """正时起课的昼夜贵人按当地日出日落分，不按卯酉定界。"""
    from tianzhi_core.calendar.solar_time import is_daytime
    from datetime import datetime
    # 北京夏至：寅时末（04:50）日已出，是昼；冬至：卯时初（06:30）日未出，仍是夜
    assert is_daytime(datetime(2026, 6, 21, 4, 50), 39.9, 116.4)
    assert not is_daytime(datetime(2026, 12, 21, 6, 30), 39.9, 116.4)
    # 春分酉时初（17:30）日未落，是昼；秋分后八月酉时末（18:50）日已落，是夜
    assert is_daytime(datetime(2026, 3, 20, 17, 30), 39.9, 116.4)
    assert not is_daytime(datetime(2026, 9, 25, 18, 50), 39.9, 116.4)
    # 起课：夏至寅时末用昼贵
    r = L.qike(2026, 6, 21, 4, 50)
    assert r["tian_jiang_is_day_time"] is True
    # 活时报数没有真实时刻，仍按占时支：寅属夜
    assert L.qike(2026, 6, 21, 4, 50, user_number=3)["tian_jiang_is_day_time"] is False


def test_plate_fixed_layout_and_sky_fields():
    """天地盘方阵：地盘固定通行方位，每宫的遁干、天将、空亡都跟天盘支走。
    2026-09-28 18:30 乙巳日酉时、月将辰（夜占），与他家排盘逐格对照：
    上排天盘 子丑寅卯（勾龙空虎、壬癸◎◎），左 亥戌（合雀、辛庚），右 辰巳（常玄、甲乙），
    下排 酉申未午（蛇贵后阴、己戊丁丙）"""
    plate = L.qike(2026, 9, 28, 18, 30)["plate"]
    assert plate["layout"] == {"top": ["巳", "午", "未", "申"], "right": ["酉", "戌"],
                               "bottom": ["寅", "丑", "子", "亥"], "left": ["辰", "卯"]}
    order = plate["layout"]["top"] + plate["layout"]["left"] + plate["layout"]["right"] + plate["layout"]["bottom"]
    got = [(plate["palaces"][z]["sky"], plate["palaces"][z]["tian_jiang_short"], plate["palaces"][z]["xun_gan"]) for z in order]
    assert got == [("子", "勾", "壬"), ("丑", "龙", "癸"), ("寅", "空", ""), ("卯", "虎", ""),
                   ("亥", "合", "辛"), ("戌", "雀", "庚"), ("辰", "常", "甲"), ("巳", "玄", "乙"),
                   ("酉", "蛇", "己"), ("申", "贵", "戊"), ("未", "后", "丁"), ("午", "阴", "丙")]
    assert {z for z, p in plate["palaces"].items() if p["is_kong"]} == {"未", "申"}   # 天盘寅卯空，压在未申上
