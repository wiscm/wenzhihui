# 🪶 文智汇 — 文献智能数据获取系统

> 本地运行的 AI 文献工作站：检索 → 下载 → AI 阅读 → 数据提取，全流程自动化。

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.32+-red.svg)](https://streamlit.io/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](#license)

## ✨ 功能一览

| 页面 | 功能 |
|---|---|
| ① 批量检索 | 5 大公开数据源（arXiv / PMC / S2 / OpenAlex / 中文库）+ AI 智能检索助手 + 关键词/作者/期刊三种检索 + 中英双语 |
| ② 下载文献 | 一键批量下载 OA PDF 与 PMC 支撑材料到本地 |
| ③ AI 阅读与数据提取 | 全文 PDF / 上传 PDF / 在线全文三选一；可指定数据关键词；领域模板（材料/能源/化学/生物/物理/通用）；批量模式 |
| ④ 数据管理 | 自由路径 + Excel 多表 + CSV 导出 |

## 🚀 快速开始

### 用户安装（推荐）
前往 [Releases](../../releases) 页面下载最新版 `文智汇_v1.0_setup.exe`，双击运行安装向导即可。

### 开发者运行

```bash
# 1. 创建 conda 环境（克隆 base 已装好的依赖）
conda create -n wenZhiHui python=3.11 -y
conda activate wenZhiHui

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动
streamlit run app.py
```

浏览器自动打开 <http://127.0.0.1:8501>。

## 📁 项目结构

```
.
├── app.py                     # Streamlit 主应用入口
├── requirements.txt
├── 启动.bat                   # 用户日常启动
├── 首次安装并启动.bat          # 用户首次自动装依赖 + 启动
├── assets/                    # UI 图片
├── literature_system/         # 核心模块（12 个 .py）
│   ├── models.py              # 统一文献数据模型
│   ├── searchers.py           # 多来源检索
│   ├── cn_searchers.py        # 中文库检索
│   ├── downloader.py          # PDF / 支撑材料下载、在线全文获取
│   ├── pdf_reader.py          # PDF 文本提取与分块
│   ├── ai_client.py           # OpenAI 兼容大模型客户端
│   ├── excel_store.py         # Excel 存储与表格导入
│   ├── journal_rank.py        # 中科院期刊分区
│   ├── search_history.py      # 历史去重
│   ├── translator.py          # 中英翻译
│   ├── background.py          # 后台线程
│   └── __init__.py
├── installer/                 # 自解压安装包构建工具（PyInstaller）
│   └── install.py             # Tkinter 安装向导
└── README.md
```

> ⚠️ `data/` 目录（含 `config.json` 中的 AI API Key、`pdfs/`、`supplementary/`、Excel 表）**不入仓**，是用户私有数据。

## 🤖 AI 模型配置（OpenAI 兼容）

启动后左侧边栏填入：

| Base URL 示例 | 提供方 |
|---|---|
| `https://api.deepseek.com/v1` | DeepSeek（推荐，便宜） |
| `https://dashscope.aliyuncs.com/compatible-mode/v1` | 通义千问 |
| `https://api.openai.com/v1` | OpenAI |

模型示例：`deepseek-chat`、`qwen-plus`、`gpt-4o-mini`。

配置存到本地 `data/config.json`，**不要提交该文件**。

## 🛠 自行构建安装包

需要 Python 3.11+ + PyInstaller：

```bash
pip install pyinstaller
cd installer
pyinstaller --onefile --noconsole --name 文智汇_v1.0_setup \
    --add-data "release.zip;." \
    --add-binary "C:\ProgramData\anaconda3\Library\bin\tcl86t.dll;." \
    --add-binary "C:\ProgramData\anaconda3\Library\bin\tk86t.dll;." \
    --collect-all tkinter \
    install.py
```

> 注意 tcl86t.dll/tk86t.dll 路径需根据本机 Anaconda 调整。

## 📜 注意事项

- Semantic Scholar 匿名接口限流较严，偶发 429 会自动重试
- 非开放获取（付费墙）文献无法下载 PDF，请用"在线阅读"模式
- 扫描件 PDF（无文本层）自动回退到在线阅读
- AI 提取的数据建议人工核对后再用于科研

## 📄 License

MIT