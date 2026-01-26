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

# --- 深度研究员 (汇总与核查) ---
researcher = Agent(
    role='Chief Editor & Fact Checker',
    goal='Compile a 3-section report (China, Global, Legal) with strict fact-checking',
    backstory="""
    You strictly organize the data from the scouts.
    Structure your report into three distinct sections:
    1. CHINA NEWS
    2. GLOBAL NEWS (Must retain English Headlines)
    3. LEGAL NEWS
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
    The layout MUST have 3 columns (or stacked sections on mobile) corresponding to the 3 news categories.
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

# 关键：强制要求包含所有部分
task_research = Task(
    description="""
    Aggregate the outputs from China Scout, Global Scout, and Legal Scout.
    Verify that ALL THREE SECTIONS exist.
    For Global News, ensure the original English title is preserved.
    Format the output as a structured Markdown report.
    """,
    expected_output="A complete Markdown report containing exactly 3 sections: China, Global, and Legal.",
    agent=researcher,
    context=[task_china, task_global, task_legal]
)

current_date = datetime.now().strftime("%Y-%m-%d")

task_publish = Task(
    description=f"""
    Convert the provided research report into a full `index.html` file.
    
    Design Requirements:
    - Use a clean, newspaper-style layout (like New York Times or Bloomberg).
    - Title: "Daily Briefing {current_date}"
    - Use CSS Grid to display 3 columns on desktop: [China] | [Global] | [Legal].
    - On mobile, stack them vertically.
    - Use clear typography (Serif for headings, Sans-serif for body).
    - **CRITICAL**: You MUST include the content from ALL 3 sections provided in the context. Do not summarize them away.
    - Output ONLY the raw HTML code, starting with <!DOCTYPE html>.
    """,
    expected_output="A complete index.html file string.",
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
        agents=[china_scout, global_scout, legal_scout, researcher, editor],
        tasks=[task_china, task_global, task_legal, task_research, task_publish],
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
