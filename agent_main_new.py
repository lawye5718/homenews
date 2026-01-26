import os
import sys
from datetime import datetime
from crewai import Agent, Task, Crew, Process, LLM
from crewai_tools import ScrapeWebsiteTool, SerperDevTool

# --- 1. 配置 LLM (NVIDIA NIM) ---
nvidia_llm = LLM(
    model="meta/llama-3.1-405b-instruct",
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.environ.get("NVIDIA_API_KEY"),
    temperature=0.7,
    top_p=0.95,
    max_tokens=32000,
    stream=True,
    timeout=600
)

# 备用模型配置 (DeepSeek)
deepseek_llm = LLM(
    model="deepseek-chat",
    base_url="https://api.deepseek.com",
    api_key=os.environ.get("DEEPSEEK_API_KEY"),
    temperature=0.7,
    top_p=0.95,
    max_tokens=32000,
    stream=True,
    timeout=600
)

# 第三备用模型
backup_llm = LLM(
    model="nvidia/llama-3.3-nemotron-super-49b-v1.5",
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.environ.get("NVIDIA_API_KEY"),
    temperature=0.7,
    top_p=0.95,
    max_tokens=32000,
    stream=True,
    timeout=600
)

# --- 2. 初始化工具 ---
search_tool = SerperDevTool(n_results=15)
scrape_tool = ScrapeWebsiteTool()

# ==============================================================================
# Deep Humanizer Protocol (深层去伪协议)
# ==============================================================================
HUMANIZER_PROTOCOL = """
**Deep Humanizer Protocol**:
1. **禁止AI腔调**: 严禁使用 "delve", "landscape", "tapestry", "underscores", "poised to".
2. **高爆发度 (Burstiness)**: 混合极短句和长句。
3. **具象表达**: 多用动词，少用形容词。
4. **人类视角**: 允许适度的专业偏见或幽默。
"""

# --- 3. 定义智能体 (Agents) ---

china_scout = Agent(
    role='News Editor for Chinese Media',
    goal='Select 5 newsworthy stories from Chinese-language sources with real URLs and 1000+ word summaries',
    backstory=f"""
    Experienced news editor.
    Criteria: Substantive topics (tech, welfare, employment).
    Requirement: MUST include the original source URL for every story found.
    {HUMANIZER_PROTOCOL}
    """,
    tools=[search_tool, scrape_tool],
    llm=nvidia_llm,
    verbose=True
)

global_scout = Agent(
    role='International News Analyst',
    goal='Identify Top 5 Global events using English sources, preserving English headlines and URLs',
    backstory=f"""
    Focus on Tech and Geopolitics.
    Requirement: MUST retain original English Headlines and original source URLs.
    {HUMANIZER_PROTOCOL}
    """,
    tools=[search_tool, scrape_tool],
    llm=nvidia_llm,
    verbose=True
)

legal_scout = Agent(
    role='Global Legal News Curator',
    goal='Identify 5 landmark legal events with document URLs',
    backstory=f"""
    Focus on Hard Law (Rulings, Legislation).
    Requirement: MUST include direct links to court documents or official reports.
    {HUMANIZER_PROTOCOL}
    """,
    tools=[search_tool, scrape_tool],
    llm=nvidia_llm,
    verbose=True
)

health_sports_scout = Agent(
    role='Health & Sports Science Reporter',
    goal='Identify Top 5 health/sports science news from journals with URLs',
    backstory=f"""
    Focus on peer-reviewed research.
    Requirement: MUST include DOI links or journal URLs.
    {HUMANIZER_PROTOCOL}
    """,
    tools=[search_tool, scrape_tool],
    llm=nvidia_llm,
    verbose=True
)

health_analyst = Agent(
    role='Health Science Analyst',
    goal='Generate 5000+ word deep analysis reports for top 3 stories',
    backstory=f"""
    Expert science communicator.
    Create comprehensive analysis: Executive Summary, Methodology, Findings, Implications.
    {HUMANIZER_PROTOCOL}
    """,
    tools=[scrape_tool],
    llm=nvidia_llm,
    verbose=True
)

legal_scholar = Agent(
    role='Comparative Law Scholar',
    goal='Analyze law review articles with 5000+ word comprehensive analyses',
    backstory=f"""
    Comparative law expert.
    Analyze top US law review articles relevant to current topics.
    {HUMANIZER_PROTOCOL}
    """,
    tools=[search_tool, scrape_tool],
    llm=nvidia_llm,
    verbose=True
)

researcher = Agent(
    role='Chief Researcher & Architect',
    goal='Synthesize all inputs into a structured report, VERIFYING ALL URLs ARE PRESENT',
    backstory=f"""
    You are responsible for data integrity.
    You must ensure that every single news item passed to the Editor has a VALID, CLICKABLE URL.
    Do not summarize away the links. The Editor needs them for the HTML.
    {HUMANIZER_PROTOCOL}
    """,
    tools=[scrape_tool],
    llm=nvidia_llm,
    verbose=True
)

# 【重构】主编 - 专注于 NYT 风格和数据真实性
editor = Agent(
    role='Lead Editor (NYT Style & Frontend Dev)',
    goal='Generate a "New York Times" style HTML report. ENSURE ALL LINKS WORK.',
    backstory=f"""
    You are a meticulous frontend developer and editor inspired by The New York Times.
    
    **Core Philosophy**:
    1. **Data Integrity**: You NEVER create fake links (href="#"). You ONLY use the URLs provided by the researchers. If a URL is missing, you do not display a link button.
    2. **Design Aesthetic (NYT Style)**:
       - **White Background**: Clean, stark, professional (bg-white / bg-stone-50).
       - **Serif Headings**: Black, bold, serif fonts (Merriweather/Georgia) for authority.
       - **Sans Body**: Clean sans-serif (Inter/Helvetica) for readability.
       - **No Gradients**: Avoid cheap-looking gradients. Use solid colors and subtle borders.
       - **High Contrast**: Dark gray text on white/off-white background.
    
    {HUMANIZER_PROTOCOL}
    """,
    llm=nvidia_llm,
    verbose=True
)

# --- 4. 定义任务 (Tasks) ---

task_china = Task(
    description="""
    Search for 5 substantive Chinese news stories (Tech, Public Welfare).
    **CRITICAL**: You MUST collect the specific URL for each story.
    Output format: Title, Summary (1000+ words), Source Name, and **Source URL**.
    """,
    expected_output="5 news stories with valid URLs.",
    agent=china_scout
)

task_global = Task(
    description="""
    Search for 5 Global events (Tech, Geopolitics).
    **CRITICAL**: You MUST collect the specific URL for each story.
    Output format: English Headline, Chinese Summary (1000+ words), Source Name, and **Source URL**.
    """,
    expected_output="5 global stories with valid URLs.",
    agent=global_scout
)

task_legal = Task(
    description="""
    Search for 5 key legal updates.
    **CRITICAL**: You MUST collect the specific URL for each ruling/doc.
    Output format: Title, Analysis (1000+ words), Source Name, and **Source URL**.
    """,
    expected_output="5 legal updates with valid URLs.",
    agent=legal_scout
)

task_health_sports = Task(
    description="""
    Search for 5 health/sports science updates.
    **CRITICAL**: You MUST collect the specific URL for each paper/article.
    Output format: Title, Summary (1000+ words), Source Name, and **Source URL**.
    """,
    expected_output="5 health stories with valid URLs.",
    agent=health_sports_scout
)

task_health_analysis = Task(
    description="""
    Select top 3 health stories and write deep analysis (5000+ words each).
    Include specific data, methodology, and implications.
    **Preserve all citations and URLs.**
    """,
    expected_output="3 deep analysis reports with URLs.",
    agent=health_analyst,
    context=[task_health_sports]
)

task_legal_analysis = Task(
    description="""
    Select 3 relevant law review articles and write deep analysis (5000+ words each).
    **Preserve all citations and URLs.**
    """,
    expected_output="3 legal analysis reports with URLs.",
    agent=legal_scholar,
    context=[task_china, task_global, task_legal]
)

task_research = Task(
    description="""
    Compile ALL 5 sections into a Master Report.
    **VERIFICATION STEP**: Check that every single news item and analysis has its corresponding Source URL attached.
    If a URL is missing in the input, flag it clearly.
    Organize the content strictly into the 5 sections.
    """,
    expected_output="Master JSON/Markdown report containing all content AND all source URLs.",
    agent=researcher,
    context=[task_china, task_global, task_legal, task_health_sports, task_health_analysis, task_legal_analysis]
)

current_date = datetime.now().strftime("%Y-%m-%d")

# 【重构】发布任务 - NYT 风格 + 链接修复
task_publish = Task(
    description=f"""
    Generate the final `index.html` file based on the Research Report.
    
    **CRITICAL DATA RULES**:
    1. **NO FAKE LINKS**: You are STRICTLY FORBIDDEN from using `href="#"`. 
    2. **USE REAL URLS**: You must extract the URL provided in the context for each story and put it in the `href` attribute.
    3. **Fail-Safe**: If no URL is found in the context for a specific story, do NOT create a "Read More" button.
    
    **DESIGN SYSTEM (New York Times Style)**:
    1. **Library**: Use Tailwind CSS (`<script src="https://cdn.tailwindcss.com"></script>`).
    2. **Fonts**: 
       - Headlines: `font-family: 'Merriweather', serif;` (Import from Google Fonts)
       - Body: `font-family: 'Inter', sans-serif;`
    3. **Colors**:
       - Background: `bg-stone-50` (warm off-white) or `bg-white`.
       - Text: `text-stone-900` (almost black) for headings, `text-stone-700` for body.
       - Accents: Minimal use of `border-stone-300` for dividers. No bright gradients.
    4. **Layout**:
       - **Header**: Simple, centered, serif headline "Daily Insight". Date below it in italic serif. Thin border-bottom.
       - **Sections**: Clear section headers (e.g., "China News", "Global Briefing").
       - **Cards**: Clean layout. White background `bg-white`. Thin border `border border-stone-200`. No heavy shadows (`shadow-sm` at most).
       - **Typography**: High readability. Line height 1.6+.
    
    **INTERACTIVITY**:
    - **Collapsible**: Use `<details>` for the "Deep Analysis" (5000 words) sections to keep the page clean. 
    - The summary (1000 words) should be visible by default or easily toggleable.
    - **Hover**: Subtle hover effects (e.g., title turns dark red/blue on hover).
    
    **Output**: 
    - ONLY the raw HTML code (starting with `<!DOCTYPE html>`).
    """,
    expected_output="Final production-ready HTML string with real links and NYT design.",
    agent=editor,
    context=[task_research]
)

# --- 5. 执行流程 ---
def run():
    print("🚀 Starting Daily News Agent (NYT Style Edition)...")
    
    if not os.environ.get("NVIDIA_API_KEY"):
        print("❌ Error: NVIDIA_API_KEY not found.")
        sys.exit(1)
    
    try:
        news_crew = Crew(
            agents=[china_scout, global_scout, legal_scout, health_sports_scout, health_analyst, legal_scholar, researcher, editor],
            tasks=[task_china, task_global, task_legal, task_health_sports, task_health_analysis, task_legal_analysis, task_research, task_publish],
            process=Process.sequential,
            verbose=True
        )
        
        result = news_crew.kickoff()
        final_html = str(result)
        
        # 清洗 Markdown
        if "```html" in final_html:
            final_html = final_html.split("```html")[1].split("```")[0]
        elif "```" in final_html:
            final_html = final_html.split("```")[1].split("```")[0]
            
        output_path = "index.html"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(final_html.strip())
        
        print(f"✅ Report generated: {output_path}")
        
    except Exception as e:
        print(f"⚠️ Error: {e}")
        # 这里省略了备用模型的冗长代码，建议直接在主流程中修复
        sys.exit(1)

if __name__ == "__main__":
    run()
