"""奇门遁甲（时家）。定局见 ju，排盘见 pan，格局见 geju；qiju 一步到位。

默认口径（皆有书可据，见 tianzhi-classics qimen/collation.json）：
  定局  超神接气置闰，置闰之限「前远后近」（《協紀》）；可选拆补（method="chaibu"）、九日之限（rule="days9"）
  盘式  转盘、中五寄坤（《遁甲演義》）；可选九星飞布（pan_method="xieji_fei"，《協紀》）
  八神  白虎玄武；可选勾陈朱雀（names="gouchen"）
"""
from .geju import find as find_geju  # noqa: F401
from .ju import ju_of  # noqa: F401
from .pan import build as build_pan  # noqa: F401
from .qiju import qiju, xun_kong, ma_xing  # noqa: F401
