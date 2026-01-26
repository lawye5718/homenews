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

# --- 3. 定义智能体 (Agents) ---

# 【中国情报官】 - Prompt 优化：去敏感化，避免触发 API 拦截
china_scout = Agent(
    role='资深社会观察编辑',
    goal='筛选今日中国互联网最具讨论价值的Top 5社会热点',
    backstory="""
    你是一名拥有十年经验的社会版面主编。
    你的选材标准非常严格，致力于【去伪存真】：
    1. 剔除无效信息：过滤掉纯粹的明星娱乐八卦、无实质内容的公关通稿。
    2. 关注核心议题：聚焦于就业环境、教育现状、科技发展、民生福祉等与普通人息息相关的议题。
    3. 深度视角：不只看热搜排名，要看话题背后的社会意义。
    注意：在汇报时请保持客观、中立的媒体语调，避免使用激进或引发争议的敏感词汇，以免触发内容过滤。
    """,
    tools=[search_tool, scrape_tool],
    llm=deepseek_llm,
    verbose=True
)

# 【全球情报官】 - 强制英文源
global_scout = Agent(
    role='International News Analyst (English Sources)',
    goal='Identify Top 5 Global events using ONLY English primary sources',
    backstory="""
    You strictly adhere to English-language primary sources (Reuters, Bloomberg, NYT, Nature).
    Your Logic:
    1. Tech: Focus on fundamental breakthroughs (AI, Space), not PR stunts.
    2. Geopolitics: Focus on strategic implications and factual developments.
    3. CRITICAL: You MUST retain the original English Headlines to avoid translation loss.
    """,
    tools=[search_tool, scrape_tool],
    llm=deepseek_llm,
    verbose=True
)

# 【法律情报官】
legal_scout = Agent(
    role='Global Legal News Curator',
    goal='Identify 5 landmark legal events (SCOTUS, EU CJEU, China SPC)',
    backstory="""
    Focus on "Hard Law" developments:
    1. Landmark Rulings: Supreme Court decisions that change precedent.
    2. Major Legislation: EU AI Act, GDPR, Antitrust laws.
    3. Corporate Litigation: Significant Big Tech lawsuits.
    """,
    tools=[search_tool, scrape_tool],
    llm=deepseek_llm,
    verbose=True
)

# 【深度研究员】 - 架构师
researcher = Agent(
    role='Chief Researcher & Architect',
    goal='Synthesize all inputs into a cohesive, structured report',
    backstory="""
    You are responsible for the structural integrity of the report.
    You ensure:
    1. No section is missing (China, Global, Legal).
    2. Data is accurate and sources are cited.
    3. English headlines are preserved for Global news.
    """,
    tools=[scrape_tool],
    llm=deepseek_llm,
    verbose=True
)

# 【主编】 - Humanizer (去 AI 味 & UI 设计)
editor = Agent(
    role='Lead Editor & Humanizer (Anti-AI Style)',
    goal='Generate a Daily Briefing that sounds 100% Human and looks stunning',
    backstory="""
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
       - Layout: Modern Bento Grid style. Dark/Professional theme.
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
    """,
    expected_output="5个经过筛选的高质量中国新闻，包含来源链接。",
    agent=china_scout
)

task_global = Task(
    description="""
    1. Search 'Breaking news Reuters', 'Tech analysis Stratechery', 'Geopolitics Foreign Affairs'.
    2. Select 5 events with global structural impact.
    3. RETURN FORMAT: English Headline + Chinese Contextual Summary.
    """,
    expected_output="5 Global news items with English Titles.",
    agent=global_scout
)

task_legal = Task(
    description="""
    Search for today's most significant court rulings or legislative drafts (US/EU/CN).
    Focus on IP, Antitrust, AI Regulation.
    """,
    expected_output="5 Key Legal Updates.",
    agent=legal_scout
)

task_research = Task(
    description="""
    Compile ALL inputs (China, Global, Legal).
    Verify that ALL THREE SECTIONS exist.
    Ensure strict separation of content.
    Add a "Key Takeaway" one-liner for every major news item.
    """,
    expected_output="Master Report Markdown.",
    agent=researcher,
    context=[task_china, task_global, task_legal]
)

current_date = datetime.now().strftime("%Y-%m-%d")

task_publish = Task(
    description=f"""
    Generate the final `index.html` file based on the Research Report.
    
    **Technical Requirements**:
    1. Include `<script src="https://cdn.tailwindcss.com"></script>` in `<head>`.
    2. Import fonts: Google Fonts (Inter, Merriweather).
    3. Use `font-serif` for titles, `font-sans` for body.
    
    **Design Language**:
    - **Header**: "Daily Insight" | {current_date} | Minimalist.
    - **Layout**: 
      - Use a **CSS Grid** (Bento Box style) for the news cards.
      - **Global News**: Must display the **English Headline** prominently.
      - **Tags**: Use small pill-shaped tags for categories (e.g., "Tech", "Law", "Society").
    - **Tone Check**: Ensure the summary text sounds human-written (punchy, avoiding AI clichés).
    
    **Output**: 
    - ONLY the raw HTML code, starting with `<!DOCTYPE html>`.
    """,
    expected_output="Final HTML String.",
    agent=editor,
    context=[task_research]
)

# --- 5. 执行流程 ---
def run():
    print("🚀 Starting Daily News Agent...")
    
    if not os.environ.get("DEEPSEEK_API_KEY"):
        print("❌ Error: DEEPSEEK_API_KEY not found in environment variables.")
        sys.exit(1)
    
    news_crew = Crew(
        agents=[china_scout, global_scout, legal_scout, researcher, editor],
        tasks=[task_china, task_global, task_legal, task_research, task_publish],
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
        
    except Exception as e:
        print(f"❌ Critical Error during execution: {e}")
        # 如果是 Content Risk，提示用户调整 Prompt
        if "Content Exists Risk" in str(e):
            print("⚠️ Suggestion: The system prompt might contain sensitive keywords. Try softening the language in 'china_scout'.")
        sys.exit(1)

if __name__ == "__main__":
    run()
