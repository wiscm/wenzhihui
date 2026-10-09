# -*- coding: utf-8 -*-
"""统一文献数据模型。"""
from dataclasses import dataclass, field, asdict


@dataclass
class Paper:
    source: str = ""          # 来源：arXiv / PubMed/PMC / Semantic Scholar / OpenAlex
    paper_id: str = ""        # 全局唯一ID，如 "arxiv:2401.00001"
    title: str = ""
    authors: list = field(default_factory=list)
    year: str = ""
    journal: str = ""
    abstract: str = ""
    doi: str = ""
    url: str = ""             # 文献落地页
    pdf_url: str = ""         # 可直接下载的PDF链接（可能为空）
    citations: int = 0        # 被引次数
    matched_keywords: list = field(default_factory=list)  # 命中的检索关键词（用于高亮）
    is_repeat: bool = False   # 是否为本次检索前已检索过的历史文献
    extra: dict = field(default_factory=dict)  # pmcid、is_oa、fulltext_url 等

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "Paper":
        base = {k: v for k, v in d.items() if k in Paper.__dataclass_fields__}
        return Paper(**base)
