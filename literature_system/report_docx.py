# -*- coding: utf-8 -*-
"""生成"新论文研究方案"Word 文档（依赖 python-docx）。

build_paper_plan_docx(plan, ideas, datasets) -> io.BytesIO
- plan: AI 生成的论文方案 dict（含 overview / papers）
- ideas: 创新 idea 列表（写入附录 A）
- datasets: 数据集推荐列表（写入附录 B）
"""
from io import BytesIO

from docx import Document
from docx.shared import Pt, RGBColor
from docx.oxml.ns import qn
from docx.enum.text import WD_ALIGN_PARAGRAPH


_CJK_FONT = "Microsoft YaHei"


def _set_cjk(style):
    """为样式设置中文字体，避免 Word 中中文显示为默认西文字体。"""
    try:
        rpr = style.element.get_or_add_rPr()
        rfonts = rpr.get_or_add_rFonts()
        rfonts.set(qn("w:eastAsia"), _CJK_FONT)
        rfonts.set(qn("w:ascii"), _CJK_FONT)
        rfonts.set(qn("w:hAnsi"), _CJK_FONT)
    except Exception:
        pass


def _field(doc, label, val):
    """往文档追加一个"标签：值"段落（值为空则跳过）。"""
    if val in (None, "", [], {}, 0):
        return
    para = doc.add_paragraph()
    run = para.add_run(f"{label}：")
    run.bold = True
    para.add_run(str(val))


def build_paper_plan_docx(plan: dict, ideas: list = None,
                         datasets: list = None) -> BytesIO:
    """构建新论文方案 Word 文档，返回 BytesIO（可直接交给 st.download_button）。"""
    doc = Document()

    # 全局正文样式（中文字体）
    _set_cjk(doc.styles["Normal"])
    doc.styles["Normal"].font.size = Pt(11)

    # 封面标题
    title = doc.add_heading("新论文研究方案", level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = sub.add_run("由「文智汇」基于已读文献与个人需求自动生成")
    r.italic = True
    r.font.size = Pt(10)
    r.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

    overview = (plan or {}).get("overview", "")
    if overview:
        doc.add_paragraph(overview)

    papers = (plan or {}).get("papers", []) or []
    if not papers:
        doc.add_paragraph("（未生成具体论文方案，请检查输入的 idea 与数据集。）")
    else:
        for p in papers:
            doc.add_heading(f"论文 {p.get('index', '')}：{p.get('title', '')}", level=1)
            _field(doc, "研究方向", p.get("direction"))
            _field(doc, "研究问题", p.get("research_question"))

            mr = p.get("method_route")
            if mr:
                para = doc.add_paragraph()
                para.add_run("方法路线：").bold = True
                for step in mr:
                    doc.add_paragraph(str(step), style="List Number")

            _field(doc, "实验设计", p.get("experiment_design"))

            rd = p.get("required_data")
            if rd:
                para = doc.add_paragraph()
                para.add_run("所需数据：").bold = True
                for d in rd:
                    doc.add_paragraph(str(d), style="List Bullet")

            _field(doc, "预期创新点", p.get("expected_innovation"))
            _field(doc, "时间建议", p.get("timeline"))

            kr = p.get("key_references")
            if kr:
                para = doc.add_paragraph()
                para.add_run("关键参考文献：").bold = True
                for ref in kr:
                    doc.add_paragraph(str(ref), style="List Bullet")

    # ---------------- 附录 A：创新 idea 汇总 ----------------
    if ideas:
        doc.add_page_break()
        doc.add_heading("附录 A：创新 Idea 汇总", level=1)
        for it in ideas:
            doc.add_heading(it.get("idea_title", "") or "idea", level=2)
            _field(doc, "类型", it.get("type"))
            _field(doc, "源方法", it.get("source_method"))
            _field(doc, "目标领域", it.get("target_field"))
            _field(doc, "创新点", it.get("innovation"))
            _field(doc, "跨领域依据", it.get("cross_domain_rationale"))
            _field(doc, "可行性", it.get("feasibility"))
            _field(doc, "新颖度", it.get("novelty"))

            vps = it.get("related_papers_verified") or it.get("related_papers") or []
            if vps:
                para = doc.add_paragraph()
                para.add_run("相关论文（真实链接已联网检索补全）：").bold = True
                for v in vps:
                    line = f"{v.get('title', '')}（{v.get('year', '')}）"
                    link = v.get("doi_or_url") or v.get("url") or ""
                    if link:
                        line += f" — {link}"
                    doc.add_paragraph(line, style="List Bullet")

    # ---------------- 附录 B：推荐公开数据集 ----------------
    if datasets:
        doc.add_page_break()
        doc.add_heading("附录 B：推荐公开数据集", level=1)
        for d in datasets:
            doc.add_heading(d.get("dataset_name", "") or "dataset", level=2)
            _field(doc, "领域", d.get("field"))
            _field(doc, "适用方法", d.get("applicable_method"))
            _field(doc, "描述", d.get("description"))
            _field(doc, "链接", d.get("url"))
            _field(doc, "获取方式", d.get("access"))
            _field(doc, "链接置信度", d.get("confidence"))
            _field(doc, "是否跨领域同源",
                   "是" if d.get("cross_domain") else "否")
            _field(doc, "备注", d.get("note"))

    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf
