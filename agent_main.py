import os
import sys
import smtplib
from pathlib import Path
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from crewai import Agent, Task, Crew, Process, LLM
from crewai_tools import ScrapeWebsiteTool, SerperDevTool

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
    goal='Select 5 newsworthy stories from Chinese-language sources with 3+ source verification and comprehensive 1000+ word summaries',
    backstory=f"""
    You are an experienced news editor with 10 years of editorial experience.
    
    Your selection criteria:
    1. Filter out low-quality content: entertainment gossip and promotional press releases.
    2. Focus on substantive topics: employment, education, technology, and public welfare.
    3. Deep perspective: Look beyond trending topics to find meaningful stories.
    4. Multi-source integration: Each story must integrate at least 3 different perspectives.
    5. **Comprehensive reporting**: Each news summary must be at least 1000 words with detailed analysis.
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
    goal='Identify Top 5 Global events using ONLY English primary sources, with 3+ sources per story and comprehensive 1000+ word analysis',
    backstory=f"""
    You strictly adhere to English-language primary sources.
    Your Logic:
    1. Tech: Focus on fundamental breakthroughs (AI, Space), not PR stunts.
    2. Geopolitics: Focus on strategic implications and factual developments.
    3. CRITICAL: You MUST retain the original English Headlines to avoid translation loss.
    4. Multi-Source: Each story must synthesize 3+ reputable sources (Reuters, Bloomberg, NYT, Nature, Foreign Affairs, Stratechery).
    5. **Comprehensive reporting**: Each news summary must be at least 1000 words with detailed analysis and context.
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
    goal='Identify 5 landmark legal events (SCOTUS, EU CJEU, China SPC) with multi-source verification and comprehensive 1000+ word legal analysis',
    backstory=f"""
    Focus on "Hard Law" developments:
    1. Landmark Rulings: Supreme Court decisions that change precedent.
    2. Major Legislation: EU AI Act, GDPR, Antitrust laws.
    3. Corporate Litigation: Significant Big Tech lawsuits.
    4. Multi-Source: Each legal development must include court documents, expert commentary, and news coverage.
    5. **Comprehensive reporting**: Each legal news summary must be at least 1000 words with detailed legal analysis.
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
    goal='Identify Top 5 health and sports science news from peer-reviewed sources with comprehensive 1000+ word scientific summaries',
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
    - **Comprehensive reporting**: Each news summary must be at least 1000 words with detailed scientific background and analysis
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
    goal='Synthesize all inputs into a cohesive, structured report with 5 sections, preserving all source URLs',
    backstory=f"""
    You are responsible for the structural integrity of the report.
    You ensure:
    1. All FIVE sections are present: China, Global, Legal News, Health/Sports, Legal Scholarship (Law Review Articles)
    2. Data is accurate and sources are cited with original URLs preserved
    3. English headlines are preserved for Global news
    4. Deep analysis reports (5000+ words each) are properly integrated
    5. Multi-source information is clearly presented with all source links
    6. **Source URLs**: Preserve ALL original document URLs from all scouts and analysts
    7. **Comprehensive content**: Ensure all 1000+ word summaries and 5000+ word analyses are complete
    
    {HUMANIZER_PROTOCOL}
    """,
    tools=[scrape_tool],
    llm=nvidia_llm,
    verbose=True
)

# 【主编】 - Humanizer (去 AI 味 & UI 设计) - 更新：五栏布局
editor = Agent(
    role='Lead Editor & Humanizer (Anti-AI Style)',
    goal='Generate a Daily Briefing with 5 sections that sounds 100% Human with beautiful card-based UI and smooth animations',
    backstory=f"""
    You are a veteran editor who hates "AI-sounding" text and loves beautiful, user-friendly design.
    You adhere to the **Deep Humanizer Protocol**:
    
    1. **Kill the "AI Voice"**: 
       - NEVER use: "In conclusion", "delve", "landscape", "tapestry", "underscores", "complex interplay".
       - 严禁使用："总而言之"、"值得注意的是"、"这是一把双刃剑"。
    
    2. **High Burstiness (爆发度)**: 
       - Mix very short, punchy sentences with long, rhythmic ones. 
       - Example: "The market crashed. Traders panicked, screaming into their phones as red lines plummeted across screens."
    
    3. **Show, Don't Tell**: 
       - Instead of "The situation is tense", say "Diplomats slammed doors and refused to shake hands."
    
    4. **UI/UX Design (Tailwind CSS + Custom CSS)**:
       - You act as a Frontend Engineer specializing in beautiful, modern web design.
       - Use Tailwind CSS via CDN for rapid styling.
       - Font: 'Merriweather' (Serif) for headlines, 'Inter' (Sans) for body.
       - **Card-Based Layout**: Every news item and analysis in its own card with:
         * Subtle shadows and elegant hover effects (shadow-lg hover:shadow-xl)
         * Smooth transitions and animations
         * Rounded corners and clean spacing
         * White/light cards on dark gradient backgrounds
       - **Collapsible Groups**: Group related news with smooth expand/collapse animations
       - **Responsive Design**: Perfect on desktop, tablet, and mobile
       - Include custom CSS for smooth animations (fadeIn, slideDown, hover effects)
    
    5. **Five Section Layout with Cards**:
       - Section 1: Chinese-language News (中文新闻) - Blue gradient with white cards
       - Section 2: Global News (全球新闻) - Purple gradient with white cards, **English Headlines** prominent
       - Section 3: Legal News (法律新闻) - Indigo gradient with white cards
       - Section 4: Health & Sports News + Deep Analysis (健康与运动) - Green gradient with expandable cards
       - Section 5: Legal Analysis & Law Review Articles (法律学术分析) - Amber gradient with expandable cards
    
    6. **Source Links Display**:
       - Display all source URLs as clickable badges/chips
       - Use different colors for different source types (official, news, academic)
       - Make links prominent and easy to click
    
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
    5. **Word count requirement**: Each news summary must be at least 1000 words, providing comprehensive detail.
    6. **Source links required**: Include original document links (URLs) for each source cited.
    """,
    expected_output="5 curated news stories from Chinese media (1000+ words each), each with multi-source integration and source links.",
    agent=china_scout
)

task_global = Task(
    description="""
    1. Search 'Breaking news Reuters', 'Tech analysis Stratechery', 'Geopolitics Foreign Affairs'.
    2. Select 5 events with global structural impact.
    3. RETURN FORMAT: English Headline + Chinese Contextual Summary.
    4. Multi-Source: Each story must synthesize 3+ sources (Reuters, Bloomberg, NYT, Nature, etc).
    5. **Word count requirement**: Each news summary must be at least 1000 words, providing comprehensive analysis.
    6. **Source links required**: Include original document links (URLs) for each source cited.
    """,
    expected_output="5 Global news items (1000+ words each) with English Titles and multi-source verification, including source URLs.",
    agent=global_scout
)

task_legal = Task(
    description="""
    Search for today's most significant court rulings or legislative drafts (US/EU/CN).
    Focus on IP, Antitrust, AI Regulation.
    Multi-Source: Each legal development must include court documents, expert commentary, and news coverage.
    **Word count requirement**: Each legal news summary must be at least 1000 words, providing comprehensive legal analysis.
    **Source links required**: Include original document links (URLs) - court documents, legislation, expert analysis, and news articles.
    """,
    expected_output="5 Key Legal Updates (1000+ words each) with multi-source citations and original document URLs.",
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
    5. **Word count requirement**: Each news summary must be at least 1000 words, providing comprehensive scientific detail.
    6. **Source links required**: Include original document links (URLs) - journal articles, research papers, and scientific publications.
    """,
    expected_output="5 Health/Sports Science news items (1000+ words each) with source citations, key findings, and original document URLs.",
    agent=health_sports_scout
)

# 【新增】健康深度分析任务
task_health_analysis = Task(
    description="""
    Select the TOP 3 most impactful health/sports stories from the collected news.
    For each of the 3 stories, generate a comprehensive in-depth analysis report of at least 5000 words including:
    
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
    expected_output="3 comprehensive in-depth analysis reports (5000+ words each) for top health/sports stories with all source URLs.",
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
    expected_output="Analysis of 3 law review articles (5000+ words each) connected to current US-China topics with all source URLs.",
    agent=legal_scholar,
    context=[task_china, task_global, task_legal]
)

# 【更新】研究任务：整合所有5个板块
task_research = Task(
    description="""
    Compile ALL inputs from the 5 sections:
    1. Chinese-language News (中文新闻) - with 1000+ word summaries
    2. Global News (全球新闻) - with 1000+ word summaries
    3. Legal News (法律新闻) - with 1000+ word summaries
    4. Health & Sports News + Deep Analysis (健康与运动) - with 1000+ word summaries and 5000+ word analyses
    5. Legal Analysis & Law Review Articles (法律学术分析) - with 5000+ word analyses
    
    Verify that ALL FIVE SECTIONS exist with complete data.
    Ensure strict separation of content between sections.
    Add a "Key Takeaway" one-liner for every major news item.
    Preserve all deep analysis reports in their entirety (5000+ words each).
    Ensure English headlines are preserved for Global news.
    **CRITICAL**: Preserve ALL original source URLs from all sections - news articles, research papers, court documents, law review articles, etc.
    Format source URLs clearly so they can be displayed as clickable links in the final HTML.
    
    **Output Format Requirements**:
    Structure the output in clear markdown with:
    - Clear section headers (# Section Name)
    - Each news item with:
      * ## News Headline
      * Category tag
      * Full summary text
      * Sources: [URL1], [URL2], [URL3]
    - Each analysis with:
      * ## Analysis Title
      * Complete 5000+ word content with all subsections
      * All source citations with URLs
    
    Make it easy for the next agent to parse and convert to HTML.
    Include ALL content - do not truncate or summarize.
    """,
    expected_output="Master Report Markdown with all 5 sections, complete analyses, all source URLs preserved, and clear structure for HTML conversion.",
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
    4. Add smooth CSS transitions and animations for all interactive elements.
    
    **Design Language - Card-Based Layout**:
    - **Header**: "Daily Insight" | {current_date} | Minimalist with gradient background.
    - **Layout Style**: 
      - **Card-Based Design**: Each news item and analysis should be in its own distinct card with:
        - Subtle shadow and hover effects (shadow-lg hover:shadow-xl transition-shadow)
        - Rounded corners (rounded-xl)
        - Clean padding and spacing
        - White/light background on dark page for contrast
      - **Responsive Grid Layout**:
        - Desktop: Multi-column grid (2-3 columns) for news cards
        - Tablet: 2-column grid
        - Mobile: Single column stacked layout
      - **Five Section Layout**:
        1. 中文新闻 (Chinese-language News) - Gradient blue theme with card layout
        2. 全球新闻 (Global News) - Must display **English Headline** prominently in cards
        3. 法律新闻 (Legal News) - Gradient purple theme with card layout
        4. 健康与运动 (Health & Sports) - Gradient green theme with card layout
        5. 法律学术分析 (Legal Analysis) - Gradient amber theme with card layout
      
    **Collapsible & Animation Features**:
      - **Collapsible News Groups**: Group related news stories together with collapsible sections
        - Use `<details>` and `<summary>` elements for native collapsible behavior
        - Add CSS transitions for smooth expand/collapse animations
        - Style summary with hover effects and indicator icons (▶/▼)
      - **Expandable Analysis Cards**: Deep analysis content (5000+ words) should be collapsible
        - Initially show only title and first 200 words
        - "Read More" button to expand full content with smooth slide-down animation
        - Add CSS for max-height transitions and opacity fading
      - **Animation Effects**:
        - Fade-in animation for cards on page load (use @keyframes fadeIn)
        - Smooth height transitions for collapsible sections (transition: max-height 0.3s ease)
        - Hover animations for cards (transform: translateY(-4px))
        - Rotation animation for expand/collapse icons (transition: transform 0.2s)
      
    **UI/UX Details**:
      - **Tags**: Use small pill-shaped tags for categories (e.g., "Tech", "Law", "Society", "Health", "Academic").
      - **Source Links**: Display source URLs as clickable badges/chips at the bottom of each card
      - **Typography**: 
        - Headlines: Merriweather (serif), bold, larger size
        - Body: Inter (sans), comfortable line-height (1.6-1.8)
        - Analysis sections: Clear hierarchy with h3, h4 headings
      - **Color Scheme**: 
        - Dark/Professional theme with gradient backgrounds
        - Light cards on dark background for readability
        - Distinct gradient colors for each section (blue, purple, green, amber, etc.)
      - **Spacing**: Generous padding and margins for readability (p-6, gap-4, space-y-4)
      - **Tone Check**: Ensure the summary text sounds human-written (punchy, avoiding AI clichés).
    
    **Code Structure**:
    Include these key CSS animations in a `<style>` tag:
    ```css
    @keyframes fadeIn {{
      from {{ opacity: 0; transform: translateY(20px); }}
      to {{ opacity: 1; transform: translateY(0); }}
    }}
    .card {{ animation: fadeIn 0.5s ease-out; }}
    details[open] summary ~ * {{ animation: slideDown 0.3s ease; }}
    @keyframes slideDown {{
      from {{ opacity: 0; max-height: 0; }}
      to {{ opacity: 1; max-height: 5000px; }}
    }}
    ```
    
    **CRITICAL - Content Population Requirements**:
    YOU MUST populate ALL sections with the ACTUAL CONTENT from the research report.
    DO NOT create empty framework/skeleton HTML.
    
    For each news item, you MUST include:
    - The actual headline/title from the research report
    - The full summary text (1000+ words)
    - All source URLs as clickable links
    - Relevant category tags
    
    For each analysis report, you MUST include:
    - The complete 5000+ word analysis text
    - All section headings and content
    - All source citations and links
    - Collapsible structure with "Read More" functionality
    
    **Example Structure for a News Card**:
    ```html
    <div class="card bg-white rounded-xl shadow-lg p-6 hover:shadow-xl transition-shadow">
      <span class="inline-block px-3 py-1 text-xs font-semibold bg-blue-100 text-blue-800 rounded-full mb-3">Tech</span>
      <h3 class="font-serif text-2xl font-bold mb-3">[ACTUAL NEWS HEADLINE HERE]</h3>
      <div class="prose prose-lg">
        [ACTUAL FULL NEWS SUMMARY TEXT HERE - 1000+ words from research report]
      </div>
      <div class="mt-4 flex flex-wrap gap-2">
        <a href="[ACTUAL SOURCE URL]" class="text-xs px-2 py-1 bg-gray-100 rounded-full hover:bg-gray-200">Source 1</a>
        <a href="[ACTUAL SOURCE URL]" class="text-xs px-2 py-1 bg-gray-100 rounded-full hover:bg-gray-200">Source 2</a>
      </div>
    </div>
    ```
    
    **Example Structure for Collapsible Analysis**:
    ```html
    <details class="card bg-white rounded-xl shadow-lg p-6">
      <summary class="cursor-pointer font-serif text-2xl font-bold hover:text-blue-600">
        [ACTUAL ANALYSIS TITLE HERE] ▼
      </summary>
      <div class="mt-4 prose prose-lg max-w-none">
        [ACTUAL COMPLETE 5000+ WORD ANALYSIS CONTENT HERE]
      </div>
    </details>
    ```
    
    **Output**: 
    - ONLY the raw HTML code, starting with `<!DOCTYPE html>`.
    - Complete, production-ready HTML with ALL ACTUAL CONTENT from the research report.
    - NO placeholder text, NO empty sections, NO skeleton frameworks.
    - Every section must have real news items and analyses from the research report.
    """,
    expected_output="Final HTML String with 5 sections, card-based responsive layout, collapsible groups, and smooth animations.",
    agent=editor,
    context=[task_research]
)

# --- 5. 辅助函数：报告保存和邮件发送 ---

def setup_reports_directory():
    """Create directory for saving markdown reports"""
    current_date = datetime.now().strftime("%Y-%m-%d")
    reports_dir = Path(f"reports/{current_date}")
    reports_dir.mkdir(parents=True, exist_ok=True)
    return reports_dir

def save_markdown_report(content, filename, reports_dir):
    """Save a report as markdown file"""
    filepath = reports_dir / filename
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✅ Saved report: {filepath}")
    return filepath

def send_email_report(subject, body, attachments=None):
    """Send email report to configured address"""
    mail_address = os.environ.get("mailadd")
    
    if not mail_address:
        print("⚠️ Email address (mailadd) not configured, skipping email send")
        return False
    
    # Check for email server configuration
    smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER")
    smtp_password = os.environ.get("SMTP_PASSWORD")
    
    if not smtp_user or not smtp_password:
        print("⚠️ SMTP credentials not configured (SMTP_USER, SMTP_PASSWORD), skipping email send")
        return False
    
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = mail_address
        msg['Subject'] = subject
        
        # Add body
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # Add attachments if provided
        if attachments:
            for attachment_path in attachments:
                if Path(attachment_path).exists():
                    with open(attachment_path, 'r', encoding='utf-8') as f:
                        attachment = MIMEText(f.read(), 'plain', 'utf-8')
                        attachment.add_header('Content-Disposition', 'attachment', 
                                            filename=Path(attachment_path).name)
                        msg.attach(attachment)
        
        # Send email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
        
        print(f"✅ Email sent successfully to {mail_address}")
        return True
        
    except Exception as e:
        print(f"⚠️ Failed to send email: {e}")
        return False

# --- 6. 执行流程 ---
def validate_html_content(html_content):
    """Validate that the HTML contains actual content, not just framework"""
    required_sections = [
        "中文新闻",  # Chinese News
        "全球新闻",  # Global News  
        "法律新闻",  # Legal News
        "健康与运动", # Health & Sports
        "法律学术"   # Legal Analysis
    ]
    
    validation_passed = True
    issues = []
    
    # Check for DOCTYPE
    if not html_content.strip().startswith("<!DOCTYPE html>") and not html_content.strip().startswith("<html"):
        issues.append("Missing DOCTYPE or html tag")
        validation_passed = False
    
    # Check for each required section
    for section in required_sections:
        if section not in html_content:
            issues.append(f"Missing section: {section}")
            validation_passed = False
    
    # Check for content indicators (should have multiple paragraphs, not just headers)
    if html_content.count("<p>") < 10:
        issues.append(f"Suspiciously low paragraph count: {html_content.count('<p>')} (expected 10+)")
        validation_passed = False
    
    # Check for links
    if html_content.count("<a ") < 5:
        issues.append(f"Suspiciously low link count: {html_content.count('<a ')} (expected source links)")
        validation_passed = False
    
    # Check minimum length (should be substantial)
    if len(html_content) < 50000:  # Should be much larger with all content
        issues.append(f"HTML too short: {len(html_content)} bytes (expected 50000+)")
        validation_passed = False
    
    if not validation_passed:
        print("⚠️ HTML Validation Issues Found:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("✅ HTML validation passed")
        print(f"  - HTML length: {len(html_content)} bytes")
        print(f"  - Paragraph count: {html_content.count('<p>')}")
        print(f"  - Link count: {html_content.count('<a ')}")
    
    return validation_passed, issues

def run():
    print("🚀 Starting Daily News Agent (5-Section Edition)...")
    
    if not os.environ.get("NVIDIA_API_KEY"):
        print("❌ Error: NVIDIA_API_KEY not found in environment variables.")
        sys.exit(1)
    
    # Setup reports directory
    current_date = datetime.now().strftime("%Y-%m-%d")
    reports_dir = setup_reports_directory()
    print(f"📁 Reports will be saved to: {reports_dir}")
    
    # Store all reports for email
    saved_reports = []
    
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
        
        # Save intermediate task outputs as markdown
        print("\n📝 Saving intermediate reports...")
        try:
            # Get task outputs
            task_outputs = news_crew.tasks
            for i, task in enumerate(task_outputs):
                if hasattr(task, 'output') and task.output:
                    task_name = f"task_{i+1}_{task.agent.role.replace(' ', '_').replace('/', '_')}.md"
                    content = str(task.output)
                    saved_file = save_markdown_report(content, task_name, reports_dir)
                    saved_reports.append(saved_file)
        except Exception as e:
            print(f"⚠️ Could not save intermediate reports: {e}")
        
        final_html = str(result)
        
        # Log result for debugging
        print(f"\n📝 Raw result length: {len(final_html)} characters")
        print(f"📝 First 500 chars of result:\n{final_html[:500]}")
        
        # Save the research report (markdown version before HTML conversion)
        # The task_research output should contain the master markdown
        try:
            research_output = task_outputs[6].output if len(task_outputs) > 6 else None
            if research_output:
                research_md = save_markdown_report(
                    str(research_output), 
                    "master_research_report.md", 
                    reports_dir
                )
                saved_reports.append(research_md)
        except Exception as e:
            print(f"⚠️ Could not save research report: {e}")
        
        # 清洗 Markdown 标记
        if "```html" in final_html:
            final_html = final_html.split("```html")[1].split("```")[0]
        elif "```" in final_html:
            final_html = final_html.split("```")[1].split("```")[0]
        
        # Validate HTML content
        print("\n🔍 Validating HTML content...")
        validation_passed, issues = validate_html_content(final_html)
        
        if not validation_passed:
            print("⚠️ HTML validation failed, but saving anyway for review")
            
        output_path = "index.html"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(final_html.strip())
        
        print(f"\n✅ Report generated successfully: {output_path}")
        print("📊 Report includes 5 sections:")
        print("   1. 中文新闻 (Chinese-language News)")
        print("   2. 全球新闻 (Global News)")
        print("   3. 法律新闻 (Legal News)")
        print("   4. 健康与运动 (Health & Sports + Deep Analysis)")
        print("   5. 法律学术分析 (Legal Analysis & Law Review Articles)")
        
        # Send email with all reports
        print("\n📧 Preparing to send email report...")
        email_body = f"""Daily News Briefing Report - {current_date}

This email contains the daily news briefing reports generated by the AI News Agent.

Report Summary:
- 5 major sections covered
- {len(saved_reports)} intermediate reports generated
- All reports attached as markdown files

Reports are also saved locally in: {reports_dir}

Please find the attached reports for detailed analysis.

---
Generated by HomeNews AI Agent
"""
        
        send_email_report(
            subject=f"Daily News Briefing - {current_date}",
            body=email_body,
            attachments=saved_reports
        )
        
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
            
            # Save intermediate reports
            print("\n📝 Saving intermediate reports (backup model)...")
            try:
                task_outputs = news_crew_deepseek.tasks
                for i, task in enumerate(task_outputs):
                    if hasattr(task, 'output') and task.output:
                        task_name = f"backup_task_{i+1}_{task.agent.role.replace(' ', '_').replace('/', '_')}.md"
                        content = str(task.output)
                        saved_file = save_markdown_report(content, task_name, reports_dir)
                        saved_reports.append(saved_file)
            except Exception as e:
                print(f"⚠️ Could not save intermediate reports: {e}")
            
            final_html = str(result)
            
            # Log result for debugging
            print(f"\n📝 Raw result length: {len(final_html)} characters")
            
            # 清洗 Markdown 标记
            if "```html" in final_html:
                final_html = final_html.split("```html")[1].split("```")[0]
            elif "```" in final_html:
                final_html = final_html.split("```")[1].split("```")[0]
            
            # Validate HTML content
            print("\n🔍 Validating HTML content...")
            validation_passed, issues = validate_html_content(final_html)
            
            if not validation_passed:
                print("⚠️ HTML validation failed, but saving anyway for review")
                
            output_path = "index.html"
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(final_html.strip())
            
            print(f"\n✅ Report generated successfully with second backup model (DeepSeek Official API): {output_path}")
            print("📊 Report includes 4 sections (Chinese news skipped to avoid content policy issues):")
            print("   1. 全球新闻 (Global News)")
            print("   2. 法律新闻 (Legal News)")
            print("   3. 健康与运动 (Health & Sports + Deep Analysis)")
            print("   4. 法律学术分析 (Legal Analysis & Law Review Articles)")
            
            # Send email with reports
            print("\n📧 Preparing to send email report...")
            email_body = f"""Daily News Briefing Report - {current_date} (DeepSeek Backup Model)

This email contains the daily news briefing reports generated by the AI News Agent using the backup model.

Report Summary:
- 4 major sections covered (Chinese news skipped)
- {len(saved_reports)} intermediate reports generated
- All reports attached as markdown files

Reports are also saved locally in: {reports_dir}

---
Generated by HomeNews AI Agent (Backup Model)
"""
            send_email_report(
                subject=f"Daily News Briefing - {current_date} (Backup Model)",
                body=email_body,
                attachments=saved_reports
            )
            
        except Exception as deepseek_error:
            print(f"⚠️ Second backup model also failed with error: {deepseek_error}")
            print("🔄 Retrying with third backup model: nvidia/llama-3.3-nemotron-super-49b-v1.5")
            
            # 使用第三备用模型重试 (nvidia/llama-3.3-nemotron-super-49b-v1.5)
            try:
                
                # 重新创建 agents，使用第三备用 LLM (包含所有5个板块)
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
                
                # Save intermediate reports
                print("\n📝 Saving intermediate reports (third backup model)...")
                try:
                    task_outputs = news_crew_backup.tasks
                    for i, task in enumerate(task_outputs):
                        if hasattr(task, 'output') and task.output:
                            task_name = f"backup3_task_{i+1}_{task.agent.role.replace(' ', '_').replace('/', '_')}.md"
                            content = str(task.output)
                            saved_file = save_markdown_report(content, task_name, reports_dir)
                            saved_reports.append(saved_file)
                except Exception as e:
                    print(f"⚠️ Could not save intermediate reports: {e}")
                
                final_html = str(result)
                
                # Log result for debugging
                print(f"\n📝 Raw result length: {len(final_html)} characters")
                
                # 清洗 Markdown 标记
                if "```html" in final_html:
                    final_html = final_html.split("```html")[1].split("```")[0]
                elif "```" in final_html:
                    final_html = final_html.split("```")[1].split("```")[0]
                
                # Validate HTML content
                print("\n🔍 Validating HTML content...")
                validation_passed, issues = validate_html_content(final_html)
                
                if not validation_passed:
                    print("⚠️ HTML validation failed, but saving anyway for review")
                    
                output_path = "index.html"
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(final_html.strip())
                
                print(f"\n✅ Report generated successfully with third backup model (nvidia/llama-3.3-nemotron-super-49b-v1.5): {output_path}")
                print("📊 Report includes 5 sections:")
                print("   1. 中文新闻 (Chinese-language News)")
                print("   2. 全球新闻 (Global News)")
                print("   3. 法律新闻 (Legal News)")
                print("   4. 健康与运动 (Health & Sports + Deep Analysis)")
                print("   5. 法律学术分析 (Legal Analysis & Law Review Articles)")
                
                # Send email with reports
                print("\n📧 Preparing to send email report...")
                email_body = f"""Daily News Briefing Report - {current_date} (Third Backup Model)

This email contains the daily news briefing reports generated by the AI News Agent using the third backup model.

Report Summary:
- 5 major sections covered
- {len(saved_reports)} intermediate reports generated
- All reports attached as markdown files

Reports are also saved locally in: {reports_dir}

---
Generated by HomeNews AI Agent (Third Backup Model)
"""
                send_email_report(
                    subject=f"Daily News Briefing - {current_date} (Third Backup)",
                    body=email_body,
                    attachments=saved_reports
                )
                
            except Exception as backup_error:
                print(f"❌ Critical Error: All three models failed.")
                print(f"Primary model error: {e}")
                print(f"Second backup model error: {deepseek_error}")
                print(f"Third backup model error: {backup_error}")
                sys.exit(1)

if __name__ == "__main__":
    run()
