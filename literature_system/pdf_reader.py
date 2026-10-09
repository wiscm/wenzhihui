# -*- coding: utf-8 -*-
"""PDF文本提取与分块。"""
import re

try:
    import pymupdf as fitz  # 新版PyMuPDF
except ImportError:  # 兼容旧版
    import fitz


def extract_pdf_text(pdf_path: str) -> str:
    """提取PDF全文文本（扫描件将返回空文本）。"""
    doc = fitz.open(pdf_path)
    try:
        return "\n".join(page.get_text() for page in doc)
    finally:
        doc.close()


def chunk_text(text: str, size: int = 12000, max_chunks: int = 6):
    """将长文本切块，供大模型分段提取数据。"""
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= size:
        return [text]
    chunks = [text[i:i + size] for i in range(0, len(text), size)]
    return chunks[:max_chunks]


# 中英支撑材料提及模式
_SUPP_PATTERNS = [
    r"[Ss]upplementary [Mm]aterials?", r"[Ss]upporting [Ii]nformation",
    r"[Ss]upplementary [Ii]nformation", r"[Ss]upplementary [Dd]ata",
    r"\bSI\b(?![a-zA-Z])", r"[Ss]upplementary [Nn]ote",
    r"Table S\d+", r"Fig\.? ?S\d+", r"Figure S\d+", r"Scheme S\d+",
    r"表S\d+", r"图S\d+", r"附表\d+", r"补充材料", r"支撑材料", r"附加材料",
    r"[Aa]ppendix", r"[Ee]lectronic [Ss]upplementary",
]


def find_supplementary_mentions(text: str) -> list:
    """检测正文中对支撑材料的引用，返回去重的提及列表（最多10个）。

    如 "Table S1"、"补充材料"，用于提示用户数据可能在支撑材料中。
    """
    found = []
    seen = set()
    for pat in _SUPP_PATTERNS:
        for m in re.finditer(pat, text or ""):
            s = m.group(0)
            key = s.lower()
            if key not in seen:
                seen.add(key)
                found.append(s)
            if len(found) >= 10:
                return found
    return found
