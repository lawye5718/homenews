import os
from datetime import datetime
from crewai import Agent, Task, Crew, Process, LLM
from crewai_tools import ScrapeWebsiteTool, SerperDevTool

# 1. 配置 LLM
# 增加 timeout 到 600秒，因为深度分析和生成长HTML需要较长时间
deepseek_llm = LLM(
    model="deepseek/deepseek-chat", 
    base_url="https://api.deepseek.com",
    api_key=os.environ.get("DEEPSEEK_API_KEY"),
    temperature=0.6, #稍微降低温度以提高学术严谨性
    timeout=600 
)

# 2. 初始化工具
search_tool = SerperDevTool(n_results=15) # 增加搜索广度
scrape_tool = ScrapeWebsiteTool()

# 3. 定义智能体 (Agents)

# --- 中国情报官 ---
china_scout = Agent(
    role='Chief China Societal Analyst',
    goal='挖掘中国社会深层议题，拒绝表面热度',
    backstory="""
    你是一名具有社会学背景的资深媒体人。
    你的核心任务是【去伪存真】。
    1. 过滤：绝对忽略明星八卦、网络口水战、无实质内容的官方通稿。
    2. 聚焦：关注系统性问题（如人口结构、就业趋势）、司法公正（争议判决）、科技伦理。
    3. 深度：不仅看发生了什么，要看它反映了什么社会情绪。
    """,
    tools=[search_tool, scrape_tool],
    llm=deepseek_llm,
    verbose=True
)

# --- 全球情报官 ---
global_scout = Agent(
    role='International Geopolitics & Tech Analyst',
    goal='Curate Top 5 Global events via English Premier Sources',
    backstory="""
    You strictly adhere to English-language primary sources (Reuters, Bloomberg, NYT, Nature).
    Your Logic:
    1. If it's a tech breakthrough, is it a PR stunt or a fundamental shift? (Focus on the latter).
    2. If it's a conflict, what is the strategic implication?
    3. You MUST retain the original English terminology/Headlines to avoid translation loss.
    """,
    tools=[search_tool, scrape_tool],
    llm=deepseek_llm,
    verbose=True
)

# --- 法律情报官 (全球法治动态) ---
legal_scout = Agent(
    role='Global Legal News Curator',
    goal='Identify 5 landmark legal events (SCOTUS, EU CJEU, China SPC)',
    backstory="""
    Focus on "Hard Law" developments:
    1. Landmark Rulings: Supreme Court decisions that change precedent.
    2. Major Legislation: EU AI Act, GDPR, Antitrust laws.
    3. Strategic Litigation: Big Tech lawsuits, Sovereign disputes.
    """,
    tools=[search_tool, scrape_tool],
    llm=deepseek_llm,
    verbose=True
)

# --- 运动健康情报官 (循证医学) ---
health_sports_scout = Agent(
    role='Evidence-Based Health Researcher',
    goal='Find health/performance news backed by peer-reviewed studies',
    backstory="""
    You are allergic to pseudoscience. 
    Sources MUST be: The Lancet, JAMA, NEJM, Cell, Nature, or authoritative sports science journals.
    Focus on:
    1. Meta-analyses and Systematic Reviews (highest evidence).
    2. Randomized Controlled Trials (RCTs).
    3. Physiological mechanism breakthroughs.
    """,
    tools=[search_tool, scrape_tool],
    llm=deepseek_llm,
    verbose=True
)

# --- 法律学术分析师 (核心优化：学术深度) ---
legal_scholar = Agent(
    role='Comparative Law Scholar',
    goal='Conduct deep jurisprudential analysis on US-China legal frictions or trends',
    backstory="""
    You are a Professor of Comparative Law.
    
    Since full law review PDFs are often paywalled, you utilize:
    1. SSRN (Social Science Research Network) abstracts and working papers.
    2. High-level legal analysis blogs (Lawfare, SCOTUSblog, Just Security, Volokh Conspiracy).
    3. Open-access Law Review repositories.
    
    Methodology (IRAC):
    - Issue: What is the core legal conflict?
    - Rule: What statutes or precedents are involved?
    - Analysis: How do scholars interpret this? What are the opposing arguments?
    - Conclusion: What is the theoretical impact?
    """,
    tools=[search_tool, scrape_tool],
    llm=deepseek_llm,
    verbose=True
)

# --- 健康运动深度分析师 (核心优化：科学解释) ---
health_analyst = Agent(
    role='Senior Science Communicator',
    goal='Translate complex papers into actionable, scientifically accurate advice',
    backstory="""
    You bridge the gap between the lab and the living room.
    Structure your analysis:
    1. **The Study**: Sample size? Duration? Subjects (Mice or Humans)?
    2. **The Mechanism**: How does it work biologically?
    3. **Critical Assessment**: Is the effect size significant? Correlation vs Causation?
    4. **Application**: How should a professional athlete or regular person apply this?
    """,
    tools=[search_tool, scrape_tool],
    llm=deepseek_llm,
    verbose=True
)

# --- 深度研究员 (架构师) ---
researcher = Agent(
    role='Chief Editor & Architect',
    goal='Synthesize all inputs into a coherent, structured JSON-like Markdown report',
    backstory="""
    You are responsible for the structural integrity of the report.
    You ensure:
    1. No section is missing.
    2. The "Deep Analysis" sections are truly deep (not just summaries).
    3. Sources are cited.
    4. English headlines are preserved for Global news.
    """,
    tools=[scrape_tool],
    llm=deepseek_llm,
    verbose=True
)

# --- 主编 (UI/UX 专家) ---
editor = Agent(
    role='Senior Frontend Engineer (Tailwind Specialist)',
    goal='Generate a distinct, high-end HTML5 Daily Briefing',
    backstory="""
    You are an award-winning web designer.
    You DO NOT use basic HTML. You use **Tailwind CSS** via CDN.
    
    Design Language: "Digital Economist" or "Modern Bloomberg".
    - Font: 'Merriweather' for headings (Serif), 'Inter' for body (Sans).
    - Palette: Slate-900 (Text), Slate-50 (Background), Blue-700 (Accents), Amber-600 (Highlights).
    - Components:
      - **Hero Section**: Date and heavy typography.
      - **Bento Grid**: For top news stories.
      - **Analysis Cards**: With "Read Time" tags and author attribution.
      - **Details/Summary**: For collapsible deep dives.
    """,
    llm=deepseek_llm,
    verbose=True
)

# 4. 定义任务 (Tasks)

task_global = Task(
    description="""
    1. Search 'Breaking news Reuters', 'Tech analysis Stratechery', 'Geopolitics Foreign Affairs'.
    2. Select 5 events with global structural impact.
    3. RETURN FORMAT: English Headline + Chinese Contextual Summary.
    """,
    expected_output="5 Global news items (English Titles).",
    agent=global_scout
)

task_china = Task(
    description="""
    1. 挖掘今日中国社会最具"张力"的5个议题（政策vs民意、科技vs伦理）。
    2. 必须引用多方观点（官方叙事 vs 民间讨论）。
    """,
    expected_output="5个深度中国社会议题。",
    agent=china_scout
)

task_legal = Task(
    description="""
    Search for today's most significant court rulings or legislative drafts (US/EU/CN).
    Focus on IP, Antitrust, AI Regulation, and Constitutional rights.
    """,
    expected_output="5 Key Legal Updates.",
    agent=legal_scout
)

task_health_sports = Task(
    description="""
    Search reputable scientific sources (Nature, Cell, ACSM).
    Find 5 studies released in the last week regarding:
    - Longevity/Aging
    - Hypertrophy/Strength Training
    - Cognitive Health
    """,
    expected_output="5 Scientific Health/Sports Updates.",
    agent=health_sports_scout
)

task_health_analysis = Task(
    description="""
    Select the Top 2 most practical/impactful studies from the list.
    Write a 'Deep Dive' for each (500 words each).
    Structure:
    - **Hypothesis**: What did they test?
    - **Methodology Check**: (e.g., "Double-blind RCT with n=500")
    - **Results**: Specific data points (e.g., "15% increase in VO2Max").
    - **Takeaway**: Actionable advice.
    """,
    expected_output="2 Scientific Deep Dives.",
    agent=health_analyst,
    context=[task_health_sports]
)

task_legal_analysis = Task(
    description="""
    Select 1 major legal controversy (US or China).
    Find 2-3 academic or high-level professional commentaries (SSRN, Law Review Blogs).
    Write a 'Jurisprudential Analysis' (800 words):
    1. **Legal Question**: The core conflict.
    2. **Theoretical Framework**: How implies strict scrutiny vs rational basis? (or equivalent concepts).
    3. **Comparative Perspective**: How would this be handled in the other jurisdiction (CN vs US)?
    4. **Future Implication**: Prediction of legal trends.
    """,
    expected_output="1 Comprehensive Legal Theory Analysis.",
    agent=legal_scholar,
    context=[task_china, task_global, task_legal]
)

task_research = Task(
    description="""
    Compile ALL inputs.
    Ensure strict separation of "News Briefs" and "Deep Analysis".
    Add a "Key Takeaway" one-liner for every long section.
    """,
    expected_output="Master Report Markdown.",
    agent=researcher,
    context=[task_china, task_global, task_legal, task_health_sports, task_health_analysis, task_legal_analysis]
)

current_date = datetime.now().strftime("%Y-%m-%d")

task_publish = Task(
    description=f"""
    Generate the `index.html`.
    
    **Technical Constraints**:
    1. Include `<script src="https://cdn.tailwindcss.com"></script>` in `<head>`.
    2. Import fonts: `<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=Merriweather:wght@300;700&display=swap" rel="stylesheet">`.
    3. Use `font-serif` for titles, `font-sans` for body.
    
    **Layout Structure**:
    - **Header**: "Daily Insight Briefing" | {current_date} | Minimalist White on Dark Blue.
    - **Grid Area A (News Ticker)**: 3-column grid for China/Global/Legal Briefs. Small cards.
    - **Grid Area B (Deep Dives)**: Full width sections.
      - *Legal Analysis*: Styled like a Law Journal (Cream background, serif text).
      - *Health Science*: Styled like a Medical Paper (Clean white, blue accents, data points highlighted).
    - **Footer**: Copyright & Disclaimer.
    
    **Content**:
    - MUST include ALL content from the Context.
    - Use `<details class="cursor-pointer ...">` for expanding long texts on mobile.
    """,
    expected_output="Final HTML String.",
    agent=editor,
    context=[task_research]
)

# 5. 执行流程
def run():
    print("🚀 Starting Daily News Agent (Deep Analysis Edition)...")
    
    if not os.environ.get("DEEPSEEK_API_KEY"):
        raise ValueError("❌ DEEPSEEK_API_KEY is missing!")
    
    # 按照逻辑顺序执行
    news_crew = Crew(
        agents=[china_scout, global_scout, legal_scout, health_sports_scout, health_analyst, legal_scholar, researcher, editor],
        tasks=[task_china, task_global, task_legal, task_health_sports, task_health_analysis, task_legal_analysis, task_research, task_publish],
        process=Process.sequential,
        verbose=True
    )
    
    result = news_crew.kickoff()
    final_html = str(result)
    
    # 增强的清洗逻辑
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
