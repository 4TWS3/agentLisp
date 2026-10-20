"""agentLisp 运行时核心库：编译产物调用的辅助函数。

设计原则：
1. 不引入解释器。产物是**生成的 Python 代码**，这里只提供被调用的函数。
2. 名字带 al_ 前缀，避免污染产物命名空间。
3. 语义对齐 Racket 的核心形式（hash-ref / format / list-ref 等）。
"""

from __future__ import annotations

import importlib
import os
from typing import Any


# ---------- 字典（Racket hash 的对应物） ----------
def hash_ref(d: Any, key: Any, default: Any = None) -> Any:
    """Racket (hash-ref d key [default])。非 dict 时返回 default，不抛。"""
    if isinstance(d, dict):
        return d.get(key, default)
    return default


def hash_set(d: Any, key: Any, val: Any) -> dict:
    """返回新 dict（Racket hash-set 是不可变的）。"""
    out = dict(d) if isinstance(d, dict) else {}
    out[key] = val
    return out


def al_hash(*kvs: Any) -> dict:
    """(hash k1 v1 k2 v2 ...) -> dict。"""
    if len(kvs) % 2:
        raise ValueError("al_hash 需要偶数个参数")
    return {kvs[i]: kvs[i + 1] for i in range(0, len(kvs), 2)}


def hash_keys(d: Any) -> list:
    return list(d.keys()) if isinstance(d, dict) else []


def hash_has_key(d: Any, key: Any) -> bool:
    return isinstance(d, dict) and key in d


# ---------- 字符串 ----------
def al_format(fmt: str, *args: Any) -> str:
    """Racket 风格 format：把 ~a / ~s / ~v 依次替换成参数。"""
    out = []
    idx = 0
    i = 0
    while i < len(fmt):
        ch = fmt[i]
        if ch == "~" and i + 1 < len(fmt):
            nxt = fmt[i + 1]
            if nxt in "asv":
                if idx < len(args):
                    out.append(str(args[idx]))
                    idx += 1
                i += 2
                continue
            if nxt == "n":
                out.append("\n")
                i += 2
                continue
            if nxt == "%":
                out.append("\n")
                i += 2
                continue
        out.append(ch)
        i += 1
    return "".join(out)


def string_append(*parts: Any) -> str:
    return "".join("" if p is None else str(p) for p in parts)


def string_split(s: Any, sep: str = " ") -> list:
    return str(s).split(sep)


def string_contains(s: Any, sub: Any) -> bool:
    return str(sub) in str(s)


def string_upcase(s: Any) -> str:
    return str(s).upper()


def string_downcase(s: Any) -> str:
    return str(s).lower()


def string_join(parts: Any, sep: str = "") -> str:
    return sep.join("" if p is None else str(p) for p in (parts or []))


# ---------- 列表 ----------
def first(lst: Any) -> Any:
    if isinstance(lst, (list, tuple)) and lst:
        return lst[0]
    return None


def rest(lst: Any) -> list:
    if isinstance(lst, (list, tuple)):
        return list(lst[1:])
    return []


def list_ref(lst: Any, i: int, default: Any = None) -> Any:
    """Racket 的 list-ref：越界/类型不符时返回 default，不抛。

    这里刻意不用 try/except：仓库标准禁止静默 except（P5/E3）。
    显式判型同样安全，且失败路径可见。
    """
    if isinstance(lst, (list, tuple, str)) and -len(lst) <= i < len(lst):
        return lst[i]
    return default


def length(x: Any) -> int:
    """Racket 的 length：无长度的值返回 0（不抛，也不静默吞异常）。"""
    if isinstance(x, (list, tuple, dict, str, set)):
        return len(x)
    return 0


def al_append(*seqs: Any) -> list:
    out: list = []
    for s in seqs:
        if isinstance(s, (list, tuple)):
            out.extend(s)
        elif s is not None:
            out.append(s)
    return out


def al_cons(x: Any, lst: Any) -> list:
    return [x] + (list(lst) if isinstance(lst, (list, tuple)) else [])


def map_list(f, lst: Any) -> list:
    return [f(x) for x in (lst or [])]


def filter_list(f, lst: Any) -> list:
    return [x for x in (lst or []) if f(x)]


def foldl(f, init: Any, lst: Any) -> Any:
    acc = init
    for x in lst or []:
        acc = f(x, acc)
    return acc


def list_index(lst: Any, x: Any, default: int = -1) -> int:
    """Racket 没有 list-index，但阶序判断常用；找不到返回 default。"""
    seq = list(lst or [])
    for i, v in enumerate(seq):
        if v == x:
            return i
    return default


def null_p(x: Any) -> bool:
    return x is None or (isinstance(x, (list, tuple, dict, str)) and len(x) == 0)


# ---------- 比较与布尔 ----------
def num_eq(*xs: Any) -> bool:
    return all(xs[i] == xs[i + 1] for i in range(len(xs) - 1))


def equal(*xs: Any) -> bool:
    return all(xs[i] == xs[i + 1] for i in range(len(xs) - 1))


def al_not(x: Any) -> bool:
    return not x


# ---------- 错误 ----------
def al_error(msg: Any) -> None:
    raise RuntimeError(str(msg))


# ---------- LLM（节点体在 Lisp 里直接调模型） ----------
def llm_complete(prompt: str, system: str | None = None) -> str:
    """在节点体里调一次模型。

    没配 DEEPSEEK_API_KEY 时返回确定性桩（离线可跑、可测）。
    同步签名：LangGraph 的同步节点跑在执行器线程里，没有运行中的事件循环；
    若真有循环（ainvoke 直接调同步节点），放到子线程里跑，避免 asyncio.run 报错。
    """
    key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not key:
        return f"[scripted] {prompt[:60]}"

    import asyncio
    import threading

    async def _call() -> str:
        from runtime.llm_client import OpenAIClient

        llm = OpenAIClient(
            model=os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash"),
            api_key=key,
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
            timeout=float(os.getenv("AGENTLISP_LLM_TIMEOUT", "180")),
        )
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        out = await llm.achat(messages)
        return str(out.get("content") or "").strip()

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(_call())

    box: dict[str, object] = {}

    def _worker() -> None:
        # 显式建/关事件循环：asyncio.run 在子线程里退出时会留
        # "RuntimeError: Event loop is closed"（实测污染日志，结果不受影响）。
        loop = asyncio.new_event_loop()
        try:
            box["v"] = loop.run_until_complete(_call())
        finally:
            loop.close()

    th = threading.Thread(target=_worker)
    th.start()
    th.join()
    return str(box.get("v") or "")


# ---------- 人工中断（LangGraph 的 interrupt） ----------
def interrupt_payload(payload: Any) -> Any:
    """在节点体里暂停等人工输入。

    LangGraph 的 interrupt() 用 contextvar 定位运行中的任务，
    从任意调用深度调用都可以 —— 所以这里可以直接包一层。
    恢复时 LangGraph 会重跑整个节点，interrupt() 返回用户给的值。
    """
    from langgraph.types import interrupt as _lg_interrupt

    return _lg_interrupt(payload)


# ---------- 并行扇出 ----------
def fanout(items: Any, fn) -> list:
    """并行跑 N 个子任务，任一失败则整体抛出（顺序与输入一致）。"""
    seq = list(items or [])
    if not seq:
        return []
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=min(8, len(seq))) as pool:
        return list(pool.map(fn, seq))


def fanout_safe(items: Any, fn) -> list:
    """并行扇出 + 失败隔离：每项返回 {ok, value, error}，不因单项失败中断。

    xuanji 的 dispatch 语义：单星失败不拖垮整体。
    """
    seq = list(items or [])
    if not seq:
        return []

    def _one(item: Any) -> dict:
        try:
            return {"ok": True, "value": fn(item), "error": None}
        except Exception as exc:
            # 失败隔离是这里的语义本身；错误被**记录**并发给调用方，不是静默吞掉
            return {"ok": False, "value": None, "error": f"{type(exc).__name__}('{exc}')"}

    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=min(8, len(seq))) as pool:
        return list(pool.map(_one, seq))


# ---------- 宿主互操作 ----------
def py_import(name: str) -> Any:
    return importlib.import_module(name)


def py_attr(obj: Any, name: str) -> Any:
    if isinstance(obj, str):
        obj = importlib.import_module(obj)
    return getattr(obj, name)


def _resolve_target(target: str) -> Any:
    """把 "a.b.c" 解析成对象：先找最长的可导入前缀，再逐级 getattr。

    为什么不能简单 rpartition：实际写法有 pathlib.Path.read_text 这种
    「模块.类.方法」，rpartition 会把 pathlib.Path 当成模块名 -> ModuleNotFoundError。
    """
    parts = target.split(".")
    if len(parts) < 2:
        raise ValueError(f"py/call 需要 '模块.函数' 形式，得到 {target!r}")
    errors: list[str] = []
    for i in range(len(parts) - 1, 0, -1):
        try:
            obj: Any = importlib.import_module(".".join(parts[:i]))
        except ImportError as exc:
            errors.append(f"{'.'.join(parts[:i])}: {exc}")
            continue
        for part in parts[i:]:
            obj = getattr(obj, part)
        return obj
    raise ImportError(f"py/call 无法解析 {target!r}；尝试过：{errors}")


def py_call(target: str, *args: Any, **kwargs: Any) -> Any:
    """(py/call "模块.函数" arg...) -> 调用。目标不存在时抛 ImportError/AttributeError。"""
    return _resolve_target(target)(*args, **kwargs)


def py_call_kw(target: str, *args: Any) -> Any:
    """(py/call-kw "模块.函数" arg... (hash "kw" v)) -> 带关键字参数调用。

    为什么需要：os.makedirs(name, mode, exist_ok) 的 exist_ok 是第三个参数，
    位置传 True 会变成 mode=True（权限位 1）→ 目录建出来但没有写权限，
    后续写文件报 PermissionError（实测踩过）。
    """
    kwargs: dict[str, Any] = {}
    if args and isinstance(args[-1], dict):
        kwargs = dict(args[-1])
        args = args[:-1]
    return _resolve_target(target)(*args, **kwargs)


def py_method(obj: Any, name: str, *args: Any, **kwargs: Any) -> Any:
    return getattr(obj, name)(*args, **kwargs)
