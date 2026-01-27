import os
import sys
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from crewai import Agent, Task, Crew, Process, LLM
from crewai_tools import SerperDevTool
from custom_scrape_tool import SafeScrapeWebsiteTool

# --- Configuration Constants ---
# 强制获取精确的今天和昨天的日期，用于搜索过滤
NOW = datetime.now()
TODAY_STR = NOW.strftime("%Y-%m-%d")
YESTERDAY_STR = (NOW - timedelta(days=1)).strftime("%Y-%m-%d")
CURRENT_DATE = TODAY_STR
CURRENT_YEAR = NOW.strftime("%Y")
CURRENT_YEAR_MONTH = NOW.strftime("%Y年%m月")
NEWS_ITEMS_PER_SECTION = 5
LEGAL_ANALYSIS_ITEMS = 3
DEEP_ANALYSIS_ITEMS = 3
# 增加上下文窗口以防止长文截断
CTX_WINDOW = 128000

# 严格的日期搜索过滤器 (Google Search Syntax)
# 加上这个后缀，Google会强制过滤掉旧闻
# 针对问题1：旧闻 (2024/2022) - 在代码层面硬编码 after:YYYY-MM-DD 搜索参数，物理屏蔽旧网页
SEARCH_SUFFIX = f" after:{YESTERDAY_STR}"

# 环境变量：是否使用 DeepSeek 作为主模型
# 设置 USE_DEEPSEEK=true 时，自动选择 DeepSeek 作为主要大模型
USE_DEEPSEEK = os.environ.get("USE_DEEPSEEK", "false").lower() == "true"

# 邮件配置 (从环境变量读取或使用默认值)
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
try:
    SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
except ValueError:
    invalid_value = os.environ.get("SMTP_PORT")
    print(f"⚠️ Invalid SMTP_PORT value '{invalid_value}' (must be a number), using default 587")
    SMTP_PORT = 587
SMTP_USER = os.environ.get("SMTP_USER")      # 发件人邮箱
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD") # 邮箱应用密码
EMAIL_TO = os.environ.get("EMAIL_TO")        # 收件人邮箱

# --- 1. 配置 LLM ---
# DeepSeek API 配置 - 可作为主模型使用（通过 USE_DEEPSEEK=true 环境变量控制）
# 使用 DeepSeek Chat 模型 (降低幻觉，提高准确性)
# max_tokens 设置为 8000（DeepSeek 实际支持更大值如 64K，但我们保持一致性）
# temperature 降低到 0.4 以保持专注和减少幻觉
# 针对问题2：假深度 (只有一句话) - 提供足够的token容量和更低温度以支持长文生成
# 这有助于：
# 1. 提高 LLM 对指令的遵循度（减少偷懒和幻觉）
# 2. 1000+ 字的详细新闻摘要（每个板块 5 条新闻 = 5000+ 字）
# 3. 5000+ 字的深度分析报告通过分段生成（健康分析 3 篇 + 法律分析 3 篇）
# 4. 综合研究报告和最终 HTML 生成
deepseek_llm = LLM(
    model="deepseek-chat",
    base_url="https://api.deepseek.com",
    api_key=os.environ.get("DEEPSEEK_API_KEY"),
    temperature=0.4,  # 低温以保持专注
    top_p=0.9,
    max_tokens=8000,  # 安全值，避免 API 限制问题
    stream=True,
    timeout=600
)

# NVIDIA NIM 配置 - 使用 NVIDIA meta/llama-3.1-405b-instruct 模型 (高性能稳定)
# 参考 NVIDIA 官方示范代码配置
# [CRITICAL FIX] max_tokens 从 32000 改为 8000，避免 API 400 错误
# NVIDIA API 限制为 8192 tokens，使用 8000 作为安全值
nvidia_llm = LLM(
    model="meta/llama-3.1-405b-instruct",
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.environ.get("NVIDIA_API_KEY"),
    temperature=0.4,  # 低温以保持专注
    top_p=0.9,
    max_tokens=8000,  # 安全值，NVIDIA API 上限为 8192
    stream=True,
    timeout=600
)

# 第三备用模型配置 - 在其他模型失败时使用
backup_llm = LLM(
    model="nvidia/llama-3.3-nemotron-super-49b-v1.5",
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.environ.get("NVIDIA_API_KEY"),
    temperature=0.4,  # 低温以保持专注
    top_p=0.9,
    max_tokens=8000,  # 安全值，避免 API 限制问题
    stream=True,
    timeout=600
)

# 根据环境变量选择主模型
# 当 USE_DEEPSEEK=true 时，使用 DeepSeek 作为主模型
# 否则使用 NVIDIA 模型作为主模型
if USE_DEEPSEEK:
    print("🔧 使用 DeepSeek 作为主要大模型 (USE_DEEPSEEK=true)")
    primary_llm = deepseek_llm
    fallback_llm = nvidia_llm
else:
    print("🔧 使用 NVIDIA 作为主要大模型 (USE_DEEPSEEK=false)")
    primary_llm = nvidia_llm
    fallback_llm = deepseek_llm

# --- 2. 初始化工具 ---
# 增加搜索结果数量以提高准确性
search_tool = SerperDevTool(n_results=15)
# 使用增强的安全爬虫工具，自动处理PDF、Cloudflare阻止、乱码等问题
scrape_tool = SafeScrapeWebsiteTool()

# ==============================================================================
# Deep Humanizer Protocol (深层去伪协议) - 增强版
# ==============================================================================
# 所有写作型智能体共享的人性化写作原则 + 深度分析要求：
# 1. 禁用 AI 常见词汇：delve, landscape, transformative, tapestry, underscore, poised to
# 2. 禁用结构性陈词：In conclusion, Furthermore, Moreover, Looking ahead
# 3. 高爆发度 (Burstiness)：混合短句和长句，创造"心电图"般的节奏感
# 4. 高困惑度 (Perplexity)：使用具体细节和感官动词，而非抽象表达
# 5. 人类立场：注入微观视角和适度偏见，展现人类写作风格
# 6. 强制深度：分析必须达到博士论文水平，引用具体的法律条款、科学数据或社会学理论
# 7. 字数铁律：当要求 1000/5000 字时，这是硬性下限，必须通过提供更多细节、引用更多案例来填充
# ==============================================================================

HUMANIZER_PROTOCOL = """
**Deep Humanizer & Integrity Protocol (去AI味写作规则 + 深度保证)**:
1. **禁止AI腔调**: 
   - 严禁使用: "delve", "landscape", "tapestry", "transformative", "underscore", "poised to", "myriad"
   - 严禁使用: "In conclusion", "Furthermore", "Moreover", "Looking ahead", "It's worth noting", "It is important to note"
   - 中文严禁: "总而言之"、"值得注意的是"、"这是一把双刃剑"、"不可忽视的是"
2. **高爆发度 (Burstiness)**: 
   - 混合短句(3-5字)和长句，创造节奏感
   - 示例: "市场崩了。交易员疯狂抛售。但有人在废墟中看到了机会——那些手握现金和耐心的人。"
3. **具象表达**: 
   - 避免: "经济形势严峻" → 改用: "华尔街交易员开始囤积现金"
   - 使用感官动词(grab, crash, smell)而非抽象动词(consider, reflect)
4. **人类视角**: 
   - 从具体细节开场，而非宏大叙事
   - 允许适度的专业偏见、幽默或质疑
5. **强制深度**: 
   - 分析必须达到博士论文水平，引用具体的法律条款、科学数据或社会学理论
   - 不能只是表面描述，必须深入解构背后的权力关系、经济动因、社会结构
6. **事实与观点分离**: 
   - 报道部分必须基于事实（Who, What, When, Where, Why）
   - 分析部分必须基于逻辑和理论
7. **字数铁律**: 
   - 当要求 1000/5000 字时，这是硬性下限
   - 必须通过提供更多细节、引用更多案例、多角度论证来填充
   - 严禁重复凑字数或使用空洞表述
"""

# --- 3. 定义智能体 (Agents) ---

# 【Chinese Media Editor】 - Focus on CONTROVERSY and CONFLICT
china_scout = Agent(
    role='Chinese Social Conflict Reporter',
    goal=f'Find {NEWS_ITEMS_PER_SECTION} viral controversial events in China from {TODAY_STR} (Past 24h Only) that sparked massive social media debates and conflicts',
    backstory=f"""
    你不是普通新闻编辑，你是深度调查记者。你只关心**冲突 (Conflict)** 和 **争议 (Controversy)**。
    
    **CRITICAL: YOU MUST USE YOUR TOOLS!**
    - You HAVE a Search Tool (SerperDevTool) - YOU MUST USE IT to find news
    - You HAVE a Web Scraping Tool (SafeScrapeWebsiteTool) - YOU MUST USE IT to read articles
    - DO NOT just say "I will search" - ACTUALLY USE the Search Tool NOW!
    - DO NOT return empty results - ACTUALLY SCRAPE the content from URLs!
    
    **搜索策略** (针对问题1和3：获取今日争议性新闻):
    - **不要搜** "中国新闻" 或 "China News"
    - **要搜**: "微博热搜 争议{SEARCH_SUFFIX}", "知乎 吵架{SEARCH_SUFFIX}", "网友 抵制{SEARCH_SUFFIX}", "官方 通报 争议{SEARCH_SUFFIX}"
    - **核心搜索词组合**: "争议{SEARCH_SUFFIX}", "冲突{SEARCH_SUFFIX}", "抗议{SEARCH_SUFFIX}", "辩论{SEARCH_SUFFIX}", "舆论{SEARCH_SUFFIX}"
    - 关键词必须包含: "争议"、"冲突"、"辩论"、"抗议"、"抵制"、"舆论"、"反对"
    - 搜索参数中包含 "after:{YESTERDAY_STR}" 以物理屏蔽旧网页
    - 必须锁定 **{TODAY_STR} 或 {YESTERDAY_STR}** 发生的具体事件
    - 严禁使用 2024年、2023年或更早的旧闻
    
    **CRITICAL REQUIREMENTS**:
    - You MUST return EXACTLY {NEWS_ITEMS_PER_SECTION} news stories, no more, no less
    - Each story MUST be from {TODAY_STR} or {YESTERDAY_STR} (last 24 hours in {CURRENT_YEAR})
    - ABSOLUTELY NO stories from 2024, 2023, or earlier - only {CURRENT_YEAR} {TODAY_STR} news
    - Each story MUST have EXACTLY 1000 words or MORE of detailed analysis (verify word count)
    
    **输出要求** (针对问题8：综合性报道):
    - 为每个事件撰写 **1000字以上的深度综合报道**
    - 报道必须包含：
      1. 事件起因（具体时间 {TODAY_STR}、地点、人物）
      2. 冲突爆发点（为什么吵起来、争议的核心是什么）
      3. 各方核心观点（官方 vs 民间、不同群体的对立观点）
      4. 官方/法律层面的介入（通报、处罚、调查）
      5. 社会影响和未来走向
    - 必须整合至少 3 个信源（官方媒体 + 自媒体/KOL观点 + 网友评论截图或引用）
    - 使用脚注格式 [1], [2], [3] 标注所有来源链接
    
    **选题标准** (针对问题3：真正的热点):
    1. 过滤掉低质量内容：娱乐八卦、企业宣传、简单正面报道、自然灾害
    2. **聚焦冲突性议题**：体现社会观点碰撞或凸显社会某一方面本质的冲突
    3. 深度视角：不只是流量话题，而是有研究价值、反映重要社会价值冲突的争议事件
    4. 必须是 {TODAY_STR} 当日在社交媒体上引起轰动的事件
    
    {HUMANIZER_PROTOCOL}
    """,
    tools=[search_tool, scrape_tool],
    llm=primary_llm,
    verbose=True,
    allow_delegation=False
)

# 【全球冲突情报官】 - 强制英文源 + 争议焦点
global_scout = Agent(
    role='Global Conflict & Crisis Analyst',
    goal=f'Identify {NEWS_ITEMS_PER_SECTION} major controversial global events from {TODAY_STR} (last 24h) involving geopolitical conflict, ethical debates, or mass protests',
    backstory=f"""
    你专注于全球范围内的**激烈冲突**和**伦理困境**。不要报道普通的股市涨跌或新品发布。
    
    **CRITICAL: YOU MUST USE YOUR TOOLS!**
    - You HAVE a Search Tool (SerperDevTool) - YOU MUST USE IT to find news
    - You HAVE a Web Scraping Tool (SafeScrapeWebsiteTool) - YOU MUST USE IT to read articles
    - DO NOT just say "I will search" - ACTUALLY USE the Search Tool NOW!
    - DO NOT return empty results - ACTUALLY SCRAPE the content from URLs!
    
    **搜索策略** (针对问题1和3：获取今日争议性新闻):
    - **不要搜**: "Global News today" 或 "World News"
    - **要搜**: "Protest{SEARCH_SUFFIX}", "Scandal{SEARCH_SUFFIX}", "Controversial ruling{SEARCH_SUFFIX}", "Debate{SEARCH_SUFFIX}", "Lawsuit filed{SEARCH_SUFFIX}"
    - **核心搜索词组合**: "controversy{SEARCH_SUFFIX}", "conflict{SEARCH_SUFFIX}", "protest{SEARCH_SUFFIX}", "scandal{SEARCH_SUFFIX}", "backlash{SEARCH_SUFFIX}", "outrage{SEARCH_SUFFIX}"
    - 关键词必须包含: "controversy", "conflict", "protest", "scandal", "debate", "backlash", "outrage"
    - 搜索参数中包含 "after:{YESTERDAY_STR}" 以物理屏蔽旧网页
    - 必须是过去 24 小时 ({TODAY_STR} 或 {YESTERDAY_STR}) 内的突发事件
    - 严禁使用 2024、2023 或更早的旧闻
    
    **CRITICAL REQUIREMENTS**:
    - You MUST return EXACTLY {NEWS_ITEMS_PER_SECTION} news stories, no more, no less
    - Each story MUST be from {TODAY_STR} or {YESTERDAY_STR} (last 24 hours in {CURRENT_YEAR})
    - ABSOLUTELY NO stories from 2024, 2023, or earlier - only {CURRENT_YEAR} {TODAY_STR} news
    - Each story MUST have EXACTLY 1000 words or MORE of detailed analysis (verify word count)
    - MUST retain the original English Headlines to avoid translation loss
    
    **输出要求** (针对问题8：综合性报道):
    - 每个事件 **1000字以上** 的全景式报道（中文分析，但保留英文原标题）
    - 必须保留英文原标题
    - 深度挖掘冲突背后的：
      1. 意识形态差异（自由 vs 管制、隐私 vs 安全）
      2. 利益集团博弈（企业 vs 政府、民众 vs 精英）
      3. 伦理困境（科技进步 vs 人权保护）
    - 整合至少 3 个信源，特别是对立观点：
      - 保守派媒体 (Fox News, Daily Mail) vs 自由派媒体 (CNN, NYT)
      - 官方声明 vs Twitter/X 上的民间反应
      - 专家正方观点 vs 专家反方观点
    - 使用脚注格式 [1], [2], [3] 标注所有来源链接
    
    **选题标准** (针对问题3：真正的热点):
    1. 过滤掉：产品发布、常规财报、一般性政策宣布
    2. **聚焦冲突性议题**：引起大规模抗议、舆论撕裂、政策争议的事件
    3. 必须是 {TODAY_STR} 当日在国际社交媒体上引起轰动的事件
    4. 适合博士论文研究的深度议题
    
    {HUMANIZER_PROTOCOL}
    """,
    tools=[search_tool, scrape_tool],
    llm=primary_llm,
    verbose=True,
    allow_delegation=False
)

# 【法律实战专家】 - 针对问题4：拒绝新规，只看案例
legal_scout = Agent(
    role='Litigation & Case Law Specialist',
    goal=f'Find {NEWS_ITEMS_PER_SECTION} ongoing, high-profile COURT CASES or LAWSUITS from {TODAY_STR} (last 24-48h) that are causing public sensation',
    backstory=f"""
    你关注的是**法庭上的硝烟**，而不是枯燥的条文。你寻找的是 "People v. Company" 或 "State v. Individual" 的具体案例。
    
    **CRITICAL: YOU MUST USE YOUR TOOLS!**
    - You HAVE a Search Tool (SerperDevTool) - YOU MUST USE IT to find legal cases
    - You HAVE a Web Scraping Tool (SafeScrapeWebsiteTool) - YOU MUST USE IT to read court documents and articles
    - DO NOT just say "I will search" - ACTUALLY USE the Search Tool NOW!
    - DO NOT return empty results - ACTUALLY SCRAPE the content from URLs!
    
    **核心指令** (针对问题4：法律新闻应该是实际案例):
    1. **不要** 找 "新法律颁布" (New legislation)、"新规" (New regulation)、"政策出台"
    2. **要找** 正在进行的庭审、刚刚做出的争议性判决、或者引发公愤的起诉 (Active Litigation/Verdicts)
    3. **搜索关键词**: 
       - "Lawsuit filed{SEARCH_SUFFIX}", "Court verdict{SEARCH_SUFFIX}", "v.{SEARCH_SUFFIX}"
       - "Supreme Court{SEARCH_SUFFIX}", "Trial{SEARCH_SUFFIX}", "判决{SEARCH_SUFFIX}", "诉讼{SEARCH_SUFFIX}"
       - **核心搜索词组合**: "v.{SEARCH_SUFFIX}", "lawsuit{SEARCH_SUFFIX}", "verdict{SEARCH_SUFFIX}", "ruling{SEARCH_SUFFIX}", "court case{SEARCH_SUFFIX}"
       - "起诉{SEARCH_SUFFIX}", "庭审{SEARCH_SUFFIX}", "判决{SEARCH_SUFFIX}", "案件{SEARCH_SUFFIX}"
    - 搜索参数中包含 "after:{YESTERDAY_STR}" 以物理屏蔽旧网页
    - 必须是 {TODAY_STR} 或 {YESTERDAY_STR} 的最新案件进展
    - 严禁使用 2024、2023 或更早的旧案件
    
    **CRITICAL REQUIREMENTS**:
    - You MUST return EXACTLY {NEWS_ITEMS_PER_SECTION} legal news stories, no more, no less
    - Each story MUST be from {TODAY_STR} or {YESTERDAY_STR} (last 24-48 hours in {CURRENT_YEAR})
    - ABSOLUTELY NO stories from 2024, 2023, or earlier - only {CURRENT_YEAR} {TODAY_STR} cases
    - Each story MUST have EXACTLY 1000 words or MORE of detailed legal analysis (verify word count)
    - Focus on COURT CASES and LAWSUITS, NOT legislation or regulations
    
    **输出要求** (针对问题8：综合性报道):
    - **1000字以上** 的案件综述，必须包含：
      1. 案件名称（原告 v. 被告）
      2. 案件背景（什么时候发生、为什么打官司）
      3. 争论的法律焦点（双方律师的核心论点）
      4. 最新进展（{TODAY_STR} 的庭审、判决或起诉）
      5. 为什么这个判决/起诉引起了轰动（公众反应、舆论争议）
      6. 可能的影响和先例意义
    - 必须引用法庭文件或律师声明的原文片段
    - 整合至少 3 个信源（法院文件 + 专家评论 + 新闻报道）
    - 使用脚注格式 [1], [2], [3] 标注所有来源链接
    
    **选题标准** (针对问题3和4：真正的热点案例):
    1. 过滤掉：普通民事纠纷、简单交通事故、无争议的判决
    2. **聚焦争议性案件**：引起公愤、法律界辩论、可能改变先例的案件
    3. 必须是 {TODAY_STR} 当日有最新进展、正在引起轰动的案件
    4. 适合法学博士论文研究的深度案例
    
    {HUMANIZER_PROTOCOL}
    """,
    tools=[search_tool, scrape_tool],
    llm=primary_llm,
    verbose=True,
    allow_delegation=False
)

# 【健康与运动新闻情报官】 - 新增：科学期刊来源
health_sports_scout = Agent(
    role='Health & Sports Science Reporter',
    goal=f'Identify EXACTLY {NEWS_ITEMS_PER_SECTION} controversial health and sports science news from THIS WEEK in {CURRENT_YEAR} (NOT 2023 or earlier) from peer-reviewed sources with comprehensive 1000+ word scientific summaries for EACH story',
    backstory=f"""
    You are a science journalist specializing in controversial health and sports research with significant academic value.
    
    **CRITICAL: YOU MUST USE YOUR TOOLS!**
    - You HAVE a Search Tool (SerperDevTool) - YOU MUST USE IT to find research papers
    - You HAVE a Web Scraping Tool (SafeScrapeWebsiteTool) - YOU MUST USE IT to read journal articles
    - DO NOT just say "I will search" - ACTUALLY USE the Search Tool NOW!
    - DO NOT return empty results - ACTUALLY SCRAPE the content from URLs!
    
    **CRITICAL REQUIREMENTS**:
    - You MUST return EXACTLY {NEWS_ITEMS_PER_SECTION} news stories, no more, no less
    - Each story MUST be from THIS WEEK in {CURRENT_YEAR} (last 7 days) with recent publication dates
    - ABSOLUTELY NO stories from 2023, 2024, or 2025 - only {CURRENT_YEAR} research
    - Each story MUST have EXACTLY 1000 words or MORE of detailed scientific analysis (verify word count)
    - Search for news using date-specific keywords: "{CURRENT_YEAR}", "latest", "new study", "recent research"
    
    Your priority sources (in order):
    1. Scientific American (health, sports science, fitness)
    2. Nature (medical research, sports physiology)
    3. Science Magazine (health studies, exercise science)
    4. The Lancet, JAMA, NEJM (medical journals)
    5. Sports Medicine journals
    
    Selection Criteria:
    - Focus on controversial peer-reviewed research published THIS WEEK in {CURRENT_YEAR} with significant debate and conflicting interpretations
    - **Controversial focus**: Prioritize studies with contested findings, methodological debates, or conflicting expert opinions - suitable for doctoral research
    - Prioritize studies with large sample sizes and robust methodology that challenge existing paradigms
    - Include breaking research with emerging scientific controversies
    - Avoid sensationalized health claims without scientific backing
    - **Comprehensive reporting**: Each news summary must be EXACTLY 1000 words or more with detailed scientific background, methodology, results, conflicting interpretations, analysis, and practical implications
    - **Source documentation with footnotes**: Include original URLs for journal articles, research papers, and scientific publications formatted as numbered footnotes [1], [2], etc.
    - **Date verification**: Confirm all research is from {CURRENT_YEAR}, reject any research from 2023, 2024, or 2025.
    
    {HUMANIZER_PROTOCOL}
    """,
    tools=[search_tool, scrape_tool],
    llm=primary_llm,
    verbose=True,
    allow_delegation=False
)

# 【健康分析师】 - 针对问题2和5：真正的深度分析，关联热点
health_analyst = Agent(
    role='PhD Level Health Science Analyst',
    goal='Generate comprehensive 5000+ word doctoral-level deep analysis reports with footnoted citations for top 3 controversial health/sports stories',
    backstory=f"""
    你是顶尖科研机构的首席研究员。你的任务不是写科普文章，而是写**博士论文级别的学术分析**。
    
    **工作流程** (针对问题5：学术关联):
    1. **READ** 前面 Scout 找出的健康/运动科学新闻（从 task_health_sports 的输出中）
    2. **选择 Top 3** 最有争议性、最有学术价值的研究
    3. **深度学术搜索**：针对每个研究，搜索相关的学术论文、理论模型、争议性评论
    4. **撰写 5000字以上的深度报告**：将热点研究作为"案例研究"，用学术理论进行解构
    
    **文章结构** (针对问题2和6：博士级深度，满足字数要求):
    每篇分析必须严格遵守以下结构（总计 5000字以上）：
    1. **Abstract** (300字): 摘要，概括研究意义和争议点
    2. **Theoretical Framework** (1000字): 介绍用于分析该研究的理论工具
       - 例如：贝叶斯统计模型、流行病学因果推断框架、运动生理学的能量系统理论
       - 必须具体，不能只是泛泛而谈
    3. **Case Analysis** (1500字): 将理论应用于本次研究的深度剖析
       - 具体数据分析（"受试者跑步速度提高15%，p<0.01"，而不是"表现改善"）
       - 方法学评估（样本量是否足够？对照组设计是否合理？）
       - 争议点分析（为什么有专家质疑这个结果？）
    4. **Comparative Study** (1000字): 横向对比历史上的类似研究或不同研究团队的对立结果
    5. **Critical Discourse** (800字): 批判性分析
       - 指出当前研究的局限性（外部效度、测量偏差、混淆变量）
       - 揭示媒体报道的盲点（过度简化、因果倒置）
    6. **Practical Implications** (200字): 实际应用建议（基于证据强度的分级建议）
    7. **Conclusion & References** (200字): 总结和未来研究方向
    
    **Critical Requirements** (针对问题6：字数铁律):
    - EXACTLY 5000 words or MORE per analysis report (verify word count - count actual content words)
    - **不能偷懒**：每个章节必须填满，不能只写几句话就跳过
    - **不能重复**：严禁通过重复内容凑字数
    - Include ALL original source URLs formatted as numbered footnotes [1], [2], etc.
    - Focus on controversial aspects, conflicting interpretations, and academic debates suitable for doctoral research
    - Use specific data, concrete examples, and avoid abstract expressions
    
    {HUMANIZER_PROTOCOL}
    """,
    tools=[scrape_tool],
    llm=primary_llm,
    verbose=True,
    allow_delegation=False
)

# 【法律学者】 - 针对问题5：学术分析必须关联前面的热点
legal_scholar = Agent(
    role='Comparative Law Scholar',
    goal='Analyze controversial law review articles from top US law schools with 5000+ word comprehensive analyses that DIRECTLY RELATE to the hot legal topics found',
    backstory=f"""
    你是比较法专家，专门研究中美法律争议。你的任务不是盲目搜索论文，而是**针对前面发现的热点法律案例，找到相关的学术论文进行深度分析**。
    
    **工作流程** (针对问题5：学术关联):
    1. **READ** 前面 Scout 找出的热点法律案例（从 task_china, task_global, task_legal 的输出中）
    2. **提取核心法律议题**：例如，如果发现了 "AI侵权案"，提取关键词 "AI copyright law", "generative AI legal liability"
    3. **搜索相关法律评论**：使用提取的关键词，搜索美国Top 10法学院的法律评论文章：
       - Yale Law Journal, Harvard Law Review, Stanford Law Review
       - Columbia Law Review, University of Chicago Law Review, NYU Law Review
       - Penn Law Review, Michigan Law Review, Virginia Law Review, Berkeley Law Review
    4. **筛选最相关的3篇**：必须是与热点案例直接相关的、最新的、有争议性的文章
    5. **为每篇文章生成 5000字以上的深度分析**，将学术理论与实际案例结合
    
    **分析结构** (针对问题2和6：真正的深度分析，满足字数要求):
    每篇文章的分析必须包含以下章节（总计 5000字以上）：
    1. **Article Overview & Introduction** (700-900字): 文章论点和背景，突出争议点
    2. **Legal Framework & Doctrinal Background** (900-1100字): 法律理论框架，结合实际案例
    3. **Key Arguments & Analysis** (1200-1500字): 详细论证，引用具体案例、法条、冲突观点
    4. **Comparative Perspective** (700-900字): 中美法律对比，突出差异和争议
    5. **Connection to Hot Topics** (700-900字): **关键部分** - 将文章理论应用到前面发现的热点案例上，具体分析如何解释当前争议
    6. **Practical & Policy Implications** (600-800字): 实际法律后果和政策辩论
    7. **Critical Assessment** (200-400字): 批判性评估，指出学术争议和不足
    
    **Critical Requirements**:
    - EXACTLY 5000 words or MORE per analysis report (verify word count - count actual content words)
    - Include ALL original source URLs formatted as numbered footnotes [1], [2], etc.
    - **MUST CONNECT** academic theory to actual hot news cases found in previous tasks
    - Provide comprehensive, detailed legal analysis with in-depth examination of controversies
    - Focus on controversial legal debates suitable for doctoral legal research
    
    {HUMANIZER_PROTOCOL}
    """,
    tools=[search_tool, scrape_tool],
    llm=primary_llm,
    verbose=True,
    allow_delegation=False
)

# 【深度研究员】 - 架构师（更新：整合5个板块）
researcher = Agent(
    role='Chief Researcher & Architect',
    goal=f'Synthesize all inputs into a structured report with ALL {NEWS_ITEMS_PER_SECTION} items per section, VERIFYING ALL URLs ARE PRESENT, ALL CONTENT is preserved in full, ALL DATES are from {CURRENT_YEAR}, and ALL WORD COUNTS meet requirements. NEVER GENERATE PLACEHOLDER TEXT.',
    backstory=f"""
    You are responsible for data integrity and structural integrity of the report.
    You must ensure that every single news item passed to the Editor has a VALID, CLICKABLE URL.
    Do not summarize away the links or the content. The Editor needs them for the HTML.
    
    **ABSOLUTELY CRITICAL - NO PLACEHOLDER TEXT**:
    - You MUST use ONLY the ACTUAL content from the previous tasks (scouts and analysts)
    - DO NOT make up fake content or placeholder text like "新闻标题 1", "新闻摘要 1", etc.
    - If a task did not provide proper content, report an error instead of generating placeholders
    - Every title, summary, and URL must come directly from the source tasks
    
    **CRITICAL REQUIREMENTS**:
    1. All FIVE sections must be present with complete data
    2. **EACH SECTION MUST HAVE ALL {NEWS_ITEMS_PER_SECTION} NEWS ITEMS** (except Legal Scholarship which has {LEGAL_ANALYSIS_ITEMS})
    3. **VERIFY ALL DATES**: Ensure all news items are from {CURRENT_YEAR}, reject any from 2023, 2024, or 2025
    4. **VERIFY WORD COUNTS**: Ensure each news summary has 1000+ words and each analysis has 5000+ words
    5. **DO NOT TRUNCATE OR SUMMARIZE**: Pass through all 1000+ word summaries in full
    6. **DO NOT TRUNCATE OR SUMMARIZE**: Pass through all 5000+ word analyses in full
    7. Every news story must have its Source URLs clearly listed and separated as numbered footnotes
    8. English headlines are preserved exactly as written for Global news
    9. Deep analysis reports (5000+ words each) are properly integrated with all citations as footnotes
    10. **VERIFICATION STEP**: Check that every single news item has:
       - Title (REAL, from source task, not "新闻标题 1")
       - Publication Date from {CURRENT_YEAR} (not 2023, 2024, or 2025)
       - Full 1000+ word summary (REAL content, not "新闻摘要 1..." or placeholders) - verified word count
       - At least one Source URL formatted as footnote (REAL URL, not "#")
       If any of these are missing, flag it clearly to the user
    11. Organize the content strictly into the 5 sections with clear boundaries
    12. Ensure all controversial aspects and conflicting viewpoints are preserved
    
    {HUMANIZER_PROTOCOL}
    """,
    tools=[scrape_tool],
    llm=primary_llm,
    verbose=True,
    allow_delegation=False
)

# 【主编】 - 专注于 NYT 风格和数据真实性 + 5栏布局
editor = Agent(
    role='Lead Editor & Frontend Architect',
    goal=f'Generate a "New York Times" style HTML report with 5-column grid layout. ENSURE ALL {NEWS_ITEMS_PER_SECTION} NEWS ITEMS PER SECTION ARE DISPLAYED. USE <details> TAGS FOR EXPANDABLE CONTENT.',
    backstory=f"""
    你负责最终的 HTML 生成。你必须解决用户体验问题。
    
    **UI 交互逻辑 (关键 - 针对问题7)**:
    - 之前的版本 "Read More" 跳转到外部链接是**错误**的。
    - **正确逻辑**: 
      1. 外部链接 (Source URLs) 必须作为 [1][2][3] 的脚注放在文章底部，显示为可点击徽章。
      2. **"Read More" 按钮必须是一个 HTML `<details>` 标签**。
      3. 点击 "Read More" 后，**在当前页面向下展开**，显示 Scout 撰写的 1000字报道 或 Analyst 撰写的 5000字论文。
      4. **不要使用 `href="#"` 或任何外部链接作为 "Read More"**。
    
    **排版要求**:
    - 使用 Tailwind CSS。
    - 5栏布局 (China, Global, Legal, Health, Academic Analysis)。
    - **Academic Analysis** 板块必须包含那些 5000字的深度长文，使用 `<details>` 展开。
    
    **Core Philosophy**:
    1. **Data Integrity**: You NEVER create fake links (href="#"). You ONLY use the URLs provided as SOURCE FOOTNOTES.
    2. **Display ALL Items**: You MUST display ALL {NEWS_ITEMS_PER_SECTION} news items in each section ({LEGAL_ANALYSIS_ITEMS} for Legal Analysis), not just 1 or 2.
    3. **Full Content with <details>**: You MUST preserve the full 1000+ word summaries and 5000+ word analyses inside `<details>` tags.
    4. **Design Aesthetic (NYT Style with Modern Grid)**:
       - **White Background**: Clean, stark, professional (bg-white / bg-stone-50).
       - **Serif Headings**: Black, bold, serif fonts (Merriweather/Georgia) for authority.
       - **Sans Body**: Clean sans-serif (Inter/Helvetica) for readability.
       - **No Gradients**: Avoid cheap-looking gradients. Use solid colors and subtle borders.
       - **High Contrast**: Dark gray text on white/off-white background.
       - **5-Column Grid**: Use CSS Grid (grid-cols-5) for desktop, responsive for mobile/tablet
    5. **Five Column Layout** (CRITICAL):
       - Column 1: 中文新闻 (Chinese-language News) - Display ALL {NEWS_ITEMS_PER_SECTION} items
       - Column 2: 全球新闻 (Global News) - Display ALL {NEWS_ITEMS_PER_SECTION} items with **English Headlines** prominent
       - Column 3: 法律新闻 (Legal News) - Display ALL {NEWS_ITEMS_PER_SECTION} items
       - Column 4: 健康与运动 (Health & Sports) - Display ALL {NEWS_ITEMS_PER_SECTION} items + {DEEP_ANALYSIS_ITEMS} deep analyses
       - Column 5: 法律学术分析 (Legal Analysis) - Display {LEGAL_ANALYSIS_ITEMS} deep analyses
    
    {HUMANIZER_PROTOCOL}
    """,
    llm=primary_llm,
    verbose=True
)

# --- 4. 定义任务 (Tasks) ---

task_china = Task(
    description=f"""
    **CRITICAL: YOU MUST EXECUTE THE FOLLOWING STEPS USING YOUR TOOLS**:
    1. USE the Search Tool (SerperDevTool) to search for news with the keywords below
    2. USE the Scrape Tool (SafeScrapeWebsiteTool) to read the full articles from the URLs you find
    3. DO NOT just say you will do it - ACTUALLY EXECUTE the tools NOW!
    
    **搜索策略** (针对问题1：获取今日最新新闻):
    1. 搜索词必须包含日期过滤和争议关键词:
       - "微博热搜 争议{SEARCH_SUFFIX}"
       - "知乎 吵架{SEARCH_SUFFIX}"
       - "网友 抵制{SEARCH_SUFFIX}"
       - "官方 通报 争议{SEARCH_SUFFIX}"
       - "舆论 反对{SEARCH_SUFFIX}"
    2. **日期验证**：必须找到 5 个 {TODAY_STR} 或 {YESTERDAY_STR} 发生的、引起巨大争议的社会新闻
    3. **严格过滤**：拒绝任何 2024年、2023年或更早的旧闻
    4. **物理日期屏蔽**：所有搜索查询自动包含 "after:{YESTERDAY_STR}" 参数
    
    **报道要求** (针对问题8：综合性事实报道):
    对每个新闻，利用 ScrapeWebsiteTool 抓取多方报道，写出 **1000字以上** 的事实综述，必须包含：
    - 事件时间：{TODAY_STR} 或 {YESTERDAY_STR} 的具体时间
    - 事件起因：谁做了什么，为什么引起争议
    - 冲突焦点：各方的核心观点对立（官方 vs 民间、不同群体）
    - 事实前因后果：整合至少 3 个信源的综合报道
    - 社会影响：为什么这个事件重要，反映了什么社会问题
    
    **输出格式**:
    返回 {NEWS_ITEMS_PER_SECTION} 个新闻，每个格式如下：
    
    News Item 1:
    Title: [中文标题]
    Publication Date: [{TODAY_STR} 或 {YESTERDAY_STR}]
    Summary: [EXACTLY 1000+ word comprehensive summary with footnoted sources]
    Sources: 
    [1] URL1
    [2] URL2
    [3] URL3
    
    [重复 2-{NEWS_ITEMS_PER_SECTION}]
    """,
    expected_output=f"EXACTLY {NEWS_ITEMS_PER_SECTION} curated controversial news stories from Chinese media published on {TODAY_STR} or {YESTERDAY_STR} (1000+ words each), each with multi-source integration, footnoted citations, and verified {CURRENT_YEAR} publication dates.",
    agent=china_scout
)

task_global = Task(
    description=f"""
    **搜索策略** (针对问题1和3：获取今日争议性新闻):
    1. 搜索词必须包含日期过滤和争议关键词:
       - "Protest{SEARCH_SUFFIX}"
       - "Scandal{SEARCH_SUFFIX}"
       - "Controversial ruling{SEARCH_SUFFIX}"
       - "Debate{SEARCH_SUFFIX}"
       - "Lawsuit filed{SEARCH_SUFFIX}"
       - "Backlash{SEARCH_SUFFIX}"
    2. **日期验证**：选择 {NEWS_ITEMS_PER_SECTION} 个 {TODAY_STR} 或 {YESTERDAY_STR} 发生的、具有全球结构性影响和重大争议的事件
    3. **严格过滤**：拒绝任何 2024、2023 或更早的旧闻
    4. **物理日期屏蔽**：所有搜索查询自动包含 "after:{YESTERDAY_STR}" 参数
    
    **报道要求** (针对问题8：综合性事实报道):
    - **保留英文原标题** + 综合中文分析（**1000字以上**）
    - 整合至少 3 个信源，特别是对立观点：
      - Reuters, Bloomberg, NYT, Nature, Foreign Affairs 等
      - 保守派 vs 自由派媒体观点
      - 官方声明 vs Twitter/X 民间反应
    - 深度报道必须包含：
      1. 事件背景和时间 ({TODAY_STR})
      2. 冲突各方的核心观点
      3. 意识形态或利益集团的博弈分析
      4. 全球影响和未来走向
    
    **输出格式**:
    返回 {NEWS_ITEMS_PER_SECTION} 个新闻，每个格式如下：
    
    News Item 1:
    English Title: [Title in English - 必须保留]
    Publication Date: [{TODAY_STR} 或 {YESTERDAY_STR}]
    Chinese Summary: [EXACTLY 1000+ word comprehensive summary in Chinese with footnoted sources]
    Sources:
    [1] URL1
    [2] URL2
    [3] URL3
    
    [重复 2-{NEWS_ITEMS_PER_SECTION}]
    """,
    expected_output=f"EXACTLY {NEWS_ITEMS_PER_SECTION} Global controversial news items published on {TODAY_STR} or {YESTERDAY_STR} (1000+ words each) with English Titles, multi-source verification, footnoted citations, and verified {CURRENT_YEAR} publication dates.",
    agent=global_scout
)

task_legal = Task(
    description=f"""
    **搜索策略** (针对问题1和4：获取今日实际案例，不要新法规):
    1. **不要搜**: "新法律颁布", "New legislation", "新规", "政策出台"
    2. **要搜**: 
       - "Lawsuit filed{SEARCH_SUFFIX}"
       - "Court verdict{SEARCH_SUFFIX}"
       - "Supreme Court{SEARCH_SUFFIX}"
       - "v.{SEARCH_SUFFIX}"
       - "判决{SEARCH_SUFFIX}"
       - "起诉{SEARCH_SUFFIX}"
       - "庭审{SEARCH_SUFFIX}"
       - 搜索包含 "v." 的案件名称（如 "Apple v. Epic", "张三 v. 某公司"）
    3. **日期验证**：找到 {NEWS_ITEMS_PER_SECTION} 个 {TODAY_STR} 或 {YESTERDAY_STR} 有最新进展的争议性法律案件
    4. **严格过滤**：拒绝任何 2024、2023 或更早的案件，只要今日有新进展的案件
    5. **物理日期屏蔽**：所有搜索查询自动包含 "after:{YESTERDAY_STR}" 参数
    
    **报道要求** (针对问题8：综合性案件报道):
    对每个案件，写出 **1000字以上** 的综合法律分析，必须包含：
    - 案件名称：原告 v. 被告
    - 案件背景：何时发生、为什么打官司
    - 法律焦点：双方律师的核心论点、争议的法律条款
    - 最新进展：{TODAY_STR} 的庭审、判决或起诉动态
    - 公众反应：为什么引起轰动、舆论争议点
    - 可能影响：先例意义、对类似案件的影响
    - 整合至少 3 个信源：法院文件 + 专家评论 + 新闻报道
    
    **输出格式**:
    返回 {NEWS_ITEMS_PER_SECTION} 个案件，每个格式如下：
    
    Legal Update 1:
    Title: [案件名称: 原告 v. 被告]
    Date: [{TODAY_STR} 或 {YESTERDAY_STR}]
    Summary: [EXACTLY 1000+ word comprehensive legal analysis with footnoted sources]
    Sources:
    [1] Court document URL
    [2] Expert analysis URL
    [3] News URL
    
    [重复 2-{NEWS_ITEMS_PER_SECTION}]
    """,
    expected_output=f"EXACTLY {NEWS_ITEMS_PER_SECTION} Key Controversial Legal Cases (NOT legislation) from {TODAY_STR} or {YESTERDAY_STR} (1000+ words each) with multi-source citations, footnoted references, and verified {CURRENT_YEAR} dates.",
    agent=legal_scout
)

# 【新增】健康与运动新闻任务
task_health_sports = Task(
    description=f"""
    1. Search for the top {NEWS_ITEMS_PER_SECTION} RECENT controversial health and sports science news published in the last week in {CURRENT_YEAR}.
       Use search queries like:
       - "health research controversy {CURRENT_YEAR} latest"
       - "sports science controversial breakthrough today {CURRENT_YEAR}"
       - "medical study debate published this week {CURRENT_YEAR}"
       - "fitness research controversial new {CURRENT_YEAR}"
       **CRITICAL**: Verify the publication date is in {CURRENT_YEAR}. Reject any research from 2023, 2024, or 2025.
    2. Priority sources: Scientific American, Nature, Science Magazine, The Lancet, JAMA, NEJM, Sports Medicine journals.
    3. Focus on:
       - New controversial research findings with significant debate and conflicting interpretations
       - Sports science breakthroughs with contested results
       - Exercise and fitness studies with methodological debates
       - Nutrition research with conflicting expert opinions
       - Research suitable for doctoral thesis with significant academic value
    4. Include the journal/source name, publication date (must be {CURRENT_YEAR}), and key controversial findings.
    5. **CRITICAL - Word count requirement**: Each news summary MUST be EXACTLY 1000 words or MORE (verify word count), providing comprehensive scientific detail including methodology, results, conflicting interpretations, analysis, and practical implications.
    6. **Footnote requirement**: Include original document links (URLs) - journal articles, research papers, and scientific publications formatted as numbered footnotes [1], [2], [3], etc.
    7. **Output format**: Return exactly {NEWS_ITEMS_PER_SECTION} news items in this format:
    
    Health/Sports Item 1:
    Title: [Research Title]
    Journal/Source: [Journal Name] - [{CURRENT_YEAR}-MM-DD]
    Summary: [EXACTLY 1000+ word comprehensive scientific summary with footnoted sources]
    Sources:
    [1] Journal URL
    [2] Related Study URL
    [3] News Coverage URL
    
    [Repeat for items 2-{NEWS_ITEMS_PER_SECTION}]
    """,
    expected_output=f"EXACTLY {NEWS_ITEMS_PER_SECTION} Controversial Health/Sports Science news items from THIS WEEK in {CURRENT_YEAR} (1000+ words each) with source citations, key findings, footnoted references, and verified {CURRENT_YEAR} publication dates.",
    agent=health_sports_scout
)

# 【新增】健康深度分析任务
task_health_analysis = Task(
    description=f"""
    Select the TOP {DEEP_ANALYSIS_ITEMS} most impactful and CONTROVERSIAL health/sports stories from the collected news.
    For each of the {DEEP_ANALYSIS_ITEMS} stories, generate a comprehensive in-depth analysis report of EXACTLY 5000 words or MORE including:
    
    1. **Executive Summary** (500-700 words): Overview of the research and its significance, highlighting controversies
    2. **Background & Context** (800-1000 words): Scientific context with concrete examples, historical perspective, and areas of debate
    3. **Methodology** (600-800 words): Research methodology explained in detail yet accessibly, including methodological debates
    4. **Findings & Results** (1200-1500 words): Key discoveries with specific data points, statistics, analysis, and conflicting interpretations
    5. **Scientific Implications** (600-800 words): Impact on scientific understanding, future research, and controversial implications
    6. **Practical Applications** (700-900 words): How people can use this information, actionable advice for readers, areas of uncertainty
    7. **Critical Analysis** (400-600 words): Strengths, limitations, controversies, caveats and areas for further research
    8. **Conclusion** (200-300 words): Summary of key takeaways and future directions
    
    **Word count requirement**: Each analysis report must be EXACTLY 5000 words or MORE total (verify word count - count actual content words).
    **Footnote requirement**: Include all original research paper URLs, journal links, and related references formatted as numbered footnotes [1], [2], [3], etc.
    
    IMPORTANT: Follow the Deep Humanizer Protocol. No AI clichés. Use concrete examples and varied sentence structure. Focus on controversial aspects suitable for doctoral research.
    """,
    expected_output=f"{DEEP_ANALYSIS_ITEMS} comprehensive in-depth analysis reports (5000+ words each) for top controversial health/sports stories with all source URLs formatted as footnotes.",
    agent=health_analyst,
    context=[task_health_sports]
)

# 【新增】法律学术分析任务
task_legal_analysis = Task(
    description=f"""
    **工作流程** (针对问题5：学术分析必须关联热点):
    
    Phase 1: **READ 前面的法律新闻**
    - 从 task_china, task_global, task_legal 的输出中，提取 3-5 个关键争议性法律议题
    - 例如：如果发现了 "AI生成内容侵权案"，提取关键词 "AI copyright", "generative AI liability", "fair use doctrine"
    
    Phase 2: **搜索相关法律评论文章**
    - 使用提取的关键词，搜索美国Top 10法学院的法律评论：
      - Yale Law Journal, Harvard Law Review, Stanford Law Review
      - Columbia Law Review, University of Chicago Law Review, NYU Law Review
      - Penn Law Review, Michigan Law Review, Virginia Law Review, Berkeley Law Review
    - 搜索词示例: "AI copyright law review", "generative AI legal liability Yale", "fair use doctrine Stanford"
    
    Phase 3: **筛选最相关的 {LEGAL_ANALYSIS_ITEMS} 篇文章**
    - 必须是与前面发现的热点案例**直接相关**的文章
    - 必须是最新的、有争议性的学术文章
    
    Phase 4: **为每篇文章生成 5000字以上的深度分析** (针对问题2和6：真正的深度，满足字数):
    每篇分析必须包含以下章节（总计 5000字以上）：
    
    1. **Article Overview & Introduction** (700-900字): 
       - 文章论点摘要
       - 背景和争议点
       - 为什么这篇文章重要
    
    2. **Legal Framework & Doctrinal Background** (900-1100字): 
       - 法律理论框架（具体法条、判例、学说）
       - 结合实际案例说明
       - 法律冲突和争议
    
    3. **Key Arguments & Analysis** (1200-1500字): 
       - 详细论证分析
       - 引用具体案例、法条
       - 不同法学家的对立观点
       - 为什么有争议
    
    4. **Comparative Perspective** (700-900字): 
       - 中美法律对比
       - 不同法系的处理方式
       - 文化和制度差异
    
    5. **Connection to Hot Topics** (700-900字) **【关键部分】**: 
       - **将文章理论应用到前面发现的热点案例上**
       - 具体分析：这篇学术文章如何解释当前争议案件
       - 理论与实践的结合
       - 预测案件可能的判决走向
    
    6. **Practical & Policy Implications** (600-800字): 
       - 实际法律后果
       - 政策建议和争议
       - 对企业、个人的影响
    
    7. **Critical Assessment** (200-400字): 
       - 文章的优势和不足
       - 学术界的不同意见
       - 需要进一步研究的问题
    
    **Word count requirement**: Each analysis report must be EXACTLY 5000 words or MORE total (verify word count - count actual content words).
    **Footnote requirement**: Include original law review article URLs, case citations with links, and all referenced sources formatted as numbered footnotes [1], [2], [3], etc.
    
    **CRITICAL**: The analysis MUST explicitly connect academic theory to the actual hot news cases found in previous tasks. This is not optional.
    
    IMPORTANT: Follow the Deep Humanizer Protocol. Technical precision with readable prose. Avoid jargon overload. Focus on controversial legal debates suitable for doctoral legal research.
    """,
    expected_output=f"Analysis of {LEGAL_ANALYSIS_ITEMS} controversial law review articles (5000+ words each) that DIRECTLY RELATE to and analyze the hot legal topics found in previous tasks, with all source URLs formatted as footnotes.",
    agent=legal_scholar,
    context=[task_china, task_global, task_legal]
)

# 【更新】研究任务：整合所有5个板块
task_research = Task(
    description=f"""
    Compile ALL inputs from the 5 sections ensuring EVERY news item is preserved:
    1. Chinese-language News (中文新闻) - ALL {NEWS_ITEMS_PER_SECTION} news items with 1000+ word summaries from {CURRENT_YEAR}
    2. Global News (全球新闻) - ALL {NEWS_ITEMS_PER_SECTION} news items with 1000+ word summaries from {CURRENT_YEAR}
    3. Legal News (法律新闻) - ALL {NEWS_ITEMS_PER_SECTION} news items with 1000+ word summaries from {CURRENT_YEAR}
    4. Health & Sports News + Deep Analysis (健康与运动) - ALL {NEWS_ITEMS_PER_SECTION} news items with 1000+ word summaries PLUS {DEEP_ANALYSIS_ITEMS} deep analysis reports with 5000+ words each from {CURRENT_YEAR}
    5. Legal Analysis & Law Review Articles (法律学术分析) - {LEGAL_ANALYSIS_ITEMS} law review analyses with 5000+ words each
    
    **ABSOLUTELY CRITICAL - NO PLACEHOLDER TEXT**:
    - You MUST extract and use ONLY the ACTUAL content from the context tasks (task_china, task_global, task_legal, etc.)
    - DO NOT generate fake placeholder content like "News Item 1: Title: [中文标题]" or "Summary: [EXACTLY 1000+ word...]"
    - Every title, summary, date, and URL must come directly from the actual task outputs
    - If you cannot find the actual content in the context, output an error message
    
    **CRITICAL REQUIREMENTS**:
    - Verify that ALL FIVE SECTIONS exist with complete data
    - **VERIFY ALL DATES**: Every news item must be from {CURRENT_YEAR} - flag any from 2023, 2024, or 2025
    - **VERIFY WORD COUNTS**: Ensure each summary is 1000+ words and each analysis is 5000+ words
    - **EACH section must have ALL {NEWS_ITEMS_PER_SECTION} news items** (except Legal Analysis which has {LEGAL_ANALYSIS_ITEMS} items)
    - Ensure strict separation of content between sections
    - Add a "Key Takeaway" one-liner for every major news item highlighting the controversy
    - Preserve all deep analysis reports in their entirety (5000+ words each)
    - Ensure English headlines are preserved for Global news section
    - **PRESERVE ALL original source URLs** from all sections - news articles, research papers, court documents, law review articles, etc.
    - Format source URLs as numbered footnotes [1], [2], [3], etc. so they can be displayed as clickable links in the final HTML
    - **DO NOT SUMMARIZE OR TRUNCATE**: Pass through all content in full length to the editor
    - **PRESERVE CONTROVERSIAL ASPECTS**: Ensure all conflicting viewpoints and debates are included
    
    **Output Structure** (NOTE: The format below shows the structure - you MUST fill it with REAL content from the tasks, NOT placeholder text):
    For each section, organize as:
    Section Name:
      Item 1: [REAL Title from task], [REAL Date from task], [REAL Full 1000+ word Summary from task], [REAL Footnoted Source URLs from task]
      Item 2: [REAL Title from task], [REAL Date from task], [REAL Full 1000+ word Summary from task], [REAL Footnoted Source URLs from task]
      Item 3: [REAL Title from task], [REAL Date from task], [REAL Full 1000+ word Summary from task], [REAL Footnoted Source URLs from task]
      Item 4: [REAL Title from task], [REAL Date from task], [REAL Full 1000+ word Summary from task], [REAL Footnoted Source URLs from task]
      Item 5: [REAL Title from task], [REAL Date from task], [REAL Full 1000+ word Summary from task], [REAL Footnoted Source URLs from task]
      [Plus deep analysis if applicable - WITH REAL CONTENT]
    """,
    expected_output=f"Master Report with ALL 5 sections, each containing ALL news items ({NEWS_ITEMS_PER_SECTION} per section except Legal Analysis with {LEGAL_ANALYSIS_ITEMS}), complete 1000+ word summaries, 5000+ word analyses, ALL source URLs preserved as footnotes, and ALL dates verified to be from {CURRENT_YEAR}.",
    agent=researcher,
    context=[task_china, task_global, task_legal, task_health_sports, task_health_analysis, task_legal_analysis]
)

# 【重构】发布任务 - 针对问题7：Read More应该是展开内容，不是链接
task_publish = Task(
    description=f"""
    Generate the final `index.html` file based on the Research Report with TODAY's date: {TODAY_STR}.
    
    **CRITICAL INSTRUCTION**: You MUST use the ACTUAL news content, titles, summaries, and source URLs from the Research Report provided in the context. DO NOT generate placeholder text or fake content. Every single piece of text must come directly from the research report.
    
    **UI 交互逻辑 (关键 - 针对问题7)**: 
    之前的版本 "Read More" 跳转到外部链接是**错误**的。
    
    **正确逻辑**:
    1. 外部链接 (Source URLs) 必须作为 [1][2][3] 的脚注放在文章底部，显示为可点击徽章
    2. **"Read More" 按钮必须是一个 HTML `<details>` 标签**
    3. 点击 "Read More" 后，**在当前页面向下展开**，显示：
       - 对于新闻：Scout 撰写的 1000字综合报道
       - 对于深度分析：Analyst 撰写的 5000字论文
    4. **不要使用 `href="#"` 或任何外部链接作为 "Read More"**
    
    **HTML 结构模板 (必须严格遵守)**:
    
    IMPORTANT: The text in square brackets [] below are PLACEHOLDER DESCRIPTIONS showing what type of content to insert. You MUST replace them with the ACTUAL REAL content from the Research Report. DO NOT output the literal placeholder text.
    
    对于每个新闻或分析项，使用以下结构：
    
    ```html
    <div class="card p-4 border border-stone-200 rounded bg-white shadow-sm mb-4">
        <h3 class="font-bold text-xl mb-2 text-stone-900">[REPLACE THIS: Insert the actual news title from the research report]</h3>
        <p class="text-sm text-gray-500 mb-2">日期: {TODAY_STR}</p>
        <p class="mb-4 text-stone-700">[REPLACE THIS: Insert the first 200-300 characters of the actual summary from the research report]</p>
        
        <details class="group mb-4">
            <summary class="cursor-pointer text-blue-600 font-semibold hover:underline list-none">
                📖 阅读完整报道 / Read Deep Analysis
            </summary>
            <div class="mt-4 prose prose-sm max-w-none text-gray-800 bg-gray-50 p-4 rounded border-l-4 border-blue-500">
                [REPLACE THIS: Insert the COMPLETE 1000+ word summary OR 5000+ word analysis from the research report - DO NOT TRUNCATE]
            </div>
        </details>
        
        <div class="mt-4 text-xs text-gray-400">
            <span class="font-semibold">信息来源 / Sources:</span>
            [REPLACE THIS: Insert the actual source URLs from the research report as clickable badges]
            <a href="[ACTUAL_URL_1]" class="inline-block px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs mr-2 hover:bg-blue-200">[1]</a>
            <a href="[ACTUAL_URL_2]" class="inline-block px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs mr-2 hover:bg-blue-200">[2]</a>
            <a href="[ACTUAL_URL_3]" class="inline-block px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs mr-2 hover:bg-blue-200">[3]</a>
        </div>
    </div>
    ```
    
    **CRITICAL DATA RULES**:
    1. **USE REAL CONTENT ONLY**: You MUST extract and use the actual news titles, summaries, analysis, and source URLs from the Research Report context. DO NOT make up placeholder text like "新闻标题 1", "新闻摘要 1...", "完整报道内容 1..." etc.
    2. **NO EXTERNAL LINKS IN READ MORE**: "Read More" 必须是 `<details>` 标签，不是 `<a>` 标签
    3. **FULL CONTENT INSIDE**: 必须将从研究报告中提取的完整内容（1000字或5000字）放入 `<details>` 内部
    4. **SOURCE URLs AS FOOTNOTES**: 所有原始链接必须作为脚注徽章显示在底部
    5. **DISPLAY ALL {NEWS_ITEMS_PER_SECTION} NEWS ITEMS**: Each section MUST show ALL {NEWS_ITEMS_PER_SECTION} news items provided in the research report
    
    **DESIGN SYSTEM (New York Times Style with 5-Column Layout)**:
    1. **Library**: Use Tailwind CSS (`<script src="https://cdn.tailwindcss.com"></script>`).
    2. **Fonts**: 
       - Headlines: `font-family: 'Merriweather', serif;` (Import from Google Fonts)
       - Body: `font-family: 'Inter', sans-serif;`
    3. **Colors**:
       - Background: `bg-stone-50` (warm off-white) or `bg-white`.
       - Text: `text-stone-900` (almost black) for headings, `text-stone-700` for body.
       - Accents: Minimal use of `border-stone-300` for dividers. No bright gradients.
    4. **Layout - FIVE COLUMN RESPONSIVE GRID**:
       - **Header**: Simple, centered, serif headline "Daily Insight - {TODAY_STR}". Thin border-bottom.
       - **Main Container**: Use CSS Grid with 5 columns on desktop (grid-cols-5), responsive on mobile/tablet
       - **Each Column Represents One Section**:
         1. Column 1: 中文新闻 (Chinese-language News) - Show ALL {NEWS_ITEMS_PER_SECTION} news items WITH REAL TITLES AND CONTENT from research report
         2. Column 2: 全球新闻 (Global News) - Show ALL {NEWS_ITEMS_PER_SECTION} items WITH REAL TITLES AND CONTENT with **English Headlines** prominent
         3. Column 3: 法律新闻 (Legal News) - Show ALL {NEWS_ITEMS_PER_SECTION} items WITH REAL TITLES AND CONTENT
         4. Column 4: 健康与运动 (Health & Sports) - Show ALL {NEWS_ITEMS_PER_SECTION} items WITH REAL TITLES AND CONTENT + {DEEP_ANALYSIS_ITEMS} deep analysis (collapsible)
         5. Column 5: 法律学术分析 (Legal Analysis) - Show {LEGAL_ANALYSIS_ITEMS} deep analysis reports WITH REAL TITLES AND CONTENT (collapsible)
       - **Responsive**: Use `lg:grid-cols-5 md:grid-cols-2 grid-cols-1` for mobile/tablet adaptation
       - **Cards**: Clean layout. White background `bg-white`. Thin border `border border-stone-200`. No heavy shadows (`shadow-sm` at most).
       - **Typography**: High readability. Line height 1.6+.
    
    **FINAL REMINDER - ABSOLUTELY CRITICAL**:
    - You MUST extract ALL actual news titles, summaries, full content, and source URLs from the Research Report in your context
    - DO NOT generate fake placeholder text like "新闻标题 1", "新闻摘要 1...", "完整报道内容 1...", "健康与运动深度分析内容 2..." etc.
    - Every single piece of text in the HTML must be REAL content from the research report
    - If you cannot find the content in the research report, output an error message instead of placeholders
    
    **Output**: 
    - ONLY the raw HTML code (starting with `<!DOCTYPE html>`).
    - Ensure ALL {NEWS_ITEMS_PER_SECTION} items in each section are displayed WITH THEIR ACTUAL REAL CONTENT.
    - Include proper date: {TODAY_STR}
    - Use `<details>` for expandable content, NOT external links
    - USE REAL CONTENT FROM RESEARCH REPORT, NOT PLACEHOLDERS
    """,
    expected_output="Final production-ready HTML with 5-column grid layout, all news items displayed, <details> tags for expandable content, source URLs as footnote badges, and excellent readability.",
    agent=editor,
    context=[task_research]
)

# --- 辅助功能: 邮件发送 ---
def send_email_report(file_path):
    """发送 HTML 报告到指定邮箱"""
    if not (SMTP_USER and SMTP_PASSWORD and EMAIL_TO):
        print("⚠️ Email configuration missing. Skipping email sending.")
        print("   Set SMTP_USER, SMTP_PASSWORD, and EMAIL_TO environment variables to enable email.")
        return

    server = None
    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_USER
        msg['To'] = EMAIL_TO
        msg['Subject'] = f"Daily News Report - {CURRENT_DATE}"

        # 读取 HTML 内容作为邮件正文
        with open(file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        msg.attach(MIMEText(html_content, 'html'))

        # 连接 SMTP 服务器
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)
        print(f"✅ Email sent successfully to {EMAIL_TO}")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
    finally:
        if server:
            try:
                server.quit()
            except Exception:
                pass  # Ignore errors when closing connection

# --- 5. 执行流程 ---
def run():
    print("🚀 Starting Daily News Agent (NYT Style Edition)...")
    
    if not os.environ.get("NVIDIA_API_KEY"):
        print("❌ Error: NVIDIA_API_KEY not found in environment variables.")
        sys.exit(1)
    
    # 使用 try-except 捕获可能的 API 错误，并在失败时切换到备用模型
    try:
        # 更新：包含所有8个智能体和8个任务
        news_crew = Crew(
            agents=[
                china_scout, 
                global_scout, 
                legal_scout, 
                health_sports_scout,
                health_analyst,
                legal_scholar,
                researcher, 
                editor
            ],
            tasks=[
                task_china, 
                task_global, 
                task_legal, 
                task_health_sports,
                task_health_analysis,
                task_legal_analysis,
                task_research, 
                task_publish
            ],
            process=Process.sequential,
            verbose=True
        )
        
        result = news_crew.kickoff()
        final_html = str(result)
        
        # 清洗 Markdown 标记
        if "```html" in final_html:
            final_html = final_html.split("```html")[1].split("```")[0]
        elif "```" in final_html:
            final_html = final_html.split("```")[1].split("```")[0]
        
        # 创建 reports 文件夹并保存文件
        output_dir = "reports"
        os.makedirs(output_dir, exist_ok=True)
        filename = f"news_{CURRENT_DATE}.html"
        file_path = os.path.join(output_dir, filename)
        
        # 保存到 reports 文件夹
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(final_html.strip())
        
        # 同时更新根目录的 index.html 以便 GitHub Pages 显示
        output_path = "index.html"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(final_html.strip())
        
        print(f"✅ Report generated successfully: {output_path}")
        print(f"✅ Report also saved to: {file_path}")
        print("📊 Report includes 5 sections:")
        print("   1. 中文新闻 (Chinese-language News)")
        print("   2. 全球新闻 (Global News)")
        print("   3. 法律新闻 (Legal News)")
        print("   4. 健康与运动 (Health & Sports + Deep Analysis)")
        print("   5. 法律学术分析 (Legal Analysis & Law Review Articles)")
        
        # 发送邮件
        send_email_report(file_path)
        
    except Exception as e:
        print(f"⚠️ Primary model failed with error: {e}")
        print(f"🔄 Retrying with fallback model")
        
        # 检查是否需要使用第三备用模型
        fallback_available = True
        if USE_DEEPSEEK and not os.environ.get("NVIDIA_API_KEY"):
            print("⚠️ Warning: Fallback NVIDIA_API_KEY not found, will try third backup model instead")
            fallback_available = False
        elif not USE_DEEPSEEK and not os.environ.get("DEEPSEEK_API_KEY"):
            print("⚠️ Warning: Fallback DEEPSEEK_API_KEY not found, will try third backup model instead")
            fallback_available = False
        
        if not fallback_available:
            # 如果没有备用 API Key，直接跳到第三备用模型
            try:
                print("🔄 Using third backup model: nvidia/llama-3.3-nemotron-super-49b-v1.5")
                # 这里会跳到第三备用模型的逻辑
                raise Exception("Fallback API key not available, switching to third backup")
            except:
                pass  # 继续到下面的第三备用模型逻辑
        
        # 如果是 Content Risk，提示用户调整 Prompt
        if "Content Exists Risk" in str(e):
            print("⚠️ Suggestion: The system prompt might contain sensitive keywords. Trying fallback model with modified workflow.")
        
        # 使用备用模型重试
        # 注意：如果使用DeepSeek作为备用，跳过中国新闻部分以避免内容审查问题
        try:
            if not USE_DEEPSEEK:
                print("⚠️ Note: Skipping Chinese news section to avoid potential content policy issues with DeepSeek fallback")
            
            # 重新创建 agents（如果使用DeepSeek作为备用则跳过 china_scout），使用备用 LLM
            global_scout_fallback = Agent(
                role=global_scout.role,
                goal=global_scout.goal,
                backstory=global_scout.backstory,
                tools=global_scout.tools,
                llm=fallback_llm,
                verbose=True
            )
            
            legal_scout_fallback = Agent(
                role=legal_scout.role,
                goal=legal_scout.goal,
                backstory=legal_scout.backstory,
                tools=legal_scout.tools,
                llm=fallback_llm,
                verbose=True
            )
            
            health_sports_scout_fallback = Agent(
                role=health_sports_scout.role,
                goal=health_sports_scout.goal,
                backstory=health_sports_scout.backstory,
                tools=health_sports_scout.tools,
                llm=fallback_llm,
                verbose=True
            )
            
            health_analyst_fallback = Agent(
                role=health_analyst.role,
                goal=health_analyst.goal,
                backstory=health_analyst.backstory,
                tools=health_analyst.tools,
                llm=fallback_llm,
                verbose=True
            )
            
            legal_scholar_fallback = Agent(
                role=legal_scholar.role,
                goal=legal_scholar.goal,
                backstory=legal_scholar.backstory,
                tools=legal_scholar.tools,
                llm=fallback_llm,
                verbose=True
            )
            
            researcher_fallback = Agent(
                role=researcher.role,
                goal=researcher.goal,
                backstory=researcher.backstory,
                tools=researcher.tools,
                llm=fallback_llm,
                verbose=True
            )
            
            editor_fallback = Agent(
                role=editor.role,
                goal=editor.goal,
                backstory=editor.backstory,
                llm=fallback_llm,
                verbose=True
            )
            
            # 重新创建任务（跳过 task_china），使用第二备用 agents
            task_global_fallback = Task(
                description=task_global.description,
                expected_output=task_global.expected_output,
                agent=global_scout_fallback
            )
            
            task_legal_fallback = Task(
                description=task_legal.description,
                expected_output=task_legal.expected_output,
                agent=legal_scout_fallback
            )
            
            task_health_sports_fallback = Task(
                description=task_health_sports.description,
                expected_output=task_health_sports.expected_output,
                agent=health_sports_scout_fallback
            )
            
            task_health_analysis_fallback = Task(
                description=task_health_analysis.description,
                expected_output=task_health_analysis.expected_output,
                agent=health_analyst_fallback,
                context=[task_health_sports_fallback]
            )
            
            task_legal_analysis_fallback = Task(
                description=task_legal_analysis.description,
                expected_output=task_legal_analysis.expected_output,
                agent=legal_scholar_fallback,
                context=[task_global_fallback, task_legal_fallback]  # 跳过中国新闻上下文
            )
            
            task_research_fallback = Task(
                description=task_research.description,
                expected_output=task_research.expected_output,
                agent=researcher_fallback,
                context=[task_global_fallback, task_legal_fallback, 
                        task_health_sports_fallback, task_health_analysis_fallback, task_legal_analysis_fallback]  # 跳过中国新闻
            )
            
            task_publish_deepseek = Task(
                description=task_publish.description,
                expected_output=task_publish.expected_output,
                agent=editor_fallback,
                context=[task_research_fallback]
            )
            
            # 创建新的 Crew，使用第二备用模型（跳过中国新闻）
            news_crew_fallback = Crew(
                agents=[
                    global_scout_fallback, 
                    legal_scout_fallback, 
                    health_sports_scout_fallback,
                    health_analyst_fallback,
                    legal_scholar_fallback,
                    researcher_fallback, 
                    editor_fallback
                ],
                tasks=[
                    task_global_fallback, 
                    task_legal_fallback, 
                    task_health_sports_fallback,
                    task_health_analysis_fallback,
                    task_legal_analysis_fallback,
                    task_research_fallback, 
                    task_publish_deepseek
                ],
                process=Process.sequential,
                verbose=True
            )
            
            result = news_crew_fallback.kickoff()
            final_html = str(result)
            
            # 清洗 Markdown 标记
            if "```html" in final_html:
                final_html = final_html.split("```html")[1].split("```")[0]
            elif "```" in final_html:
                final_html = final_html.split("```")[1].split("```")[0]
            
            # 创建 reports 文件夹并保存文件
            output_dir = "reports"
            os.makedirs(output_dir, exist_ok=True)
            filename = f"news_{CURRENT_DATE}.html"
            file_path = os.path.join(output_dir, filename)
            
            # 保存到 reports 文件夹
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(final_html.strip())
            
            # 同时更新根目录的 index.html 以便 GitHub Pages 显示
            output_path = "index.html"
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(final_html.strip())
            
            print(f"✅ Report generated successfully with second backup model (DeepSeek Official API): {output_path}")
            print(f"✅ Report also saved to: {file_path}")
            print("📊 Report includes 4 sections (Chinese news skipped to avoid content policy issues):")
            print("   1. 全球新闻 (Global News)")
            print("   2. 法律新闻 (Legal News)")
            print("   3. 健康与运动 (Health & Sports + Deep Analysis)")
            print("   4. 法律学术分析 (Legal Analysis & Law Review Articles)")
            
            # 发送邮件
            send_email_report(file_path)
            
        except Exception as deepseek_error:
            print(f"⚠️ Second backup model also failed with error: {deepseek_error}")
            print("🔄 Retrying with third backup model: nvidia/llama-3.3-nemotron-super-49b-v1.5")
            
            # 使用第三备用模型重试 (nvidia/llama-3.3-nemotron-super-49b-v1.5)
            try:
                
                # 重新创建 agents 使用第三备用 LLM (backup_llm)
                china_scout_backup = Agent(
                    role=china_scout.role,
                    goal=china_scout.goal,
                    backstory=china_scout.backstory,
                    tools=china_scout.tools,
                    llm=backup_llm,
                    verbose=True
                )
                
                global_scout_backup = Agent(
                    role=global_scout.role,
                    goal=global_scout.goal,
                    backstory=global_scout.backstory,
                    tools=global_scout.tools,
                    llm=backup_llm,
                    verbose=True
                )
                
                legal_scout_backup = Agent(
                    role=legal_scout.role,
                    goal=legal_scout.goal,
                    backstory=legal_scout.backstory,
                    tools=legal_scout.tools,
                    llm=backup_llm,
                    verbose=True
                )
                
                health_sports_scout_backup = Agent(
                    role=health_sports_scout.role,
                    goal=health_sports_scout.goal,
                    backstory=health_sports_scout.backstory,
                    tools=health_sports_scout.tools,
                    llm=backup_llm,
                    verbose=True
                )
                
                health_analyst_backup = Agent(
                    role=health_analyst.role,
                    goal=health_analyst.goal,
                    backstory=health_analyst.backstory,
                    tools=health_analyst.tools,
                    llm=backup_llm,
                    verbose=True
                )
                
                legal_scholar_backup = Agent(
                    role=legal_scholar.role,
                    goal=legal_scholar.goal,
                    backstory=legal_scholar.backstory,
                    tools=legal_scholar.tools,
                    llm=backup_llm,
                    verbose=True
                )
                
                researcher_backup = Agent(
                    role=researcher.role,
                    goal=researcher.goal,
                    backstory=researcher.backstory,
                    tools=researcher.tools,
                    llm=backup_llm,
                    verbose=True
                )
                
                editor_backup = Agent(
                    role=editor.role,
                    goal=editor.goal,
                    backstory=editor.backstory,
                    llm=backup_llm,
                    verbose=True
                )
                
                # 重新创建任务，使用第三备用 agents (包含所有5个板块)
                task_china_backup = Task(
                    description=task_china.description,
                    expected_output=task_china.expected_output,
                    agent=china_scout_backup
                )
                
                task_global_backup = Task(
                    description=task_global.description,
                    expected_output=task_global.expected_output,
                    agent=global_scout_backup
                )
                
                task_legal_backup = Task(
                    description=task_legal.description,
                    expected_output=task_legal.expected_output,
                    agent=legal_scout_backup
                )
                
                task_health_sports_backup = Task(
                    description=task_health_sports.description,
                    expected_output=task_health_sports.expected_output,
                    agent=health_sports_scout_backup
                )
                
                task_health_analysis_backup = Task(
                    description=task_health_analysis.description,
                    expected_output=task_health_analysis.expected_output,
                    agent=health_analyst_backup,
                    context=[task_health_sports_backup]
                )
                
                task_legal_analysis_backup = Task(
                    description=task_legal_analysis.description,
                    expected_output=task_legal_analysis.expected_output,
                    agent=legal_scholar_backup,
                    context=[task_china_backup, task_global_backup, task_legal_backup]
                )
                
                task_research_backup = Task(
                    description=task_research.description,
                    expected_output=task_research.expected_output,
                    agent=researcher_backup,
                    context=[task_china_backup, task_global_backup, task_legal_backup, 
                            task_health_sports_backup, task_health_analysis_backup, task_legal_analysis_backup]
                )
                
                task_publish_backup = Task(
                    description=task_publish.description,
                    expected_output=task_publish.expected_output,
                    agent=editor_backup,
                    context=[task_research_backup]
                )
                
                # 创建新的 Crew，使用第三备用模型 (包含所有5个板块)
                news_crew_backup = Crew(
                    agents=[
                        china_scout_backup, 
                        global_scout_backup, 
                        legal_scout_backup, 
                        health_sports_scout_backup,
                        health_analyst_backup,
                        legal_scholar_backup,
                        researcher_backup, 
                        editor_backup
                    ],
                    tasks=[
                        task_china_backup, 
                        task_global_backup, 
                        task_legal_backup, 
                        task_health_sports_backup,
                        task_health_analysis_backup,
                        task_legal_analysis_backup,
                        task_research_backup, 
                        task_publish_backup
                    ],
                    process=Process.sequential,
                    verbose=True
                )
                
                result = news_crew_backup.kickoff()
                final_html = str(result)
                
                # 清洗 Markdown 标记
                if "```html" in final_html:
                    final_html = final_html.split("```html")[1].split("```")[0]
                elif "```" in final_html:
                    final_html = final_html.split("```")[1].split("```")[0]
                
                # 创建 reports 文件夹并保存文件
                output_dir = "reports"
                os.makedirs(output_dir, exist_ok=True)
                filename = f"news_{CURRENT_DATE}.html"
                file_path = os.path.join(output_dir, filename)
                
                # 保存到 reports 文件夹
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(final_html.strip())
                
                # 同时更新根目录的 index.html 以便 GitHub Pages 显示
                output_path = "index.html"
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(final_html.strip())
                
                print(f"✅ Report generated successfully with third backup model (nvidia/llama-3.3-nemotron-super-49b-v1.5): {output_path}")
                print(f"✅ Report also saved to: {file_path}")
                print("📊 Report includes 5 sections:")
                print("   1. 中文新闻 (Chinese-language News)")
                print("   2. 全球新闻 (Global News)")
                print("   3. 法律新闻 (Legal News)")
                print("   4. 健康与运动 (Health & Sports + Deep Analysis)")
                print("   5. 法律学术分析 (Legal Analysis & Law Review Articles)")
                
                # 发送邮件
                send_email_report(file_path)
                
            except Exception as backup_error:
                print(f"❌ Critical Error: All three models failed.")
                print(f"Primary model error: {e}")
                print(f"Second backup model error: {deepseek_error}")
                print(f"Third backup model error: {backup_error}")
                sys.exit(1)

if __name__ == "__main__":
    run()
