# -*- coding: utf-8 -*-
"""多来源文献检索模块：arXiv / PubMed&PMC(经Europe PMC) / Semantic Scholar / OpenAlex。

所有接口均为公开免费接口，无需申请密钥（Semantic Scholar 匿名调用有速率限制，
失败时自动重试；如需更高配额可自行注册 S2 API key 后修改代码）。
"""
import time
import re
import xml.etree.ElementTree as ET

import requests

from .models import Paper

TIMEOUT = 30
UA = {"User-Agent": "literature-data-system/1.0 (research use)"}


def _get(url, params=None, timeout=TIMEOUT, retries=3):
    """GET请求，429限流时自动等待重试。"""
    for attempt in range(retries):
        r = requests.get(url, params=params, headers=UA, timeout=timeout)
        if r.status_code == 429 and attempt < retries - 1:
            time.sleep(2 * (attempt + 1))
            continue
        r.raise_for_status()
        return r
    return r


# ---------------------------------------------------------------- arXiv
def search_arxiv(query: str, max_results: int = 10, search_type: str = "keyword"):
    """优先使用 arXiv 官方API；网络不可达时自动回退到 OpenAlex 镜像检索arXiv文献。"""
    from .cn_searchers import contains_cjk
    if contains_cjk(query):
        return []  # arXiv无中文文献，中文关键词直接跳过
    try:
        return _search_arxiv_api(query, max_results, search_type)
    except Exception:
        return _search_arxiv_openalex(query, max_results, search_type)


def _search_arxiv_api(query: str, max_results: int = 10, search_type: str = "keyword"):
    if search_type == "journal":
        return []  # arXiv为预印本，无期刊检索
    ns = {"a": "http://www.w3.org/2005/Atom", "ar": "http://arxiv.org/schemas/atom"}
    prefix = "au:" if search_type == "author" else "all:"
    r = _get("http://export.arxiv.org/api/query",
             {"search_query": f"{prefix}{query}", "start": 0, "max_results": max_results},
             timeout=20)
    root = ET.fromstring(r.content)
    papers = []
    for e in root.findall("a:entry", ns):
        entry_id = (e.findtext("a:id", "", ns) or "").strip()
        arxiv_id = entry_id.split("/abs/")[-1]
        pdf_url = ""
        for link in e.findall("a:link", ns):
            if link.get("title") == "pdf":
                pdf_url = link.get("href", "")
        papers.append(Paper(
            source="arXiv",
            paper_id=f"arxiv:{arxiv_id}",
            title=re.sub(r"\s+", " ", e.findtext("a:title", "", ns)).strip(),
            authors=[(a.findtext("a:name", "", ns) or "").strip() for a in e.findall("a:author", ns)],
            year=(e.findtext("a:published", "", ns) or "")[:4],
            journal="arXiv preprint",
            abstract=re.sub(r"\s+", " ", e.findtext("a:summary", "", ns)).strip(),
            doi=(e.findtext("ar:doi", "", ns) or "").strip(),
            url=entry_id,
            pdf_url=pdf_url,
            extra={"arxiv_id": arxiv_id},
        ))
    return papers


def _search_arxiv_openalex(query: str, max_results: int = 10, search_type: str = "keyword"):
    """arXiv官方API不可达时的回退：经OpenAlex限定arXiv来源检索。

    OpenAlex中arXiv来源ID为 S4306400194。
    """
    filt = "primary_location.source.id:S4306400194"
    if search_type == "author":
        filt += f",raw_author_name.search:{query}"
    elif search_type == "journal":
        return []
    else:
        filt += f",title_and_abstract.search:{query}"
    r = _get("https://api.openalex.org/works",
             {"filter": filt, "per-page": max(1, min(max_results, 50)),
              "mailto": "user@example.com"})
    papers = []
    for w in r.json().get("results", []) or []:
        prim = w.get("primary_location") or {}
        oa = w.get("open_access") or {}
        doi = (w.get("doi") or "").replace("https://doi.org/", "")
        # arXiv DOI形如 10.48550/arXiv.xxxx -> 构造arxiv.org主站PDF直链
        arxiv_id = ""
        if doi.lower().startswith("10.48550/arxiv."):
            arxiv_id = doi.split("arxiv.", 1)[1]
        pdf_url = (f"https://arxiv.org/pdf/{arxiv_id}" if arxiv_id
                   else (oa.get("oa_url") or ""))
        papers.append(Paper(
            source="arXiv",
            paper_id=f"openalex:{str(w.get('id', '')).split('/')[-1]}",
            title=(w.get("title") or w.get("display_name") or "").strip(),
            authors=[(a.get("author") or {}).get("display_name", "")
                     for a in w.get("authorships") or []],
            year=str(w.get("publication_year") or ""),
            journal="arXiv preprint",
            abstract="",  # OpenAlex过滤检索不返回摘要倒排索引
            doi=doi,
            url=(prim.get("landing_page_url") or ""),
            pdf_url=pdf_url,
            citations=int(w.get("cited_by_count") or 0),
            extra={"is_oa": bool(oa.get("is_oa")), "via": "OpenAlex镜像",
                   "arxiv_id": arxiv_id},
        ))
    if not papers:
        raise RuntimeError("arXiv官方API不可达，且OpenAlex镜像未返回结果；"
                           "arXiv官方接口地址为 export.arxiv.org，可能被网络阻断")
    return papers


# ------------------------------------------------------- Semantic Scholar
def search_semantic_scholar(query: str, max_results: int = 10, search_type: str = "keyword"):
    fields = "title,abstract,year,authors,externalIds,openAccessPdf,url,venue,citationCount"
    last_err = None
    for attempt in range(3):  # 匿名接口限流，自动重试
        try:
            params = {"query": query, "limit": max(1, min(max_results, 100)),
                      "fields": fields}
            if search_type == "journal":
                params["venue"] = query
            r = _get("https://api.semanticscholar.org/graph/v1/paper/search", params)
            papers = []
            for it in r.json().get("data", []) or []:
                oa = it.get("openAccessPdf") or {}
                papers.append(Paper(
                    source="Semantic Scholar",
                    paper_id=f"s2:{it.get('paperId', '')}",
                    title=(it.get("title") or "").strip(),
                    authors=[a.get("name", "") for a in it.get("authors") or []],
                    year=str(it.get("year") or ""),
                    journal=(it.get("venue") or ""),
                    abstract=(it.get("abstract") or "").strip(),
                    doi=(it.get("externalIds") or {}).get("DOI", ""),
                    url=it.get("url", ""),
                    pdf_url=(oa.get("url") or ""),
                    citations=int(it.get("citationCount") or 0),
                ))
            return papers
        except Exception as ex:
            last_err = ex
            time.sleep(3 * (attempt + 1))
    raise last_err


# -------------------------------------------------------------- OpenAlex
def _openalex_journal_filter(query: str) -> str:
    """期刊检索：先查来源ID，再按ID过滤works（display_name过滤不被API支持）。"""
    src = _get("https://api.openalex.org/sources",
               {"search": query, "per-page": 5, "mailto": "user@example.com"})
    ids = [str(s.get("id", "")).rsplit("/", 1)[-1]
           for s in src.json().get("results", []) or []]
    if not ids:
        return ""
    return "primary_location.source.id:" + "|".join(ids)


def search_openalex(query: str, max_results: int = 10, search_type: str = "keyword"):
    params = {"per-page": max(1, min(max_results, 100)),
              "mailto": "user@example.com"}
    if search_type == "author":
        params["filter"] = f"raw_author_name.search:{query}"
    elif search_type == "journal":
        filt = _openalex_journal_filter(query)
        if not filt:
            return []
        params["filter"] = filt
    else:
        params["search"] = query
    r = _get("https://api.openalex.org/works", params)
    papers = []
    for w in r.json().get("results", []) or []:
        inv = w.get("abstract_inverted_index")
        abstract = ""
        if inv:
            pos = {}
            for word, idxs in inv.items():
                for i in idxs:
                    pos[i] = word
            abstract = " ".join(pos[i] for i in sorted(pos))
        prim = w.get("primary_location") or {}
        oa = w.get("open_access") or {}
        papers.append(Paper(
            source="OpenAlex",
            paper_id=f"openalex:{str(w.get('id', '')).split('/')[-1]}",
            title=(w.get("title") or w.get("display_name") or "").strip(),
            authors=[(a.get("author") or {}).get("display_name", "")
                     for a in w.get("authorships") or []],
            year=str(w.get("publication_year") or ""),
            journal=((prim.get("source") or {}).get("display_name") or ""),
            abstract=abstract,
            doi=(w.get("doi") or "").replace("https://doi.org/", ""),
            url=(prim.get("landing_page_url") or w.get("doi") or ""),
            pdf_url=(oa.get("oa_url") or prim.get("pdf_url") or ""),
            citations=int(w.get("cited_by_count") or 0),
            extra={"is_oa": bool(oa.get("is_oa"))},
        ))
    return papers


# --------------------------------------------- PubMed / PMC（经Europe PMC）
def search_europepmc(query: str, max_results: int = 10, search_type: str = "keyword"):
    if search_type == "author":
        q = f'AUTH:"{query}"'
    elif search_type == "journal":
        q = f'JOURNAL:"{query}"'
    else:
        q = query
    r = _get("https://www.ebi.ac.uk/europepmc/webservices/rest/search",
             {"query": q, "format": "json",
              "pageSize": max(1, min(max_results, 100)), "resultType": "core"})
    papers = []
    for it in r.json().get("resultList", {}).get("result", []) or []:
        pmcid = it.get("pmcid", "") or ""
        pdf_url, fulltext_url = "", ""
        for link in it.get("fullTextUrlList", {}).get("fullTextUrlInfo", []) or []:
            style = link.get("documentStyle", "")
            if style == "pdf" and not pdf_url:
                pdf_url = link.get("url", "")
            if style == "html" and not fulltext_url:
                fulltext_url = link.get("url", "")
        abstract = (it.get("abstractText") or "")
        abstract = abstract.replace("<h4>", "【").replace("</h4>", "】")
        abstract = re.sub(r"<[^>]+>", " ", abstract).strip()
        papers.append(Paper(
            source="PubMed/PMC",
            paper_id=f"pmc:{pmcid or it.get('id', '')}",
            title=re.sub(r"\s+", " ", it.get("title") or "").strip(),
            authors=[a.strip() for a in (it.get("authorString") or "").split(",") if a.strip()],
            year=str(it.get("pubYear") or ""),
            journal=(it.get("journalTitle") or ""),
            abstract=abstract,
            doi=(it.get("doi") or ""),
            url=f"https://europepmc.org/article/{it.get('source', 'MED')}/{pmcid or it.get('id', '')}",
            pdf_url=pdf_url,
            citations=int(it.get("citedByCount") or 0),
            extra={"pmcid": pmcid, "is_oa": it.get("isOpenAccess") == "Y",
                   "fulltext_url": fulltext_url},
        ))
    return papers


SEARCH_FUNCS = {
    "arXiv": search_arxiv,
    "PubMed/PMC": search_europepmc,
    "Semantic Scholar": search_semantic_scholar,
    "OpenAlex": search_openalex,
}

# 中文文献来源（经OpenAlex language:zh 检索）
from .cn_searchers import search_chinese_openalex as _search_chinese  # noqa: E402
SEARCH_FUNCS["中文文献"] = _search_chinese


def search_all(queries, sources, max_results: int = 10, search_type: str = "keyword",
               zh_map: dict = None, progress_cb=None):
    """多关键词/作者/期刊 × 多来源批量检索。

    queries: 检索词列表（关键词/作者名/期刊名）
    zh_map: {原检索词: 中文译文}，"中文文献"来源优先用中文检索词
    progress_cb: 可选回调 progress_cb(进度0~1, 说明文字)
    返回 (去重合并后的Paper列表, 各来源错误信息dict)。
    """
    if isinstance(queries, str):
        queries = [queries]
    queries = [q for q in queries if q and q.strip()]
    results, errors = [], {}
    total = max(len(queries) * len(sources), 1)
    done = 0
    for q in queries:
        for s in sources:
            done += 1
            if progress_cb:
                progress_cb(done / total, f"「{q[:20]}」· {s}")
            func = SEARCH_FUNCS.get(s)
            if not func:
                continue
            try:
                use_q = q
                if s == "中文文献" and zh_map and zh_map.get(q):
                    use_q = zh_map[q]
                papers = func(use_q, max_results, search_type)
                for p in papers:
                    if q not in p.matched_keywords:
                        p.matched_keywords.append(q)
                results.extend(papers)
            except Exception as ex:
                errors[f"{s}·{q[:15]}"] = str(ex)
    # 去重合并：按 paper_id 优先，其次DOI/标题；合并命中关键词，保留最大引用量
    seen = {}
    ordered = []
    for p in results:
        key = p.paper_id or (p.doi or p.title.lower())[:120]
        if key in seen:
            old = seen[key]
            for kw in p.matched_keywords:
                if kw not in old.matched_keywords:
                    old.matched_keywords.append(kw)
            old.citations = max(old.citations, p.citations)
            if not old.abstract and p.abstract:
                old.abstract = p.abstract
            continue
        seen[key] = p
        ordered.append(p)
    return ordered, errors
