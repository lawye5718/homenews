import os
from datetime import datetime
from crewai import Agent, Task, Crew, Process, LLM
from crewai_tools import ScrapeWebsiteTool, SerperDevTool

# 1. 配置 LLM
# 增加 timeout 防止长任务中断
deepseek_llm = LLM(
    model="deepseek/deepseek-chat", 
    base_url="https://api.deepseek.com",
    api_key=os.environ.get("DEEPSEEK_API_KEY"),
    temperature=0.7,
    timeout=120 
)

# 2. 初始化工具
search_tool = SerperDevTool(n_results=10) # 增加搜索结果数量以获取更多优质源
scrape_tool = ScrapeWebsiteTool()

# 3. 定义智能体 (Agents)

# --- 中国情报官 (去伪存真) ---
china_scout = Agent(
    role='中国社会深度观察员',
    goal='挖掘今日中国互联网最具公共价值的Top 5社会议题',
    backstory="""
    你是一名有新闻理想的资深编辑。你痛恨营销号制造的焦虑、明星八卦以及毫无信息量的官方通稿。
    你的选材标准：
    1. 【拒绝通稿】：如果新闻只是"某某会议召开"而无实质政策变动，丢弃。
    2. 【拒绝伪热点】：如果热搜是"某明星过生日"或"猫咪跳舞"，丢弃。
    3. 【关注民生】：关注就业、法律公义、重大政策调整、科技对普通人的影响。
    """,
    tools=[search_tool, scrape_tool],
    llm=deepseek_llm,
    verbose=True
)

# --- 全球情报官 (强制英文源) ---
global_scout = Agent(
    role='International News Analyst (Source: English Media)',
    goal='Identify Top 5 Global events using ONLY English sources (NYT, Reuters, Bloomberg)',
    backstory="""
    You are a rigorous international analyst. 
    CRITICAL RULE: You MUST search in English and read English sources.
    Do NOT use Chinese media summaries for international news because they are often delayed or biased.
    Focus on: US Politics, Global Economy, AI/Tech Breakthroughs (OpenAI, SpaceX), and Major Geopolitical Conflicts.
    Reject: TikTok challenges, minor celebrity gossip.
    """,
    tools=[search_tool, scrape_tool],
    llm=deepseek_llm,
    verbose=True
)

# --- 法律情报官 (判例导向) ---
legal_scout = Agent(
    role='Global Legal Researcher',
    goal='Find Top 5 significant legal cases or legislations globally',
    backstory="""
    Focus on:
    1. US Supreme Court (SCOTUS) rulings or major oral arguments.
    2. EU Tech Regulation (AI Act, GDPR penalties).
    3. China's Supreme Court guiding cases (not petty crimes).
    Provide the specific case name or statute name.
    """,
    tools=[search_tool, scrape_tool],
    llm=deepseek_llm,
    verbose=True
)

# --- 运动健康情报官 (科学导向) ---
health_sports_scout = Agent(
    role='Health & Sports Science Reporter',
    goal='Find Top 5 health and sports news with focus on scientific sources',
    backstory="""
    You are a science journalist specializing in health and sports.
    PRIORITY SOURCES:
    1. Scientific American (health, sports science, fitness)
    2. Nature (medical research, sports physiology)
    3. Science Magazine (health studies, exercise science)
    4. The Lancet, JAMA, NEJM (medical journals)
    5. Sports Medicine journals
    
    Focus on:
    - New medical research findings
    - Sports science breakthroughs
    - Exercise and fitness studies
    - Public health developments
    - Athletic performance research
    
    Reject: Celebrity fitness routines, weight loss fads, unscientific health tips.
    Always cite the original research or scientific source.
    """,
    tools=[search_tool, scrape_tool],
    llm=deepseek_llm,
    verbose=True
)

# --- 法律学术分析师 (法学院期刊研究) ---
legal_scholar = Agent(
    role='Law Review Article Analyst',
    goal='Identify key legal points from US-China hot topics and find relevant law review articles',
    backstory="""
    You are a legal scholar with expertise in comparative law.
    
    Your task:
    1. Analyze current US and China hot topics to identify key legal issues
    2. Search for law review articles from top 10 US law schools:
       - Yale Law Journal
       - Harvard Law Review
       - Stanford Law Review
       - Columbia Law Review
       - University of Chicago Law Review
       - NYU Law Review
       - University of Pennsylvania Law Review
       - Michigan Law Review
       - Virginia Law Review
       - Berkeley Law Review
    
    3. Find the 3 most relevant articles related to the identified legal issues
    4. For each article, provide:
       - Article title and author
       - Publication and year
       - Key legal arguments
       - Relevance to current hot topics
    
    Use academic databases and law school journal websites.
    """,
    tools=[search_tool, scrape_tool],
    llm=deepseek_llm,
    verbose=True
)

# --- 健康运动深度分析师 ---
health_analyst = Agent(
    role='Health & Sports Deep Analysis Specialist',
    goal='Provide in-depth analysis of top 3 health/sports news',
    backstory="""
    You are a science writer who excels at explaining complex research in simple terms.
    
    For each of the top 3 health/sports news items:
    1. Explain the scientific background and methodology
    2. Discuss the implications for public health or athletic performance
    3. Provide context from related research
    4. Explain practical applications
    5. Note any limitations or controversies
    
    Write in an accessible, engaging style that makes science understandable.
    """,
    tools=[search_tool, scrape_tool],
    llm=deepseek_llm,
    verbose=True
)

# --- 深度研究员 (汇总与核查) ---
researcher = Agent(
    role='Chief Editor & Fact Checker',
    goal='Compile a 5-section report (China, Global, Legal, Health/Sports, Legal Analysis) with strict fact-checking',
    backstory="""
    You strictly organize the data from the scouts.
    Structure your report into five distinct sections:
    1. CHINA NEWS
    2. GLOBAL NEWS (Must retain English Headlines)
    3. LEGAL NEWS
    4. HEALTH & SPORTS NEWS
    5. LEGAL ANALYSIS & LAW REVIEW ARTICLES
    If any section is missing, you must state "No significant news found" instead of omitting the section.
    """,
    tools=[scrape_tool], # 允许它在必要时自己再查一下原文
    llm=deepseek_llm,
    verbose=True
)

# --- 主编 (HTML 生成) ---
editor = Agent(
    role='HTML Frontend Developer',
    goal='Generate a responsive, modern HTML5 Daily News page',
    backstory="""
    You are an expert in Tailwind CSS and modern web design. 
    You will receive a text report and must convert it into a beautiful single-page HTML file.
    The layout MUST have 5 sections (or stacked sections on mobile) corresponding to the 5 news categories:
    1. China News
    2. Global News
    3. Legal News
    4. Health & Sports News
    5. Legal Analysis & Law Review Articles
    
    Use a grid layout for desktop and stack vertically on mobile.
    """,
    llm=deepseek_llm,
    verbose=True
)

# 4. 定义任务 (Tasks)

# 优化搜索词，强制英文
task_global = Task(
    description="""
    1. Search for 'Top global news today', 'Breaking news Reuters', 'Tech news Bloomberg'.
    2. Search for 'Trending on X today world news'.
    3. Select 5 most important events. 
    4. OUTPUT MUST BE IN ENGLISH for the titles, followed by a Chinese summary.
    """,
    expected_output="A list of 5 global news items with English Titles and Origin URLs.",
    agent=global_scout
)

task_china = Task(
    description="""
    1. 搜索"今日中国社会热点"、"知乎热榜 社会议题"、"财新网 热门"。
    2. 严格过滤：剔除所有娱乐明星八卦、无实质内容的会议通稿。
    3. 挑选5个具有讨论价值的真问题（如：就业、新规、争议性判决）。
    """,
    expected_output="5个经过筛选的高质量中国新闻，包含来源链接。",
    agent=china_scout
)

task_legal = Task(
    description="""
    1. Search for 'Supreme Court opinions today', 'EU AI Act latest', 'Major corporate lawsuit 2026'.
    2. Find 5 key legal updates.
    """,
    expected_output="5 legal news items with case names and legal implications.",
    agent=legal_scout
)

task_health_sports = Task(
    description="""
    1. Search for health and sports news from scientific sources:
       - 'Scientific American health news'
       - 'Nature medicine latest research'
       - 'Science magazine sports physiology'
       - 'Latest medical research JAMA Lancet'
    2. Focus on peer-reviewed research and scientific findings
    3. Select 5 most significant health/sports science news items
    4. Include source links and research citations
    """,
    expected_output="5 health and sports science news items with scientific sources and links.",
    agent=health_sports_scout
)

task_health_analysis = Task(
    description="""
    From the health/sports news collected, select the TOP 3 most impactful stories.
    For each of these 3 stories, write a detailed analysis report that includes:
    1. Background: What is the scientific context?
    2. Methods: How was the research conducted (if applicable)?
    3. Findings: What are the key discoveries or developments?
    4. Implications: What does this mean for public health, sports, or fitness?
    5. Practical Applications: How can people use this information?
    6. Limitations: What are the caveats or areas for further research?
    
    Write in clear, accessible language suitable for educated general readers.
    Each analysis should be 300-500 words.
    """,
    expected_output="3 in-depth analysis reports on the top health/sports news, each 300-500 words.",
    agent=health_analyst,
    context=[task_health_sports]
)

task_legal_analysis = Task(
    description="""
    Phase 1: Identify Key Legal Issues
    - Analyze the current US and China hot topics from the news
    - Identify 3-5 key legal issues or questions raised by these topics
    
    Phase 2: Search Law Review Articles
    - Search for recent law review articles from top 10 US law schools addressing these issues:
      * Use search terms like: "[legal issue] site:law.yale.edu/ylj"
      * Search: Harvard Law Review, Stanford Law Review, Columbia Law Review, etc.
    
    Phase 3: Select Top 3 Articles
    - Choose the 3 most relevant and recent articles
    - For each article provide:
      * Full citation (title, author, journal, year)
      * Link to the article
      * Brief summary of the main argument
      
    Phase 4: Deep Analysis
    For each of the 3 selected articles, write a comprehensive report:
    1. Article Overview: Summarize the article's thesis and main points (200 words)
    2. Legal Framework: Explain the legal doctrines and precedents discussed (150 words)
    3. Key Arguments: Break down the author's main arguments in simple terms (200 words)
    4. Connection to Hot Topics: How does this article relate to current US-China issues? (150 words)
    5. Practical Implications: What are the real-world legal implications? (100 words)
    
    Each article analysis should be 800-1000 words total.
    Write in clear language that makes complex legal concepts accessible.
    """,
    expected_output="3 comprehensive law review article analyses, each 800-1000 words, with full citations and connections to current US-China topics.",
    agent=legal_scholar,
    context=[task_china, task_global, task_legal]
)

# 关键：强制要求包含所有部分
task_research = Task(
    description="""
    Aggregate the outputs from all scouts and analysts:
    1. China Scout
    2. Global Scout  
    3. Legal Scout
    4. Health & Sports Scout (with deep analysis)
    5. Legal Scholar (with law review analysis)
    
    Verify that ALL FIVE SECTIONS exist.
    For Global News, ensure the original English title is preserved.
    Format the output as a structured Markdown report with clear section headers.
    """,
    expected_output="A complete Markdown report containing exactly 5 sections: China, Global, Legal, Health & Sports (with deep analysis), and Legal Analysis & Law Review Articles.",
    agent=researcher,
    context=[task_china, task_global, task_legal, task_health_sports, task_health_analysis, task_legal_analysis]
)

current_date = datetime.now().strftime("%Y-%m-%d")

task_publish = Task(
    description=f"""
    Convert the provided research report into a full `index.html` file.
    
    Design Requirements:
    - Use a clean, newspaper-style layout (like New York Times or Bloomberg).
    - Title: "Daily Briefing {current_date}"
    - Create a responsive layout with 5 main sections:
      1. China News
      2. Global News  
      3. Legal News
      4. Health & Sports News (with in-depth analysis reports)
      5. Legal Analysis & Law Review Articles
    - On desktop: Use CSS Grid with 2 columns for China/Global, then full-width sections for others
    - On tablet/mobile: Stack all sections vertically
    - Use clear typography (Serif for headings, Sans-serif for body).
    - For the Health & Sports section, clearly distinguish the news items from the deep analysis reports
    - For the Legal Analysis section, format each law review article analysis as a distinct card or article
    - Add collapsible sections for long analysis content to improve readability
    - **CRITICAL**: You MUST include the content from ALL 5 sections provided in the context. Do not summarize them away.
    - Output ONLY the raw HTML code, starting with <!DOCTYPE html>.
    """,
    expected_output="A complete index.html file string with all 5 sections properly formatted.",
    agent=editor,
    context=[task_research]
)

# 5. 执行流程
def run():
    print("🚀 Starting Daily News Agent...")
    
    # 检查 API Key
    if not os.environ.get("DEEPSEEK_API_KEY"):
        raise ValueError("❌ DEEPSEEK_API_KEY is missing!")
    
    news_crew = Crew(
        agents=[china_scout, global_scout, legal_scout, health_sports_scout, health_analyst, legal_scholar, researcher, editor],
        tasks=[task_china, task_global, task_legal, task_health_sports, task_health_analysis, task_legal_analysis, task_research, task_publish],
        process=Process.sequential,
        verbose=True
    )
    
    result = news_crew.kickoff()
    final_html = str(result)
    
    # 清洗 Markdown 代码块标记（如果 LLM 为了格式好看加了 ```html ... ```）
    if "```html" in final_html:
        final_html = final_html.split("```html")[1].split("```")[0]
    elif "```" in final_html:
        final_html = final_html.split("```")[1].split("```")[0]
        
    output_path = "index.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(final_html.strip())
    
    print(f"✅ Report generated successfully: {output_path}")

if __name__ == "__main__":
    run()
