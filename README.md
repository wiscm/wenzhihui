# 文智汇 · AI 文献智能数据获取系统

一个面向科研文献的 AI 辅助工具：检索文献、AI 速读、批量阅读 PDF 并提取数据、
跨领域挖掘创新 idea、推荐公开数据集，并一键导出新论文 Word 方案。

## 功能
- 🔍 **文献检索与 AI 速读**：关键词/作者/期刊检索（Semantic Scholar / OpenAlex / 知网 / 万方），
  命中关键词高亮、引用量与期刊分区、历史去重；AI 对话式检索；批量/单篇 AI 速读。
- ⬇️ **下载文献全文与支撑材料**：勾选文献后台批量下载 PDF 与 supplement。
- 🤖 **AI 阅读与数据提取**：本地/上传/在线 PDF 阅读 + 领域模板提取，生成机器学习数据集；
  后台运行，可随时切换页面。
- 🔥 **创新挖掘与论文规划**：基于已读文献挖掘创新 idea（含跨领域迁移、附真实论文链接）、
  推荐公开数据集、生成新论文执行方案并导出 Word。
- 🌐 **双语界面**：侧栏可选 中文 / English / 中英。
- 📊 **数据管理**：本地 Excel 查看与导出。

## 安装（推荐）
到 GitHub **Releases** 下载 `文智汇_v1.0_setup.exe`，双击按向导安装即可
（会自动探测本机 conda 环境并安装依赖，无需手动配置 Python）。

## 开发者运行
```bash
pip install -r requirements.txt
streamlit run app.py
```

## 重新打包安装程序
```powershell
powershell -ExecutionPolicy Bypass -File _rebuild_installer.ps1
```
（需本机已安装 PyInstaller 与 conda 环境）

## 目录结构
- `app.py`：Streamlit 主程序（多页）
- `literature_system/`：检索、AI 客户端、PDF 阅读、Excel 存储、影响因子/分区等模块
- `installer/`：PyInstaller 安装向导源码
- `assets/`：logo 等素材
