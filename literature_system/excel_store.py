# -*- coding: utf-8 -*-
"""Excel数据存储模块：追加提取记录、读取、导入支撑材料表格。"""
import os

import pandas as pd

META_COLS = ["论文标题", "作者", "年份", "期刊", "DOI", "来源", "提取时间", "数据类型"]


def _ensure_file(excel_path: str):
    """确保Excel文件存在（不存在则以说明表创建）。"""
    if not os.path.exists(excel_path):
        parent = os.path.dirname(os.path.abspath(excel_path))
        os.makedirs(parent, exist_ok=True)
        pd.DataFrame({"说明": ["文献数据获取系统 - 本文件由系统自动创建"]}).to_excel(
            excel_path, index=False, sheet_name="说明")


def append_records(excel_path: str, records: list, sheet_name: str = "提取数据") -> int:
    """将记录（list[dict]）追加到指定工作表，返回本次追加条数。"""
    sheet_name = (sheet_name or "提取数据")[:31]
    df_new = pd.DataFrame(records)
    if df_new.empty:
        return 0
    # 元信息列排前面
    ordered = [c for c in META_COLS if c in df_new.columns] + \
              [c for c in df_new.columns if c not in META_COLS]
    df_new = df_new.reindex(columns=ordered)
    _ensure_file(excel_path)
    df_old = None
    try:
        df_old = pd.read_excel(excel_path, sheet_name=sheet_name)
    except Exception:
        pass
    if df_old is not None and not df_old.empty:
        df_new = pd.concat([df_old, df_new], ignore_index=True, sort=False)
    with pd.ExcelWriter(excel_path, engine="openpyxl", mode="a",
                        if_sheet_exists="replace") as w:
        df_new.to_excel(w, sheet_name=sheet_name, index=False)
    return len(pd.DataFrame(records))


def list_sheets(excel_path: str):
    try:
        return pd.ExcelFile(excel_path).sheet_names
    except Exception:
        return []


def read_sheet(excel_path: str, sheet_name: str):
    return pd.read_excel(excel_path, sheet_name=sheet_name)


def read_table_file(path: str):
    """读取支撑材料中的表格文件（xlsx/csv/tsv/txt），非表格返回None。"""
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext in (".xlsx", ".xls"):
            return pd.read_excel(path)
        if ext == ".csv":
            return pd.read_csv(path, sep=None, engine="python")
        if ext in (".tsv", ".txt"):
            return pd.read_csv(path, sep="\t", engine="python")
    except Exception:
        return None
    return None


def import_table_files(table_files: list, paper_title: str, excel_path: str) -> list:
    """把支撑材料中的表格文件导入Excel，每个文件写入独立工作表。

    返回成功导入的工作表名列表。
    """
    if not table_files:
        return []
    _ensure_file(excel_path)
    imported, used_names = [], set()
    existing = set(pd.ExcelFile(excel_path).sheet_names)
    for path in table_files:
        df = read_table_file(path)
        if df is None or df.empty:
            continue
        df.insert(0, "来源文件", os.path.basename(path))
        df.insert(0, "论文标题", paper_title)
        stem = os.path.splitext(os.path.basename(path))[0][:25] or "支撑材料"
        name = stem
        k = 1
        while name in used_names or name in existing:
            k += 1
            name = f"{stem[:25]}_{k}"
        used_names.add(name)
        existing.add(name)
        with pd.ExcelWriter(excel_path, engine="openpyxl", mode="a",
                            if_sheet_exists="replace") as w:
            df.to_excel(w, sheet_name=name, index=False)
        imported.append(name)
    return imported
