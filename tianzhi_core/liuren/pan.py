"""大六壬起课。

给定时刻，排出月将、天地盘、四课、九宗门三传、十二天将、旬空、遁干、六亲与神煞。

底本：《六壬大全》（四库全书本）——卷一入手法与九宗门、卷二十二神与十二天将、卷五至卷八课经。
课经诸卷的起例课 48 个已逐一核对三传（tests/test_liuren.py）。底本来历、核对经过与校勘记
见 tianzhi-classics：catalog.json 与 liuren/collation.json。

本模块自天秩网站迁入，与网站同一份取传逻辑。
"""
from datetime import datetime

from lunar_python import Solar

from ..calendar.solar_time import is_daytime
from lunar_python.util import LunarUtil

# ============================================================
# 基础常量
# ============================================================
ZHI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
GAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]

# 日干寄宫（六壬日干转地盘位）
GAN_JIGONG = {
    "甲": "寅", "乙": "辰", "丙": "巳", "丁": "未", "戊": "巳",
    "己": "未", "庚": "申", "辛": "戌", "壬": "亥", "癸": "丑",
}

# 五行
WUXING_GAN = {
    "甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土",
    "己": "土", "庚": "金", "辛": "金", "壬": "水", "癸": "水",
}
WUXING_ZHI = {
    "子": "水", "丑": "土", "寅": "木", "卯": "木", "辰": "土", "巳": "火",
    "午": "火", "未": "土", "申": "金", "酉": "金", "戌": "土", "亥": "水",
}

# 五行相克
KE = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}

# 十二天将（顺序：贵-蛇-朱-合-勾-龙-空-虎-常-武-阴-后）
TIAN_JIANG = ["贵人", "腾蛇", "朱雀", "六合", "勾陈", "青龙",
              "天空", "白虎", "太常", "玄武", "太阴", "天后"]
TIAN_JIANG_SHORT = {
    "贵人": "贵", "腾蛇": "蛇", "朱雀": "雀", "六合": "合", "勾陈": "勾",
    "青龙": "龙", "天空": "空", "白虎": "虎", "太常": "常", "玄武": "玄",
    "太阴": "阴", "天后": "后",
}

# 贵人（昼贵 / 夜贵）。按常见六壬排盘口径：
# 甲戊庚牛羊，乙己鼠猴，丙丁猪鸡，壬癸蛇兔，辛马虎。
GUI_REN = {
    "甲": ("丑", "未"), "戊": ("丑", "未"), "庚": ("丑", "未"),
    "乙": ("子", "申"), "己": ("子", "申"),
    "丙": ("亥", "酉"), "丁": ("亥", "酉"),
    "壬": ("巳", "卯"), "癸": ("巳", "卯"),
    "辛": ("午", "寅"),
}

# 卯辰巳午未申为昼，酉戌亥子丑寅为夜。
DAY_ZHI = {"卯", "辰", "巳", "午", "未", "申"}

# 中气与月将（雨水起 → 月将亥）
# 按口诀：雨水后用亥将，春分后戌，谷雨后酉，小满后申，夏至后未，大暑后午，
#        处暑后巳，秋分后辰，霜降后卯，小雪后寅，冬至后丑，大寒后子。
ZHONGQI_YUE_JIANG = [
    ("雨水", "亥"), ("春分", "戌"), ("谷雨", "酉"), ("小满", "申"),
    ("夏至", "未"), ("大暑", "午"), ("处暑", "巳"), ("秋分", "辰"),
    ("霜降", "卯"), ("小雪", "寅"), ("冬至", "丑"), ("大寒", "子"),
]

# 六十甲子顺序
JIA_ZI = LunarUtil.JIA_ZI  # 60 个


# ============================================================
# 工具函数
# ============================================================
def zhi_idx(z: str) -> int:
    return ZHI.index(z)


def add_zhi(z: str, n: int) -> str:
    return ZHI[(zhi_idx(z) + n) % 12]


def ke_relation(a: str, b: str) -> str:
    """返回 a 对 b 的五行关系：克/被克/同/生/被生"""
    wa = WUXING_GAN.get(a) or WUXING_ZHI.get(a)
    wb = WUXING_GAN.get(b) or WUXING_ZHI.get(b)
    if not wa or not wb:
        return "无"
    if wa == wb:
        return "同"
    if KE.get(wa) == wb:
        return "克"
    if KE.get(wb) == wa:
        return "被克"
    SHENG = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
    if SHENG.get(wa) == wb:
        return "生"
    if SHENG.get(wb) == wa:
        return "被生"
    return "无"


def is_day_time(hour: int) -> bool:
    """简化昼夜判定：卯辰巳午未申(5-17 时)为昼，其余为夜"""
    return 5 <= hour < 17


def is_day_zhi(zhi: str) -> bool:
    return zhi in DAY_ZHI


def get_yue_jiang(year: int, month: int, day: int, hour: int = 12) -> str:
    """根据公历日期推月将（按中气精确时间换将）。"""
    target = datetime(year, month, day, hour)
    solar = Solar.fromYmd(year, month, day)
    lunar = solar.getLunar()
    jq_table = lunar.getJieQiTable()  # dict: 节气名 -> Solar

    # 收集已发生的中气，取最近一个
    last = None
    for name, target_zhi in ZHONGQI_YUE_JIANG:
        if name in jq_table:
            jq_solar = jq_table[name]
            jq_dt = datetime(
                jq_solar.getYear(), jq_solar.getMonth(), jq_solar.getDay(),
                jq_solar.getHour(), jq_solar.getMinute(),
            )
            if jq_dt <= target:
                if last is None or jq_dt > last[1]:
                    last = (target_zhi, jq_dt)

    if last:
        return last[0]

    # fallback：用上一年的大寒（月将子）
    return "子"


# ============================================================
# 盘面方阵布局：以「占时的六合支」为左上起手（对齐权威排盘的动态画法：每换占时起手位随之变）。
# 12 支按顺时针铺成 4×4 边框：顶 4、右 2、底 4（左→右展示是顺时针的反向）、左 2（上→下展示是顺时针的反向）。
# ============================================================
# 天地盘方阵：地盘固定在通行方位——上巳午未申、右酉戌、下亥子丑寅、左卯辰。
# 下排、左列按画面从左到右、从上到下列出。格内写的是压在该地盘位上的天盘支
PLATE_LAYOUT = {
    "top": ["巳", "午", "未", "申"],
    "right": ["酉", "戌"],
    "bottom": ["寅", "丑", "子", "亥"],
    "left": ["辰", "卯"],
}


def build_palaces(tdp: dict, tj_map: dict, day_ganzhi: str, xun_kong, shen_sha) -> dict:
    """天地盘十二宫，键是地盘支。每宫除 earth 外各项都说的是压在上面的天盘支：遁干、天将、
    六亲、神煞、空亡都随天盘支走，与三传所标同一口径。天将尤其如此——贵人乘天盘上的贵人支、
    其余依次布开，《六壬大全》课经诸例三传所标天将，按天盘支查 45 例合 42，按地盘支查只合 3。
    tj_map 为 {天盘支: 天将}，shen_sha 为 [{name, zhi}]"""
    day_gan = day_ganzhi[0]
    by_zhi = {}
    for item in shen_sha or []:
        by_zhi.setdefault(item["zhi"], []).append(item["name"])
    out = {}
    for z in ZHI:
        sky = tdp.get(z, "")
        jiang = tj_map.get(sky, "")
        out[z] = {
            "earth": z,
            "sky": sky,
            "xun_gan": get_xun_dun_gan(day_ganzhi, sky),
            "tian_jiang": jiang,
            "tian_jiang_short": TIAN_JIANG_SHORT.get(jiang, ""),
            "liu_qin": liu_qin(sky, day_gan),
            "shen_sha": by_zhi.get(sky, []),
            "is_kong": sky in (xun_kong or []),
        }
    return out


def refresh_plate(ke: dict) -> dict:
    """按当前口径重建一课的盘面布局与十二宫，只用课里自带的天地盘、天将表、日干支、旬空、神煞，
    不重新起课。给旧版本存下来的课用：老课的布局随占时转、遁干按地盘取。原地更新并返回 ke"""
    tdp, tj = ke.get("tian_di_pan"), ke.get("tian_jiang_map")
    day_gz = (ke.get("ganzhi") or {}).get("day") or (ke.get("day_gan", "") + ke.get("day_zhi", ""))
    if not (tdp and tj and len(day_gz) == 2):
        return ke
    plate = ke.setdefault("plate", {})
    plate["layout"] = PLATE_LAYOUT
    plate["palaces"] = build_palaces(tdp, tj, day_gz, ke.get("xun_kong"), ke.get("shen_sha"))
    return ke


# ============================================================
# 月将加占时 -> 天地盘
# ============================================================
def build_tian_di_pan(yue_jiang: str, zhan_shi: str) -> dict:
    """月将加占时：天盘的「月将字」落在地盘的「占时位」上。
    返回 { 地盘地支: 该位上的天盘地支 }
    """
    offset = zhi_idx(yue_jiang) - zhi_idx(zhan_shi)
    return {ZHI[z]: ZHI[(z + offset) % 12] for z in range(12)}


# ============================================================
# 四课
# ============================================================
def build_four_classes(day_gan: str, day_zhi: str, tdp: dict) -> list[dict]:
    """
    四课（从第一课到第四课）
    一课（干上神）：以日干寄宫取上神；课内下神仍为日干本身
    二课（干阳神）：下 = 一课的上字（视为地盘字），上 = 该位的天盘字
    三课（支上神）：下 = 日支，上 = 日支位的天盘字
    四课（支阳神）：下 = 三课的上字，上 = 该位的天盘字
    """
    jigong = GAN_JIGONG[day_gan]

    one_up = tdp[jigong]
    two_up = tdp[one_up]
    three_up = tdp[day_zhi]
    four_up = tdp[three_up]

    return [
        {
            "idx": 1,
            "up": one_up,
            "down": day_gan,
            "down_show": day_gan,
            "down_position": jigong,
        },
        {"idx": 2, "up": two_up, "down": one_up, "down_show": one_up},
        {"idx": 3, "up": three_up, "down": day_zhi, "down_show": day_zhi},
        {"idx": 4, "up": four_up, "down": three_up, "down_show": three_up},
    ]


# ============================================================
# 三传（九宗门起法）
# 简化实现：贼克 → 比用 → 涉害 → 遥克 → 昴星 → 别责 → 八专 → 伏吟 → 返吟
# 篇幅大，先实现常用前 4 法，其余以"暂归贼克/遥克"兜底
# ============================================================
def _has_ke(upper: str, lower: str) -> bool:
    return KE.get(WUXING_ZHI.get(upper) or WUXING_GAN.get(upper)) == (
        WUXING_ZHI.get(lower) or WUXING_GAN.get(lower)
    )


# 干五合（别责课取干合寄宫上神用）
GAN_HE = {"甲": "己", "己": "甲", "乙": "庚", "庚": "乙", "丙": "辛",
          "辛": "丙", "丁": "壬", "壬": "丁", "戊": "癸", "癸": "戊"}

# 三刑（伏吟课迤逦取刑用；辰午酉亥自刑）
ZHI_XING = {"子": "卯", "卯": "子", "丑": "戌", "戌": "未", "未": "丑",
            "寅": "巳", "巳": "申", "申": "寅",
            "辰": "辰", "午": "午", "酉": "酉", "亥": "亥"}

# 三合局顺行次一位（别责课阴日"支前三合"用：申子辰、寅午戌、巳酉丑、亥卯未）
SAN_HE_NEXT = {"申": "子", "子": "辰", "辰": "申", "寅": "午", "午": "戌", "戌": "寅",
               "巳": "酉", "酉": "丑", "丑": "巳", "亥": "卯", "卯": "未", "未": "亥"}

# 涉害数克：各地盘宫所含计克项 = 地盘支本身 + 该宫所寄之干（十干寄宫，子午卯酉无寄干）。
# 口径照《六壬大全》卷五课经：自所临之宫「前行」数至本家，临位与本家都不计。书中七处实例一致，
# 如「丑加卯前行只歷辰中乙木一重」——卯本身是木、会克丑，书里不算；「亥加丑前行歷辰戊未己戌五重」，
# 也不算丑。寄宫干要算（「辰中乙木」「戊」「己」「辛」「丁」「癸」俱在数内）。
#
# 另一家《大六壬指南》根本不数深浅：「涉害取法，只以孟仲季为准，不以涉害深浅为义」。
# 这里不取，原因见 tianzhi-classics 的校勘记。此前的注释称本数法出自《指南》且连临位一并计，两处都不对。
GONG_KE_ITEMS = {z: [z] for z in ZHI}
for _g, _gong in GAN_JIGONG.items():
    GONG_KE_ITEMS[_gong].append(_g)

MENG_ZHI = {"寅", "申", "巳", "亥"}   # 四孟
ZHONG_ZHI = {"子", "午", "卯", "酉"}  # 四仲


def _is_yang_day(day_gan: str) -> bool:
    return GAN.index(day_gan) % 2 == 0  # 甲丙戊庚壬 阳


def _course_gong(c: dict) -> str:
    """该课上神所临的地盘宫（一课为日干寄宫，余课即下神）"""
    return c.get("down_position") or c["down"]


def _shehai_depth(upper: str, gong: str, upper_is_victim: bool) -> int:
    """涉害深浅（《六壬大全》卷五课经口径）：候选上神自所临地盘宫的下一宫起顺行，
    涉归本家（临位、本家都不计），沿途各宫以"支 + 寄宫干"逐项计克。
    下贼上候选数地盘克我之重数（upper_is_victim=True），上克下候选数我克地盘之重数。
    受克/所克多者为深。"""
    w = WUXING_ZHI[upper]
    steps = (zhi_idx(upper) - zhi_idx(gong)) % 12
    depth = 0
    for i in range(1, steps):
        for item in GONG_KE_ITEMS[add_zhi(gong, i)]:
            iw = WUXING_GAN.get(item) or WUXING_ZHI[item]
            if upper_is_victim:
                if KE.get(iw) == w:
                    depth += 1
            elif KE.get(w) == iw:
                depth += 1
    return depth


def _select_by_ke(classes: list[dict], day_gan: str) -> tuple[str, str, str] | None:
    """贼克 → 比用 → 涉害 的发用选择。返回 (初传, 法名, 格)；四课无上下克返回 None。
    格照《六壬大全》课经的名目：元首、重审、知一、涉害、见机、察微、缀瑕。

    古法口径：
      - "贼" = 下克上（重审课），"克" = 上克下（元首课），有贼先取贼。
      - 多贼/多克 → 比用：取与日干俱比（阴阳同）者，独比则用。
      - 俱比/俱不比 → 涉害：取涉害最深者；深浅相等取临四孟者，
        再等取临四仲者，复等则刚日用干上神、柔日用支上神。
    """
    zei, ke = [], []
    for c in classes:
        if _has_ke(c["down"], c["up"]):
            zei.append(c)
        elif _has_ke(c["up"], c["down"]):
            ke.append(c)
    primary = zei if zei else ke
    # 同一神重复之课（如一四课全同）只算一个候选
    seen, uniq = set(), []
    for c in primary:
        if c["up"] not in seen:
            seen.add(c["up"])
            uniq.append(c)
    if not uniq:
        return None
    if len(uniq) == 1:
        return uniq[0]["up"], "贼克", ("重审" if zei else "元首")

    # 比用
    day_yang = _is_yang_day(day_gan)
    same = [c for c in uniq if (zhi_idx(c["up"]) % 2 == 0) == day_yang]
    if len(same) == 1:
        return same[0]["up"], "比用", "知一"

    # 涉害：贼候选数受克于地盘，克候选数所克之地盘
    pool = same or uniq
    is_victim = bool(zei)
    depths = [(_shehai_depth(c["up"], _course_gong(c), is_victim), c) for c in pool]
    max_d = max(d for d, _ in depths)
    tied = [c for d, c in depths if d == max_d]
    if len(tied) == 1:
        return tied[0]["up"], "涉害", "涉害"
    # 见机：深浅相等取临四孟者；孟上不止一个则直接复等（缀瑕例：俱孟相等不取仲）
    meng = [c for c in tied if _course_gong(c) in MENG_ZHI]
    if len(meng) == 1:
        return meng[0]["up"], "涉害", "见机"
    if not meng:
        # 察微：无孟上者取临四仲者
        zhong = [c for c in tied if _course_gong(c) in ZHONG_ZHI]
        if len(zhong) == 1:
            return zhong[0]["up"], "涉害", "察微"
    # 缀瑕（复等）：刚日用干上神，柔日用支上神
    chu = classes[0]["up"] if day_yang else classes[2]["up"]
    return chu, "涉害", "缀瑕"


def _fuyin_chuan(classes: list[dict], day_gan: str) -> dict:
    """伏吟课取传：有克还将克发用，无克刚日用干上、柔日用支上；
    中末迤逦取刑；发用自刑则中传颠倒取另一上神；中传又自刑则末传取冲。"""
    gan_up, zhi_up = classes[0]["up"], classes[2]["up"]
    yang = _is_yang_day(day_gan)
    picked = _select_by_ke(classes, day_gan)
    if picked:
        chu = picked[0]
    else:
        chu = gan_up if yang else zhi_up
    # 卷五：伏吟无克，刚日自任、柔日自信。传行杜塞者为杜传：发用自刑，或初传所刑之神又刑回初传
    # （「丁卯己卯辛卯日卯子午……子卯兩刑不復再傳」，书中列在杜传之下）
    stuck = ZHI_XING[chu] == chu or ZHI_XING[ZHI_XING[chu]] == chu
    ge = "杜传" if stuck else ("伏吟" if picked else ("自任" if yang else "自信"))
    if ZHI_XING[chu] != chu:
        zhong = ZHI_XING[chu]
    else:
        # 发用自刑：干上发用取支上神为中传，支上发用取干上神
        zhong = zhi_up if chu == gan_up else gan_up
    # 末传：中传所刑。中传自刑，或刑回初传（子卯互刑），都不再传，改取中传之冲。
    # 《六壬大全》卷五：「丁卯己卯辛卯日卯子午……子卯兩刑不復再傳，以子冲午為末傳」
    if ZHI_XING[zhong] != zhong and ZHI_XING[zhong] != chu:
        mo = ZHI_XING[zhong]
    else:
        mo = add_zhi(zhong, 6)
    return {"method": "伏吟", "ge": ge, "chu": chu, "zhong": zhong, "mo": mo}


def get_three_chuan(classes: list[dict], tdp: dict, day_gan: str, day_zhi: str) -> dict:
    """九宗门取三传：返回 {method, chu, zhong, mo}。

    取课顺序：伏吟/返吟（盘面特例优先）→ 贼克/比用/涉害 → 无克时
    八专（两课）→ 遥克 → 别责（三课备，无遥无克）→ 昴星（四课全备）。
    """
    gan_up, zhi_up = classes[0]["up"], classes[2]["up"]
    yang = _is_yang_day(day_gan)

    # ---------- 伏吟（天地盘相同） ----------
    if all(tdp[z] == z for z in ZHI):
        return _fuyin_chuan(classes, day_gan)

    # ---------- 返吟（天地盘对冲） ----------
    if all(tdp[z] == add_zhi(z, 6) for z in ZHI):
        picked = _select_by_ke(classes, day_gan)
        if picked:
            chu = picked[0]
            return {"method": "返吟", "ge": "无依", "chu": chu,
                    "zhong": tdp.get(chu, chu), "mo": chu}
        # 无克（丁丑己丑辛丑丁未己未辛未六日）：初传取日支驿马，中支上神，末干上神。卷五名井栏射
        return {"method": "返吟", "ge": "井栏射", "chu": day_ma(day_zhi), "zhong": zhi_up, "mo": gan_up}

    # ---------- 1. 贼克 / 比用 / 涉害 ----------
    picked = _select_by_ke(classes, day_gan)
    if picked:
        chu, method, ge = picked
        return {**_finish_chuan(chu, tdp, method, classes, day_gan, day_zhi), "ge": ge}

    # 四课备数：两课=八专日，三课=别责候选，四课=昴星候选
    distinct = {(c["up"], _course_gong(c)) for c in classes}

    # ---------- 2. 八专法 ----------
    # 干支同位（甲寅、丁未、己未、庚申、癸丑），四课只有两课。
    # 无贼克时直接用八专取传，不再看遥克（课经"两课无克号八专"，
    # 与别责"无遥无克"不同，八专不考虑遥克）：
    #   阳日：干上神顺数三位（含本位）为初传
    #   阴日：第四课上神逆数三位（含本位）为初传
    #   中传、末传均为干上神
    if len(distinct) == 2:
        chu = add_zhi(gan_up, 2) if yang else add_zhi(classes[3]["up"], -2)
        return {"method": "八专", "ge": "八专", "chu": chu, "zhong": gan_up, "mo": gan_up}

    # ---------- 3. 遥克法 ----------
    # 四课上下不克，看四上神与日干遥克：先取上神克日（蒿矢），
    # 无则取日克上神（弹射）；多者取与日干俱比（阴阳同）者。
    for rel_key in ("克", "被克"):
        cands, seen = [], set()
        for c in classes:
            if ke_relation(c["up"], day_gan) == rel_key and c["up"] not in seen:
                seen.add(c["up"])
                cands.append(c["up"])
        if cands:
            if len(cands) > 1:
                same = [z for z in cands if (zhi_idx(z) % 2 == 0) == yang]
                cands = same or cands
            # 卷五：上神克日为蒿矢，日克上神为弹射
            return {**_finish_chuan(cands[0], tdp, "遥克", classes, day_gan, day_zhi),
                    "ge": "蒿矢" if rel_key == "克" else "弹射"}

    # ---------- 4. 别责法 ----------
    # 四课不全三课备，无遥无克：刚日取干合之干寄宫上神为初传，
    # 柔日取日支三合局顺行次一位；中末传均用干上神。
    if len(distinct) == 3:
        if yang:
            chu = tdp.get(GAN_JIGONG[GAN_HE[day_gan]], "")
        else:
            chu = SAN_HE_NEXT[day_zhi]
        return {"method": "别责", "ge": "别责", "chu": chu, "zhong": gan_up, "mo": gan_up}

    # ---------- 5. 昴星法 ----------
    # 四课全备无克无遥：刚日仰取地盘酉宫上神为初传，中传支上神，末传干上神（虎视）；
    # 柔日俯取天盘酉所临地盘之辰为初传，中传干上神，末传支上神（冬蛇掩目）。
    if yang:
        chu = tdp.get("酉", "酉")
        return {"method": "昴星", "ge": "虎视", "chu": chu, "zhong": zhi_up, "mo": gan_up}
    chu = next((e for e in ZHI if tdp.get(e) == "酉"), "酉")
    return {"method": "昴星", "ge": "冬蛇掩目", "chu": chu, "zhong": gan_up, "mo": zhi_up}


def _finish_chuan(chu: str, tdp: dict, method: str, classes: list, day_gan: str, day_zhi: str) -> dict:
    """常规取传：中传 = 初传地盘位上的天盘字，末传 = 中传地盘位上的天盘字。
    （伏吟/返吟/八专/别责/昴星各有专门取传，不走此链。）"""
    zhong = tdp.get(chu, chu)
    mo = tdp.get(zhong, zhong)
    return {"method": method, "chu": chu, "zhong": zhong, "mo": mo}


# ============================================================
# 十二天将（按贵人 + 顺逆布在地盘上）
# ============================================================
def get_gui_ren_position(day_gan: str, is_day: bool) -> str:
    day_gui, night_gui = GUI_REN[day_gan]
    return day_gui if is_day else night_gui


def build_tian_jiang_map(day_gan: str, is_day: bool, tdp: dict) -> dict:
    """
    返回 { 天盘支: 天将名 }——天将乘天盘支。要画到盘上，得再看这个天盘支压在哪个地盘位。

    古法："贵神临天门顺布、临地户逆布"：
      - 贵人乘天盘上的贵人支（按日干+昼夜口诀），其余天将沿天盘支依次布开
      - 顺逆判定 = 把贵人字当成天盘字反查：它落在地盘哪一位
          · 落 亥/子/丑/寅/卯/辰（天门六阴）→ 顺布
          · 落 巳/午/未/申/酉/戌（地户六阳）→ 逆布
    这与"按贵人本身地盘位判顺逆"是两套截然不同的口径，本实现走前者，
    与主流大六壬排盘软件一致。
    """
    gui_zhi = get_gui_ren_position(day_gan, is_day)
    # 反查"贵人字"作为天盘字时所落的地盘位
    gui_sky_loc = next(earth for earth, sky in tdp.items() if sky == gui_zhi)
    reverse = gui_sky_loc in {"巳", "午", "未", "申", "酉", "戌"}
    step = -1 if reverse else 1
    sky_order = [add_zhi(gui_zhi, i * step) for i in range(12)]
    return dict(zip(sky_order, TIAN_JIANG))


def get_tian_jiang_day_flag(hour_zhi: str) -> bool:
    """天将用昼贵还是夜贵。活时起课时传入活时地支，正时起课时传入真实时支。"""
    return is_day_zhi(hour_zhi)


# ============================================================
# 旬空
# ============================================================
def get_xun_kong(day_ganzhi: str) -> list[str]:
    """根据日干支返回旬空二支"""
    idx = JIA_ZI.index(day_ganzhi)
    xun_start = (idx // 10) * 10  # 旬首在第 0/10/20/30/40/50 位
    # 该旬涵盖 10 个干支，未涉及的两个地支为旬空
    zhi_used = set()
    for j in range(10):
        gz = JIA_ZI[xun_start + j]
        zhi_used.add(gz[1])
    return [z for z in ZHI if z not in zhi_used]


def get_xun_shou(day_ganzhi: str) -> str:
    idx = JIA_ZI.index(day_ganzhi)
    xun_start = (idx // 10) * 10
    return JIA_ZI[xun_start]


def get_xun_dun_gan(day_ganzhi: str, zhi: str) -> str:
    """按日旬取该支的旬遁天干；旬空支无遁干。"""
    idx = JIA_ZI.index(day_ganzhi)
    xun_start = (idx // 10) * 10
    for j in range(10):
        gz = JIA_ZI[xun_start + j]
        if gz[1] == zhi:
            return gz[0]
    return ""


# ============================================================
# 六亲
# ============================================================
SHISHEN_TO_LIUQIN = {
    "比肩": "兄", "劫财": "兄",
    "食神": "孙", "伤官": "孙",
    "偏财": "财", "正财": "财",
    "七杀": "官", "正官": "官",
    "偏印": "父", "正印": "父",
}


DAY_LU = {
    "甲": "寅", "乙": "卯", "丙": "巳", "丁": "午", "戊": "巳",
    "己": "午", "庚": "申", "辛": "酉", "壬": "亥", "癸": "子",
}

DAY_DE = {
    "甲": "寅", "己": "寅",
    "乙": "申", "庚": "申",
    "丙": "巳", "辛": "巳",
    "丁": "亥", "壬": "亥",
    "戊": "巳", "癸": "巳",
}

DAY_MA_GROUPS = [
    ({"申", "子", "辰"}, "寅"),
    ({"寅", "午", "戌"}, "申"),
    ({"巳", "酉", "丑"}, "亥"),
    ({"亥", "卯", "未"}, "巳"),
]

TIAN_MA_BY_MONTH_ZHI = {
    "寅": "午", "卯": "申", "辰": "戌", "巳": "子",
    "午": "寅", "未": "辰", "申": "午", "酉": "申",
    "戌": "戌", "亥": "子", "子": "寅", "丑": "辰",
}

RELATION_LAYERS = [
    {
        "name": "天干寄宫",
        "items": [f"{gan}{zhi}" for gan, zhi in GAN_JIGONG.items()],
    },
    {
        "name": "三合",
        "items": ["申子辰水", "亥卯未木", "寅午戌火", "巳酉丑金"],
    },
    {
        "name": "刑",
        "items": ["子卯", "寅巳申", "丑未戌", "辰午酉亥"],
    },
    {
        "name": "害",
        "items": ["子未", "丑午", "寅巳", "卯辰", "申亥", "酉戌"],
    },
    {
        "name": "破",
        "items": ["子酉", "丑辰", "寅亥", "卯午", "巳申", "未戌"],
    },
    {
        "name": "六合",
        "items": ["子丑", "寅亥", "卯戌", "辰酉", "巳申", "午未"],
    },
    {
        "name": "五行长生",
        "items": ["木亥", "火寅", "金巳", "水土申"],
    },
]


def liu_qin(zhi: str, day_gan: str) -> str:
    """该地支对日干的六亲（取本气）"""
    hide_gan = LunarUtil.ZHI_HIDE_GAN.get(zhi, [])
    if not hide_gan:
        return ""
    ben_qi = hide_gan[0]
    ss = LunarUtil.SHI_SHEN.get(day_gan + ben_qi, "")
    return SHISHEN_TO_LIUQIN.get(ss, "")


def day_ma(day_zhi: str) -> str:
    for group, ma in DAY_MA_GROUPS:
        if day_zhi in group:
            return ma
    return ""


def xing_nian(gender: int, age: int) -> str:
    """行年干支（按虚岁）：男一岁起丙寅顺行，女一岁起壬申逆行。gender: 1男 0女。"""
    if not age or age < 1:
        return ""
    step = age - 1
    if gender == 1:
        g, z = (2 + step) % 10, (2 + step) % 12
    else:
        g, z = (8 - step) % 10, (8 - step) % 12
    return GAN[g] + ZHI[z]


def get_shen_sha(day_gan: str, day_zhi: str, month_zhi: str) -> list[dict]:
    """核心辅助神煞。用于盘面标注和解读，不参与四课三传成盘。"""
    items = [
        {"name": "日禄", "zhi": DAY_LU.get(day_gan, ""), "basis": "日干"},
        {"name": "日德", "zhi": DAY_DE.get(day_gan, ""), "basis": "日干"},
        {"name": "天马", "zhi": TIAN_MA_BY_MONTH_ZHI.get(month_zhi, ""), "basis": "月建"},
        {"name": "日马", "zhi": day_ma(day_zhi), "basis": "日支"},
    ]
    return [item for item in items if item["zhi"]]


# ============================================================
# 主函数：起一课
# ============================================================
# 占事所在地的默认经纬度：北京。调用方知道实际地点就传进来。
DEFAULT_LATITUDE, DEFAULT_LONGITUDE = 39.9, 116.4


def qike(year: int, month: int, day: int, hour: int, minute: int,
        user_number: int | None = None,
        gender: int = 0, benming: str = "",
        latitude: float = DEFAULT_LATITUDE, longitude: float = DEFAULT_LONGITUDE) -> dict:
    """
    起一卦六壬课
    user_number: 用户报的活时数字，任意正整数按十二地支循环。若 None，则用系统时辰（正时）
    benming: 本命年支（生肖，如 子/丑…），仅作断课参考随结果带出，不参与排盘
    """
    solar = Solar.fromYmdHms(year, month, day, hour, minute, 0)
    lunar = solar.getLunar()

    # 干支历
    day_ganzhi = lunar.getDayInGanZhiExact()
    hour_ganzhi = lunar.getTimeInGanZhi()
    month_ganzhi = lunar.getMonthInGanZhiExact()
    year_ganzhi = lunar.getYearInGanZhiExact()

    day_gan = day_ganzhi[0]
    day_zhi = day_ganzhi[1]

    # 占时：活时（用户报数）优先，否则用系统时辰
    if user_number is not None:
        zhan_shi = ZHI[(user_number - 1) % 12]
    else:
        zhan_shi = hour_ganzhi[1]

    # 月将
    yue_jiang = get_yue_jiang(year, month, day, hour)

    # 昼夜贵人：正时起课按占时那一刻当地日出日落分——酉时日未落仍是昼，卯时日未出仍是夜。
    # 《六壬大全》课经诸例用贵，卯至申皆昼、戌至丑皆夜，而寅、酉两时随季节而变（六月寅时用昼贵，
    # 二月、七月酉时用昼贵）；《大六壬指南》占验亦有「虽寅时，用昼贵」、八月酉时用夜贵之例。
    # 固定以卯酉分界（卯至申为昼）只是它的近似。活时报数没有真实时刻，仍按占时支判定。
    day_time = is_day_time(hour)
    tian_jiang_hour_zhi = zhan_shi if user_number is not None else hour_ganzhi[1]
    if user_number is None:
        tian_jiang_day_time = is_daytime(datetime(year, month, day, hour, minute), latitude, longitude)
    else:
        tian_jiang_day_time = get_tian_jiang_day_flag(tian_jiang_hour_zhi)

    # 天地盘
    tdp = build_tian_di_pan(yue_jiang, zhan_shi)

    # 四课
    classes = build_four_classes(day_gan, day_zhi, tdp)

    # 三传
    chuan = get_three_chuan(classes, tdp, day_gan, day_zhi)

    # 十二天将（布在地盘上）
    tj_map = build_tian_jiang_map(day_gan, tian_jiang_day_time, tdp)

    # 旬空
    xk = get_xun_kong(day_ganzhi)
    xs = get_xun_shou(day_ganzhi)
    shen_sha = get_shen_sha(day_gan, day_zhi, month_ganzhi[1])
    shen_sha_by_zhi = {}
    for item in shen_sha:
        shen_sha_by_zhi.setdefault(item["zhi"], []).append(item["name"])

    # 六亲对应：给每一传 + 四课上字附加六亲
    def annotate(z: str) -> dict:
        return {
            "zhi": z,
            "wuxing": WUXING_ZHI.get(z, ""),
            "liu_qin": liu_qin(z, day_gan),
            "xun_gan": get_xun_dun_gan(day_ganzhi, z),
            "tian_jiang": tj_map.get(z, ""),
            "shen_sha": shen_sha_by_zhi.get(z, []),
            "is_kong": z in xk,
        }

    classes_full = [{
        **c,
        "up_info": annotate(c["up"]),
        "down_info": {
            "zhi": c["down"],
            "wuxing": WUXING_ZHI.get(c["down"]) or WUXING_GAN.get(c["down"], ""),
        },
    } for c in classes]

    chuan_full = {
        "method": chuan["method"],
        "ge": chuan.get("ge", ""),
        "chu": annotate(chuan["chu"]),
        "zhong": annotate(chuan["zhong"]),
        "mo": annotate(chuan["mo"]),
    }

    plate = {
        "layout": PLATE_LAYOUT,
        "palaces": build_palaces(tdp, tj_map, day_ganzhi, xk, shen_sha),
        "four_courses": list(reversed(classes_full)),
        "three_transmissions": [
            {"stage": "初", "info": chuan_full["chu"]},
            {"stage": "中", "info": chuan_full["zhong"]},
            {"stage": "末", "info": chuan_full["mo"]},
        ],
    }

    result = {
        "input": {
            "year": year, "month": month, "day": day,
            "hour": hour, "minute": minute,
            "user_number": user_number, "gender": gender, "benming": benming,
        },
        "ganzhi": {
            "year": year_ganzhi, "month": month_ganzhi,
            "day": day_ganzhi, "hour": hour_ganzhi,
        },
        "day_gan": day_gan,
        "day_zhi": day_zhi,
        "yue_jiang": yue_jiang,
        "zhan_shi": zhan_shi,
        "is_day_time": day_time,
        "tian_jiang_is_day_time": tian_jiang_day_time,
        "tian_jiang_hour_zhi": tian_jiang_hour_zhi,
        "gui_ren": get_gui_ren_position(day_gan, tian_jiang_day_time),
        "xun_shou": xs,
        "xun_kong": xk,
        "xun_dun_gan_map": {z: get_xun_dun_gan(day_ganzhi, z) for z in ZHI},
        "shen_sha": shen_sha,
        "tian_di_pan": tdp,             # { 地盘: 天盘 }
        "tian_jiang_map": tj_map,        # { 天盘支: 天将 }
        "relation_layers": RELATION_LAYERS,
        "four_classes": classes_full,
        "three_chuan": chuan_full,
        "plate": plate,
    }
    # 课体：照《六壬大全》课经逐条判定（见 keti.py）。放在这里而非模块顶部，免得循环引用
    from .keti import detect_ke
    from .bifa import detect_ke as bifa_ke
    result["keti"] = detect_ke(result)
    result["bifa"] = bifa_ke(result)  # 毕法赋中本课命中的句子
    return result


if __name__ == "__main__":
    # 简单自测
    import json
    r = qike(2026, 5, 20, 16, 16, user_number=None, gender=0)
    print(json.dumps(r, ensure_ascii=False, indent=2))
