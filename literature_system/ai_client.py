# -*- coding: utf-8 -*-
"""OpenAI兼容大模型客户端：文献总结、数据提取、问答。

支持任何OpenAI兼容接口（DeepSeek / 通义千问 / Kimi / OpenAI / 本地vLLM等），
只需配置 base_url、api_key、model。
"""
import json
import re

import requests

# 默认数据提取字段（数值/表格数据）
DEFAULT_FIELDS = [
    {"name": "数据名称", "desc": "数据项或指标名称，例如：拉伸强度、吸附容量、准确率、产率等"},
    {"name": "数值", "desc": "提取到的数值；如同一指标有多个值，用分号分隔"},
    {"name": "单位", "desc": "数值对应的单位，无单位填'-'"},
    {"name": "实验对象/条件", "desc": "该数据对应的材料、对象或实验条件"},
    {"name": "数据位置", "desc": "数据出处，如'摘要'、'正文3.2节'、'表2'、'图4'"},
]

# 领域数据提取模板：为机器学习数据集准备的结构化字段
DOMAIN_TEMPLATES = {
    "材料学（性能/工艺/结构，机器学习数据集）": [
        {"name": "材料体系", "desc": "材料名称/体系，如 NCM811正极材料、304不锈钢"},
        {"name": "组成/成分", "desc": "化学成分、掺杂元素及含量比例"},
        {"name": "合成/制备方法", "desc": "如水热法、磁控溅射、熔铸、3D打印等"},
        {"name": "工艺参数", "desc": "关键制备工艺参数：温度、时间、气氛、压力、退火/烧结条件等"},
        {"name": "结构特征", "desc": "物相/晶体结构、晶格参数、缺陷密度、比表面积、孔隙率等"},
        {"name": "形貌/尺寸", "desc": "微观形貌（纳米颗粒/纳米线/层状等）、粒径、厚度、晶粒尺寸"},
        {"name": "性能指标", "desc": "性能名称，如拉伸强度、导热系数、比容量、光电转换效率、Tc等"},
        {"name": "数值", "desc": "性能数值；同一指标多个值用分号分隔，顺序与条件对应"},
        {"name": "单位", "desc": "性能数值单位，无单位填'-'"},
        {"name": "测试方法/条件", "desc": "测试标准/仪器及测试条件（温度、频率、载荷等）"},
    ],
    "能源/电池": [
        {"name": "材料/电极体系", "desc": "电池类型与材料，如锂离子电池-Si负极"},
        {"name": "组成/配比", "desc": "活性物质、电解液、粘结剂等组成及比例"},
        {"name": "制备工艺", "desc": "合成与电极制备方法及关键参数"},
        {"name": "电化学性能指标", "desc": "如首次容量、循环保持率、倍率性能、库仑效率等"},
        {"name": "数值", "desc": "性能数值，多值用分号分隔"},
        {"name": "单位", "desc": "数值单位，如 mAh/g、%、V"},
        {"name": "测试条件", "desc": "充放电倍率、电压窗口、循环次数、温度等"},
    ],
    "化学/催化": [
        {"name": "反应类型", "desc": "如CO2还原、加氢、偶联、光催化降解等"},
        {"name": "催化剂/试剂", "desc": "催化剂名称、负载量、助剂"},
        {"name": "制备方法", "desc": "催化剂合成方法与关键参数"},
        {"name": "反应条件", "desc": "温度、压力、时间、溶剂、气氛、底物浓度"},
        {"name": "性能指标", "desc": "如转化率、选择性、产率、TOF、法拉第效率"},
        {"name": "数值", "desc": "性能数值，多值用分号分隔"},
        {"name": "单位", "desc": "数值单位，如 %、h⁻¹，无单位填'-'"},
    ],
    "生物医学": [
        {"name": "研究对象", "desc": "细胞系/动物模型/患者群体"},
        {"name": "样本量", "desc": "样本数量，如 n=30"},
        {"name": "干预/处理", "desc": "给药/处理方案、剂量、周期"},
        {"name": "效应指标", "desc": "结局指标，如存活率、肿瘤体积、指标改善幅度"},
        {"name": "数值", "desc": "效应数值，多值用分号分隔"},
        {"name": "单位/统计量", "desc": "单位或统计指标，如 %、mg/kg、p值"},
        {"name": "对照/比较", "desc": "对照组设置与显著性结论"},
    ],
    "物理/电子": [
        {"name": "材料/器件体系", "desc": "如钙钛矿太阳能电池、GaN HEMT"},
        {"name": "制备方法", "desc": "制备/加工方法及关键参数"},
        {"name": "结构/表征", "desc": "结构参数与表征结果（厚度、晶格、界面等）"},
        {"name": "物理性能指标", "desc": "如迁移率、居里温度、击穿场强、响应度"},
        {"name": "数值", "desc": "性能数值，多值用分号分隔"},
        {"name": "单位", "desc": "数值单位，如 cm²/V·s、K、MV/cm"},
        {"name": "测试条件", "desc": "测试温度、场强、频率等条件"},
    ],
    "通用（数值/表格）": DEFAULT_FIELDS,
}

TIMEOUT = 300


class AIClient:
    def __init__(self, base_url: str, api_key: str, model: str):
        if not base_url or not api_key or not model:
            raise ValueError("请先在左侧边栏完成AI模型设置（Base URL / API Key / 模型名）")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    def chat(self, messages, temperature: float = 0.2) -> str:
        url = f"{self.base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}",
                   "Content-Type": "application/json"}
        payload = {"model": self.model, "messages": messages, "temperature": temperature}
        r = requests.post(url, headers=headers, json=payload, timeout=TIMEOUT)
        if r.status_code != 200:
            raise RuntimeError(f"模型接口返回 {r.status_code}: {r.text[:300]}")
        return r.json()["choices"][0]["message"]["content"].strip()

    # ---------------------------------------------------------- 总结
    def summarize(self, text: str, max_chars: int = 12000) -> str:
        content = (text or "").strip()[:max_chars] or "（无内容）"
        messages = [
            {"role": "system", "content": "你是科研文献阅读助手，请用简体中文输出。"},
            {"role": "user", "content":
                "请阅读以下文献内容，输出简明扼要的中文总结，包含："
                "1) 研究目标；2) 研究方法；3) 主要结果与关键数据；4) 结论与意义。"
                "使用markdown编号列表。\n\n文献内容：\n" + content},
        ]
        return self.chat(messages)

    # ---------------------------------------------------------- 数据提取
    def extract_data(self, text: str, fields, data_keywords=None,
                     is_abstract=False, supp_hints="", user_requirements="") -> list:
        """从文献正文片段提取**可量化**数据，返回记录列表（list[dict]）。

        data_keywords: 用户指定的数据关键词（如"拉伸强度;硬度"），AI优先提取相关数据
        is_abstract: 当前文本是否为摘要（摘要中通常无正文数据，会明确提示AI谨慎）
        supp_hints: 正文中检出的支撑材料引用提示（如"Table S1"），让AI在记录中注明
        """
        field_desc = "\n".join(f"- {f['name']}：{f['desc']}" for f in fields)
        system = ("你是严谨的科研数据提取助手。只输出JSON，不要输出任何解释性文字，"
                  "不要使用markdown代码块标记。")
        req = [
            "从下面的文献【正文】内容中提取可量化的实验/计算数据。",
            "需要提取的字段：", field_desc, "",
            "提取规则：",
            "1) 只提取可量化数据：必须有明确数值（可带误差范围），如实验测量值、"
            "表格数据、计算结果；不要提取纯定性描述、背景介绍或无数值的结论。",
            "2) 数值保持原文写法（含单位、误差、条件）。",
            "3) 每条数据注明来源位置（章节/表/图编号）。",
        ]
        if data_keywords:
            req.append(f"4) 用户重点关注以下数据关键词，凡与这些关键词相关的量化数据"
                       f"必须优先、完整提取：{'、'.join(data_keywords)}；"
                       "同时也提取其他重要量化数据。")
        if supp_hints:
            req.append(f"5) 正文提及了支撑材料（{supp_hints}）：若某数据标注在支撑材料中"
                       "（如表S1），在\"数据位置\"字段注明\"支撑材料-表S1\"。")
        if is_abstract:
            req.append("注意：本段内容是摘要而非正文。摘要中通常只有主要结论性数值，"
                       "请在每条记录的\"数据位置\"注明\"摘要\"。")
        if user_requirements:
            req.append("")
            req.append("用户的研究背景与提取要求（提取时必须遵循，例如：只要某类数据、"
                       "数值必须带单位与测试条件、某些字段优先等）：")
            req.append(str(user_requirements))
        req += ["", "输出要求：输出一个JSON数组，每个元素是一条数据记录（JSON对象），"
                "键为上述字段名。字段提取不到时填\"未找到\"；"
                "若本段没有任何可量化的数据，输出 []。", "",
                "文献内容：", (text or "")]
        resp = self.chat([{"role": "system", "content": system},
                          {"role": "user", "content": "\n".join(req)}], temperature=0)
        return parse_json_array(resp)

    # ------------------------------------------------- 检索对话助手
    def search_assistant(self, history: list) -> tuple:
        """与用户多轮对话明确文献需求，生成检索方案。

        history: [{"role":"user"/"assistant","content":...}, ...]
        返回 (回复文本, 检索建议dict或None)。
        建议格式：{"keywords":[...], "authors":[...], "journals":[...], "reason":"..."}
        """
        system = (
            "你是文献检索顾问（科研领域）。任务：与用户对话，弄清TA想要哪方面的文献。"
            "原则：\n"
            "1) 若需求已经足够具体（明确了主题/领域，必要时补充默认合理范围），直接给出检索方案；"
            "若还很模糊（如\"帮我找点材料学的文献\"），先提出1-2个具体问题"
            "（如具体材料体系？关注性能还是工艺？年份范围？），不要一次问太多。\n"
            "2) 回复用简体中文，简洁友好，先一两句话回应用户，再给方案或问题。\n"
            "3) 当你准备好检索方案时，在回复末尾追加一行JSON（独占一行，格式："
            "{\"keywords\":[\"词1\",\"词2\"],\"authors\":[],\"journals\":[],"
            "\"reason\":\"简要说明\"}）。关键词3-6个、具体且互不重复，"
            "中英文均可（系统会自动翻译）；authors/journals可为空数组。\n"
            "4) 没准备好之前，绝不要输出JSON行。")
        messages = [{"role": "system", "content": system}] + history[-12:]
        resp = self.chat(messages, temperature=0.4)
        suggestion = None
        m = re.search(r'\{[^{}]*"keywords"[^{}]*\}', resp, flags=re.S)
        if m:
            try:
                suggestion = json.loads(m.group(0))
                if not isinstance(suggestion, dict):
                    suggestion = None
            except Exception:
                suggestion = None
        reply = resp
        if suggestion:
            reply = resp.replace(m.group(0), "").strip().rstrip("`").strip()
        return reply, suggestion

    # ---------------------------------------------------------- 针对性问答
    def answer_question(self, text: str, question: str, max_chars: int = 12000) -> str:
        messages = [
            {"role": "system", "content": "你是科研文献阅读助手，请用简体中文回答，简洁准确。"},
            {"role": "user", "content":
                f"文献内容：\n{(text or '')[:max_chars]}\n\n请根据文献内容回答问题：{question}"},
        ]
        return self.chat(messages, temperature=0.3)

    # ---------------------------------------------------- 文献对话（多轮）
    def chat_about_paper(self, text: str, messages: list, context: str = "",
                         max_chars: int = 15000) -> str:
        """就当前文献/批量结果与用户多轮对话。

        text: 参考内容（文献全文、批量总结/数据等）
        messages: 对话历史 [{"role":..., "content":...}, ...]
        context: 用户在①页提出的检索与数据提取需求背景（可为空）
        """
        system = ("你是科研文献阅读与数据提取助手，请用简体中文回答，简洁准确、"
                  "有条理。基于提供的参考内容回答问题、解释数据、协助分析；"
                  "若参考内容中没有答案，如实说明，不要编造。")
        if context:
            system += ("\n\n用户此前在检索阶段提出的需求背景（回答时请结合该背景，"
                       "理解用户真正想要什么）：\n" + str(context))
        msgs = [{"role": "system", "content": system},
                {"role": "system",
                 "content": "参考内容：\n" + (text or "")[:max_chars]}]
        msgs += [m for m in (messages or [])[-10:]
                 if m.get("role") in ("user", "assistant") and m.get("content")]
        return self.chat(msgs, temperature=0.4)


def parse_json_array(text: str) -> list:
    """从模型输出中稳健地解析JSON数组。"""
    if not text:
        return []
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.S).strip()
    try:
        data = json.loads(cleaned)
        if isinstance(data, list):
            return [r for r in data if isinstance(r, dict)]
        if isinstance(data, dict):
            return [data]
    except Exception:
        pass
    m = re.search(r"\[.*\]", cleaned, flags=re.S)
    if m:
        try:
            data = json.loads(m.group(0))
            if isinstance(data, list):
                return [r for r in data if isinstance(r, dict)]
        except Exception:
            pass
    m = re.search(r"\{.*\}", cleaned, flags=re.S)
    if m:
        try:
            data = json.loads(m.group(0))
            return [data]
        except Exception:
            pass
    raise ValueError("模型未返回有效的JSON数据：" + text[:200])
