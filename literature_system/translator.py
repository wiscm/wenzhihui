# -*- coding: utf-8 -*-
"""关键词在线翻译模块：中英互译，用于双语文献检索。

翻译通道（按顺序尝试）：
1. 用户配置的AI大模型（OpenAI兼容接口）——质量最高，推荐
2. 免费公开翻译接口（谷歌gtx / 有道）——部分网络环境不可用时自动跳过
"""
import re

import requests

from .cn_searchers import contains_cjk

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


class TranslationError(RuntimeError):
    pass


# ------------------------------------------------------------ AI翻译
def _translate_by_ai(text: str, to_lang: str, ai) -> str:
    lang_name = "英文" if to_lang.startswith("en") else "中文"
    prompt = (f"请将下面的学术检索关键词翻译为{lang_name}，"
              "要求：准确使用学术/科研领域标准术语；"
              "只输出翻译结果本身，不要输出任何解释、引号或标点说明。\n\n"
              f"关键词：{text}")
    out = ai.chat([{"role": "user", "content": prompt}], temperature=0.1)
    out = (out or "").strip().strip('"“”‘’').splitlines()[0].strip()
    if not out:
        raise TranslationError("AI返回了空翻译")
    return out


# ---------------------------------------------------- 免费接口翻译（备用）
def _translate_by_google(text: str, to_lang: str) -> str:
    sl = "zh-CN" if contains_cjk(text) else "en"
    r = requests.get(
        "https://translate.googleapis.com/translate_a/single",
        params={"client": "gtx", "sl": sl, "tl": to_lang, "dt": "t", "q": text},
        headers=UA, timeout=10)
    r.raise_for_status()
    return "".join(seg[0] for seg in r.json()[0] if seg and seg[0]).strip()


def _translate_by_youdao(text: str, to_lang: str) -> str:
    typ = "ZH_CN2EN" if contains_cjk(text) else "EN2ZH_CN"
    r = requests.get(
        "https://fanyi.youdao.com/translate",
        params={"doctype": "json", "type": typ, "i": text},
        headers={**UA, "Referer": "https://fanyi.youdao.com/"}, timeout=10)
    r.raise_for_status()
    data = r.json()
    if data.get("errorCode") == "0" and data.get("translateResult"):
        return "".join(seg.get("tgt", "") for seg in data["translateResult"][0]).strip()
    raise TranslationError("有道接口返回异常")


FALLBACKS = [_translate_by_google, _translate_by_youdao]


# ---------------------------------------------------------------- 主入口
def translate(text: str, to_lang: str, ai=None) -> str:
    """把关键词翻译为目标语言。优先AI，其次免费接口。

    to_lang: 'en' 或 'zh'
    返回译文；全部通道失败时抛 TranslationError。
    """
    text = (text or "").strip()
    if not text:
        raise TranslationError("关键词为空")
    # 已是目标语言则直接返回
    if to_lang.startswith("en") and not contains_cjk(text):
        return text
    if to_lang.startswith("zh") and contains_cjk(text):
        return text
    if ai is not None:
        try:
            return _translate_by_ai(text, to_lang, ai)
        except Exception:
            pass
    errs = []
    for func in FALLBACKS:
        try:
            return func(text, to_lang)
        except Exception as ex:
            errs.append(f"{func.__name__}: {ex}")
    raise TranslationError(
        "所有翻译通道均失败。最可靠的方式是在左侧边栏配置AI模型（Base URL/API Key/模型名）"
        "后使用AI翻译；当前网络下免费翻译接口不可达。详情：" + "；".join(errs[:2]))


def translate_query_pair(query: str, ai=None):
    """返回 (中文关键词, 英文关键词, 使用的通道说明)。

    输入中文 -> AI/接口译为英文；输入英文 -> 译为中文。
    """
    query = (query or "").strip()
    if contains_cjk(query):
        zh = query
        en = translate(query, "en", ai)
        channel = "中→英"
    else:
        en = query
        zh = translate(query, "zh", ai)
        channel = "英→中"
    return zh, en, channel


def translate_many(texts: list, to_lang: str, ai=None) -> list:
    """批量翻译多个关键词（一次AI调用完成，效率高）。

    返回与 texts 等长的译文列表；已是目标语言的项原样返回。
    全部通道失败时抛 TranslationError。
    """
    texts = [(t or "").strip() for t in texts]
    if not texts:
        return []

    def already_target(t):
        if to_lang.startswith("en"):
            return not contains_cjk(t)
        return contains_cjk(t)

    if all(already_target(t) for t in texts):
        return list(texts)

    if ai is not None:
        try:
            lang_name = "英文" if to_lang.startswith("en") else "中文"
            import json as _json
            from .ai_client import parse_json_array
            prompt = (
                f"请将下面JSON数组中的每个学术检索关键词翻译为{lang_name}，"
                "要求使用各学科标准学术术语。"
                "只输出一个等长的JSON字符串数组，不要输出任何解释或代码块标记。\n"
                + _json.dumps(texts, ensure_ascii=False))
            out = ai.chat([{"role": "user", "content": prompt}], temperature=0.1)
            arr = parse_json_array(out) if out.strip().startswith("[") else None
            if arr and len(arr) == len(texts):
                res = []
                for t, x in zip(texts, arr):
                    x = str(list(x.values())[0]) if isinstance(x, dict) else str(x)
                    res.append(x.strip() if x.strip() else t)
                return res
        except Exception:
            pass
    # 免费接口逐条回退
    res = []
    for t in texts:
        if already_target(t):
            res.append(t)
            continue
        try:
            res.append(translate(t, to_lang, None))
        except Exception:
            res.append(None)
    if all(x is None for x in res):
        raise TranslationError("批量翻译失败：AI未配置且免费翻译接口不可达")
    return [t if x is None else x for t, x in zip(texts, res)]
