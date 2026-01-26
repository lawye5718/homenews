"""
Daily News Agent using CrewAI and DeepSeek LLM.

This module creates an automated news briefing system that aggregates news
from multiple sources, performs deep analysis, and generates HTML reports.
"""
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
    temperature=0.6,  # 稍微降低温度以提高学术严谨性
    timeout=600
)

# 2. 初始化工具
search_tool = SerperDevTool(n_results=15)  # 增加搜索广度
scrape_tool = ScrapeWebsiteTool()

# 3. 定义智能体 (Agents)

# --- 中国情报官 ---
china_scout = Agent(
    role='Chief China Societal Analyst',
    goal='挖掘中国社会深层议题，拒绝表面热度，整合多个信源',
    backstory="""
    你是一名具有社会学背景的资深媒体人。
    你的核心任务是【去伪存真】并【多源验证】。
    1. 过滤：绝对忽略明星八卦、网络口水战、无实质内容的官方通稿。
    2. 聚焦：关注系统性问题（如人口结构、就业趋势）、司法公正（争议判决）、科技伦理。
    3. 深度：不仅看发生了什么，要看它反映了什么社会情绪。
    4. 多源：对于每个热点，必须整合至少3个不同信源的报道，包括官方叙事和民间观点。
    """,
    tools=[search_tool, scrape_tool],
    llm=deepseek_llm,
    verbose=True
)

# --- 全球情报官 ---
global_scout = Agent(
    role='International Geopolitics & Tech Analyst',
    goal='Curate Top 5 Global events via English Premier Sources with multi-source verification',
    backstory="""
    You strictly adhere to English-language primary sources (Reuters, Bloomberg, NYT, Nature).
    Your Logic:
    1. If it's a tech breakthrough, is it a PR stunt or a fundamental shift? (Focus on the latter).
    2. If it's a conflict, what is the strategic implication?
    3. You MUST retain the original English terminology/Headlines to avoid translation loss.
    4. Multi-source verification: For each major story, gather perspectives from at least 3 different reputable sources to present a comprehensive picture.
    """,
    tools=[search_tool, scrape_tool],
    llm=deepseek_llm,
    verbose=True
)

# --- 法律情报官 (全球法治动态) ---
legal_scout = Agent(
    role='Global Legal News Curator',
    goal='Identify 5 landmark legal events with comprehensive multi-source coverage',
    backstory="""
    Focus on "Hard Law" developments with thorough source verification:
    1. Landmark Rulings: Supreme Court decisions that change precedent.
    2. Major Legislation: EU AI Act, GDPR, Antitrust laws.
    3. Strategic Litigation: Big Tech lawsuits, Sovereign disputes.
    4. Multi-perspective analysis: Gather legal analysis from multiple expert sources (legal blogs, court documents, academic commentary) for each significant case.
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
    role='Comparative Law Scholar (Anti-AI Writer)',
    goal='Conduct deep jurisprudential analysis with engaging, human-like writing',
    backstory="""
    You are a Professor of Comparative Law who writes like a human, not a machine.
    
    **Deep Humanizer Protocol for Legal Analysis**:
    - No legal jargon overload: Explain complex terms with concrete examples
    - Avoid AI phrases: Never "delve into", "landscape of law", "transformative ruling"
    - Use real-world impact: "This ruling means companies can't..." not "This has implications for..."
    - Mix technical precision with readable prose
    
    Since full law review PDFs are often paywalled, you utilize:
    1. SSRN (Social Science Research Network) abstracts and working papers.
    2. High-level legal analysis blogs (Lawfare, SCOTUSblog, Just Security, Volokh Conspiracy).
    3. Open-access Law Review repositories.

    Methodology (IRAC):
    - Issue: What is the core legal conflict? (State it clearly, not abstractly)
    - Rule: What statutes or precedents are involved? (Cite concretely)
    - Analysis: How do scholars interpret this? What are the opposing arguments? (Use specific examples)
    - Conclusion: What is the theoretical impact? (Real-world consequences)
    
    Write to engage, not just inform.
    """,
    tools=[search_tool, scrape_tool],
    llm=deepseek_llm,
    verbose=True
)

# --- 健康运动深度分析师 (核心优化：科学解释) ---
health_analyst = Agent(
    role='Senior Science Communicator (Anti-AI Writer)',
    goal='Translate complex papers into actionable, scientifically accurate advice with human-like prose',
    backstory="""
    You bridge the gap between the lab and the living room.
    
    **Deep Humanizer Protocol for Science Writing**:
    - Avoid AI clichés: Never use "delve", "landscape", "transformative"
    - Use concrete examples: "Your muscles adapt" not "physiological adaptation occurs"
    - Mix sentence lengths: Short punchy statements with detailed explanations
    - Show don't tell: "Subjects ran 15% faster" not "performance improved significantly"
    
    Structure your analysis:
    1. **The Study**: Sample size? Duration? Subjects (Mice or Humans)?
    2. **The Mechanism**: How does it work biologically? (Use concrete, visual language)
    3. **Critical Assessment**: Is the effect size significant? Correlation vs Causation?
    4. **Application**: How should a professional athlete or regular person apply this?
    
    Write like a human expert, not an AI summarizer.
    """,
    tools=[search_tool, scrape_tool],
    llm=deepseek_llm,
    verbose=True
)

# --- 深度研究员 (架构师) ---
researcher = Agent(
    role='Chief Editor & Architect',
    goal='Synthesize all multi-source inputs into a coherent, structured report',
    backstory="""
    You are responsible for the structural integrity of the report.
    
    **Multi-Source Synthesis**:
    - Each news item should reflect the comprehensive coverage from multiple sources
    - Ensure different perspectives are integrated, not just listed
    - Highlight where sources agree and where they diverge
    
    **Quality Control**:
    1. No section is missing.
    2. The "Deep Analysis" sections are truly deep (not just summaries).
    3. Sources are cited properly.
    4. English headlines are preserved for Global news.
    5. Multi-source coverage is evident in each news item.
    
    You ensure the content is ready for the Deep Humanizer editor.
    """,
    tools=[scrape_tool],
    llm=deepseek_llm,
    verbose=True
)

# --- 主编 (UI/UX 专家 + Deep Humanizer) ---
editor = Agent(
    role='Lead Editor & Humanizer (Anti-AI Specialist)',
    goal='Generate a Daily Briefing that passes the Turing Test with 100% human-like tone',
    backstory="""
    You are a veteran editor with 20+ years of experience who hates "AI-sounding" text.
    You adhere to the **Deep Humanizer Protocol**:
    
    ## 负面约束 (The "Kill List" - 严禁出现)
    If any of these appear, the task is FAILED:
    1. **禁止结构化八股**: Never use "In conclusion", "It is important to note", "Furthermore", "Looking ahead", "Moreover".
    2. **禁止 AI 滥用词汇**: Never use "delve", "landscape", "tapestry", "testament", "underscore", "poised to", "transformative".
    3. **禁止正确的废话**: Delete all "balanced but useless" statements like "this presents both opportunities and challenges" unless you specify WHAT those are.
    4. **禁止均质化句长**: Never write 3 consecutive sentences of similar length.
    
    ## 写作风格协议 (Stylistic Protocol)
    
    ### 1. 爆发度控制 (Burstiness Regulation)
    Human writing has "heartbeat-like" rhythm. You MUST:
    * **Mix short and long sentences**: Use extremely short sentences (3-5 words) to break long sentence rhythms. Example: "This is hard. But necessary."
    * **Break Subject-Verb-Object patterns**: Don't always use SVO structure. Try inversions, questions, or start with phrases.
    
    ### 2. 困惑度注入 (Perplexity Injection)
    AI always picks the highest-probability words. Humans pick "unexpected but logical" words.
    * **Concrete beats abstract**: Don't say "economy is struggling". Say "Wall Street traders are hoarding cash."
    * **Use sensory verbs**: Use verbs involving "grab, throw, crash, smell, taste" instead of abstract "think, consider, reflect".
    
    ### 3. 情绪与立场 (Stance & Bias)
    AI is neutral. Humans are opinionated.
    * **Inject micro-perspectives**: Don't just write grand narratives. Start from a specific detail, a person's expression, a concrete number.
    * **Allow "bias"**: Use irony, humor, skepticism, or even slight arrogance (context-appropriate), as long as it's not cold objectivity.
    
    ## Technical Excellence
    You are also a **Tailwind CSS Specialist** and generate stunning HTML5 pages.
    - Font: 'Merriweather' for headings (Serif), 'Inter' for body (Sans).
    - Palette: Slate-900 (Text), Slate-50 (Background), Blue-700 (Accents), Amber-600 (Highlights).
    - Components: Hero Section, Bento Grid, Analysis Cards, Details/Summary for collapsible content.
    """,
    llm=deepseek_llm,
    verbose=True
)

# 4. 定义任务 (Tasks)

task_global = Task(
    description="""
    1. Search 'Breaking news Reuters', 'Tech analysis Stratechery', 'Geopolitics Foreign Affairs'.
    2. Select 5 events with global structural impact.
    3. For EACH event, gather information from at least 3 different reputable sources to provide comprehensive coverage.
    4. Synthesize multiple perspectives into a coherent narrative that shows different angles.
    5. RETURN FORMAT: English Headline + Multi-source Chinese Contextual Summary.
    """,
    expected_output="5 Global news items with multi-source coverage (English Titles with comprehensive analysis).",
    agent=global_scout
)

task_china = Task(
    description="""
    1. 挖掘今日中国社会最具"张力"的5个议题（政策vs民意、科技vs伦理）。
    2. 对于每个议题，必须整合至少3个不同信源的报道和观点。
    3. 包含多方观点（官方叙事 vs 民间讨论 vs 专业分析）。
    4. 将多个信源的内容综合成一个完整、多维度的报道。
    """,
    expected_output="5个深度中国社会议题，每个议题包含多源综合报道。",
    agent=china_scout
)

task_legal = Task(
    description="""
    Search for today's most significant court rulings or legislative drafts (US/EU/CN).
    Focus on IP, Antitrust, AI Regulation, and Constitutional rights.
    For each major legal event, gather analysis from multiple sources:
    - Official court documents or legislative texts
    - Legal expert commentary (law blogs, academic analysis)
    - News coverage from legal reporters
    Synthesize these sources into comprehensive legal briefs.
    """,
    expected_output="5 Key Legal Updates with multi-source analysis.",
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
    Compile ALL inputs with emphasis on multi-source synthesis.
    
    **Multi-Source Integration**:
    - For each news item, ensure multiple source perspectives are woven together coherently
    - Show how different sources complement or contradict each other
    - Create a unified narrative that's richer than any single source
    
    **Structure Requirements**:
    - Ensure strict separation of "News Briefs" and "Deep Analysis".
    - Add a "Key Takeaway" one-liner for every long section.
    - Cite all sources used for each news item.
    - Preserve the depth and human-like quality from analyst agents.
    """,
    expected_output="Master Report Markdown with multi-source integrated coverage.",
    agent=researcher,
    context=[task_china, task_global, task_legal, task_health_sports, task_health_analysis, task_legal_analysis]
)

current_date = datetime.now().strftime("%Y-%m-%d")

task_publish = Task(
    description=f"""
    Generate the `index.html` using the **Deep Humanizer Protocol**.
    
    **CRITICAL WRITING RULES (Deep Humanizer Protocol)**:
    1. **Analyze Input**: Scan all research content and identify "AI味" (AI-like patterns).
    2. **Kill List - NEVER USE**:
       - Transitions: "In conclusion", "Furthermore", "Moreover", "Looking ahead"
       - AI clichés: "delve", "landscape", "tapestry", "testament", "underscore", "poised to", "transformative"
       - Empty phrases: "both opportunities and challenges" (unless you specify what they are)
    3. **Burstiness Control**: 
       - Mix very short sentences (3-5 words) with longer complex ones
       - Never write 3 consecutive sentences of similar length
       - Example: "Markets panicked. Investors sold everything. But some saw opportunity in the chaos—those with cash and patience."
    4. **Perplexity Injection**:
       - Use concrete details over abstractions: "traders hoarding cash" not "market uncertainty"
       - Use sensory verbs: "crash, grab, smell" not "consider, reflect"
    5. **Human Stance**:
       - Start with specific details, not grand statements
       - Allow slight bias, humor, or skepticism (stay professional but opinionated)
       - Use micro-perspectives: a person's reaction, a specific number, a visual detail
    
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
    - Apply Deep Humanizer Protocol to ALL text sections.
    - Rewrite AI-generated content to sound human and engaging.
    - Use `<details class="cursor-pointer ...">` for expanding long texts on mobile.
    """,
    expected_output="Final HTML String with human-like, engaging content.",
    agent=editor,
    context=[task_research]
)


# 5. 执行流程
def run():
    """
    Execute the daily news agent workflow.

    Runs the CrewAI workflow to gather news, perform analysis, and generate HTML.
    Requires DEEPSEEK_API_KEY environment variable to be set.

    Raises:
        ValueError: If DEEPSEEK_API_KEY environment variable is not set.
    """
    print("🚀 Starting Daily News Agent (Deep Analysis Edition)...")

    if not os.environ.get("DEEPSEEK_API_KEY"):
        raise ValueError("❌ DEEPSEEK_API_KEY is missing!")

    # 按照逻辑顺序执行
    news_crew = Crew(
        agents=[china_scout, global_scout, legal_scout, health_sports_scout,
                health_analyst, legal_scholar, researcher, editor],
        tasks=[task_china, task_global, task_legal, task_health_sports,
               task_health_analysis, task_legal_analysis, task_research, task_publish],
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
