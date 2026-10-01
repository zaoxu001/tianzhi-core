"""可调用什么：在运行时列出本包的全部公开方法、作用与返回结构。

写给 agent 用。与其把方法表抄进一份说明书——抄完那一刻就开始过期——
不如让调用方自己来问。这里每一条都是从代码现读的：

- **作用** 取自函数 docstring 的首行
- **怎么调** 取自真实签名
- **拿得到什么** 取自返回类型；是 dataclass 就把字段名列出来

所以代码改了，这份清单跟着改，不存在两处说法打架的可能。

    from tianzhi_core import catalog

    catalog.layers()                    # 各层是什么（历法、干支、八字、六壬、紫微）
    catalog.tools('bazi')               # 某一层的全部方法
    catalog.describe('bazi.yongshen.select')   # 单个方法的完整说明
    print(catalog.as_text())            # 整份清单，可直接贴给模型
"""
from __future__ import annotations

import dataclasses as _dc
import importlib
import inspect
import pkgutil
from dataclasses import dataclass

__all__ = ["Tool", "LAYERS", "layers", "tools", "describe", "as_text"]

#: 四层各自的性质。分层不是装饰：calendar 算错了是 bug，bazi 不同可能只是口径不同。
LAYERS: dict[str, str] = {
    "calendar": "历法与纪时。节气精确时刻、真太阳时。天文计算，只有对错，无流派。",
    "core": "干支与五行。藏干、刑冲合害、十二长生、旺相休囚死、人元司令。基础常识。",
    "bazi": "八字。排盘、量化、调候、格局、取用、排运、引动、评分、合盘、神煞。流派分歧集中在这一层。",
    "liuren": "大六壬。起课（月将加时）、天地盘、四课三传、十二天将、遁干六亲、空亡神煞，课体、毕法与占事断。",
    "ziwei": "紫微斗数。安星排盘（十二宫、主星辅星、四化、五行局、命主身主）、格局、断语，大限流年等六层运限与限运论断。",
}


@dataclass(frozen=True, slots=True)
class Tool:
    """一个可调用的方法。"""

    name: str           #: 形如 'bazi.yongshen.select'
    layer: str
    module: str
    summary: str        #: docstring 首行
    signature: str
    returns: str        #: 返回类型；dataclass 会列出字段名


def layers() -> dict[str, str]:
    return dict(LAYERS)


def _returns_of(fn) -> str:
    """返回类型能说多少说多少：dataclass 列字段，别的给类型名。"""
    ann = getattr(fn, "__annotations__", {}).get("return")
    if ann is None:
        return ""
    text = ann if isinstance(ann, str) else getattr(ann, "__name__", str(ann))
    # 返回的是本包里的 dataclass 时，字段名比类型名有用得多
    bare = text.strip().strip("'\"").split("[")[0].split("|")[0].strip()
    mod = inspect.getmodule(fn)
    target = getattr(mod, bare, None) if mod else None
    if target is not None and _dc.is_dataclass(target):
        fields = ", ".join(f.name for f in _dc.fields(target))
        return f"{bare}（{fields}）"
    return text


def tools(layer: str | None = None, module: str | None = None) -> list[Tool]:
    """列出方法。给 layer 或 module 就只列那一部分。"""
    out: list[Tool] = []
    for lay in ([layer] if layer else LAYERS):
        if lay not in LAYERS:
            raise ValueError(f"没有这一层：{lay}。可选 {', '.join(LAYERS)}")
        pkg = importlib.import_module(f"{__package__}.{lay}")
        for info in pkgutil.iter_modules(pkg.__path__):
            if module and info.name != module:
                continue
            mod = importlib.import_module(f"{__package__}.{lay}.{info.name}")
            for name, fn in vars(mod).items():
                if name.startswith("_") or not callable(fn) or isinstance(fn, type):
                    continue
                if getattr(fn, "__module__", "") != mod.__name__:
                    continue          # 只列本模块定义的，不列 import 进来的
                doc = (inspect.getdoc(fn) or "").strip()
                try:
                    sig = f"{name}{inspect.signature(fn)}"
                except (TypeError, ValueError):
                    sig = f"{name}(...)"
                out.append(Tool(
                    name=f"{lay}.{info.name}.{name}",
                    layer=lay, module=info.name,
                    summary=doc.split("\n")[0] if doc else "",
                    signature=sig,
                    returns=_returns_of(fn),
                ))
    return out


def describe(name: str) -> str:
    """单个方法的完整说明：签名、返回、以及整段 docstring。"""
    parts = name.split(".")
    if len(parts) != 3:
        raise ValueError("名字要写成 '层.模块.方法'，例如 'bazi.yongshen.select'")
    lay, mod_name, fn_name = parts
    if lay not in LAYERS:
        raise ValueError(f"没有这一层：{lay}")
    mod = importlib.import_module(f"{__package__}.{lay}.{mod_name}")
    fn = getattr(mod, fn_name, None)
    if fn is None or not callable(fn):
        raise ValueError(f"没有这个方法：{name}")
    t = next((x for x in tools(lay, mod_name) if x.name == name), None)
    head = f"{name}\n{t.signature if t else fn_name}"
    if t and t.returns:
        head += f"\n→ {t.returns}"
    return f"{head}\n\n{inspect.getdoc(fn) or '（无说明）'}"


def as_text(layer: str | None = None) -> str:
    """整份清单，纯文本。可以直接贴给模型看。"""
    lines: list[str] = []
    for lay, note in LAYERS.items():
        if layer and lay != layer:
            continue
        lines.append(f"# {lay} — {note}")
        last = None
        for t in tools(lay):
            if t.module != last:
                lines.append(f"\n## {lay}.{t.module}")
                last = t.module
            lines.append(f"- {t.signature}\n  {t.summary}")
            if t.returns:
                lines.append(f"  → {t.returns}")
        lines.append("")
    return "\n".join(lines)
