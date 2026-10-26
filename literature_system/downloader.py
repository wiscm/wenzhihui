# -*- coding: utf-8 -*-
"""文献下载与在线阅读模块：PDF下载、PMC支撑材料下载、在线全文获取。"""
import io
import os
import re
import zipfile

import requests

from .models import Paper

TIMEOUT = 60
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}


def _sanitize(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', "_", name).strip()[:80]


def download_pdf(paper: Paper, save_dir: str):
    """下载PDF到本地。依次尝试多个候选链接。

    返回 (本地路径或None, 错误信息或None)。
    """
    os.makedirs(save_dir, exist_ok=True)
    # 候选链接：原始PDF链接 + arXiv主站直链回退
    candidates = []
    if paper.pdf_url:
        candidates.append(paper.pdf_url)
    arxiv_id = (paper.extra or {}).get("arxiv_id", "")
    if arxiv_id:
        direct = f"https://arxiv.org/pdf/{arxiv_id}"
        if direct not in candidates:
            candidates.append(direct)
    if not candidates:
        return None, "无可用的PDF下载链接（可在提取页在线阅读）"
    last_err = ""
    for url in candidates:
        try:
            r = requests.get(url, headers=UA, timeout=TIMEOUT)
            ct = r.headers.get("content-type", "").lower()
            if r.status_code == 200 and ("pdf" in ct or r.content[:5] == b"%PDF-"):
                fname = _sanitize(f"{paper.paper_id.replace(':', '_')}_{paper.title}") + ".pdf"
                path = os.path.join(save_dir, fname)
                with open(path, "wb") as f:
                    f.write(r.content)
                return path, None
            last_err = f"HTTP {r.status_code}（content-type: {ct or '未知'}）"
        except Exception as ex:
            last_err = str(ex)
    return None, f"下载失败：{last_err}（该文献可能为付费墙或需机构权限，请使用在线阅读）"


def download_supplementary(paper: Paper, save_dir: str):
    """下载PMC开放获取文章的支撑材料（Europe PMC提供ZIP打包接口）。

    返回解压后的文件路径列表；不适用或失败时返回空列表。
    """
    pmcid = (paper.extra or {}).get("pmcid", "")
    if not pmcid:
        return []
    try:
        r = requests.get(
            f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/supplementaryFiles",
            headers=UA, timeout=120)
        if r.status_code != 200 or r.content[:2] != b"PK":
            return []
        folder = os.path.join(save_dir, pmcid)
        os.makedirs(folder, exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            z.extractall(folder)
        return [os.path.join(folder, f) for f in sorted(os.listdir(folder))]
    except Exception:
        return []


def fetch_online_text(paper: Paper):
    """无法下载PDF时的在线阅读：优先取PMC开放获取全文XML，否则用摘要。

    返回 (text, kind)：kind为 "fulltext"（正文全文）或 "abstract"（仅摘要）。
    """
    pmcid = (paper.extra or {}).get("pmcid", "")
    if pmcid:
        try:
            r = requests.get(
                f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML",
                headers=UA, timeout=TIMEOUT)
            if r.status_code == 200 and r.text.strip():
                text = re.sub(r"<[^>]+>", " ", r.text)
                text = re.sub(r"\s+", " ", text).strip()
                if len(text) > 200:
                    return text, "fulltext"
        except Exception:
            pass
    return paper.abstract, ("abstract" if paper.abstract else "none")
