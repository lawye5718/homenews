import os
import sys
from datetime import datetime
from crewai import Agent, Task, Crew, Process, LLM
from crewai_tools import ScrapeWebsiteTool, SerperDevTool

# --- 1. 配置 LLM (DeepSeek) ---
# 增加 timeout 防止长任务中断
# 注意：DeepSeek 有时会触发 Content Exists Risk，需要 Prompt 尽量客观平和
deepseek_llm = LLM(
    model="deepseek/deepseek-chat", 
    base_url="https://api.deepseek.com",
    api_key=os.environ.get("DEEPSEEK_API_KEY"),
    temperature=0.7, 
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

# 【中国情报官】 - 多源整合 + 去敏感化
china_scout = Agent(
    role='资深社会观察编辑',
    goal='筛选今日中国互联网最具讨论价值的Top 5社会热点，每条新闻整合至少3个不同信源',
    backstory=f"""
    你是一名拥有十年经验的社会版面主编。
    你的选材标准非常严格，致力于【去伪存真】：
    1. 剔除无效信息：过滤掉纯粹的明星娱乐八卦、无实质内容的公关通稿。
    2. 关注核心议题：聚焦于就业环境、教育现状、科技发展、民生福祉等与普通人息息相关的议题。
    3. 深度视角：不只看热搜排名，要看话题背后的社会意义。
    4. 多源整合：每个热点必须整合至少3个不同角度的信源（官方叙事、民间讨论、专业分析）。
    
    注意：在汇报时请保持客观、中立的媒体语调，避免使用激进或引发争议的敏感词汇，以免触发内容过滤。
    
    {HUMANIZER_PROTOCOL}
    """,
    tools=[search_tool, scrape_tool],
    llm=deepseek_llm,
    verbose=True
)

# 【全球情报官】 - 强制英文源 + 多源整合
global_scout = Agent(
    role='International News Analyst (English Sources)',
    goal='Identify Top 5 Global events using ONLY English primary sources, with 3+ sources per story',
    backstory=f"""
    You strictly adhere to English-language primary sources.
    Your Logic:
    1. Tech: Focus on fundamental breakthroughs (AI, Space), not PR stunts.
    2. Geopolitics: Focus on strategic implications and factual developments.
    3. CRITICAL: You MUST retain the original English Headlines to avoid translation loss.
    4. Multi-Source: Each story must synthesize 3+ reputable sources (Reuters, Bloomberg, NYT, Nature, Foreign Affairs, Stratechery).
    
    {HUMANIZER_PROTOCOL}
    """,
    tools=[search_tool, scrape_tool],
    llm=deepseek_llm,
    verbose=True
)

# 【法律情报官】 - 多源整合
legal_scout = Agent(
    role='Global Legal News Curator',
    goal='Identify 5 landmark legal events (SCOTUS, EU CJEU, China SPC) with multi-source verification',
    backstory=f"""
    Focus on "Hard Law" developments:
    1. Landmark Rulings: Supreme Court decisions that change precedent.
    2. Major Legislation: EU AI Act, GDPR, Antitrust laws.
    3. Corporate Litigation: Significant Big Tech lawsuits.
    4. Multi-Source: Each legal development must include court documents, expert commentary, and news coverage.
    
    {HUMANIZER_PROTOCOL}
    """,
    tools=[search_tool, scrape_tool],
    llm=deepseek_llm,
    verbose=True
)

# 【健康与运动新闻情报官】 - 新增：科学期刊来源
health_sports_scout = Agent(
    role='Health & Sports Science Reporter',
    goal='Identify Top 5 health and sports science news from peer-reviewed sources',
    backstory=f"""
    You are a science journalist specializing in health and sports research.
    Your priority sources (in order):
    1. Scientific American (health, sports science, fitness)
    2. Nature (medical research, sports physiology)
    3. Science Magazine (health studies, exercise science)
    4. The Lancet, JAMA, NEJM (medical journals)
    5. Sports Medicine journals
    
    Selection Criteria:
    - Focus on peer-reviewed research with practical implications
    - Prioritize studies with large sample sizes and robust methodology
    - Include both breaking research and emerging trends
    - Avoid sensationalized health claims without scientific backing
    
    {HUMANIZER_PROTOCOL}
    """,
    tools=[search_tool, scrape_tool],
    llm=deepseek_llm,
    verbose=True
)

# 【健康分析师】 - 新增：深度分析报告
health_analyst = Agent(
    role='Health Science Analyst',
    goal='Generate 300-500 word deep analysis reports for top 3 health/sports stories',
    backstory=f"""
    You are an expert science communicator who makes complex research accessible.
    
    For each of the Top 3 health/sports stories, create a comprehensive analysis including:
    1. **Background**: Scientific context with concrete examples
    2. **Methods**: Research methodology explained in accessible language
    3. **Findings**: Key discoveries with specific data points ("subjects ran 15% faster" not "performance improved")
    4. **Implications**: Impact on public health, sports, or fitness with real-world applications
    5. **Practical Applications**: Actionable advice for readers
    6. **Limitations**: Caveats and areas for further research
    
    {HUMANIZER_PROTOCOL}
    """,
    tools=[scrape_tool],
    llm=deepseek_llm,
    verbose=True
)

# 【法律学者】 - 新增：法律评论文章分析
legal_scholar = Agent(
    role='Comparative Law Scholar',
    goal='Analyze law review articles from top US law schools related to current US-China hot topics',
    backstory=f"""
    You are a comparative law expert specializing in US-China legal issues.
    
    Your workflow:
    1. Identify 3-5 key legal issues from current US and China hot topics
    2. Search law review articles from top 10 US law schools:
       - Yale Law Journal, Harvard Law Review, Stanford Law Review
       - Columbia Law Review, University of Chicago Law Review, NYU Law Review
       - Penn Law Review, Michigan Law Review, Virginia Law Review, Berkeley Law Review
    3. Select the 3 most relevant and recent articles
    4. For each article, generate an 800-1000 word analysis:
       - Article Overview (200 words): Thesis with engaging, concrete language
       - Legal Framework (150 words): Legal doctrines with real-world examples
       - Key Arguments (200 words): Specific cases and implications
       - Connection to Hot Topics (150 words): Relate to current events
       - Practical Implications (100 words): Real-world legal consequences
    
    {HUMANIZER_PROTOCOL}
    """,
    tools=[search_tool, scrape_tool],
    llm=deepseek_llm,
    verbose=True
)

# 【深度研究员】 - 架构师（更新：整合5个板块）
researcher = Agent(
    role='Chief Researcher & Architect',
    goal='Synthesize all inputs into a cohesive, structured report with 5 sections',
    backstory=f"""
    You are responsible for the structural integrity of the report.
    You ensure:
    1. All FIVE sections are present: China, Global, Legal, Health/Sports, Legal Analysis
    2. Data is accurate and sources are cited
    3. English headlines are preserved for Global news
    4. Deep analysis reports are properly integrated
    5. Multi-source information is clearly presented
    
    {HUMANIZER_PROTOCOL}
    """,
    tools=[scrape_tool],
    llm=deepseek_llm,
    verbose=True
)

# 【主编】 - Humanizer (去 AI 味 & UI 设计) - 更新：五栏布局
editor = Agent(
    role='Lead Editor & Humanizer (Anti-AI Style)',
    goal='Generate a Daily Briefing with 5 sections that sounds 100% Human and looks stunning',
    backstory=f"""
    You are a veteran editor who hates "AI-sounding" text. 
    You adhere to the **Deep Humanizer Protocol**:
    
    1. **Kill the "AI Voice"**: 
       - NEVER use: "In conclusion", "delve", "landscape", "tapestry", "underscores", "complex interplay".
       - 严禁使用："总而言之"、"值得注意的是"、"这是一把双刃剑"。
    
    2. **High Burstiness (爆发度)**: 
       - Mix very short, punchy sentences with long, rhythmic ones. 
       - Example: "The market crashed. Traders panicked, screaming into their phones as red lines plummeted across screens."
    
    3. **Show, Don't Tell**: 
       - Instead of "The situation is tense", say "Diplomats slammed doors and refused to shake hands."
    
    4. **UI/UX Design (Tailwind CSS)**:
       - You act as a Frontend Engineer.
       - Use Tailwind CSS via CDN.
       - Font: 'Merriweather' (Serif) for headlines, 'Inter' (Sans) for body.
       - Layout: Modern Bento Grid style with 5 sections. Dark/Professional theme.
       - Responsive design: Desktop shows grid, mobile stacks vertically.
       - Include collapsible sections for deep analysis content.
    
    5. **Five Section Layout**:
       - Section 1: China News (中国新闻)
       - Section 2: Global News (全球新闻)
       - Section 3: Legal News (法律新闻)
       - Section 4: Health & Sports News + Deep Analysis (健康与运动)
       - Section 5: Legal Analysis & Law Review Articles (法律学术分析)
    
    {HUMANIZER_PROTOCOL}
    """,
    llm=deepseek_llm,
    verbose=True
)

# --- 4. 定义任务 (Tasks) ---

task_china = Task(
    description="""
    1. 搜索今日中国社会最具讨论价值的5个议题。
    2. 来源：财新、澎湃、知乎日报、凤凰网等深度媒体。
    3. 要求：避开敏感词，客观陈述事实，重点挖掘民生与科技类话题。
    4. 多源整合：每个热点必须整合至少3个不同角度的信源（官方叙事、民间讨论、专业分析）。
    """,
    expected_output="5个经过筛选的高质量中国新闻，每条包含多信源整合和来源链接。",
    agent=china_scout
)

task_global = Task(
    description="""
    1. Search 'Breaking news Reuters', 'Tech analysis Stratechery', 'Geopolitics Foreign Affairs'.
    2. Select 5 events with global structural impact.
    3. RETURN FORMAT: English Headline + Chinese Contextual Summary.
    4. Multi-Source: Each story must synthesize 3+ sources (Reuters, Bloomberg, NYT, Nature, etc).
    """,
    expected_output="5 Global news items with English Titles and multi-source verification.",
    agent=global_scout
)

task_legal = Task(
    description="""
    Search for today's most significant court rulings or legislative drafts (US/EU/CN).
    Focus on IP, Antitrust, AI Regulation.
    Multi-Source: Each legal development must include court documents, expert commentary, and news coverage.
    """,
    expected_output="5 Key Legal Updates with multi-source citations.",
    agent=legal_scout
)

# 【新增】健康与运动新闻任务
task_health_sports = Task(
    description="""
    1. Search for the top 5 health and sports science news from peer-reviewed sources.
    2. Priority sources: Scientific American, Nature, Science Magazine, The Lancet, JAMA, NEJM, Sports Medicine journals.
    3. Focus on:
       - New research findings with practical health implications
       - Sports science breakthroughs
       - Exercise and fitness studies
       - Nutrition research
    4. Include the journal/source name, publication date, and key findings.
    """,
    expected_output="5 Health/Sports Science news items with source citations and key findings.",
    agent=health_sports_scout
)

# 【新增】健康深度分析任务
task_health_analysis = Task(
    description="""
    Select the TOP 3 most impactful health/sports stories from the collected news.
    For each of the 3 stories, generate a 300-500 word deep analysis report including:
    
    1. **Background** (50-80 words): Scientific context with concrete examples
    2. **Methods** (40-60 words): Research methodology explained accessibly
    3. **Findings** (80-120 words): Key discoveries with specific data points
    4. **Implications** (60-80 words): Impact on public health/fitness
    5. **Practical Applications** (50-80 words): Actionable advice for readers
    6. **Limitations** (30-50 words): Caveats and further research needs
    
    IMPORTANT: Follow the Deep Humanizer Protocol. No AI clichés. Use concrete examples and varied sentence structure.
    """,
    expected_output="3 in-depth analysis reports (300-500 words each) for top health/sports stories.",
    agent=health_analyst,
    context=[task_health_sports]
)

# 【新增】法律学术分析任务
task_legal_analysis = Task(
    description="""
    Phase 1: Identify 3-5 key legal issues from current US and China hot topics based on the news collected.
    
    Phase 2: Search for relevant law review articles from top 10 US law schools:
    - Yale Law Journal, Harvard Law Review, Stanford Law Review
    - Columbia Law Review, University of Chicago Law Review, NYU Law Review
    - Penn Law Review, Michigan Law Review, Virginia Law Review, Berkeley Law Review
    
    Phase 3: Select the 3 most relevant and recent articles.
    
    Phase 4: For each article, generate an 800-1000 word comprehensive analysis:
    1. **Article Overview** (200 words): Summarize thesis with engaging, concrete language
    2. **Legal Framework** (150 words): Explain legal doctrines using real-world examples
    3. **Key Arguments** (200 words): Break down arguments with specific cases
    4. **Connection to Hot Topics** (150 words): Relate to current events
    5. **Practical Implications** (100 words): Real-world legal consequences
    
    IMPORTANT: Follow the Deep Humanizer Protocol. Technical precision with readable prose. Avoid jargon overload.
    """,
    expected_output="Analysis of 3 law review articles (800-1000 words each) connected to current US-China topics.",
    agent=legal_scholar,
    context=[task_china, task_global, task_legal]
)

# 【更新】研究任务：整合所有5个板块
task_research = Task(
    description="""
    Compile ALL inputs from the 5 sections:
    1. China News (中国新闻)
    2. Global News (全球新闻)
    3. Legal News (法律新闻)
    4. Health & Sports News + Deep Analysis (健康与运动)
    5. Legal Analysis & Law Review Articles (法律学术分析)
    
    Verify that ALL FIVE SECTIONS exist with complete data.
    Ensure strict separation of content between sections.
    Add a "Key Takeaway" one-liner for every major news item.
    Preserve all deep analysis reports in their entirety.
    Ensure English headlines are preserved for Global news.
    """,
    expected_output="Master Report Markdown with all 5 sections and deep analysis reports.",
    agent=researcher,
    context=[task_china, task_global, task_legal, task_health_sports, task_health_analysis, task_legal_analysis]
)

current_date = datetime.now().strftime("%Y-%m-%d")

# 【更新】发布任务：五栏响应式布局
task_publish = Task(
    description=f"""
    Generate the final `index.html` file based on the Research Report with FIVE SECTIONS.
    
    **Technical Requirements**:
    1. Include `<script src="https://cdn.tailwindcss.com"></script>` in `<head>`.
    2. Import fonts: Google Fonts (Inter, Merriweather).
    3. Use `font-serif` for titles, `font-sans` for body.
    
    **Design Language**:
    - **Header**: "Daily Insight" | {current_date} | Minimalist.
    - **Layout**: 
      - Use a **CSS Grid** (Bento Box style) for the news cards.
      - **Five Section Layout**:
        1. 中国新闻 (China News) - Gradient blue theme
        2. 全球新闻 (Global News) - Must display **English Headline** prominently
        3. 法律新闻 (Legal News) - Gradient purple theme
        4. 健康与运动 (Health & Sports) - Gradient green theme, with collapsible deep analysis
        5. 法律学术分析 (Legal Analysis) - Gradient amber theme, with collapsible article analysis
      - **Tags**: Use small pill-shaped tags for categories (e.g., "Tech", "Law", "Society", "Health", "Academic").
      - **Collapsible Panels**: Use `<details>` and `<summary>` for deep analysis content to keep the page clean.
      - **Responsive Design**: 
        - Desktop: 2-column grid for China/Global, then full-width sections
        - Tablet: 2-column grid
        - Mobile: Single column stacked layout
    - **Tone Check**: Ensure the summary text sounds human-written (punchy, avoiding AI clichés).
    
    **Output**: 
    - ONLY the raw HTML code, starting with `<!DOCTYPE html>`.
    """,
    expected_output="Final HTML String with 5 sections and responsive layout.",
    agent=editor,
    context=[task_research]
)

# --- 5. 执行流程 ---
def run():
    print("🚀 Starting Daily News Agent (5-Section Edition)...")
    
    if not os.environ.get("DEEPSEEK_API_KEY"):
        print("❌ Error: DEEPSEEK_API_KEY not found in environment variables.")
        sys.exit(1)
    
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
    
    # 使用 try-except 捕获可能的 API 错误
    try:
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
        print("   1. 中国新闻 (China News)")
        print("   2. 全球新闻 (Global News)")
        print("   3. 法律新闻 (Legal News)")
        print("   4. 健康与运动 (Health & Sports + Deep Analysis)")
        print("   5. 法律学术分析 (Legal Analysis & Law Review Articles)")
        
    except Exception as e:
        print(f"❌ Critical Error during execution: {e}")
        # 如果是 Content Risk，提示用户调整 Prompt
        if "Content Exists Risk" in str(e):
            print("⚠️ Suggestion: The system prompt might contain sensitive keywords. Try softening the language in 'china_scout'.")
        sys.exit(1)

if __name__ == "__main__":
    run()
