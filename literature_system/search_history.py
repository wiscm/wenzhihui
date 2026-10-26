# -*- coding: utf-8 -*-
"""检索历史模块：记录每次检索命中的文献ID，避免重复推送已看过的文献。

历史文件为 JSON：{ 检索键: {"ids": [...], "count": N, "last": 时间戳} }
检索键 = 检索类型|关键词集合（排序后拼接），与来源无关。
"""
import json
import os
import time


def load(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save(path: str, hist: dict):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(hist, f, ensure_ascii=False)


def hist_key(search_type: str, keywords: list) -> str:
    kws = sorted({(k or "").strip().lower() for k in keywords if k and k.strip()})
    return f"{search_type}|" + "|".join(kws)


def seen_ids(hist: dict, key: str) -> set:
    entry = hist.get(key) or {}
    return set(entry.get("ids") or [])


def record(hist: dict, key: str, ids: list) -> int:
    """将本次检索命中的ID记入历史，返回该键累计文献数。"""
    entry = hist.setdefault(key, {"ids": [], "count": 0, "last": 0})
    id_set = set(entry.get("ids") or [])
    id_set.update(ids)
    entry["ids"] = sorted(id_set)
    entry["count"] = len(entry["ids"])
    entry["last"] = time.strftime("%Y-%m-%d %H:%M:%S")
    return entry["count"]


def stats(hist: dict) -> list:
    """全部历史记录概览，供界面展示。"""
    rows = []
    for key, e in hist.items():
        stype, _, kws = key.partition("|")
        rows.append({"检索类型": stype, "关键词": kws.replace("|", "、"),
                     "累计文献数": e.get("count", 0), "最近检索": e.get("last", "")})
    return rows
