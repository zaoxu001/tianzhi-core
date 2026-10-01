"""catalog 要把六壬、紫微两层也列出来：agent 靠它知道库里有什么，漏了一层就等于没有"""
from tianzhi_core import catalog


def test_all_layers_listed():
    assert {"calendar", "core", "bazi", "liuren", "ziwei"} <= set(catalog.layers())


def test_liuren_and_ziwei_tools_discoverable():
    names = {t.name for t in catalog.tools("liuren")} | {t.name for t in catalog.tools("ziwei")}
    assert "liuren.pan.qike" in names
    assert "ziwei.chart.build_chart" in names
    assert "ziwei.yunxian.horoscope" in names
    text = catalog.as_text("ziwei")
    assert "build_chart" in text
    assert "qike" in catalog.describe("liuren.pan.qike")
