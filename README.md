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
1. Install dependencies: `pip install -r requirements.txt`
2. Configure environment variables
3. Run the application

## License
TBD

## 新增功能：AI自动化新闻简报系统

本项目集成了一个使用DeepSeek V3和CrewAI的自动化新闻简报系统。

### 功能特点

- **智能新闻抓取**：自动收集中国和全球热点新闻
- **事实核查**：对新闻进行验证和背景分析
- **自动化生成**：每日自动生成新闻简报页面
- **交互式界面**：使用折叠面板展示详细内容

### 技术栈

- **AI框架**: CrewAI
- **语言模型**: DeepSeek V3
- **搜索工具**: SerperDevTool
- **部署**: GitHub Actions + GitHub Pages

### 配置要求

要启用自动化新闻简报功能，需要配置以下环境变量：

1. **DEEPSEEK_API_KEY**: DeepSeek API密钥
2. **SERPER_API_KEY**: Serper.dev API密钥

### 部署指南

系统通过GitHub Actions每天自动运行，生成的新闻简报会发布到GitHub Pages。

1. 在仓库设置中添加上述API密钥到Secrets
2. 启用GitHub Actions工作流
3. 配置GitHub Pages使用gh-pages分支

### 文件结构

- `agent_main.py`: AI新闻代理主程序
- `.github/workflows/daily_news.yml`: 自动化工作流配置
- `index.html`: 生成的新闻简报页面
