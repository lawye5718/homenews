# 工作记忆档案 (Memory Archive)

## 概述
此文件记录重要的项目工作记忆，包括用户需求、代码实现、版本更新等关键信息，供未来工作参考。

---

## 日期: 2024年1月26日
### 项目: HomeNews 新闻聚合系统
#### 用户需求:
- 修复DeepSeek "Content Exists Risk"报错问题
- 解决缺少fastapi依赖问题
- 修复requirements.txt格式错误
- 设置北京时间凌晨3点运行(UTC 19:00)

#### 代码实现:
- 优化"中国情报官"的Prompt，避免敏感词汇
- 添加try-catch错误处理机制
- 增加600秒超时设置防止长任务中断
- 实现"Deep Humanizer Protocol"去AI味协议
- 集成Tailwind CSS和专业字体

#### 版本更新:
- 更新requirements.txt添加fastapi依赖
- 修改agent_main.py修复API调用问题
- 更新GitHub Actions工作流配置
- 提交修复版本到远程仓库

#### 关键配置:
- DeepSeek API配置: model="deepseek/deepseek-chat", base_url="https://api.deepseek.com"
- 时区转换: 北京时间03:00 = UTC 19:00, cron: '0 19 * * *'

---

## 日期: 2024年1月26日
### 项目: NVIDIA NIM 模型测试
#### 用户需求:
- 测试多个NVIDIA NIM模型的可用性
- 验证模型调用方式和参数配置

#### 测试结果:
- 可用模型: 
  - `nvidia/llama-3.3-nemotron-super-49b-v1.5` (支持特殊参数/think system prompt)
  - `meta/llama-3.1-405b-instruct`
- 不可用模型:
  - `zhipuai/glm-4.7` (连接重置)
  - `z-ai/glm-4.7` (404错误)
  - `deepseek-ai/deepseek-v3.2` (超时)

#### 代码实现:
- 创建模型测试脚本
- 实现错误处理和重试机制
- 提供通用的模型调用函数

#### 关键配置:
- API端点: https://integrate.api.nvidia.com/v1/chat/completions
- API密钥: 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

---

## 日期: 2024年1月26日
### 项目: HomeNews 深度分析功能
#### 用户需求:
- 实现法律和健康科学领域的深度分析
- 优化UI/UX设计，使用Tailwind CSS
- 改进搜索策略，解决法学文献访问问题

#### 代码实现:
- 新增健康运动情报官(循证医学分析)
- 新增健康运动深度分析师(科学解释)
- 新增法律学术分析师(学术深度分析)
- 采用IRAC方法论(问题-规则-分析-结论)
- 实现Bento Grid布局

#### 版本更新:
- 更新agent_main.py添加深度分析功能
- 优化UI/UX设计元素
- 提交深度分析版本到远程仓库

#### 关键配置:
- 增加执行超时时间到600秒
- 扩大搜索结果数量到15个
- 使用SSRN和法律博客资源避免付费墙

---

## 日期: 2024年1月25日
### 项目: HomeNews 项目初始化
#### 用户需求:
- 创建homenews工作空间
- 实现新闻聚合系统基础架构
- 配置GitHub Actions自动化部署
- 实现三栏布局新闻页面设计

#### 代码实现:
- 创建FastAPI后端服务
- 设计数据模型和API路由
- 实现CrewAI智能体框架
- 配置DeepSeek V3语言模型和SerperDevTool搜索工具

#### 版本更新:
- 初始化项目结构
- 创建GitHub远程仓库: https://github.com/lawye5718/homenews
- 配置Docker容器化部署方案
- 提交初始版本到远程仓库

#### 关键配置:
- 使用CrewAI智能体框架
- 集成DeepSeek和SerperDevTool
- 配置GitHub Actions自动部署到Pages

---

## 日期: 2024年1月25日
### 项目: Superstar 项目配置
#### 用户需求:
- 查找superstar项目中的火山引擎和腾讯云COS密钥配置
- 将密钥放入superstar2.0项目环境文件
- 确保敏感信息不上传到GitHub
- 创建homenews工作空间

#### 代码实现:
- 实现Git安全操作流程
- 创建项目备份和版本管理机制
- 配置环境变量管理
- 实现Cloudflare和Nginx配置联动

#### 版本更新:
- 遵循Git操作流程规范
- 实现先pull后commit再push的安全流程
- 配置远程仓库备份机制

#### 关键配置:
- Git操作流程: 修改前先git pull，修改后git commit，提交前本地备份
- 环境变量安全: 不将敏感信息硬编码到代码中

---

## 使用说明
在开始任何新工作之前，请查阅此记忆档案，了解相关项目的背景、需求、实现方式和关键配置。这有助于：
- 快速了解项目历史和上下文
- 避免重复工作或破坏已有功能
- 保持代码风格和架构的一致性
- 有效利用之前的经验和解决方案

## 维护说明
每次完成重要工作后，请在此档案中添加新的条目，确保知识积累和传承。
