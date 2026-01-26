import os
import sys
from datetime import datetime
from crewai import Agent, Task, Crew, Process, LLM
from crewai_tools import ScrapeWebsiteTool, SerperDevTool

# --- Configuration Constants ---
CURRENT_DATE = datetime.now().strftime("%Y-%m-%d")
CURRENT_YEAR = datetime.now().strftime("%Y")
CURRENT_YEAR_MONTH = datetime.now().strftime("%Y年%m月")
NEWS_ITEMS_PER_SECTION = 5
LEGAL_ANALYSIS_ITEMS = 3
DEEP_ANALYSIS_ITEMS = 3

# --- 1. 配置 LLM (NVIDIA NIM) ---
# 替换为 NVIDIA API 配置
# 使用 NVIDIA meta/llama-3.1-405b-instruct 模型 (高性能稳定)
# 参考 NVIDIA 官方示范代码配置
# max_tokens 设置为 32000（从 8192 增加）以支持：
# 1. 1000+ 字的详细新闻摘要（每个板块 5 条新闻 = 5000+ 字）
# 2. 5000+ 字的深度分析报告（健康分析 3 篇 + 法律分析 3 篇 = 30000+ 字）
# 3. 综合研究报告和最终 HTML 生成
# 注意：此限制基于内容需求，同时在大多数 LLM 的上下文窗口范围内
nvidia_llm = LLM(
    model="meta/llama-3.1-405b-instruct",
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.environ.get("NVIDIA_API_KEY"),
    temperature=0.7,
    top_p=0.95,
    max_tokens=32000,  # Increased to support longer, detailed outputs
    stream=True,
    timeout=600
)

# 第二备用模型配置 - 使用 DeepSeek 官方 API (中国版)
# 在主模型调用失败时使用，为避免敏感问题跳过中国新闻板块
deepseek_llm = LLM(
    model="deepseek-chat",
    base_url="https://api.deepseek.com",
    api_key=os.environ.get("DEEPSEEK_API_KEY"),
    temperature=0.7,
    top_p=0.95,
    max_tokens=32000,  # Increased to support longer, detailed outputs
    stream=True,
    timeout=600
)

# 第三备用模型配置 - 在第二备用模型失败时使用
backup_llm = LLM(
    model="nvidia/llama-3.3-nemotron-super-49b-v1.5",
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.environ.get("NVIDIA_API_KEY"),
    temperature=0.7,
    top_p=0.95,
    max_tokens=32000,  # Increased to support longer, detailed outputs
    stream=True,
    timeout=600
)

# --- 2. 初始化工具 ---
# 增加搜索结果数量以提高准确性
search_tool = SerperDevTool(n_results=15)
scrape_tool = ScrapeWebsiteTool()

# ==============================================================================
# Deep Humanizer Protocol (深层去伪协议)
# ==============================================================================
# 所有写作型智能体共享的人性化写作原则：
# 1. 禁用 AI 常见词汇：delve, landscape, transformative, tapestry, underscore, poised to
# 2. 禁用结构性陈词：In conclusion, Furthermore, Moreover, Looking ahead
# 3. 高爆发度 (Burstiness)：混合短句和长句，创造"心电图"般的节奏感
# 4. 高困惑度 (Perplexity)：使用具体细节和感官动词，而非抽象表达
# 5. 人类立场：注入微观视角和适度偏见，展现人类写作风格
# ==============================================================================

HUMANIZER_PROTOCOL = """
**Deep Humanizer Protocol (去AI味写作规则)**:
1. **禁止AI腔调**: 
   - 严禁使用: "delve", "landscape", "tapestry", "transformative", "underscore", "poised to", "myriad"
   - 严禁使用: "In conclusion", "Furthermore", "Moreover", "Looking ahead", "It's worth noting"
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
"""

# --- 3. 定义智能体 (Agents) ---

# 【Chinese Media Editor】 - Multi-source integration + Neutral objective tone
china_scout = Agent(
    role='News Editor for Chinese Media',
    goal=f'Select EXACTLY {NEWS_ITEMS_PER_SECTION} newsworthy stories from TODAY published in Chinese-language sources with 3+ source verification and comprehensive 1000+ word summaries for EACH story',
    backstory=f"""
    You are an experienced news editor with 10 years of editorial experience.
    
    **CRITICAL REQUIREMENTS**:
    - You MUST return EXACTLY {NEWS_ITEMS_PER_SECTION} news stories, no more, no less
    - Each story MUST be from TODAY or the last 24 hours
    - Each story MUST have a minimum of 1000 words of detailed analysis
    - Search for news using date-specific keywords: "今天", "最新", "{CURRENT_YEAR_MONTH}"
    
    Your selection criteria:
    1. Filter out low-quality content: entertainment gossip and promotional press releases.
    2. Focus on substantive topics FROM TODAY: employment, education, technology, and public welfare.
    3. Deep perspective: Look beyond trending topics to find meaningful stories happening NOW.
    4. Multi-source integration: Each story must integrate at least 3 different perspectives.
    5. **Comprehensive reporting**: Each news summary must be at least 1000 words with detailed analysis including background, context, multiple viewpoints, and implications.
    6. **Source documentation**: Include original URLs for every source cited (news articles, official documents, social media posts).
    
    Style Guidelines:
    - Maintain objective, neutral journalistic tone
    - Use factual, descriptive language
    - Focus on concrete events and developments
    - Avoid inflammatory or controversial terminology
    - Always provide clickable source links
    
    {HUMANIZER_PROTOCOL}
    """,
    tools=[search_tool, scrape_tool],
    llm=nvidia_llm,
    verbose=True
)

# 【全球情报官】 - 强制英文源 + 多源整合
global_scout = Agent(
    role='International News Analyst (English Sources)',
    goal=f'Identify EXACTLY {NEWS_ITEMS_PER_SECTION} Global events from TODAY using ONLY English primary sources, with 3+ sources per story and comprehensive 1000+ word analysis for EACH story',
    backstory=f"""
    You strictly adhere to English-language primary sources and TODAY's breaking news.
    
    **CRITICAL REQUIREMENTS**:
    - You MUST return EXACTLY {NEWS_ITEMS_PER_SECTION} news stories, no more, no less
    - Each story MUST be from TODAY or the last 24 hours
    - Each story MUST have a minimum of 1000 words of detailed analysis
    - Search for news using date-specific keywords: "today", "breaking", "latest {CURRENT_YEAR}"
    
    Your Logic:
    1. Tech: Focus on fundamental breakthroughs from TODAY (AI, Space), not PR stunts.
    2. Geopolitics: Focus on strategic implications and factual developments happening NOW.
    3. CRITICAL: You MUST retain the original English Headlines to avoid translation loss.
    4. Multi-Source: Each story must synthesize 3+ reputable sources (Reuters, Bloomberg, NYT, Nature, Foreign Affairs, Stratechery).
    5. **Comprehensive reporting**: Each news summary must be at least 1000 words with detailed analysis including background, expert opinions, data, and global implications.
    6. **Source documentation**: Include original URLs for every source cited (news articles, research papers, analysis pieces).
    
    {HUMANIZER_PROTOCOL}
    """,
    tools=[search_tool, scrape_tool],
    llm=nvidia_llm,
    verbose=True
)

# 【法律情报官】 - 多源整合
legal_scout = Agent(
    role='Global Legal News Curator',
    goal=f'Identify EXACTLY {NEWS_ITEMS_PER_SECTION} landmark legal events from TODAY (SCOTUS, EU CJEU, China SPC) with multi-source verification and comprehensive 1000+ word legal analysis for EACH case',
    backstory=f"""
    **CRITICAL REQUIREMENTS**:
    - You MUST return EXACTLY {NEWS_ITEMS_PER_SECTION} legal news stories, no more, no less
    - Each story MUST be from TODAY or the last 24-48 hours
    - Each story MUST have a minimum of 1000 words of detailed legal analysis
    - Search for news using date-specific keywords: "today", "latest", "{CURRENT_YEAR}"
    
    Focus on "Hard Law" developments from TODAY:
    1. Landmark Rulings: Supreme Court decisions that change precedent.
    2. Major Legislation: EU AI Act, GDPR, Antitrust laws.
    3. Corporate Litigation: Significant Big Tech lawsuits.
    4. Multi-Source: Each legal development must include court documents, expert commentary, and news coverage.
    5. **Comprehensive reporting**: Each legal news summary must be at least 1000 words with detailed legal analysis including case background, legal reasoning, precedents, and implications.
    6. **Source documentation**: Include original URLs for court documents, legislation texts, expert analyses, and news articles.
    
    {HUMANIZER_PROTOCOL}
    """,
    tools=[search_tool, scrape_tool],
    llm=nvidia_llm,
    verbose=True
)

# 【健康与运动新闻情报官】 - 新增：科学期刊来源
health_sports_scout = Agent(
    role='Health & Sports Science Reporter',
    goal=f'Identify EXACTLY {NEWS_ITEMS_PER_SECTION} health and sports science news from THIS WEEK from peer-reviewed sources with comprehensive 1000+ word scientific summaries for EACH story',
    backstory=f"""
    You are a science journalist specializing in health and sports research.
    
    **CRITICAL REQUIREMENTS**:
    - You MUST return EXACTLY {NEWS_ITEMS_PER_SECTION} news stories, no more, no less
    - Each story MUST be from THIS WEEK (last 7 days) with recent publication dates
    - Each story MUST have a minimum of 1000 words of detailed scientific analysis
    - Search for news using date-specific keywords: "{CURRENT_YEAR}", "latest", "new study", "recent research"
    
    Your priority sources (in order):
    1. Scientific American (health, sports science, fitness)
    2. Nature (medical research, sports physiology)
    3. Science Magazine (health studies, exercise science)
    4. The Lancet, JAMA, NEJM (medical journals)
    5. Sports Medicine journals
    
    Selection Criteria:
    - Focus on peer-reviewed research published THIS WEEK with practical implications
    - Prioritize studies with large sample sizes and robust methodology
    - Include both breaking research and emerging trends
    - Avoid sensationalized health claims without scientific backing
    - **Comprehensive reporting**: Each news summary must be at least 1000 words with detailed scientific background, methodology, results, analysis, and practical implications
    - **Source documentation**: Include original URLs for journal articles, research papers, and scientific publications
    
    {HUMANIZER_PROTOCOL}
    """,
    tools=[search_tool, scrape_tool],
    llm=nvidia_llm,
    verbose=True
)

# 【健康分析师】 - 新增：深度分析报告
health_analyst = Agent(
    role='Health Science Analyst',
    goal='Generate comprehensive 5000+ word deep analysis reports for top 3 health/sports stories',
    backstory=f"""
    You are an expert science communicator who makes complex research accessible through detailed, comprehensive analysis.
    
    For each of the Top 3 health/sports stories, create a comprehensive 5000+ word analysis including:
    1. **Executive Summary**: Overview of significance with engaging prose
    2. **Background & Context**: Historical and scientific context with concrete examples
    3. **Methodology**: Research design and methods explained in accessible yet thorough detail
    4. **Findings & Results**: Key discoveries with specific data points, statistical analysis ("subjects ran 15% faster" not "performance improved")
    5. **Scientific Implications**: Impact on scientific understanding and future research directions
    6. **Practical Applications**: Detailed actionable advice for readers with real-world applications
    7. **Critical Analysis**: Comprehensive evaluation of strengths, limitations, and caveats
    8. **Conclusion**: Summary and future directions
    
    **Critical Requirements**:
    - Minimum 5000 words per analysis report
    - Include ALL original source URLs (research papers, journals, related studies)
    - Provide comprehensive, detailed analysis - not superficial summaries
    
    {HUMANIZER_PROTOCOL}
    """,
    tools=[scrape_tool],
    llm=nvidia_llm,
    verbose=True
)

# 【法律学者】 - 新增：法律评论文章分析
legal_scholar = Agent(
    role='Comparative Law Scholar',
    goal='Analyze law review articles from top US law schools with 5000+ word comprehensive analyses',
    backstory=f"""
    You are a comparative law expert specializing in US-China legal issues.
    
    Your workflow:
    1. Identify 3-5 key legal issues from current US and China hot topics
    2. Search law review articles from top 10 US law schools:
       - Yale Law Journal, Harvard Law Review, Stanford Law Review
       - Columbia Law Review, University of Chicago Law Review, NYU Law Review
       - Penn Law Review, Michigan Law Review, Virginia Law Review, Berkeley Law Review
    3. Select the 3 most relevant and recent articles
    4. For each article, generate a comprehensive 5000+ word analysis:
       - Article Overview & Introduction (700-900 words): Thesis and context with engaging language
       - Legal Framework & Doctrinal Background (900-1100 words): Legal doctrines with real-world examples
       - Key Arguments & Analysis (1200-1500 words): Detailed breakdown with specific cases and implications
       - Comparative Perspective (700-900 words): US-China legal comparison
       - Connection to Hot Topics (700-900 words): Relate to current events with concrete details
       - Practical & Policy Implications (600-800 words): Real-world legal consequences
       - Critical Assessment (200-400 words): Evaluate strengths and weaknesses
    
    **Critical Requirements**:
    - Minimum 5000 words per analysis report
    - Include ALL original source URLs (law review articles, cases, statutes, related sources)
    - Provide comprehensive, detailed legal analysis - not superficial summaries
    
    {HUMANIZER_PROTOCOL}
    """,
    tools=[search_tool, scrape_tool],
    llm=nvidia_llm,
    verbose=True
)

# 【深度研究员】 - 架构师（更新：整合5个板块）
researcher = Agent(
    role='Chief Researcher & Architect',
    goal=f'Synthesize all inputs into a structured report with ALL {NEWS_ITEMS_PER_SECTION} items per section, VERIFYING ALL URLs ARE PRESENT and ALL CONTENT is preserved in full',
    backstory=f"""
    You are responsible for data integrity and structural integrity of the report.
    You must ensure that every single news item passed to the Editor has a VALID, CLICKABLE URL.
    Do not summarize away the links or the content. The Editor needs them for the HTML.
    
    **CRITICAL REQUIREMENTS**:
    1. All FIVE sections must be present with complete data
    2. **EACH SECTION MUST HAVE ALL {NEWS_ITEMS_PER_SECTION} NEWS ITEMS** (except Legal Scholarship which has {LEGAL_ANALYSIS_ITEMS})
    3. **DO NOT TRUNCATE OR SUMMARIZE**: Pass through all 1000+ word summaries in full
    4. **DO NOT TRUNCATE OR SUMMARIZE**: Pass through all 5000+ word analyses in full
    5. Every news story must have its Source URLs clearly listed and separated
    6. English headlines are preserved exactly as written for Global news
    7. Deep analysis reports (5000+ words each) are properly integrated with all citations
    8. **VERIFICATION STEP**: Check that every single news item has:
       - Title
       - Full 1000+ word summary (or 5000+ for deep analysis)
       - At least one Source URL
       If any of these are missing, flag it clearly to the user
    9. Organize the content strictly into the 5 sections with clear boundaries
    
    {HUMANIZER_PROTOCOL}
    """,
    tools=[scrape_tool],
    llm=nvidia_llm,
    verbose=True
)

# 【主编】 - 专注于 NYT 风格和数据真实性 + 5栏布局
editor = Agent(
    role='Lead Editor (NYT Style & Frontend Dev)',
    goal=f'Generate a "New York Times" style HTML report with 5-column grid layout. ENSURE ALL {NEWS_ITEMS_PER_SECTION} NEWS ITEMS PER SECTION ARE DISPLAYED. ENSURE ALL LINKS WORK.',
    backstory=f"""
    You are a meticulous frontend developer and editor inspired by The New York Times.
    
    **Core Philosophy**:
    1. **Data Integrity**: You NEVER create fake links (href="#"). You ONLY use the URLs provided by the researchers. If a URL is missing, you do not display a link button.
    2. **Display ALL Items**: You MUST display ALL {NEWS_ITEMS_PER_SECTION} news items in each section ({LEGAL_ANALYSIS_ITEMS} for Legal Analysis), not just 1 or 2.
    3. **Full Content**: You MUST preserve the full 1000+ word summaries and 5000+ word analyses, using collapsible sections to keep the page clean.
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
    llm=nvidia_llm,
    verbose=True
)

# --- 4. 定义任务 (Tasks) ---

task_china = Task(
    description=f"""
    1. Search for TODAY's {NEWS_ITEMS_PER_SECTION} most newsworthy stories from Chinese-language media sources published in the last 24 hours.
       Use search queries like: "China news today", "中国新闻 今天", "微博热搜 今日", "知乎热榜 最新"
    2. Sources: Major news outlets and reputable media platforms (今日头条, 新浪新闻, 澎湃新闻, etc.).
    3. Requirements: Focus on factual reporting, emphasize technology and public welfare topics FROM TODAY.
    4. Multi-source integration: Each story must integrate at least 3 different source perspectives.
    5. **CRITICAL - Word count requirement**: Each news summary MUST be at least 1000 words, providing comprehensive detail with context, background, analysis, and implications.
    6. **Source links required**: Include original document links (URLs) for each source cited.
    7. **Output format**: Return exactly {NEWS_ITEMS_PER_SECTION} news items in this format:
       
       News Item 1:
       Title: [Title in Chinese]
       Summary: [1000+ word comprehensive summary]
       Sources: [URL1], [URL2], [URL3]
       
       [Repeat for items 2-{NEWS_ITEMS_PER_SECTION}]
    """,
    expected_output=f"EXACTLY {NEWS_ITEMS_PER_SECTION} curated news stories from Chinese media published TODAY (1000+ words each), each with multi-source integration and source links.",
    agent=china_scout
)

task_global = Task(
    description=f"""
    1. Search for TODAY's breaking news using these queries:
       - "Breaking news today Reuters"
       - "Tech news today {CURRENT_YEAR}"
       - "Global news latest 24 hours"
       - "Technology breakthrough today"
       - "Geopolitics news today"
    2. Select {NEWS_ITEMS_PER_SECTION} events with global structural impact published in the last 24 hours.
    3. RETURN FORMAT: English Headline + Comprehensive Chinese Analysis (1000+ words).
    4. Multi-Source: Each story must synthesize 3+ sources (Reuters, Bloomberg, NYT, Nature, etc).
    5. **CRITICAL - Word count requirement**: Each news summary MUST be at least 1000 words, providing comprehensive analysis with context, background, expert opinions, and implications.
    6. **Source links required**: Include original document links (URLs) for each source cited.
    7. **Output format**: Return exactly {NEWS_ITEMS_PER_SECTION} news items in this format:
       
       News Item 1:
       English Title: [Title in English]
       Chinese Summary: [1000+ word comprehensive summary in Chinese]
       Sources: [URL1], [URL2], [URL3]
       
       [Repeat for items 2-{NEWS_ITEMS_PER_SECTION}]
    """,
    expected_output=f"EXACTLY {NEWS_ITEMS_PER_SECTION} Global news items published TODAY (1000+ words each) with English Titles and multi-source verification, including source URLs.",
    agent=global_scout
)

task_legal = Task(
    description=f"""
    Search for TODAY's most significant court rulings or legislative drafts (US/EU/CN) from the last 24-48 hours.
    Use search queries like:
    - "Supreme Court ruling today {CURRENT_YEAR}"
    - "Legal news today USA"
    - "Court decision latest"
    - "EU legislation today"
    - "China legal news today"
    
    Focus on IP, Antitrust, AI Regulation, Privacy Law.
    Multi-Source: Each legal development must include court documents, expert commentary, and news coverage.
    **CRITICAL - Word count requirement**: Each legal news summary MUST be at least 1000 words, providing comprehensive legal analysis with case background, legal reasoning, precedents, and implications.
    **Source links required**: Include original document links (URLs) - court documents, legislation, expert analysis, and news articles.
    **Output format**: Return exactly {NEWS_ITEMS_PER_SECTION} news items in this format:
    
    Legal Update 1:
    Title: [Case/Legislation Title]
    Summary: [1000+ word comprehensive legal analysis]
    Sources: [Court document URL], [Expert analysis URL], [News URL]
    
    [Repeat for items 2-{NEWS_ITEMS_PER_SECTION}]
    """,
    expected_output=f"EXACTLY {NEWS_ITEMS_PER_SECTION} Key Legal Updates from TODAY (1000+ words each) with multi-source citations and original document URLs.",
    agent=legal_scout
)

# 【新增】健康与运动新闻任务
task_health_sports = Task(
    description=f"""
    1. Search for the top {NEWS_ITEMS_PER_SECTION} RECENT health and sports science news published in the last week.
       Use search queries like:
       - "health research {CURRENT_YEAR} latest"
       - "sports science breakthrough today"
       - "medical study published this week"
       - "fitness research new {CURRENT_YEAR}"
    2. Priority sources: Scientific American, Nature, Science Magazine, The Lancet, JAMA, NEJM, Sports Medicine journals.
    3. Focus on:
       - New research findings with practical health implications
       - Sports science breakthroughs
       - Exercise and fitness studies
       - Nutrition research
    4. Include the journal/source name, publication date, and key findings.
    5. **CRITICAL - Word count requirement**: Each news summary MUST be at least 1000 words, providing comprehensive scientific detail including methodology, results, analysis, and practical implications.
    6. **Source links required**: Include original document links (URLs) - journal articles, research papers, and scientific publications.
    7. **Output format**: Return exactly {NEWS_ITEMS_PER_SECTION} news items in this format:
    
    Health/Sports Item 1:
    Title: [Research Title]
    Journal/Source: [Journal Name] - [Publication Date]
    Summary: [1000+ word comprehensive scientific summary]
    Sources: [Journal URL], [Related Study URL], [News Coverage URL]
    
    [Repeat for items 2-{NEWS_ITEMS_PER_SECTION}]
    """,
    expected_output=f"EXACTLY {NEWS_ITEMS_PER_SECTION} Health/Sports Science news items from THIS WEEK (1000+ words each) with source citations, key findings, and original document URLs.",
    agent=health_sports_scout
)

# 【新增】健康深度分析任务
task_health_analysis = Task(
    description=f"""
    Select the TOP {DEEP_ANALYSIS_ITEMS} most impactful health/sports stories from the collected news.
    For each of the {DEEP_ANALYSIS_ITEMS} stories, generate a comprehensive in-depth analysis report of at least 5000 words including:
    
    1. **Executive Summary** (500-700 words): Overview of the research and its significance
    2. **Background & Context** (800-1000 words): Scientific context with concrete examples, historical perspective
    3. **Methodology** (600-800 words): Research methodology explained in detail yet accessibly
    4. **Findings & Results** (1200-1500 words): Key discoveries with specific data points, statistics, and analysis
    5. **Scientific Implications** (600-800 words): Impact on scientific understanding and future research
    6. **Practical Applications** (700-900 words): How people can use this information, actionable advice for readers
    7. **Critical Analysis** (400-600 words): Strengths, limitations, caveats and areas for further research
    8. **Conclusion** (200-300 words): Summary of key takeaways and future directions
    
    **Word count requirement**: Each analysis report must be at least 5000 words total.
    **Source links required**: Include all original research paper URLs, journal links, and related references.
    
    IMPORTANT: Follow the Deep Humanizer Protocol. No AI clichés. Use concrete examples and varied sentence structure.
    """,
    expected_output=f"{DEEP_ANALYSIS_ITEMS} comprehensive in-depth analysis reports (5000+ words each) for top health/sports stories with all source URLs.",
    agent=health_analyst,
    context=[task_health_sports]
)

# 【新增】法律学术分析任务
task_legal_analysis = Task(
    description=f"""
    Phase 1: Identify 3-5 key legal issues from current US and China hot topics based on the news collected.
    
    Phase 2: Search for relevant law review articles from top 10 US law schools:
    - Yale Law Journal, Harvard Law Review, Stanford Law Review
    - Columbia Law Review, University of Chicago Law Review, NYU Law Review
    - Penn Law Review, Michigan Law Review, Virginia Law Review, Berkeley Law Review
    
    Phase 3: Select the {LEGAL_ANALYSIS_ITEMS} most relevant and recent articles.
    
    Phase 4: For each article, generate a comprehensive in-depth analysis of at least 5000 words:
    1. **Article Overview & Introduction** (700-900 words): Summarize thesis with engaging, concrete language and context
    2. **Legal Framework & Doctrinal Background** (900-1100 words): Explain legal doctrines, precedents, and theoretical foundations using real-world examples
    3. **Key Arguments & Analysis** (1200-1500 words): Break down arguments in detail with specific cases, statutory analysis, and implications
    4. **Comparative Perspective** (700-900 words): Compare US and China legal approaches if applicable
    5. **Connection to Hot Topics** (700-900 words): Relate article to current events with concrete details and real-world examples
    6. **Practical & Policy Implications** (600-800 words): Real-world legal consequences, policy recommendations
    7. **Critical Assessment** (200-400 words): Strengths, weaknesses, gaps in the analysis
    
    **Word count requirement**: Each analysis report must be at least 5000 words total.
    **Source links required**: Include original law review article URLs, case citations with links, and all referenced sources.
    
    IMPORTANT: Follow the Deep Humanizer Protocol. Technical precision with readable prose. Avoid jargon overload.
    """,
    expected_output=f"Analysis of {LEGAL_ANALYSIS_ITEMS} law review articles (5000+ words each) connected to current US-China topics with all source URLs.",
    agent=legal_scholar,
    context=[task_china, task_global, task_legal]
)

# 【更新】研究任务：整合所有5个板块
task_research = Task(
    description=f"""
    Compile ALL inputs from the 5 sections ensuring EVERY news item is preserved:
    1. Chinese-language News (中文新闻) - ALL {NEWS_ITEMS_PER_SECTION} news items with 1000+ word summaries
    2. Global News (全球新闻) - ALL {NEWS_ITEMS_PER_SECTION} news items with 1000+ word summaries  
    3. Legal News (法律新闻) - ALL {NEWS_ITEMS_PER_SECTION} news items with 1000+ word summaries
    4. Health & Sports News + Deep Analysis (健康与运动) - ALL {NEWS_ITEMS_PER_SECTION} news items with 1000+ word summaries PLUS {DEEP_ANALYSIS_ITEMS} deep analysis reports with 5000+ words each
    5. Legal Analysis & Law Review Articles (法律学术分析) - {LEGAL_ANALYSIS_ITEMS} law review analyses with 5000+ words each
    
    **CRITICAL REQUIREMENTS**:
    - Verify that ALL FIVE SECTIONS exist with complete data
    - **EACH section must have ALL {NEWS_ITEMS_PER_SECTION} news items** (except Legal Analysis which has {LEGAL_ANALYSIS_ITEMS} items)
    - Ensure strict separation of content between sections
    - Add a "Key Takeaway" one-liner for every major news item
    - Preserve all deep analysis reports in their entirety (5000+ words each)
    - Ensure English headlines are preserved for Global news section
    - **PRESERVE ALL original source URLs** from all sections - news articles, research papers, court documents, law review articles, etc.
    - Format source URLs clearly and separately so they can be displayed as clickable links in the final HTML
    - **DO NOT SUMMARIZE OR TRUNCATE**: Pass through all content in full length to the editor
    
    **Output Structure**:
    For each section, organize as:
    Section Name:
      Item 1: Title, Full Summary (1000+ words), Source URLs
      Item 2: Title, Full Summary (1000+ words), Source URLs
      Item 3: Title, Full Summary (1000+ words), Source URLs
      Item 4: Title, Full Summary (1000+ words), Source URLs
      Item 5: Title, Full Summary (1000+ words), Source URLs
      [Plus deep analysis if applicable]
    """,
    expected_output=f"Master Report with ALL 5 sections, each containing ALL news items ({NEWS_ITEMS_PER_SECTION} per section except Legal Analysis with {LEGAL_ANALYSIS_ITEMS}), complete 1000+ word summaries, 5000+ word analyses, and ALL source URLs preserved.",
    agent=researcher,
    context=[task_china, task_global, task_legal, task_health_sports, task_health_analysis, task_legal_analysis]
)

# 【重构】发布任务 - NYT 风格 + 链接修复 + 5栏布局
task_publish = Task(
    description=f"""
    Generate the final `index.html` file based on the Research Report with TODAY's date: {CURRENT_DATE}.
    
    **CRITICAL DATA RULES**:
    1. **NO FAKE LINKS**: You are STRICTLY FORBIDDEN from using `href="#"`. 
    2. **USE REAL URLS**: You must extract the URL provided in the context for each story and put it in the `href` attribute.
    3. **Fail-Safe**: If no URL is found in the context for a specific story, do NOT create a "Read More" button.
    4. **DISPLAY ALL {NEWS_ITEMS_PER_SECTION} NEWS ITEMS**: Each section MUST show ALL {NEWS_ITEMS_PER_SECTION} news items provided, not just 1.
    
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
       - **Header**: Simple, centered, serif headline "Daily Insight - {CURRENT_DATE}". Thin border-bottom.
       - **Main Container**: Use CSS Grid with 5 columns on desktop (grid-cols-5), responsive on mobile/tablet
       - **Each Column Represents One Section**:
         1. Column 1: 中文新闻 (Chinese-language News) - Show ALL {NEWS_ITEMS_PER_SECTION} news items
         2. Column 2: 全球新闻 (Global News) - Show ALL {NEWS_ITEMS_PER_SECTION} items with **English Headlines** prominent
         3. Column 3: 法律新闻 (Legal News) - Show ALL {NEWS_ITEMS_PER_SECTION} items
         4. Column 4: 健康与运动 (Health & Sports) - Show ALL {NEWS_ITEMS_PER_SECTION} items + {DEEP_ANALYSIS_ITEMS} deep analysis (collapsible)
         5. Column 5: 法律学术分析 (Legal Analysis) - Show {LEGAL_ANALYSIS_ITEMS} deep analysis reports (collapsible)
       - **Responsive**: Use `lg:grid-cols-5 md:grid-cols-2 grid-cols-1` for mobile/tablet adaptation
       - **Cards**: Clean layout. White background `bg-white`. Thin border `border border-stone-200`. No heavy shadows (`shadow-sm` at most).
       - **Typography**: High readability. Line height 1.6+. Use `line-clamp-3` for previews.
    
    **CONTENT DISPLAY**:
    - **News Items**: Show title and first 200-300 characters as preview, with "Read More" toggle to expand full 1000+ word summary
    - **Deep Analysis**: Use `<details>` tag with engaging summary, full 5000+ word content hidden until expanded
    - **Source Links**: Display as clickable badges/chips below each item
    
    **INTERACTIVITY & READABILITY**:
    - **Collapsible**: Use `<details>` for long content (1000+ and 5000+ word sections) to keep page scannable
    - **Preview Mode**: Show first 200-300 chars by default with "Read Full Article" button
    - **Hover**: Subtle hover effects (e.g., title underline, card slight elevation)
    - **Clear Hierarchy**: Section headers (text-2xl), item titles (text-xl), body (text-base)
    
    **Output**: 
    - ONLY the raw HTML code (starting with `<!DOCTYPE html>`).
    - Ensure ALL {NEWS_ITEMS_PER_SECTION} items in each section are displayed.
    - Include proper date: {CURRENT_DATE}
    """,
    expected_output="Final production-ready HTML with 5-column grid layout, all news items displayed, real links, and excellent readability.",
    agent=editor,
    context=[task_research]
)

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
            
        output_path = "index.html"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(final_html.strip())
        
        print(f"✅ Report generated successfully: {output_path}")
        print("📊 Report includes 5 sections:")
        print("   1. 中文新闻 (Chinese-language News)")
        print("   2. 全球新闻 (Global News)")
        print("   3. 法律新闻 (Legal News)")
        print("   4. 健康与运动 (Health & Sports + Deep Analysis)")
        print("   5. 法律学术分析 (Legal Analysis & Law Review Articles)")
        
    except Exception as e:
        print(f"⚠️ Primary model failed with error: {e}")
        print("🔄 Retrying with second backup model: deepseek-chat (DeepSeek Official API)")
        
        # 检查是否有 DeepSeek API Key
        if not os.environ.get("DEEPSEEK_API_KEY"):
            print("⚠️ Warning: DEEPSEEK_API_KEY not found, will try third backup model instead")
            # 如果没有 DeepSeek API Key，直接跳到第三备用模型
            try:
                print("🔄 Using third backup model: nvidia/llama-3.3-nemotron-super-49b-v1.5")
                # 这里会跳到第三备用模型的逻辑
                raise Exception("DEEPSEEK_API_KEY not available, switching to third backup")
            except:
                pass  # 继续到下面的第三备用模型逻辑
        
        # 如果是 Content Risk，提示用户调整 Prompt
        if "Content Exists Risk" in str(e):
            print("⚠️ Suggestion: The system prompt might contain sensitive keywords. Trying DeepSeek with modified workflow.")
        
        # 使用第二备用模型重试 (DeepSeek Official API)
        # 注意：跳过中国新闻部分以避免内容审查问题
        try:
            print("⚠️ Note: Skipping Chinese news section to avoid content policy issues with DeepSeek API")
            
            # 重新创建 agents（跳过 china_scout），使用第二备用 LLM (DeepSeek)
            global_scout_deepseek = Agent(
                role=global_scout.role,
                goal=global_scout.goal,
                backstory=global_scout.backstory,
                tools=global_scout.tools,
                llm=deepseek_llm,
                verbose=True
            )
            
            legal_scout_deepseek = Agent(
                role=legal_scout.role,
                goal=legal_scout.goal,
                backstory=legal_scout.backstory,
                tools=legal_scout.tools,
                llm=deepseek_llm,
                verbose=True
            )
            
            health_sports_scout_deepseek = Agent(
                role=health_sports_scout.role,
                goal=health_sports_scout.goal,
                backstory=health_sports_scout.backstory,
                tools=health_sports_scout.tools,
                llm=deepseek_llm,
                verbose=True
            )
            
            health_analyst_deepseek = Agent(
                role=health_analyst.role,
                goal=health_analyst.goal,
                backstory=health_analyst.backstory,
                tools=health_analyst.tools,
                llm=deepseek_llm,
                verbose=True
            )
            
            legal_scholar_deepseek = Agent(
                role=legal_scholar.role,
                goal=legal_scholar.goal,
                backstory=legal_scholar.backstory,
                tools=legal_scholar.tools,
                llm=deepseek_llm,
                verbose=True
            )
            
            researcher_deepseek = Agent(
                role=researcher.role,
                goal=researcher.goal,
                backstory=researcher.backstory,
                tools=researcher.tools,
                llm=deepseek_llm,
                verbose=True
            )
            
            editor_deepseek = Agent(
                role=editor.role,
                goal=editor.goal,
                backstory=editor.backstory,
                llm=deepseek_llm,
                verbose=True
            )
            
            # 重新创建任务（跳过 task_china），使用第二备用 agents
            task_global_deepseek = Task(
                description=task_global.description,
                expected_output=task_global.expected_output,
                agent=global_scout_deepseek
            )
            
            task_legal_deepseek = Task(
                description=task_legal.description,
                expected_output=task_legal.expected_output,
                agent=legal_scout_deepseek
            )
            
            task_health_sports_deepseek = Task(
                description=task_health_sports.description,
                expected_output=task_health_sports.expected_output,
                agent=health_sports_scout_deepseek
            )
            
            task_health_analysis_deepseek = Task(
                description=task_health_analysis.description,
                expected_output=task_health_analysis.expected_output,
                agent=health_analyst_deepseek,
                context=[task_health_sports_deepseek]
            )
            
            task_legal_analysis_deepseek = Task(
                description=task_legal_analysis.description,
                expected_output=task_legal_analysis.expected_output,
                agent=legal_scholar_deepseek,
                context=[task_global_deepseek, task_legal_deepseek]  # 跳过中国新闻上下文
            )
            
            task_research_deepseek = Task(
                description=task_research.description,
                expected_output=task_research.expected_output,
                agent=researcher_deepseek,
                context=[task_global_deepseek, task_legal_deepseek, 
                        task_health_sports_deepseek, task_health_analysis_deepseek, task_legal_analysis_deepseek]  # 跳过中国新闻
            )
            
            task_publish_deepseek = Task(
                description=task_publish.description,
                expected_output=task_publish.expected_output,
                agent=editor_deepseek,
                context=[task_research_deepseek]
            )
            
            # 创建新的 Crew，使用第二备用模型（跳过中国新闻）
            news_crew_deepseek = Crew(
                agents=[
                    global_scout_deepseek, 
                    legal_scout_deepseek, 
                    health_sports_scout_deepseek,
                    health_analyst_deepseek,
                    legal_scholar_deepseek,
                    researcher_deepseek, 
                    editor_deepseek
                ],
                tasks=[
                    task_global_deepseek, 
                    task_legal_deepseek, 
                    task_health_sports_deepseek,
                    task_health_analysis_deepseek,
                    task_legal_analysis_deepseek,
                    task_research_deepseek, 
                    task_publish_deepseek
                ],
                process=Process.sequential,
                verbose=True
            )
            
            result = news_crew_deepseek.kickoff()
            final_html = str(result)
            
            # 清洗 Markdown 标记
            if "```html" in final_html:
                final_html = final_html.split("```html")[1].split("```")[0]
            elif "```" in final_html:
                final_html = final_html.split("```")[1].split("```")[0]
                
            output_path = "index.html"
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(final_html.strip())
            
            print(f"✅ Report generated successfully with second backup model (DeepSeek Official API): {output_path}")
            print("📊 Report includes 4 sections (Chinese news skipped to avoid content policy issues):")
            print("   1. 全球新闻 (Global News)")
            print("   2. 法律新闻 (Legal News)")
            print("   3. 健康与运动 (Health & Sports + Deep Analysis)")
            print("   4. 法律学术分析 (Legal Analysis & Law Review Articles)")
            
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
                    
                output_path = "index.html"
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(final_html.strip())
                
                print(f"✅ Report generated successfully with third backup model (nvidia/llama-3.3-nemotron-super-49b-v1.5): {output_path}")
                print("📊 Report includes 5 sections:")
                print("   1. 中文新闻 (Chinese-language News)")
                print("   2. 全球新闻 (Global News)")
                print("   3. 法律新闻 (Legal News)")
                print("   4. 健康与运动 (Health & Sports + Deep Analysis)")
                print("   5. 法律学术分析 (Legal Analysis & Law Review Articles)")
                
            except Exception as backup_error:
                print(f"❌ Critical Error: All three models failed.")
                print(f"Primary model error: {e}")
                print(f"Second backup model error: {deepseek_error}")
                print(f"Third backup model error: {backup_error}")
                sys.exit(1)

if __name__ == "__main__":
    run()
