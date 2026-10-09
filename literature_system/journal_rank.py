# -*- coding: utf-8 -*-
"""期刊中科院分区查询模块。

知网/官方分区表无免费API，本模块内置常见高水平期刊分区（人工整理，仅供参考，
以中科院分区表最新版 / LetPub 为准）；未收录的期刊提供LetPub查询链接。
"""
import urllib.parse

# 期刊名（小写） -> 中科院分区（大类，近似值，仅供参考）
JOURNAL_RANKS = {
    "nature": "1区Top", "science": "1区Top", "cell": "1区Top",
    "nature communications": "1区", "science advances": "1区",
    "pnas": "1区Top", "proceedings of the national academy of sciences": "1区Top",
    "nature materials": "1区Top", "nature energy": "1区Top",
    "nature nanotechnology": "1区Top", "nature chemistry": "1区Top",
    "nature physics": "1区Top", "nature catalysis": "1区Top",
    "nature electronics": "1区Top", "nature machine intelligence": "1区Top",
    "chemical reviews": "1区Top", "chemical society reviews": "1区Top",
    "journal of the american chemical society": "1区Top",
    "angewandte chemie": "1区Top",
    "advanced materials": "1区Top", "advanced energy materials": "1区Top",
    "energy & environmental science": "1区Top", "joule": "1区Top",
    "advanced functional materials": "1区", "advanced science": "1区",
    "nano letters": "1区", "acs nano": "1区", "nano energy": "1区Top",
    "small": "2区", "nanoscale": "2区", "nanoscale horizons": "2区",
    "carbon": "1区", "acta materialia": "1区",
    "applied surface science": "1区", "materials today": "1区",
    "materials today advances": "2区",
    "journal of materials chemistry a": "1区",
    "journal of materials chemistry b": "2区", "journal of materials chemistry c": "2区",
    "chemical engineering journal": "1区", "journal of power sources": "1区",
    "journal of alloys and compounds": "2区", "materials letters": "3区",
    "journal of energy chemistry": "1区", "energy storage materials": "1区",
    "applied energy": "1区Top", "energy": "1区", "renewable energy": "1区",
    "progress in materials science": "1区Top",
    "physical review letters": "1区Top", "physical review b": "2区",
    "applied physics letters": "2区", "journal of applied physics": "3区",
    "npj computational materials": "1区", "acta crystallographica": "3区",
    "acs applied materials & interfaces": "1区", "acs energy letters": "1区",
    "ieee transactions on pattern analysis": "1区Top", "pattern recognition": "1区",
    "neural networks": "2区", "artificial intelligence": "1区",
    "the lancet": "1区Top", "new england journal of medicine": "1区Top",
    "the bmj": "1区Top", "plos one": "3区", "elife": "2区",
    "nucleic acids research": "1区", "bioactive materials": "1区",
    "科学通报": "2区", "chinese science bulletin": "2区",
    "science china materials": "1区", "中国科学材料": "1区",
    "中国科学:化学": "1区", "化学学报": "2区", "物理学报": "2区",
    "新型炭材料": "3区", "无机材料学报": "3区", "材料工程": "3区",
    "中国材料进展": "4区",
}

UNKNOWN = "未收录"


def lookup_rank(journal: str) -> str:
    """按期刊名模糊查询中科院分区，返回如 '≈1区Top'；未收录返回 '未收录'。"""
    j = (journal or "").strip().lower()
    if not j:
        return UNKNOWN
    if j in JOURNAL_RANKS:
        return f"≈{JOURNAL_RANKS[j]}"
    # 子串匹配（OpenAlex返回的期刊名常带括号等后缀）
    for name, rank in JOURNAL_RANKS.items():
        if name in j or j in name:
            return f"≈{rank}"
    return UNKNOWN


def letpub_link(journal: str) -> str:
    """未收录期刊的LetPub查询链接。"""
    return ("https://www.letpub.com.cn/index.php?page=journalapp&view=search&searchname="
            + urllib.parse.quote(journal or ""))
