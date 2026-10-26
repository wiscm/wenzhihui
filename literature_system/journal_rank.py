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

# 期刊名（小写） -> 影响因子（近似值，参考 JCR 近年，仅供排序/参考；
# 精确数值请以官方 JCR / 期刊官网 / LetPub 为准）
IMPACT_FACTOR = {
    "nature": 64.8, "science": 56.9, "cell": 45.5,
    "nature communications": 16.6, "science advances": 13.6,
    "pnas": 11.1, "proceedings of the national academy of sciences": 11.1,
    "nature materials": 41.8, "nature energy": 56.7,
    "nature nanotechnology": 38.1, "nature chemistry": 24.3,
    "nature physics": 19.6, "nature catalysis": 44.6,
    "nature electronics": 33.7, "nature machine intelligence": 23.8,
    "chemical reviews": 62.1, "chemical society reviews": 46.2,
    "journal of the american chemical society": 16.4,
    "angewandte chemie": 16.6,
    "advanced materials": 29.4, "advanced energy materials": 27.8,
    "energy & environmental science": 39.7, "joule": 41.1,
    "advanced functional materials": 19.0, "advanced science": 15.1,
    "nano letters": 10.8, "acs nano": 17.1, "nano energy": 19.0,
    "small": 13.3, "nanoscale": 6.7, "nanoscale horizons": 9.4,
    "carbon": 10.9, "acta materialia": 9.2,
    "applied surface science": 6.7, "materials today": 26.4,
    "materials today advances": 7.6,
    "journal of materials chemistry a": 11.9,
    "journal of materials chemistry b": 7.4, "journal of materials chemistry c": 6.4,
    "chemical engineering journal": 15.1, "journal of power sources": 9.2,
    "journal of alloys and compounds": 6.2, "materials letters": 3.0,
    "journal of energy chemistry": 14.0, "energy storage materials": 20.4,
    "applied energy": 11.2, "energy": 9.0, "renewable energy": 9.0,
    "progress in materials science": 37.4,
    "physical review letters": 9.2, "physical review b": 3.7,
    "applied physics letters": 3.6, "journal of applied physics": 2.7,
    "npj computational materials": 9.7, "acta crystallographica": 3.0,
    "acs applied materials & interfaces": 9.5, "acs energy letters": 22.0,
    "ieee transactions on pattern analysis": 20.8, "pattern recognition": 8.0,
    "neural networks": 7.8, "artificial intelligence": 9.0,
    "the lancet": 168.9, "new england journal of medicine": 96.2,
    "the bmj": 93.6, "plos one": 3.7, "elife": 6.4,
    "nucleic acids research": 16.6, "bioactive materials": 18.0,
    "科学通报": 1.1, "chinese science bulletin": 1.1,
    "science china materials": 6.8, "中国科学材料": 6.8,
    "中国科学:化学": 9.0, "化学学报": 1.0, "物理学报": 1.0,
}


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


def get_impact_factor(journal: str):
    """按期刊名查询影响因子（float），未收录返回 None。"""
    j = (journal or "").strip().lower()
    if not j:
        return None
    if j in IMPACT_FACTOR:
        return IMPACT_FACTOR[j]
    for name, fac in IMPACT_FACTOR.items():
        if name in j or j in name:
            return fac
    return None


def letpub_link(journal: str) -> str:
    """未收录期刊的LetPub查询链接。"""
    return ("https://www.letpub.com.cn/index.php?page=journalapp&view=search&searchname="
            + urllib.parse.quote(journal or ""))
