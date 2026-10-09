# -*- coding: utf-8 -*-
"""文献数据获取系统 - Streamlit 主应用。

功能：
① 批量检索文献（arXiv / PubMed-PMC / Semantic Scholar / OpenAlex）+ AI批量速读
② 下载文献PDF与支撑材料到本地
③ AI阅读文献并提取数据（默认数值/表格字段 + 用户自定义字段），支持在线阅读无PDF文献
④ 数据统一存储到本地Excel，可查看/导出
"""
import os
import glob
import json
import io
import re
import time
import base64
import hashlib
import html as html_mod
import datetime

import pandas as pd
import streamlit as st

from literature_system import ai_client, background, cn_searchers, downloader, \
    excel_store, journal_rank, pdf_reader, search_history, searchers, translator
from literature_system.models import Paper

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
PDF_DIR = os.path.join(DATA_DIR, "pdfs")
SUPP_DIR = os.path.join(DATA_DIR, "supplementary")
CONFIG_PATH = os.path.join(DATA_DIR, "config.json")
HIST_PATH = os.path.join(DATA_DIR, "search_history.json")
for d in (DATA_DIR, PDF_DIR, SUPP_DIR):
    os.makedirs(d, exist_ok=True)

LOGO_PATH = os.path.join(BASE_DIR, "assets", "logo.png")
LOGO_B64 = ""
if os.path.exists(LOGO_PATH):
    with open(LOGO_PATH, "rb") as _f:
        LOGO_B64 = base64.b64encode(_f.read()).decode()

st.set_page_config(
    page_title="文智汇 · 文献智能数据工作站",
    page_icon=LOGO_PATH if os.path.exists(LOGO_PATH) else "🪶",
    layout="wide")

SOURCE_OPTIONS = ["arXiv", "PubMed/PMC", "Semantic Scholar", "OpenAlex", "中文文献"]

# ------------------------------------------------------------ 全局样式
GLOBAL_CSS = """
<style>
/* ---------- 主页 Hero ---------- */
.hero{
    text-align:center; padding:2.4rem 1.2rem 1.8rem; margin-bottom:1.3rem;
    background:linear-gradient(135deg,#0f2b46 0%,#1a4e8a 55%,#0e7c86 100%);
    border-radius:18px; color:#fff;
    box-shadow:0 6px 24px rgba(15,43,70,.25);
}
.hero h1{font-size:2.7rem; margin:.4rem 0 .05rem; color:#fff; letter-spacing:.06em;}
.hero-badge{
    display:inline-block; background:rgba(255,255,255,.15);
    border:1px solid rgba(255,255,255,.38); padding:.28rem 1rem;
    border-radius:999px; font-size:.82rem; letter-spacing:.18em;
}
.hero-sub{font-size:1.18rem; opacity:.95; margin:.15rem 0 .5rem; font-weight:600;}
.hero-desc{opacity:.88; font-size:.95rem; max-width:660px; margin:0 auto; line-height:1.6;}

/* ---------- 功能卡片 ---------- */
.fcard{
    background:#ffffff; border:1px solid #e3e8ef; border-radius:14px;
    border-top:4px solid #1a4e8a; padding:1.15rem 1rem 1rem; height:100%;
    box-shadow:0 2px 10px rgba(15,40,70,.07); margin-bottom:.55rem;
    transition:transform .15s ease, box-shadow .15s ease;
}
.fcard:hover{transform:translateY(-3px); box-shadow:0 8px 20px rgba(15,40,70,.14);}
.fcard .ficon{font-size:1.9rem; line-height:1;}
.fcard h3{margin:.45rem 0 .4rem; font-size:1.06rem; color:#12324f;}
.fcard p{color:#5b6b7c; font-size:.86rem; line-height:1.55; margin:0;}

/* ---------- 四列卡片等高对齐：按钮统一沉底 ---------- */
@supports selector(:has(*)) {
    [data-testid="stHorizontalBlock"]:has(.fcard) {align-items:stretch;}
    [data-testid="stHorizontalBlock"]:has(.fcard) > [data-testid="stColumn"] {
        height:100%; display:flex; flex-direction:column;
    }
    [data-testid="stHorizontalBlock"]:has(.fcard) > [data-testid="stColumn"]
        > [data-testid="stVerticalBlock"] {
        flex:1 1 auto; display:flex; flex-direction:column; row-gap:.9rem;
    }
    [data-testid="stHorizontalBlock"]:has(.fcard) > [data-testid="stColumn"]
        > [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"]:first-child {
        flex:1 1 auto; display:flex; flex-direction:column;
    }
    [data-testid="stHorizontalBlock"]:has(.fcard) > [data-testid="stColumn"]
        > [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"]:first-child
        > [data-testid="stMarkdown"],
    [data-testid="stHorizontalBlock"]:has(.fcard) [data-testid="stMarkdown"] > div,
    [data-testid="stHorizontalBlock"]:has(.fcard) [data-testid="stMarkdownContainer"] {
        flex:1 1 auto; display:flex; flex-direction:column;
    }
    [data-testid="stHorizontalBlock"]:has(.fcard) .fcard {
        height:290px; min-height:0; overflow-y:auto; scrollbar-width:thin;
    }
}

/* ---------- 快速上手 ---------- */
.steps{
    background:#f6f9fc; border:1px solid #e3e8ef; border-radius:14px;
    padding:1.1rem 1.3rem; margin-top:1.3rem;
}
.step-chip{
    display:inline-block; background:#1a4e8a; color:#fff; width:1.55rem;
    height:1.55rem; line-height:1.55rem; border-radius:50%; text-align:center;
    font-weight:700; margin-right:.5rem; font-size:.85rem;
}

/* ---------- 次级按钮统一美化 ---------- */
.stButton > button[kind="secondary"]{
    border-radius:10px; border:1.5px solid #1a4e8a; color:#1a4e8a;
    font-weight:600; transition:all .15s;
}
.stButton > button[kind="secondary"]:hover{
    background:#1a4e8a; color:#fff; border-color:#1a4e8a;
}
</style>
"""

NAV_LABELS = [
    "🏠 主页",
    "① 文献检索与AI速读",
    "② 下载文献与支撑材料",
    "③ AI阅读与数据提取",
    "④ 数据管理（Excel）",
]

HOME_FEATURES = [
    ("🔎", "智能检索", "多来源并行检索（arXiv · PubMed · Semantic Scholar · OpenAlex · 中文文献）。"
     "多关键词彩色高亮、引用量与期刊分区一目了然，还能与AI对话让它帮你定检索方案。",
     "① 文献检索与AI速读", "#1a4e8a"),
    ("⬇️", "一键下载", "PDF与支撑材料批量下载，任务在后台运行——下载途中随时切换到其他功能，"
     "绝不中断，随时回来领取结果。", "② 下载文献与支撑材料", "#0e7c86"),
    ("🤖", "AI精读与对话", "领域模板（材料学/能源/化学/生物医学…）批量提取性能、工艺、结构等实验数据；"
     "还能就文献内容与AI自由对话，你在检索时提的要求它都记得。",
     "③ AI阅读与数据提取", "#8e44ad"),
    ("📊", "数据管理", "提取结果统一存入Excel/CSV，字段规范、直接可用作机器学习数据集，"
     "支持导出与在线查看。", "④ 数据管理（Excel）", "#d35400"),
]


def _nav_to(target: str):
    """主页卡片按钮回调：下一次脚本运行前修改导航状态（避免widget已实例化的报错）。"""
    st.session_state.nav_page = target


def render_home():
    """主页：品牌展示 + 四大功能卡片 + 快速上手。"""
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)
    _hero_logo = (f'<img src="data:image/png;base64,{LOGO_B64}" '
                  'style="width:88px;height:88px;border-radius:20px;'
                  'box-shadow:0 4px 16px rgba(0,0,0,.28);margin-bottom:.4rem">'
                  if LOGO_B64 else "")
    st.markdown(
        '<div class="hero">'
        + _hero_logo +
        '<div class="hero-badge">A I 驱 动 · 本 地 部 署 · 数 据 直 存</div>'
        "<h1>文智汇</h1>"
        '<p class="hero-sub">文献智能获取与数据提炼工作站</p>'
        '<p class="hero-desc">一句需求，AI 帮你检索全球文献、后台下载全文、精读提炼'
        "实验数据，一键生成机器学习数据集。</p>"
        "</div>", unsafe_allow_html=True)

    cols = st.columns(4, gap="medium")
    for i, (icon, title, desc, target, color) in enumerate(HOME_FEATURES):
        with cols[i]:
            st.markdown(
                f'<div class="fcard" style="border-top-color:{color}">'
                f'<div class="ficon">{icon}</div><h3>{title}</h3><p>{desc}</p></div>',
                unsafe_allow_html=True)
            st.button(f"进入{title} →", key=f"home_go_{i}", use_container_width=True,
                      on_click=_nav_to, args=(target,))

    st.markdown(
        '<div class="steps">'
        '<h3 style="margin:.1rem 0 .6rem;color:#12324f">🚀 快速上手</h3>'
        '<p><span class="step-chip">1</span>在左侧边栏配置 AI 模型（OpenAI 兼容接口）</p>'
        '<p style="margin:.45rem 0"><span class="step-chip">2</span>去「① 文献检索」描述需求或输入关键词，'
        "勾选心仪文献</p>"
        '<p style="margin:.45rem 0"><span class="step-chip">3</span>「② 下载」后台批量下载，'
        "「③ AI阅读」批量提取实验数据（期间可随意切换页面）</p>"
        '<p style="margin:.45rem 0 0"><span class="step-chip">4</span>「④ 数据管理」'
        "查看并导出 Excel / CSV 数据集</p>"
        "</div>", unsafe_allow_html=True)

DEFAULT_CONFIG = {
    "base_url": "https://api.deepseek.com/v1",
    "api_key": "",
    "model": "deepseek-chat",
    "excel_path": os.path.join(DATA_DIR, "文献提取数据.xlsx"),
    "sheet": "提取数据",
    "pdf_dir": PDF_DIR,
    "supp_dir": SUPP_DIR,
}


# ------------------------------------------------------------------ 配置
def load_config() -> dict:
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        for k, v in DEFAULT_CONFIG.items():
            cfg.setdefault(k, v)
        return cfg
    except Exception:
        return dict(DEFAULT_CONFIG)


def save_config(cfg: dict):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception as ex:
        st.warning(f"配置保存失败: {ex}")


def get_ai() -> ai_client.AIClient:
    try:
        return ai_client.AIClient(
            st.session_state.cfg["base_url"].strip(),
            st.session_state.cfg["api_key"].strip(),
            st.session_state.cfg["model"].strip())
    except ValueError as ex:
        st.error(str(ex))
        st.stop()


def parse_custom_fields(txt: str) -> list:
    fields = []
    for line in (txt or "").splitlines():
        line = line.strip()
        if not line:
            continue
        if "：" in line:
            name, desc = line.split("：", 1)
        elif ":" in line:
            name, desc = line.split(":", 1)
        else:
            name, desc = line, ""
        fields.append({"name": name.strip(), "desc": desc.strip()})
    return fields


def parse_queries(text: str) -> list:
    """解析多关键词输入：换行/逗号/顿号/分号分隔。"""
    parts = re.split(r"[\n,，、;；]", text or "")
    seen, out = set(), []
    for p in parts:
        p = p.strip()
        if p and p.lower() not in seen:
            seen.add(p.lower())
            out.append(p)
    return out


KW_COLORS = ["#e74c3c", "#2980b9", "#16a085", "#8e44ad", "#d35400",
             "#c0392b", "#f39c12", "#0e6655", "#6c3483", "#1f618d"]


def highlight_title(title: str, kw_variants: dict, matched: list) -> str:
    """按命中关键词给标题上色（不同关键词不同颜色）。"""
    esc = html_mod.escape(title or "")
    for idx, kw in enumerate(matched):
        color = KW_COLORS[idx % len(KW_COLORS)]
        for v in {kw} | set(kw_variants.get(kw, [])):
            v = (v or "").strip()
            if len(v) < 1:
                continue
            esc = re.sub(re.escape(v),
                         lambda m, c=color: f'<span style="color:{c};font-weight:700">'
                                            f"{m.group(0)}</span>",
                         esc, flags=re.I)
    return esc


def kw_legend(kw_variants: dict, matched_all: list) -> str:
    parts = []
    for idx, kw in enumerate(matched_all):
        color = KW_COLORS[idx % len(KW_COLORS)]
        parts.append(f'<span style="color:{color};font-weight:700">■ {html_mod.escape(kw)}</span>')
    return "　".join(parts)


# ------------------------------------------------------ 后台任务与需求共享
def get_search_context() -> str:
    """汇总①页的检索需求（AI检索对话、检索方案、关键词、提取要求），
    供③页AI提取与对话知晓，实现"检索提出的要求，提取时也知道"。"""
    parts = []
    if st.session_state.last_keywords:
        parts.append("本次检索关键词：" + "、".join(st.session_state.last_keywords))
    sug = st.session_state.get("chat_suggestion")
    if sug:
        bits = []
        if sug.get("keywords"):
            bits.append("关键词=" + "/".join(map(str, sug["keywords"])))
        if sug.get("authors"):
            bits.append("作者=" + "/".join(map(str, sug["authors"])))
        if sug.get("journals"):
            bits.append("期刊=" + "/".join(map(str, sug["journals"])))
        if sug.get("reason"):
            bits.append("理由=" + str(sug["reason"]))
        parts.append("AI给出的检索方案：" + "；".join(bits))
    hist = st.session_state.get("chat_history") or []
    user_said = [m.get("content", "") for m in hist if m.get("role") == "user"][-3:]
    if user_said:
        parts.append("用户检索时的原始需求：" + " | ".join(user_said))
    req = (st.session_state.get("extract_requirements") or "").strip()
    if req:
        parts.append("用户对数据提取的明确要求：" + req)
    return "\n".join(parts)


def render_ai_chat(ground_text: str, label: str):
    """③页AI对话区：就当前文献/批量结果与AI聊天，AI同时知晓①页需求。"""
    hist = st.session_state.extract_chat_history
    box = st.container(height=260)
    with box:
        if not hist:
            st.caption("（暂无对话。可让AI解释某个数据、对比实验条件、"
                       "建议补充哪些提取字段、检查数据合理性等）")
        for msg in hist:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
    q = st.chat_input(f"就{label}向AI提问…")
    if q:
        hist.append({"role": "user", "content": q})
        ai = get_ai()
        with st.chat_message("assistant"):
            with st.spinner("AI正在思考…"):
                try:
                    ans = ai.chat_about_paper(ground_text, hist[:-1], get_search_context())
                except Exception as ex:
                    ans = f"AI对话失败: {ex}"
            st.markdown(ans)
        hist.append({"role": "assistant", "content": ans})
        st.rerun()
    if hist and st.button("🗑 清空对话记录"):
        st.session_state.extract_chat_history = []
        st.rerun()


def poll_task(task, poll_secs: float = 1.5):
    """显示后台任务实时进度并自动刷新本页；任务线程独立运行，切换页面不中断。"""
    st.info(f"⚙️ **{task.name}** 正在后台运行…可自由切换到其他页面，任务不会中断。")
    st.progress(max(task.progress, 0.01), text=task.status_text or "处理中…")
    pc1, pc2 = st.columns([1, 2])
    if pc1.button("🛑 取消任务", key=f"cancel_{task.id}"):
        task.cancel()
        pc2.warning("已发送取消请求，当前条目处理完后停止")
    time.sleep(poll_secs)
    st.rerun()


def claim_task(tid: str):
    """领取已结束后台任务的结果（每个任务只领取一次）。返回Task或None。"""
    if not tid or tid in st.session_state.claimed_bg:
        return None
    task = background.MANAGER.get(tid)
    if task is not None and task.done:
        st.session_state.claimed_bg.add(tid)
        return task
    return None


def _bg_download(task, papers, pdf_dir, supp_dir):
    """后台线程：批量下载PDF+支撑材料。返回 {paper_id: {pdf_path, supp_files}}。"""
    rmap = {}
    n = len(papers)
    for j, pdict in enumerate(papers):
        task.check_cancel()
        paper = Paper.from_dict(pdict)
        pdf_path, err = downloader.download_pdf(paper, pdf_dir)
        supp = downloader.download_supplementary(paper, supp_dir)
        rmap[pdict["paper_id"]] = {"pdf_path": pdf_path or "", "supp_files": supp}
        task.add_log({
            "标题": pdict["title"], "来源": pdict["source"],
            "PDF": "✅ 已下载" if pdf_path else f"❌ {err or '无链接'}",
            "支撑材料": f"✅ {len(supp)} 个文件" if supp else "—",
        })
        task.set_progress((j + 1) / n, f"{j + 1}/{n}：{pdict['title'][:40]}")
    return rmap


def _bg_batch(task, pool, base_url, api_key, model, bfields, data_kws,
              only_fulltext, make_report, domain_label, req_ctx):
    """后台线程：批量AI阅读与数据提取。返回 {records, report, log}。"""
    ai = ai_client.AIClient(base_url, api_key, model)
    records, report, log = [], [], []
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    n = len(pool)
    for bi, bp in enumerate(pool):
        task.check_cancel()
        paper = Paper.from_dict(bp)
        text, kind, note = "", "none", ""
        lp = bp.get("pdf_path") or ""
        if lp and os.path.exists(lp):
            text = pdf_reader.extract_pdf_text(lp)
            if len(text.strip()) < 100:
                text, note = "", "PDF无文本层(扫描件)"
            else:
                kind, note = "fulltext", "PDF全文"
        if not text:
            if bp.get("local_only"):
                log.append({"标题": bp["title"][:50], "阅读方式": "本地PDF",
                            "状态": "❌ PDF无文本层(扫描件)，已跳过。请OCR后再试"})
            else:
                text, kind = downloader.fetch_online_text(paper)
                note = note or ("在线全文" if kind == "fulltext"
                                else ("仅摘要" if text else "无文本"))
        if not text:
            log.append({"标题": bp["title"][:50], "阅读方式": "-",
                        "状态": "❌ 无可用文本，已跳过"})
        elif only_fulltext and kind == "abstract":
            log.append({"论文标题": bp["title"], "阅读方式": "摘要",
                        "状态": "⚠️ 无正文全文（仅摘要），已跳过数据提取。"
                                "请下载PDF后在③页上传提取。"})
            if make_report:
                try:
                    summ = ai.summarize(text)
                except Exception as ex:
                    summ = f"总结失败: {ex}"
                report.append({"论文标题": bp["title"],
                               "作者": ", ".join(bp["authors"][:8]),
                               "年份": bp["year"], "期刊": bp["journal"],
                               "AI总结(基于摘要)": summ.replace("\n", " "),
                               "备注": "无正文全文，未提取数据"})
        else:
            supp_m = pdf_reader.find_supplementary_mentions(text)
            meta = {"论文标题": bp["title"],
                    "作者": ", ".join(bp["authors"][:8]),
                    "年份": bp["year"], "期刊": bp["journal"],
                    "期刊分区": journal_rank.lookup_rank(bp["journal"]),
                    "引用量": bp.get("citations", 0),
                    "DOI": bp["doi"] or "-", "来源": bp["source"],
                    "命中关键词": "、".join(bp.get("matched_keywords", [])),
                    "提取时间": now, "数据类型": domain_label,
                    "数据关键词": "、".join(data_kws) or "-",
                    "阅读方式": note}
            n_rec = 0
            if make_report:
                try:
                    summ = ai.summarize(text)
                except Exception as ex:
                    summ = f"总结失败: {ex}"
                row_r = dict(meta)
                row_r["AI总结"] = summ.replace("\n", " ")
                if supp_m:
                    row_r["支撑材料提示"] = (
                        "正文提及支撑材料（" + "、".join(supp_m[:6]) +
                        "），部分数据可能在支撑材料中，请到②页下载")
                report.append(row_r)
            for chunk in pdf_reader.chunk_text(text):
                task.check_cancel()
                try:
                    rs = ai.extract_data(chunk, bfields, data_keywords=data_kws or None,
                                         is_abstract=(kind == "abstract"),
                                         supp_hints="、".join(supp_m[:6]),
                                         user_requirements=req_ctx) or []
                except Exception:
                    rs = []
                for r in rs:
                    r.update(meta)
                records.extend(rs)
                n_rec += len(rs)
            status = f"✅ 提取 {n_rec} 条数据记录"
            if supp_m:
                status += f"｜📎 正文提及支撑材料（{'、'.join(supp_m[:4])}）"
            log.append({"标题": bp["title"][:50], "阅读方式": note, "状态": status})
        task.set_progress((bi + 1) / n, f"{bi + 1}/{n}：{bp['title'][:40]}")
    return {"records": records, "report": report, "log": log}


def _bg_extract_single(task, text, base_url, api_key, model, fields, data_kws,
                       question, is_abstract, supp_str, read_label, req_ctx):
    """后台线程：单篇AI阅读+分块数据提取+附加问答。"""
    ai = ai_client.AIClient(base_url, api_key, model)
    out = {"summary": "", "answer": "", "records": [], "read_label": read_label,
           "warnings": []}
    try:
        task.set_progress(0.05, "AI正在通读文献…")
        out["summary"] = ai.summarize(text)
    except Exception as ex:
        out["warnings"].append({"阶段": "AI总结", "状态": f"❌ {ex}"})
    chunks = pdf_reader.chunk_text(text)
    for ci, chunk in enumerate(chunks):
        task.check_cancel()
        try:
            out["records"] += ai.extract_data(
                chunk, fields, data_keywords=data_kws or None,
                is_abstract=is_abstract, supp_hints=supp_str,
                user_requirements=req_ctx) or []
        except Exception as ex:
            out["warnings"].append({"阶段": f"第{ci + 1}段提取", "状态": f"❌ {ex}"})
        task.set_progress(0.1 + 0.85 * (ci + 1) / max(len(chunks), 1),
                          f"数据提取中 {ci + 1}/{len(chunks)}")
    if question:
        task.set_progress(0.97, "回答附加问题…")
        try:
            out["answer"] = ai.answer_question(text, question)
        except Exception as ex:
            out["answer"] = f"回答失败: {ex}"
    return out


# ------------------------------------------------------------ 会话状态
if "cfg" not in st.session_state:
    st.session_state.cfg = load_config()
if "results" not in st.session_state:
    st.session_state.results = []          # list[dict]
if "selected" not in st.session_state:
    st.session_state.selected = {}         # paper_id -> bool
if "digest" not in st.session_state:
    st.session_state.digest = None         # AI批量速读结果
if "download_log" not in st.session_state:
    st.session_state.download_log = None
if "extract_paper_id" not in st.session_state:
    st.session_state.extract_paper_id = ""
if "summary" not in st.session_state:
    st.session_state.summary = ""
if "answer" not in st.session_state:
    st.session_state.answer = ""
if "extract_records" not in st.session_state:
    st.session_state.extract_records = []
if "current_text" not in st.session_state:
    st.session_state.current_text = ""
if "sel_version" not in st.session_state:
    st.session_state.sel_version = 0            # 勾选框版本号（一键全选时+1以刷新）
if "kw_variants" not in st.session_state:
    st.session_state.kw_variants = {}           # {关键词: [中文/英文变体]} 用于高亮
if "last_keywords" not in st.session_state:
    st.session_state.last_keywords = []         # 最近一次检索的关键词列表
if "trans_info" not in st.session_state:
    st.session_state.trans_info = None
if "search_note" not in st.session_state:
    st.session_state.search_note = None         # 检索统计说明（含历史重复提示）
if "batch_records" not in st.session_state:
    st.session_state.batch_records = []         # 批量提取结果
if "batch_report" not in st.session_state:
    st.session_state.batch_report = []          # 批量AI阅读报告
if "batch_log" not in st.session_state:
    st.session_state.batch_log = []             # 批量处理日志
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []          # AI检索对话历史
if "chat_suggestion" not in st.session_state:
    st.session_state.chat_suggestion = None     # AI给出的检索方案
if "extract_requirements" not in st.session_state:
    st.session_state.extract_requirements = ""  # ①页写下的提取要求，同步给③页AI
if "extract_chat_history" not in st.session_state:
    st.session_state.extract_chat_history = []  # ③页AI对话历史
if "bg_download_id" not in st.session_state:
    st.session_state.bg_download_id = ""        # 后台下载任务ID
if "bg_batch_id" not in st.session_state:
    st.session_state.bg_batch_id = ""           # 后台批量提取任务ID
if "bg_single_id" not in st.session_state:
    st.session_state.bg_single_id = ""          # 后台单篇提取任务ID
if "claimed_bg" not in st.session_state:
    st.session_state.claimed_bg = set()         # 已领取结果的后台任务ID
if "text_cache" not in st.session_state:
    st.session_state.text_cache = {}            # 文本获取缓存（避免轮询时重复解析PDF）
if "local_papers" not in st.session_state:
    st.session_state.local_papers = []          # ③页从本地文件夹添加的文献
if "local_pdf_scan" not in st.session_state:
    st.session_state.local_pdf_scan = []        # 本地文件夹扫描结果
if "local_pdf_pick" not in st.session_state:
    st.session_state.local_pdf_pick = set()     # 本地PDF勾选状态

# ------------------------------------------------------------------ 侧边栏
with st.sidebar:
    _logo_img = (f'<img src="data:image/png;base64,{LOGO_B64}" '
                 'style="width:54px;height:54px;border-radius:12px;'
                 'box-shadow:0 2px 8px rgba(15,43,70,.25)">'
                 if LOGO_B64 else '<div style="font-size:2rem">🪶</div>')
    st.markdown(
        '<div style="text-align:center;padding:.2rem 0 .6rem">'
        + _logo_img +
        '<div style="font-size:1.5rem;font-weight:800;color:#1a4e8a;letter-spacing:.08em;margin-top:.3rem">文智汇</div>'
        '<div style="font-size:.78rem;color:#7a8a99;margin-top:.15rem">文献智能获取与数据提炼工作站</div>'
        "</div>", unsafe_allow_html=True)

    st.subheader("AI模型设置（OpenAI兼容）")
    st.session_state.cfg["base_url"] = st.text_input(
        "Base URL", value=st.session_state.cfg["base_url"],
        help="例如：https://api.deepseek.com/v1 或其他OpenAI兼容地址")
    st.session_state.cfg["api_key"] = st.text_input(
        "API Key", value=st.session_state.cfg["api_key"], type="password")
    st.session_state.cfg["model"] = st.text_input(
        "模型名", value=st.session_state.cfg["model"], help="例如 deepseek-chat")
    st.session_state.cfg["excel_path"] = st.text_input(
        "默认Excel存储路径", value=st.session_state.cfg["excel_path"])
    st.session_state.cfg["sheet"] = st.text_input(
        "默认工作表名", value=st.session_state.cfg["sheet"])
    st.subheader("存储位置（可改为任意目录）")
    st.session_state.cfg["pdf_dir"] = st.text_input(
        "PDF保存目录", value=st.session_state.cfg["pdf_dir"],
        help="文献PDF将下载到该目录，也可在“② 下载文献”页修改")
    st.session_state.cfg["supp_dir"] = st.text_input(
        "支撑材料保存目录", value=st.session_state.cfg["supp_dir"])
    if st.button("💾 保存设置", use_container_width=True):
        save_config(st.session_state.cfg)
        st.success("设置已保存到 data/config.json")

    st.divider()
    page = st.radio("功能导航", NAV_LABELS, key="nav_page", label_visibility="collapsed")

    # 后台任务状态（所有页面可见：切换页面任务不中断）
    _running = background.MANAGER.running()
    if _running:
        st.divider()
        st.caption("⚙️ 后台任务（切换页面不会中断）")
        for t in _running[:3]:
            st.progress(max(t.progress, 0.01),
                        text=f"{t.name} {int((t.progress or 0) * 100)}%")
    for t in background.MANAGER.finished_unclaimed(st.session_state.claimed_bg)[:3]:
        if t.status == "done":
            st.success(f"✅ {t.name} 已完成，请到对应页面查看结果")
        elif t.status == "failed":
            st.error(f"❌ {t.name} 失败：{t.error}")
        else:
            st.warning(f"⬇️ {t.name} 已取消")

# ============================================================ 主页
if page.startswith("🏠"):
    render_home()

# ============================================================ 页面1：检索
elif page.startswith("①"):
    st.header("① 文献批量检索与AI速读")
    st.caption("🤖AI对话检索：说清你想要什么文献，AI帮你定检索词 | 手动检索：多关键词/作者/期刊、"
               "命中关键词彩色标注、引用量与期刊分区、历史去重")

    # ============================ AI检索对话助手 ============================
    with st.expander("🤖 AI智能检索助手（对话式，说清需求让AI帮你检索）",
                     expanded=False):
        st.caption("示例：\"我想找镁合金拉伸性能和热处理工艺相关的文献，近几年的\"，"
                   "AI会进一步确认需求，然后给出检索方案并可直接执行检索")
        hist = st.session_state.chat_history
        if hist:
            chat_box = st.container(height=260)
            with chat_box:
                for msg in hist:
                    with st.chat_message(msg["role"]):
                        st.markdown(msg["content"])
        user_msg = st.chat_input("描述你想找哪方面的文献…")
        if user_msg:
            hist.append({"role": "user", "content": user_msg})
            ai = get_ai()
            with st.chat_message("assistant"):
                with st.spinner("AI正在思考…"):
                    try:
                        reply, sug = ai.search_assistant(hist)
                    except Exception as ex:
                        reply, sug = f"AI对话失败: {ex}", None
                st.markdown(reply)
            hist.append({"role": "assistant", "content": reply})
            if sug:
                st.session_state.chat_suggestion = sug
        sug = st.session_state.chat_suggestion
        if sug:
            st.success("✅ AI已给出检索方案，可在下方确认执行，也可复制到手动检索框修改")
            sc1, sc2, sc3 = st.columns(3)
            kw = sug.get("keywords") or []
            aus = sug.get("authors") or []
            jns = sug.get("journals") or []
            sc1.markdown(f"**关键词**（{len(kw)}个）：\n" + "\n".join(f"- {k}" for k in kw)
                         or "- 无")
            sc2.markdown(f"**作者**：{'、'.join(aus) or '无'}")
            sc3.markdown(f"**期刊**：{'、'.join(jns) or '无'}")
            if sug.get("reason"):
                st.caption("理由：" + str(sug["reason"]))
            if st.button("🚀 按AI方案立即检索", type="primary"):
                # 组装检索方案：关键词为主；作者/期刊分别追加为独立检索类型
                plan = []
                if kw:
                    plan.append(("keyword", kw))
                if aus:
                    plan.append(("author", aus))
                if jns:
                    plan.append(("journal", jns))
                st.session_state.chat_search_plan = plan
                st.rerun()

    st.divider()

    def execute_search(queries, search_type, sources, n_per, bilingual, hide_repeat):
        """执行一轮完整检索（翻译→检索→历史去重→存结果）。返回错误dict。"""
        type_label = {"keyword": "关键词", "author": "作者", "journal": "期刊"}[search_type]
        zh_map, variants = {}, {}
        if bilingual and search_type == "keyword":
            ai = None
            c = st.session_state.cfg
            if c["base_url"].strip() and c["api_key"].strip() and c["model"].strip():
                try:
                    ai = ai_client.AIClient(c["base_url"].strip(), c["api_key"].strip(),
                                            c["model"].strip())
                except Exception:
                    ai = None
            zh_items = [q for q in queries if cn_searchers.contains_cjk(q)]
            en_items = [q for q in queries if not cn_searchers.contains_cjk(q)]
            try:
                with st.spinner("正在批量翻译关键词…"):
                    if zh_items:
                        ens = translator.translate_many(zh_items, "en", ai)
                        for z, e in zip(zh_items, ens):
                            variants[z] = [z, e]
                            zh_map[z] = z
                    if en_items:
                        zhs = translator.translate_many(en_items, "zh", ai)
                        for e, z in zip(en_items, zhs):
                            variants[e] = [e, z]
                            zh_map[e] = z
                st.session_state.trans_info = "🌐 关键词翻译对照：" + "；".join(
                    f"「{k}」⇄「{' / '.join(vs)}」" for k, vs in variants.items())
            except Exception as ex:
                st.session_state.trans_info = None
                st.warning(f"关键词翻译失败，将使用原文检索：{ex}")
        else:
            st.session_state.trans_info = None
        # 历史检索记录
        hist = search_history.load(HIST_PATH)
        hkey = search_history.hist_key(search_type, queries)
        seen = search_history.seen_ids(hist, hkey)
        prog = st.progress(0.0, text="检索中…")
        papers, errors = searchers.search_all(
            queries, sources, n_per, search_type=search_type,
            zh_map=zh_map if search_type == "keyword" else None,
            progress_cb=lambda f, txt: prog.progress(f, text=txt))
        prog.empty()
        n_repeat = 0
        for p in papers:
            p.is_repeat = p.paper_id in seen
            if p.is_repeat:
                n_repeat += 1
        search_history.record(hist, hkey, [p.paper_id for p in papers])
        search_history.save(HIST_PATH, hist)
        shown = [p for p in papers if not (hide_repeat and p.is_repeat)] \
            if hide_repeat else papers
        st.session_state.results = [p.to_dict() for p in shown]
        st.session_state.last_keywords = queries
        st.session_state.kw_variants = variants
        st.session_state.selected = {}
        st.session_state.sel_version += 1
        st.session_state.digest = None
        st.session_state.search_note = (
            f"按{type_label}检索 {len(queries)} 个词，共命中 {len(papers)} 篇（去重后）；"
            f"其中历史已检索过 {n_repeat} 篇（{'已过滤隐藏' if hide_repeat else '已标注⚠️'}），"
            f"本次新增 {len(papers) - n_repeat} 篇，当前展示 {len(shown)} 篇。")
        return errors

    # ---------- 执行AI检索方案 ----------
    if st.session_state.get("chat_search_plan"):
        plan = st.session_state.pop("chat_search_plan")
        all_errors = {}
        for stype, squeries in plan:
            if not squeries:
                continue
            errs = execute_search(squeries, stype, SOURCE_OPTIONS, 10, True, True)
            all_errors.update(errs)
        for s, err in all_errors.items():
            st.warning(f"来源 [{s}] 检索失败：{err}")
        st.rerun()

    # ============================ 手动检索区 ============================
    c1, c2 = st.columns([3, 1])
    search_type_label = c1.selectbox("检索类型", ["关键词", "作者", "期刊"])
    search_type = {"关键词": "keyword", "作者": "author", "期刊": "journal"}[search_type_label]
    qtext = c1.text_area(
        "检索内容（支持多个：每行一个，或用逗号/顿号/分号分隔）",
        height=110,
        placeholder="关键词示例：\n石墨烯导热\nlithium battery\n钙钛矿\n"
                    "作者示例：每行一位作者，如 Zhang Wei\n"
                    "期刊示例：每行一个期刊，如 Nature / Carbon")
    n_per = c2.number_input("每个来源每词篇数上限", 1, 100, 10)
    sources = st.multiselect("检索来源", SOURCE_OPTIONS, default=SOURCE_OPTIONS)
    bilingual = st.checkbox(
        "🌐 中英双语检索（自动在线翻译）", value=(search_type == "keyword"),
        help="输入中文时自动译为英文检索国际库；输入英文时自动译为中文检索中文库。"
             "翻译优先使用已配置的AI模型（一次调用批量翻译全部关键词），其次尝试免费接口。")
    hide_repeat = st.checkbox(
        "🚫 过滤历史已检索过的文献", value=True,
        help="同一组关键词再次检索时，之前出现过的文献默认隐藏；"
             "关闭后重复文献会保留并标注⚠️提示")

    queries = parse_queries(qtext)

    if st.button("🔍 开始检索", type="primary", disabled=not queries):
        if not sources:
            st.warning("请至少选择一个检索来源")
        else:
            errs = execute_search(queries, search_type, sources, int(n_per),
                                  bilingual, hide_repeat)
            for s, err in errs.items():
                st.warning(f"来源 [{s}] 检索失败：{err}")

    if st.session_state.get("trans_info"):
        st.info(st.session_state["trans_info"])
    if st.session_state.get("search_note"):
        st.success(st.session_state["search_note"])

    # 数据提取要求：①页写下，③页的AI提取与对话都会遵循
    with st.expander("📋 数据提取要求（写入后自动同步到 ③ AI阅读与数据提取 页）"):
        st.session_state.extract_requirements = st.text_area(
            "你对数据提取的要求/说明",
            value=st.session_state.extract_requirements, height=90,
            placeholder="例如：只要拉伸强度和硬度的数据；重点关注热处理温度的影响；"
                        "每条数据必须带单位和测试条件；表格数据优先；按样品分行…",
            help="③页AI批量/单篇提取数据以及与AI对话时，都会读取并遵循这里的要求。")

    # 中文文献库直达链接（知网/万方等无免费API，提供手动检索入口）
    if queries:
        st.markdown("**🔗 中文文献库直达链接**（知网/万方无免费API，可手动浏览、下载PDF后在"
                    "“③ AI阅读与数据提取”页上传给AI提取数据）：")
        link_cols = st.columns(5)
        for (name, url), col in zip(cn_searchers.get_cn_manual_links(queries[0]).items(),
                                    link_cols):
            col.markdown(f"[{name}]({url})")

    results = st.session_state.results
    if not results:
        st.info("输入检索内容并点击“开始检索”。检索到的文献可勾选加入下载/提取列表。")
    else:
        # 关键词颜色图例
        if st.session_state.last_keywords:
            st.markdown("**关键词颜色对照：** " + kw_legend(
                st.session_state.kw_variants, st.session_state.last_keywords),
                unsafe_allow_html=True)

        # 工具栏：一键全选 / 清空
        tb1, tb2, tb3 = st.columns([1, 1, 2])
        if tb1.button("✅ 一键全选"):
            for p in results:
                st.session_state.selected[p["paper_id"]] = True
            st.session_state.sel_version += 1
        if tb2.button("⚪ 清空选择"):
            st.session_state.selected = {}
            st.session_state.sel_version += 1
        n_sel = sum(1 for p in results if st.session_state.selected.get(p["paper_id"]))
        tb3.caption(f"已勾选 **{n_sel}** / {len(results)} 篇（勾选后可在②③页批量下载/提取）")

        st.subheader(f"检索结果（{len(results)} 篇）")

        col_a, col_b = st.columns([1, 2])
        speed_read_targets = [p for p in results
                              if st.session_state.selected.get(p["paper_id"])] or results
        if col_a.button(f"🤖 AI批量速读（已选{n_sel}篇，未选则读全部）"):
            if len(speed_read_targets) > 30:
                st.warning("单次批量速读上限30篇，将只处理前30篇（可先勾选缩小范围）")
                speed_read_targets = speed_read_targets[:30]
            ai = get_ai()
            digest, prog = [], st.progress(0.0, text="AI正在阅读…")
            for i, p in enumerate(speed_read_targets):
                src_text = p["abstract"] or f"（无摘要，标题：{p['title']}）"
                try:
                    s = ai.summarize(src_text, max_chars=4000)
                except Exception as ex:
                    s = f"AI总结失败: {ex}"
                digest.append({"论文标题": p["title"], "年份": p["year"], "来源": p["source"],
                               "引用量": p.get("citations", 0),
                               "命中关键词": "、".join(p.get("matched_keywords", [])),
                               "作者": ", ".join(p["authors"][:5]), "DOI": p["doi"],
                               "期刊": p["journal"],
                               "期刊分区": journal_rank.lookup_rank(p["journal"]),
                               "AI速读": s.replace("\n", " ")})
                prog.progress((i + 1) / len(speed_read_targets),
                              text=f"已完成 {i + 1}/{len(speed_read_targets)}")
            st.session_state.digest = digest
            prog.empty()

        if st.session_state.digest:
            st.dataframe(pd.DataFrame(st.session_state.digest), use_container_width=True,
                          height=350)
            if st.button("💾 将AI速读结果追加到Excel（工作表：AI速读）"):
                try:
                    n = excel_store.append_records(
                        st.session_state.cfg["excel_path"], st.session_state.digest, "AI速读")
                    st.success(f"已追加 {n} 条速读记录到 {st.session_state.cfg['excel_path']}")
                except PermissionError:
                    st.error("Excel文件被占用，请先关闭该文件再保存")
                except Exception as ex:
                    st.error(f"保存失败: {ex}")

        for i, p in enumerate(results):
            rank = journal_rank.lookup_rank(p["journal"])
            badges = (f'<span style="color:#6c3483;font-weight:600">[{p["source"]}]</span>'
                      f'<span style="color:#7f8c8d"> [{p["year"] or "年份未知"}]</span>'
                      f'<span style="color:#b7950b;font-weight:600">[引用 {p.get("citations", 0)}]</span>'
                      f'<span style="color:#1e8449;font-weight:600">[分区 {rank}]</span>')
            if p.get("is_repeat"):
                badges += '<span style="color:#c0392b;font-weight:700">[⚠️ 历史已检索过]</span>'
            title_html = highlight_title(
                p["title"], st.session_state.kw_variants,
                p.get("matched_keywords") or st.session_state.last_keywords)
            with st.expander(f"[{p['source']}] {p['title'][:60]}（{p['year']}）"):
                st.markdown(f"#### {title_html}", unsafe_allow_html=True)
                st.markdown(badges, unsafe_allow_html=True)
                col1, col2 = st.columns([4, 1])
                col1.markdown(f"**作者**：{', '.join(p['authors'][:8]) or '未知'}")
                jline = f"**期刊**：{p['journal'] or '-'}"
                if rank == journal_rank.UNKNOWN and p["journal"]:
                    jline += f"（分区未收录，[查LetPub]({journal_rank.letpub_link(p['journal'])})）"
                col1.markdown(jline + f"　|　**DOI**：{p['doi'] or '-'}"
                              + (f"　|　**命中**：{'、'.join(p.get('matched_keywords', []))}"
                                 if p.get("matched_keywords") else ""))
                if p["pdf_url"]:
                    col2.markdown(f"[📄 PDF下载链接]({p['pdf_url']})")
                if p["url"]:
                    col2.markdown(f"[🔗 文献主页]({p['url']})")
                st.caption((p["abstract"] or "（无摘要）")[:800] +
                           ("…" if len(p.get("abstract", "")) > 800 else ""))
                key = p["paper_id"]
                st.session_state.selected[key] = st.checkbox(
                    "➕ 加入 下载/提取 列表", value=st.session_state.selected.get(key, False),
                    key=f"sel_{st.session_state.sel_version}_{i}")
                if st.button("🤖 AI单篇速读（摘要）", key=f"quick_{i}"):
                    ai = get_ai()
                    try:
                        with st.spinner("AI正在阅读摘要…"):
                            st.session_state[f"quicksum_{key}"] = ai.summarize(
                                p["abstract"] or f"（无摘要，标题：{p['title']}）", max_chars=4000)
                    except Exception as ex:
                        st.error(f"AI速读失败: {ex}")
                if st.session_state.get(f"quicksum_{key}"):
                    st.markdown(st.session_state[f"quicksum_{key}"])

# ============================================================ 页面2：下载
elif page.startswith("②"):
    st.header("② 下载文献全文与支撑材料")

    # 保存位置（可存到任意目录，与侧边栏设置同步）
    st.subheader("保存位置")
    d1, d2 = st.columns(2)
    st.session_state.cfg["pdf_dir"] = d1.text_input(
        "PDF保存目录", value=st.session_state.cfg["pdf_dir"])
    st.session_state.cfg["supp_dir"] = d2.text_input(
        "支撑材料保存目录", value=st.session_state.cfg["supp_dir"])

    selected_papers = [p for p in st.session_state.results
                       if st.session_state.selected.get(p["paper_id"])]
    if not selected_papers:
        st.info("请先在“① 文献检索”页勾选文献加入列表，再回到此页下载。")

    # 将文献信息存入任意Excel（标题/作者/摘要/链接等）
    with st.expander("💾 将检索到的文献信息存入Excel（自选路径）"):
        tp = st.text_input("Excel文件路径", value=st.session_state.cfg["excel_path"],
                           key="meta_excel_path")
        tsheet = st.text_input("工作表名（留空=文献信息）", value="", key="meta_sheet")
        if st.button("保存文献信息（勾选的文献；未勾选则保存全部检索结果）"):
            items = selected_papers or st.session_state.results
            if not items:
                st.warning("当前没有检索结果可保存")
            else:
                rows_meta = [{
                    "论文标题": it["title"], "作者": ", ".join(it["authors"][:10]),
                    "年份": it["year"], "期刊": it["journal"],
                    "期刊分区": journal_rank.lookup_rank(it["journal"]),
                    "引用量": it.get("citations", 0),
                    "命中关键词": "、".join(it.get("matched_keywords", [])),
                    "来源": it["source"],
                    "DOI": it["doi"] or "-", "文献主页": it["url"] or "-",
                    "PDF链接": it["pdf_url"] or "-", "摘要": it["abstract"] or "-",
                } for it in items]
                try:
                    n = excel_store.append_records(tp, rows_meta, tsheet or "文献信息")
                    st.success(f"已保存 {n} 条文献信息 → {tp}（工作表：{tsheet or '文献信息'}）")
                except PermissionError:
                    st.error("Excel文件正被打开占用，请先关闭该文件")
                except Exception as ex:
                    st.error(f"保存失败: {ex}")

    if not selected_papers:
        st.caption("如需下载PDF，请在“① 文献检索”页勾选文献后回到此页。")
    else:
        st.write(f"已选择 **{len(selected_papers)}** 篇文献")
        tid = st.session_state.get("bg_download_id")
        dtask = background.MANAGER.get(tid) if tid else None
        running_dl = dtask is not None and dtask.status == "running"
        if st.button("⬇️ 开始批量下载（后台运行，切换页面不中断）", type="primary",
                     disabled=running_dl):
            pdf_dir = st.session_state.cfg["pdf_dir"].strip() or PDF_DIR
            supp_dir = st.session_state.cfg["supp_dir"].strip() or SUPP_DIR
            task = background.MANAGER.submit(
                "批量下载文献", _bg_download,
                [dict(p) for p in selected_papers], pdf_dir, supp_dir)
            st.session_state.bg_download_id = task.id
            st.rerun()
        if running_dl:
            poll_task(dtask)
        else:
            t = claim_task(tid) if tid else None
            if t is not None:
                rmap = t.result or {}
                for p in st.session_state.results:
                    hit = rmap.get(p["paper_id"])
                    if hit:
                        p["pdf_path"] = hit["pdf_path"]
                        p["supp_files"] = hit["supp_files"]
                st.session_state.download_log = t.log
                if t.status == "done":
                    st.success(f"✅ 后台下载完成，共处理 {len(t.log)} 篇")
                elif t.status == "cancelled":
                    st.warning("⬇️ 下载任务已取消")
                else:
                    st.error(f"下载任务失败：{t.error}")
            if st.session_state.download_log:
                st.dataframe(pd.DataFrame(st.session_state.download_log),
                             use_container_width=True)

        st.subheader("本地PDF库")
        pdfs = glob.glob(os.path.join(
            st.session_state.cfg["pdf_dir"].strip() or PDF_DIR, "*.pdf"))
        if pdfs:
            st.dataframe(pd.DataFrame(
                {"文件名": [os.path.basename(f) for f in pdfs],
                 "大小(KB)": [round(os.path.getsize(f) / 1024) for f in pdfs]}),
                use_container_width=True)
        else:
            st.caption("暂无本地PDF。无法下载PDF的文献可在“③ AI阅读与数据提取”页在线阅读。")

# ============================================================ 页面3：提取
elif page.startswith("③"):
    st.header("③ AI阅读文献与数据提取")
    st.caption("单篇：本地PDF/上传PDF/在线阅读 + 领域模板提取；"
               "批量：一键处理全部勾选文献，生成机器学习数据集。"
               "提取在后台运行，可随时切换页面；还可与AI对话讨论文献与数据。")

    # ①页提出的检索/提取需求，本页AI全部知晓
    _ctx = get_search_context()
    if _ctx:
        with st.expander("📌 AI已知晓你在①页提出的检索与提取需求（点击查看）"):
            st.markdown(_ctx.replace("\n", "  \n"))

    pool = [p for p in st.session_state.results if st.session_state.selected.get(p["paper_id"])]
    if not pool:
        pool = st.session_state.results

    # ---------- 从本地文件夹添加文献（无需检索，直接读取磁盘上的PDF） ----------
    with st.expander("📁 从本地文件夹添加文献（无需检索，直接读取本地PDF）"):
        lp_dir = st.text_input(
            "文件夹路径", value=st.session_state.cfg["pdf_dir"].strip() or PDF_DIR,
            help=r"例如 D:\文献\合金 或任意包含PDF的文件夹")
        lp_recurse = st.checkbox("包含子文件夹", value=True)
        if st.button("📂 扫描该文件夹中的PDF"):
            if os.path.isdir(lp_dir):
                patt = "**/*.pdf" if lp_recurse else "*.pdf"
                files = sorted(glob.glob(os.path.join(lp_dir, patt), recursive=True))
                st.session_state.local_pdf_scan = [f for f in files
                                                   if not os.path.basename(f).startswith("~$")]
                if not st.session_state.local_pdf_scan:
                    st.warning("该文件夹（及其子文件夹）中没有找到PDF文件")
            else:
                st.error("文件夹不存在，请检查路径")

        scanned = st.session_state.get("local_pdf_scan") or []
        if scanned:
            st.caption(f"扫描到 **{len(scanned)}** 个PDF，勾选要处理的文献：")
            _lp_sel = st.session_state.setdefault("local_pdf_pick", set())
            c_all, c_none, _ = st.columns([1, 1, 4])
            if c_all.button("全选"):
                _lp_sel.update(range(len(scanned)))
                st.rerun()
            if c_none.button("清空"):
                _lp_sel.clear()
                st.rerun()
            for i, f in enumerate(scanned):
                _checked = st.checkbox(
                    f"📄 {os.path.basename(f)}（{round(os.path.getsize(f) / 1024)}KB）",
                    value=i in _lp_sel, key=f"lp_ck_{i}")
                if _checked:
                    _lp_sel.add(i)
                else:
                    _lp_sel.discard(i)
            if _lp_sel and st.button(f"➕ 添加选中的 {len(_lp_sel)} 篇到处理列表", type="primary"):
                have = {p.get("pdf_path") for p in st.session_state.local_papers}
                added = 0
                for i in sorted(_lp_sel):
                    f = scanned[i]
                    if f in have:
                        continue
                    st.session_state.local_papers.append({
                        "source": "本地文件",
                        "paper_id": "local:" + hashlib.md5(f.encode("utf-8")).hexdigest()[:12],
                        "title": os.path.splitext(os.path.basename(f))[0],
                        "authors": [], "year": "", "journal": "", "abstract": "",
                        "doi": "", "url": "", "pdf_url": "", "citations": 0,
                        "matched_keywords": [], "pdf_path": f, "supp_files": [],
                        "local_only": True,
                    })
                    added += 1
                st.session_state.local_pdf_pick.clear()
                st.success(f"已添加 {added} 篇本地文献（在下方文献列表中选择即可处理）")
                st.rerun()

    # 本地文献合并进处理池（去重）
    _pool_ids = {p["paper_id"] for p in pool}
    for lp in st.session_state.local_papers:
        if lp["paper_id"] not in _pool_ids:
            pool.append(lp)
            _pool_ids.add(lp["paper_id"])
    if st.session_state.local_papers:
        if st.button("🗑 移除全部本地文献"):
            st.session_state.local_papers = []
            st.rerun()

    mode3 = st.radio("处理模式", ["单篇精读", "🛠 批量阅读与数据提取"],
                     horizontal=True)

    if mode3.startswith("🛠"):
        # ============================ 批量模式 ============================
        if not pool:
            st.info("请先在“① 文献检索”页检索并勾选文献（未勾选则处理全部结果）。")
        else:
            st.write(f"将批量处理 **{len(pool)}** 篇文献（在①页勾选可精确控制；"
                     "已下载PDF优先用全文，否则自动在线阅读）")
            domain = st.selectbox("领域数据模板（决定提取字段，为机器学习准备）",
                                  list(ai_client.DOMAIN_TEMPLATES.keys()))
            custom_txt2 = st.text_area(
                "追加自定义字段（可选，每行一个：字段名：说明）", height=80,
                placeholder="例如：\n样品编号：文中样品编号，如 S1、S2\n稳定性：循环/放置稳定性描述")
            bdata_kw_txt = st.text_input(
                "🎯 数据关键词（你想获取哪些量化数据？逗号/分号分隔，所有文献通用）",
                placeholder="例如：拉伸强度, 硬度, 导热系数",
                help="批量模式下AI优先提取与这些关键词相关的正文量化数据。留空则提取全部量化数据。")
            only_fulltext = st.checkbox(
                "仅从正文全文提取（无全文的文献跳过数据提取，不基于摘要）", value=True,
                help="勾选后：只有PDF全文或在线开放全文的文献才会提取数据；"
                     "仅剩摘要的文献在日志中标注“无正文全文，已跳过”。")
            bdata_kws = parse_queries(bdata_kw_txt)
            bfields = ai_client.DOMAIN_TEMPLATES[domain] + parse_custom_fields(custom_txt2)
            st.caption("本次提取字段：" + "、".join(f["name"] for f in bfields)
                       + (f"　|　数据关键词：{'、'.join(bdata_kws)}" if bdata_kws else ""))
            make_report = st.checkbox("同时生成批量AI阅读报告（每篇一段总结）", value=True)

            btid = st.session_state.get("bg_batch_id")
            btask = background.MANAGER.get(btid) if btid else None
            running_bx = btask is not None and btask.status == "running"
            if st.button("🚀 开始批量AI阅读与数据提取（后台运行，切换页面不中断）",
                         type="primary", disabled=running_bx):
                c = st.session_state.cfg
                if not (c["base_url"].strip() and c["api_key"].strip()
                        and c["model"].strip()):
                    st.error("请先在左侧边栏完成AI模型设置（Base URL / API Key / 模型名）")
                else:
                    task = background.MANAGER.submit(
                        "批量AI阅读与数据提取", _bg_batch,
                        [dict(p) for p in pool],
                        c["base_url"].strip(), c["api_key"].strip(), c["model"].strip(),
                        [dict(f) for f in bfields], bdata_kws, only_fulltext,
                        make_report, domain, get_search_context())
                    st.session_state.bg_batch_id = task.id
                    st.rerun()
            if running_bx:
                poll_task(btask)
            else:
                t = claim_task(btid) if btid else None
                if t is not None:
                    res = t.result or {}
                    st.session_state.batch_records = res.get("records", [])
                    st.session_state.batch_report = res.get("report", [])
                    st.session_state.batch_log = res.get("log", [])
                    if t.status == "done":
                        st.success(f"✅ 批量处理完成：{len(st.session_state.batch_log)} 篇日志，"
                                   f"提取 {len(st.session_state.batch_records)} 条数据")
                    elif t.status == "cancelled":
                        st.warning("⬇️ 批量任务已取消")
                    else:
                        st.error(f"批量任务失败：{t.error}")

            # ---------- 批量结果展示与保存 ----------
            if st.session_state.batch_log:
                st.subheader("📋 批量处理日志")
                st.dataframe(pd.DataFrame(st.session_state.batch_log),
                             use_container_width=True)
            if st.session_state.batch_report:
                st.subheader(f"📖 批量AI阅读报告（{len(st.session_state.batch_report)} 篇）")
                st.dataframe(pd.DataFrame(st.session_state.batch_report),
                             use_container_width=True, height=320)
            if st.session_state.batch_records:
                st.subheader(f"📊 共提取 {len(st.session_state.batch_records)} 条数据记录"
                             "（机器学习数据集）")
                st.dataframe(pd.DataFrame(st.session_state.batch_records),
                             use_container_width=True, height=350)
                bc1, bc2 = st.columns(2)
                b_path = bc1.text_input("Excel文件路径",
                                        value=st.session_state.cfg["excel_path"],
                                        key="batch_excel_path")
                b_sheet = bc2.text_input("工作表名",
                                         value=st.session_state.cfg["sheet"],
                                         key="batch_sheet")
                bs1, bs2 = st.columns(2)
                if bs1.button("💾 保存提取数据到Excel", type="primary"):
                    try:
                        n = excel_store.append_records(b_path,
                                                       st.session_state.batch_records,
                                                       b_sheet)
                        st.success(f"已保存 {n} 条数据 → {b_path}（{b_sheet}）")
                    except PermissionError:
                        st.error("Excel文件正被打开占用，请先关闭该文件")
                    except Exception as ex:
                        st.error(f"保存失败: {ex}")
                if bs2.button("💾 保存阅读报告到Excel（工作表：批量阅读报告）"):
                    try:
                        n = excel_store.append_records(b_path,
                                                       st.session_state.batch_report,
                                                       "批量阅读报告")
                        st.success(f"已保存 {n} 条报告 → {b_path}")
                    except PermissionError:
                        st.error("Excel文件正被打开占用，请先关闭该文件")
                    except Exception as ex:
                        st.error(f"保存失败: {ex}")
                csv_bytes = pd.DataFrame(st.session_state.batch_records).to_csv(
                    index=False).encode("utf-8-sig")
                st.download_button("⬇️ 导出数据集为CSV（可直接喂给机器学习）",
                                   data=csv_bytes, file_name="ML数据集.csv",
                                   mime="text/csv")
        # ---------- 批量结果AI对话 ----------
        if st.session_state.batch_report or st.session_state.batch_records:
            st.subheader("💬 与AI对话（关于批量处理结果）")
            ground = ""
            if st.session_state.batch_report:
                ground += "\n\n".join(
                    f"《{r.get('论文标题', '')}》"
                    + (r.get("AI总结") or r.get("AI总结(基于摘要)") or "")
                    for r in st.session_state.batch_report[:30])
            if st.session_state.batch_records:
                ground += ("\n\n批量提取数据（前100条）：\n"
                           + pd.DataFrame(st.session_state.batch_records)
                           .head(100).to_string())
            render_ai_chat(ground[:15000], "批量处理结果")

        st.caption("提示：批量模式优先使用已下载PDF全文，无PDF自动在线阅读；"
                   "AI提取结果建议人工核对后再用于建模。")
        st.stop()

    if not pool:
        st.info("请先在“① 文献检索”页检索并（可选）勾选文献；"
                "或展开上方“📁 从本地文件夹添加文献”直接读取本地PDF；"
                "或在下方单篇模式中上传PDF。")
    else:
        p = st.selectbox(
            "选择文献", pool,
            format_func=lambda x: f"[{x['source']}] {x['title'][:70]}",
            key="extract_select")

        # 切换文献时清空上次提取结果
        if p["paper_id"] != st.session_state.extract_paper_id:
            st.session_state.extract_paper_id = p["paper_id"]
            st.session_state.summary = ""
            st.session_state.answer = ""
            st.session_state.extract_records = []
            st.session_state.current_text = ""

        paper = Paper.from_dict(p)

        # ---------- 文本来源 ----------
        st.subheader("阅读来源")
        st.caption("中文文献（知网/万方下载的PDF）可通过此处上传，交给AI阅读提取")
        up = st.file_uploader("或上传本地PDF（优先使用）", type=["pdf"])
        local_pdf = p.get("pdf_path") or ""
        if up is not None:
            up_dir = st.session_state.cfg["pdf_dir"].strip() or PDF_DIR
            os.makedirs(up_dir, exist_ok=True)
            up_path = os.path.join(up_dir, f"upload_{up.name}")
            with open(up_path, "wb") as f:
                f.write(up.getvalue())
            local_pdf, p["pdf_path"] = up_path, up_path

        options, default_ix = [], 0
        if local_pdf and os.path.exists(local_pdf):
            options = ["本地PDF全文", "在线阅读"]
        else:
            options = ["在线阅读", "本地PDF路径"]
            default_ix = 0
        mode = st.radio("文本获取方式", options, index=default_ix, horizontal=True)

        text, text_note, text_kind = "", "", "none"
        # 文本缓存：同一文献同一来源只解析一次（后台轮询刷新时避免重复解析PDF）
        cache = st.session_state.setdefault("text_cache", {})
        cache_key = f"{p['paper_id']}|{local_pdf}|{mode}"
        if cache_key in cache:
            text, text_kind = cache[cache_key]
        else:
            if mode.startswith("本地PDF") and local_pdf and os.path.exists(local_pdf):
                text = pdf_reader.extract_pdf_text(local_pdf)
                if len(text.strip()) < 100:
                    text_note = "⚠️ 该PDF几乎没有文本层（可能是扫描件），已自动改用在线阅读。"
                    text = ""
                else:
                    text_kind = "fulltext"
            if not text:
                if mode.startswith("本地PDF"):
                    text_note = text_note or "⚠️ 未找到本地PDF，已自动改用在线阅读。"
                if p.get("local_only"):
                    # 本地文件不在线回退（避免按文件名搜到无关文献）
                    if mode.startswith("本地PDF"):
                        st.error("该PDF没有文本层（扫描件），无法提取文字。"
                                 "请先用OCR工具处理，或换用其他文件。")
                        st.stop()
                text, text_kind = downloader.fetch_online_text(paper)
            if text:
                cache[cache_key] = (text, text_kind)
        if not text:
            st.error("无法获取该文献的任何文本内容（无摘要、无开放全文）。")
            st.stop()
        st.session_state.current_text = text
        is_abstract = text_kind == "abstract"
        if text_note:
            st.warning(text_note)
        if is_abstract:
            st.warning("⚠️ **当前文本来源是摘要，不是正文**。数据提取要求来自正文，"
                       "摘要中通常只有结论性数值。建议：① 在②页下载该文献PDF后回到本页；"
                       "② 或从文献主页下载PDF后用上方“上传PDF”；③ 也可勾选下方"
                       "“仍基于摘要提取”继续（记录中会注明来源为摘要）。")
            allow_abstract = st.checkbox("仍基于摘要提取（不推荐，记录将注明\"摘要\"）",
                                         value=False)
        else:
            allow_abstract = False
        # 支撑材料检测：正文提及的Supplementary/Table S等
        supp_mentions = pdf_reader.find_supplementary_mentions(text)
        if supp_mentions and not is_abstract:
            supp_dir_hint = st.session_state.cfg["supp_dir"].strip() or SUPP_DIR
            st.info("📎 **正文提及了支撑材料**（检出：" + "、".join(supp_mentions[:6]) +
                    "）。你想要的数据可能在这些材料中。获取途径："
                    f"① 在“② 下载文献”页下载该文献的支撑材料（PMC文章自动打包下载，"
                    f"存放于 `{supp_dir}`）；② 从[文献主页]({p['url'] or '-'})手动下载；"
                    "③ 下载后在下方“上传PDF”处上传给AI阅读，或将支撑材料表格"
                    "在②页导入Excel。")

        with st.expander("📖 文献原文内容预览", expanded=False):
            st.text(text[:3000] + ("…" if len(text) > 3000 else ""))
        st.caption(f"正文总字符数：{len(text)}（来源：{'摘要' if is_abstract else '正文全文'}）")

        # ---------- 提取设置 ----------
        st.subheader("提取设置")
        domain = st.selectbox("领域数据模板（决定提取字段）",
                              list(ai_client.DOMAIN_TEMPLATES.keys()))
        custom_txt = st.text_area(
            "追加自定义字段（每行一个：字段名：说明）",
            value="材料体系：研究涉及的材料或体系\n方法：实验或计算方法")
        data_kw_txt = st.text_input(
            "🎯 数据关键词（你想获取哪些方面的量化数据？逗号/分号分隔）",
            placeholder="例如：拉伸强度, 屈服强度, 硬度, 导热系数",
            help="AI将优先、完整地提取与这些关键词相关的可量化数据（正文/表格中的数值），"
                 "同时也会提取其他重要量化数据。留空则提取全部量化数据。")
        question = st.text_input("附加问题（可选，AI阅读后回答）", placeholder="例如：最优性能是多少？在什么条件下实现？")

        data_kws = parse_queries(data_kw_txt)
        fields = ai_client.DOMAIN_TEMPLATES[domain] + parse_custom_fields(custom_txt)
        st.caption("本次提取字段：" + "、".join(f["name"] for f in fields)
                   + (f"　|　数据关键词：{'、'.join(data_kws)}" if data_kws else ""))

        can_extract = (not is_abstract) or allow_abstract
        if not can_extract:
            st.warning("当前文本来源为摘要且未勾选“仍基于摘要提取”，无法执行正文数据提取。"
                       "请先获取全文（下载PDF/上传PDF），或勾选该选项。")

        stid = st.session_state.get("bg_single_id")
        stask = background.MANAGER.get(stid) if stid else None
        single_running = stask is not None and stask.status == "running"
        if st.button("🤖 开始AI阅读与数据提取（后台运行，切换页面不中断）",
                     type="primary", disabled=not can_extract or single_running):
            c = st.session_state.cfg
            if not (c["base_url"].strip() and c["api_key"].strip()
                    and c["model"].strip()):
                st.error("请先在左侧边栏完成AI模型设置（Base URL / API Key / 模型名）")
            else:
                read_label = ("PDF全文" if text_kind == "fulltext" and local_pdf
                              else ("在线全文" if text_kind == "fulltext" else "摘要"))
                task = background.MANAGER.submit(
                    "单篇AI阅读与提取", _bg_extract_single,
                    text, c["base_url"].strip(), c["api_key"].strip(),
                    c["model"].strip(), fields, data_kws, question.strip(),
                    is_abstract, "、".join(supp_mentions[:6]), read_label,
                    get_search_context())
                st.session_state.bg_single_id = task.id
                st.rerun()
        if single_running:
            poll_task(stask)
        else:
            t = claim_task(stid) if stid else None
            if t is not None:
                res = t.result or {}
                st.session_state.summary = res.get("summary", "")
                st.session_state.answer = res.get("answer", "")
                st.session_state.extract_records = res.get("records", [])
                now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                for r in st.session_state.extract_records:
                    r.update({
                        "论文标题": p["title"],
                        "作者": ", ".join(p["authors"][:8]),
                        "年份": p["year"], "期刊": p["journal"],
                        "期刊分区": journal_rank.lookup_rank(p["journal"]),
                        "引用量": p.get("citations", 0),
                        "命中关键词": "、".join(p.get("matched_keywords", [])),
                        "DOI": p["doi"] or "-", "来源": p["source"],
                        "提取时间": now, "数据类型": domain,
                        "数据关键词": "、".join(data_kws) or "-",
                        "阅读方式": res.get("read_label", "-"),
                    })
                for w in res.get("warnings", []):
                    st.warning(f"{w.get('阶段', '')}：{w.get('状态', '')}")
                if t.status == "done":
                    st.success("✅ AI阅读与数据提取完成")
                elif t.status == "cancelled":
                    st.warning("⬇️ 提取任务已取消")
                else:
                    st.error(f"提取任务失败：{t.error}")

        # ---------- 结果展示 ----------
        if st.session_state.summary:
            st.subheader("📝 AI文献总结")
            st.markdown(st.session_state.summary)
        if st.session_state.answer:
            st.subheader("❓ 附加问题回答")
            st.markdown(st.session_state.answer)
        if st.session_state.extract_records:
            st.subheader(f"📊 提取到 {len(st.session_state.extract_records)} 条数据记录")
            st.dataframe(pd.DataFrame(st.session_state.extract_records),
                         use_container_width=True)

            st.subheader("保存到Excel")
            c1, c2 = st.columns(2)
            save_path = c1.text_input("Excel文件路径", value=st.session_state.cfg["excel_path"])
            sheet_name = c2.text_input("工作表名", value=st.session_state.cfg["sheet"])
            if st.button("💾 保存提取结果到Excel", type="primary"):
                try:
                    n = excel_store.append_records(save_path, st.session_state.extract_records,
                                                   sheet_name)
                    st.success(f"已保存 {n} 条记录 → {save_path}（工作表：{sheet_name}）")
                except PermissionError:
                    st.error("Excel文件正被打开占用，请先关闭该文件再保存")
                except Exception as ex:
                    st.error(f"保存失败: {ex}")
            # CSV备用导出
            csv_bytes = pd.DataFrame(st.session_state.extract_records).to_csv(
                index=False).encode("utf-8-sig")
            st.download_button("⬇️ 也可导出为CSV", data=csv_bytes,
                               file_name="提取结果.csv", mime="text/csv")

        # ---------- 支撑材料表格导入 ----------
        supp_files = p.get("supp_files") or []
        if supp_files:
            tables = [f for f in supp_files
                      if os.path.splitext(f)[1].lower() in (".xlsx", ".xls", ".csv", ".tsv", ".txt")]
            st.subheader("📎 支撑材料")
            st.write(f"已下载 {len(supp_files)} 个支撑材料文件，其中 {len(tables)} 个为表格文件")
            if tables and st.button("📥 将支撑材料表格导入Excel（每表一个工作表）"):
                try:
                    imported = excel_store.import_table_files(
                        tables, p["title"], st.session_state.cfg["excel_path"])
                    st.success(f"已导入工作表：{', '.join(imported) or '（无有效表格）'} → "
                               f"{st.session_state.cfg['excel_path']}")
                except PermissionError:
                    st.error("Excel文件正被打开占用，请先关闭该文件再导入")
                except Exception as ex:
                    st.error(f"导入失败: {ex}")

        # ---------- 与AI对话（就当前文献） ----------
        st.subheader("💬 与AI对话（就当前文献提问，AI知晓你在①页的检索与提取需求）")
        render_ai_chat(st.session_state.current_text, "当前文献")

# ============================================================ 页面4：数据管理
elif page.startswith("④"):
    st.header("④ 数据管理（本地Excel）")
    files = sorted(glob.glob(os.path.join(DATA_DIR, "**", "*.xlsx"), recursive=True))
    if not files:
        st.info("data 目录下暂无Excel文件。可在“③ AI阅读与数据提取”页保存数据后回到此页查看。")
    else:
        sel = st.selectbox("选择Excel文件",
                           files, format_func=lambda f: os.path.relpath(f, DATA_DIR))
        if sel:
            sheets = excel_store.list_sheets(sel)
            if not sheets:
                st.error("无法读取该Excel文件（可能正被Excel程序占用）")
            else:
                sheet = st.selectbox("工作表", sheets)
                try:
                    df = excel_store.read_sheet(sel, sheet)
                    st.subheader(f"{sheet}（{len(df)} 行）")
                    st.dataframe(df, use_container_width=True)
                    with open(sel, "rb") as f:
                        st.download_button("⬇️ 下载整个Excel文件", data=f.read(),
                                           file_name=os.path.basename(sel),
                                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                    csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
                    st.download_button("⬇️ 导出当前工作表为CSV", data=csv_bytes,
                                       file_name=f"{sheet}.csv", mime="text/csv")
                except Exception as ex:
                    st.error(f"读取失败: {ex}")

st.divider()
st.caption("提示：① Semantic Scholar 匿名接口限流较严，失败会自动重试；"
           "② 非开放获取文献无法下载PDF，请使用在线阅读模式；"
           "③ AI提取结果建议人工核对后再使用。")
