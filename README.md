# HomeNews Project

A news aggregation and home automation integration system.

## Overview
HomeNews is a system designed to aggregate news feeds and integrate with home automation systems.

## Features
- News aggregation from multiple sources
- Integration with home automation systems
- Real-time notifications
- Customizable news filters

## Tech Stack
- Backend: Python/FastAPI
- Frontend: React/Vue.js (to be determined)
- Database: PostgreSQL/SQLite
- Deployment: Docker

## Setup

### For the AI News Agent (快速安装)
1. Install minimal dependencies: `pip install -r requirements-agent.txt`
2. Configure environment variables (NVIDIA_API_KEY, SERPER_API_KEY)
3. Run the news agent: `python agent_main.py`

### For the Full Backend API
1. Install all dependencies: `pip install -r requirements.txt`
2. Configure environment variables
3. Run the application

**注意**: 如果只想运行AI新闻简报功能，使用 `requirements-agent.txt` 可以大幅减少安装时间（从几分钟减少到约1分钟）并避免依赖冲突。

## License
TBD

## 新增功能：AI自动化新闻简报系统

本项目集成了一个使用NVIDIA meta/llama-3.1-405b-instruct和CrewAI的自动化新闻简报系统。

### 功能特点

- **多源新闻整合**（2026年1月新增）：
  - 每个热点新闻整合至少3个不同信源
  - 中国新闻：整合官方叙事、民间讨论、专业分析
  - 全球新闻：综合Reuters、Bloomberg、NYT等多个权威来源
  - 法律新闻：整合法院文件、专家评论、新闻报道
  - 提供多维度、全方位的新闻理解

- **Deep Humanizer Protocol**（深层去伪协议 - 2026年1月新增）：
  - 采用对抗性生成逻辑，结合困惑度（Perplexity）和爆发度（Burstiness）
  - 消除AI常见生成模式，使内容通过图灵测试
  - 禁用AI常见词汇（delve、landscape、transformative等）
  - 混合短句和长句，创造"心电图"般的节奏感
  - 使用具体细节和感官动词，而非抽象表达
  - 注入微观视角和适度偏见，展现人类写作风格

- **智能新闻抓取**：自动收集五大领域热点新闻
  - 中国社交媒体热点（微博、知乎、百度）
  - 全球趋势（Twitter/X、Google Trends）
  - **法律新闻热点**（美国最高法院判决、中国及欧美涉法事件）
  - **运动与健康新闻**（Scientific American、Nature、Science等科学期刊）
  - **法律学术分析**（美国顶尖法学院期刊文章深度解读）

- **深度分析报告**（采用Deep Humanizer Protocol）：
  - 运动健康新闻：自动选择Top 3重要新闻进行深入分析（5000+字/篇）
    - 全面的科学背景、方法论、研究结果和批判性分析
    - 使用具体数据和实例，避免抽象表述
    - 混合短句与长句，增强可读性
  - 法律学术研究：
    - AI识别美中热点关键法律问题
    - 检索美国Top 10法学院法律评论文章
    - 筛选3篇最相关文章
    - 每篇文章提供5000+字深度解读报告（采用人性化写作风格）
    - 包括法律框架、关键论点、比较视角、政策含义等
    
- **详细新闻摘要**：
  - 每篇新闻总结不少于1000字
  - 提供全面的历史背景、多角度分析和详细解释
  - 深入而非表面的内容呈现
  
- **原文献链接**：
  - 尽量提供所有引用来源的原始URL
  - 包括新闻文章、研究论文、法院文件、法律评论文章等
  - 在UI中显示为可点击的徽章/芯片
    
- **事实核查**：对新闻进行验证和背景分析
  - 法律新闻特别增强：中国热点自动关联美欧经典判例和法律文献
  - 多源验证确保新闻可靠性
  
- **自动化生成**：每日自动生成新闻简报页面

- **精美界面**：五栏响应式布局，现代化卡片式UI设计
  - 卡片式布局，每个新闻和分析都在独立卡片中
  - 渐变背景和卡片阴影效果，悬停动画
  - 移动端自动适配
  - 折叠面板展示详细内容，带平滑展开/收起动画
  - 深度分析报告（5000+字）可折叠，带"阅读更多"功能
  - 内容采用人性化、吸引人的写作风格
  - 原文献链接显示为可点击徽章

- **报告保存与邮件发送**（2026年1月新增）：
  - 所有中间报告自动保存为Markdown格式
  - 按日期组织的文件夹结构（`reports/YYYY-MM-DD/`）
  - 每个智能体的输出单独保存，便于审查和调试
  - 可配置邮件自动发送功能
  - 所有报告作为附件发送到指定邮箱
  - 详细配置指南见 [REPORTS_EMAIL_GUIDE.md](REPORTS_EMAIL_GUIDE.md)

### 技术栈

- **AI框架**: CrewAI
- **语言模型**: NVIDIA meta/llama-3.1-405b-instruct (主模型), nvidia/llama-3.3-nemotron-super-49b-v1.5 (备用)
- **搜索工具**: SerperDevTool
- **部署**: GitHub Actions + GitHub Pages
- **邮件**: SMTP (支持Gmail, Outlook等)

### 配置要求

要启用自动化新闻简报功能，需要配置以下环境变量：

#### 必需配置
1. **NVIDIA_API_KEY**: NVIDIA API密钥 (从 build.nvidia.com 获取)
2. **SERPER_API_KEY**: Serper.dev API密钥

#### 可选配置
3. **DEEPSEEK_API_KEY**: DeepSeek API密钥 (可选，用于第二备用模型)

#### 邮件配置（可选，启用报告邮件发送）
4. **mailadd**: 接收报告的邮箱地址
5. **SMTP_USER**: SMTP用户名（通常是发件邮箱）
6. **SMTP_PASSWORD**: SMTP密码（建议使用应用专用密码）
7. **SMTP_SERVER**: SMTP服务器地址（默认：smtp.gmail.com）
8. **SMTP_PORT**: SMTP端口（默认：587）

详细的邮件配置说明请参考 [REPORTS_EMAIL_GUIDE.md](REPORTS_EMAIL_GUIDE.md)。

**模型故障转移机制**：
- 主模型: `meta/llama-3.1-405b-instruct` (NVIDIA API) - 高性能稳定模型，包含全部5个板块
- 第二备用: `deepseek-chat` (DeepSeek 官方 API) - **仅包含4个板块（跳过中文新闻以避免内容审查问题）**
- 第三备用: `nvidia/llama-3.3-nemotron-super-49b-v1.5` (NVIDIA API) - 包含全部5个板块

系统会在主模型失败时自动切换到备用模型，确保服务稳定性。使用第二备用模型（DeepSeek官方API）时，会自动跳过可能触发内容审查的中文新闻板块。

### 部署指南

系统通过GitHub Actions每天自动运行，生成的新闻简报会发布到GitHub Pages。

1. 在仓库设置中添加上述API密钥到Secrets
2. 启用GitHub Actions工作流
3. 配置GitHub Pages使用gh-pages分支

### 文件结构

- `agent_main.py`: AI新闻代理主程序
- `.github/workflows/daily_news.yml`: 自动化工作流配置
- `index.html`: 生成的新闻简报页面
