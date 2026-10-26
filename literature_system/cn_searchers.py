# -*- coding: utf-8 -*-
"""中文文献检索模块。

说明：
- 知网(CNKI)、万方、维普均无免费公开API，无法程序化抓取检索结果；
- 本模块经 OpenAlex 检索 language:zh 的中文期刊文献（含中文标题与中文摘要，
  覆盖科学通报、中国科学、化学进展等中文核心期刊）；
- 同时提供 知网/万方/维普/百度学术 的检索直达链接，供用户手动浏览与下载
  （下载后的PDF可在"AI阅读与数据提取"页上传，交给AI提取数据）。
"""
import re
import time
import urllib.parse

import requests

from .models import Paper

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def _get_with_retry(url, params, timeout=30, retries=3):
    for attempt in range(retries):
        r = requests.get(url, params=params, headers=UA, timeout=timeout)
        if r.status_code == 429 and attempt < retries - 1:
            time.sleep(2 * (attempt + 1))
            continue
        r.raise_for_status()
        return r
    return r


def contains_cjk(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text or ""))


def _abstract_from_inverted(inv: dict) -> str:
    if not inv:
        return ""
    pos = {}
    for word, idxs in inv.items():
        for i in idxs:
            pos[i] = word
    return " ".join(pos[i] for i in sorted(pos))


def search_chinese_openalex(query: str, max_results: int = 10, search_type: str = "keyword"):
    """经OpenAlex检索中文文献（language:zh），返回中文标题/摘要的Paper列表。"""
    params = {"filter": "language:zh",
              "per-page": max(1, min(max_results, 50)),
              "mailto": "user@example.com"}
    if search_type == "author":
        params["filter"] += f",raw_author_name.search:{query}"
    elif search_type == "journal":
        src = _get_with_retry("https://api.openalex.org/sources",
                              {"search": query, "per-page": 5,
                               "mailto": "user@example.com"})
        ids = [str(s.get("id", "")).rsplit("/", 1)[-1]
               for s in src.json().get("results", []) or []]
        if not ids:
            return []
        params["filter"] += ",primary_location.source.id:" + "|".join(ids)
    else:
        params["search"] = query
    r = _get_with_retry("https://api.openalex.org/works", params)
    r.raise_for_status()
    papers = []
    for w in r.json().get("results", []) or []:
        prim = w.get("primary_location") or {}
        oa = w.get("open_access") or {}
        papers.append(Paper(
            source="中文文献",
            paper_id=f"openalex-zh:{str(w.get('id', '')).split('/')[-1]}",
            title=(w.get("title") or w.get("display_name") or "").strip(),
            authors=[(a.get("author") or {}).get("display_name", "")
                     for a in w.get("authorships") or []],
            year=str(w.get("publication_year") or ""),
            journal=((prim.get("source") or {}).get("display_name") or ""),
            abstract=_abstract_from_inverted(w.get("abstract_inverted_index")),
            doi=(w.get("doi") or "").replace("https://doi.org/", ""),
            url=(prim.get("landing_page_url") or w.get("doi") or ""),
            pdf_url=(oa.get("oa_url") or prim.get("pdf_url") or ""),
            citations=int(w.get("cited_by_count") or 0),
            extra={"is_oa": bool(oa.get("is_oa")), "lang": "zh"},
        ))
    return papers


# 中文库手动检索直达链接（无免费API，提供网页入口）
def get_cn_manual_links(query: str) -> dict:
    q = urllib.parse.quote(query or "")
    return {
        "知网CNKI": f"https://kns.cnki.net/kns8s/defaultresult/index?kw={q}",
        "万方数据": f"https://s.wanfangdata.com.cn/paper?q={q}",
        "维普期刊": f"https://qikan.cqvip.com/Qikan/Search/Index?key={q}",
        "百度学术": f"https://xueshu.baidu.com/s?wd={q}",
        "国家哲学社会科学文献中心": f"https://www.ncpssd.cn/?a=1&key={q}",
    }
