import os
import sys
from datetime import datetime
from crewai import Agent, Task, Crew, Process, LLM
from crewai_tools import ScrapeWebsiteTool, SerperDevTool

# --- 1. 配置 LLM (NVIDIA NIM) ---
# 替换为 NVIDIA API 配置
# 使用 NVIDIA DeepSeek-V3.2 模型
# 参考 NVIDIA 官方示范代码配置
nvidia_llm = LLM(
    model="deepseek-ai/deepseek-v3.2",
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.environ.get("NVIDIA_API_KEY"),
    temperature=1,
    top_p=0.95,
    max_tokens=8192,
    stream=True,
    timeout=600,
    # DeepSeek-V3.2 的思维模式配置 (通过 extra_body 传递)
    extra_body={"chat_template_kwargs": {"thinking": True}}
)

# 第二备用模型配置 - 在主模型调用失败时使用
backup_llm = LLM(
    model="nvidia/llama-3.3-nemotron-super-49b-v1.5",
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.environ.get("NVIDIA_API_KEY"),
    temperature=1,
    top_p=0.95,
    max_tokens=8192,
    stream=True,
    timeout=600
)

# 第三备用模型配置 - 使用 DeepSeek 官方 API
# 在前两个模型都失败或长时间无响应时使用
deepseek_llm = LLM(
    model="deepseek-chat",
    base_url="https://api.deepseek.com",
    api_key=os.environ.get("DEEPSEEK_API_KEY"),
    temperature=1,
    top_p=0.95,
    max_tokens=8192,
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
    goal='Select 5 newsworthy stories from Chinese-language sources with 3+ source verification',
    backstory=f"""
    You are an experienced news editor with 10 years of editorial experience.
    
    Your selection criteria:
    1. Filter out low-quality content: entertainment gossip and promotional press releases.
    2. Focus on substantive topics: employment, education, technology, and public welfare.
    3. Deep perspective: Look beyond trending topics to find meaningful stories.
    4. Multi-source integration: Each story must integrate at least 3 different perspectives.
    
    Style Guidelines:
    - Maintain objective, neutral journalistic tone
    - Use factual, descriptive language
    - Focus on concrete events and developments
    - Avoid inflammatory or controversial terminology
    
    {HUMANIZER_PROTOCOL}
    """,
    tools=[search_tool, scrape_tool],
    llm=nvidia_llm,
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
    llm=nvidia_llm,
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
    llm=nvidia_llm,
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
    llm=nvidia_llm,
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
    llm=nvidia_llm,
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
    llm=nvidia_llm,
    verbose=True
)

# 【深度研究员】 - 架构师（更新：整合5个板块）
researcher = Agent(
    role='Chief Researcher & Architect',
    goal='Synthesize all inputs into a cohesive, structured report with 5 sections',
    backstory=f"""
    You are responsible for the structural integrity of the report.
    You ensure:
    1. All FIVE sections are present: China, Global, Legal News, Health/Sports, Legal Scholarship (Law Review Articles)
    2. Data is accurate and sources are cited
    3. English headlines are preserved for Global news
    4. Deep analysis reports are properly integrated
    5. Multi-source information is clearly presented
    
    {HUMANIZER_PROTOCOL}
    """,
    tools=[scrape_tool],
    llm=nvidia_llm,
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
       - Section 1: Chinese-language News (中文新闻)
       - Section 2: Global News (全球新闻)
       - Section 3: Legal News (法律新闻)
       - Section 4: Health & Sports News + Deep Analysis (健康与运动)
       - Section 5: Legal Analysis & Law Review Articles (法律学术分析)
    
    {HUMANIZER_PROTOCOL}
    """,
    llm=nvidia_llm,
    verbose=True
)

# --- 4. 定义任务 (Tasks) ---

task_china = Task(
    description="""
    1. Search for 5 newsworthy stories from Chinese-language media sources.
    2. Sources: Major news outlets and reputable media platforms.
    3. Requirements: Focus on factual reporting, emphasize technology and public welfare topics.
    4. Multi-source integration: Each story must integrate at least 3 different source perspectives.
    """,
    expected_output="5 curated news stories from Chinese media, each with multi-source integration and source links.",
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
    1. Chinese-language News (中文新闻)
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
        1. 中文新闻 (Chinese-language News) - Gradient blue theme
        2. 全球新闻 (Global News) - Must display **English Headline** prominently
        3. 法律新闻 (Legal News) - Gradient purple theme
        4. 健康与运动 (Health & Sports) - Gradient green theme, with collapsible deep analysis
        5. 法律学术分析 (Legal Analysis) - Gradient amber theme, with collapsible article analysis
      - **Tags**: Use small pill-shaped tags for categories (e.g., "Tech", "Law", "Society", "Health", "Academic").
      - **Collapsible Panels**: Use `<details>` and `<summary>` for deep analysis content to keep the page clean.
      - **Responsive Design**: 
        - Desktop: 2-column grid for Chinese/Global, then full-width sections
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
        print("🔄 Retrying with backup model: nvidia/llama-3.3-nemotron-super-49b-v1.5")
        
        # 如果是 Content Risk，提示用户调整 Prompt
        if "Content Exists Risk" in str(e):
            print("⚠️ Suggestion: The system prompt might contain sensitive keywords. Try softening the language in 'china_scout'.")
        
        # 使用第二备用模型重试
        try:
            # 重新创建所有 agents，使用备用 LLM
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
            
            # 重新创建任务，使用备用 agents
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
            
            # 创建新的 Crew，使用备用模型
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
            
            print(f"✅ Report generated successfully with backup model: {output_path}")
            print("📊 Report includes 5 sections:")
            print("   1. 中文新闻 (Chinese-language News)")
            print("   2. 全球新闻 (Global News)")
            print("   3. 法律新闻 (Legal News)")
            print("   4. 健康与运动 (Health & Sports + Deep Analysis)")
            print("   5. 法律学术分析 (Legal Analysis & Law Review Articles)")
            
        except Exception as backup_error:
            print(f"⚠️ Second backup model also failed with error: {backup_error}")
            print("🔄 Retrying with third backup model: deepseek-chat (DeepSeek Official API)")
            
            # 检查是否有 DeepSeek API Key
            if not os.environ.get("DEEPSEEK_API_KEY"):
                print("❌ Error: DEEPSEEK_API_KEY not found in environment variables.")
                print("❌ Critical Error: All three models failed.")
                print(f"Primary error: {e}")
                print(f"Second backup error: {backup_error}")
                sys.exit(1)
            
            # 使用第三备用模型（DeepSeek 官方 API）重试
            # 注意：跳过中国新闻部分以避免内容审查问题
            try:
                print("⚠️ Note: Skipping Chinese news section to avoid content policy issues with DeepSeek API")
                
                # 重新创建 agents（跳过 china_scout），使用第三备用 LLM
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
                
                # 重新创建任务（跳过 task_china），使用第三备用 agents
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
                
                # 创建新的 Crew，使用第三备用模型（跳过中国新闻）
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
                
                print(f"✅ Report generated successfully with third backup model (DeepSeek Official API): {output_path}")
                print("📊 Report includes 4 sections (Chinese news skipped to avoid content policy issues):")
                print("   1. 全球新闻 (Global News)")
                print("   2. 法律新闻 (Legal News)")
                print("   3. 健康与运动 (Health & Sports + Deep Analysis)")
                print("   4. 法律学术分析 (Legal Analysis & Law Review Articles)")
                
            except Exception as deepseek_error:
                print(f"❌ Critical Error: All three models failed.")
                print(f"Primary model error: {e}")
                print(f"Second backup model error: {backup_error}")
                print(f"Third backup model error: {deepseek_error}")
                sys.exit(1)

if __name__ == "__main__":
    run()
