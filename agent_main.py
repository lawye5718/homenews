# agent_main.py
import os
from datetime import datetime
from crewai import Agent, Task, Crew, Process
from crewai_tools import SerperDevTool, ScrapeWebsiteTool
from langchain_openai import ChatOpenAI

# 1. 配置 LLM (DeepSeek)
deepseek_llm = ChatOpenAI(
    model="deepseek-chat", 
    openai_api_key=os.environ.get("DEEPSEEK_API_KEY"),
    openai_api_base="https://api.deepseek.com",
    temperature=0.7
)

# 2. 初始化工具
search_tool = SerperDevTool(api_key=os.environ.get("SERPER_API_KEY"))
scrape_tool = ScrapeWebsiteTool()

# 3. 定义智能体 (Agents)
# 中国情报官
china_scout = Agent(
    role='中国社交媒体趋势分析师',
    goal='捕捉中国互联网Top 5热点新闻',
    backstory="你专注于微博、知乎、百度的社会热点，寻找最具争议和讨论价值的话题。",
    tools=[search_tool, scrape_tool],
    llm=deepseek_llm,
    verbose=True
)

# 全球情报官
global_scout = Agent(
    role='全球趋势分析师',
    goal='捕捉X(Twitter)和Google Trends的Top 5国际热点',
    backstory="你专注于英语舆论场，寻找具有跨国影响力的科技、政治或社会话题。",
    tools=[search_tool, scrape_tool],
    llm=deepseek_llm,
    verbose=True
)

# 深度研究员
researcher = Agent(
    role='资深调查记者',
    goal='对新闻进行事实核查(Fact Check)和背景深挖',
    backstory="你严谨客观，必定交叉验证信息源，并能挖掘事件背后的法律或历史背景。",
    tools=[search_tool, scrape_tool],
    llm=deepseek_llm,
    verbose=True
)

# 主编
editor = Agent(
    role='数字新闻主编',
    goal='生成 HTML 单页报告',
    backstory="你擅长HTML/CSS，能生成适配移动端的双栏布局新闻网页。",
    llm=deepseek_llm,
    verbose=True
)

# 4. 定义任务 (Tasks)
task_china = Task(
    description="搜索并列出今日中国互联网5大热点（含标题、来源、热度）。",
    expected_output="5个中国热点列表",
    agent=china_scout
)

task_global = Task(
    description="搜索并列出今日全球(Twitter/Google)5大热点。",
    expected_output="5个全球热点列表",
    agent=global_scout
)

task_research = Task(
    description="""
    对上述10个热点进行深度研究：
    1. Fact Check (核实真伪)。
    2. 提供背景上下文。
    3. 保留原始链接。
    按【中国】和【全球】分类撰写。
    """,
    expected_output="一份包含深度分析和链接的研究简报",
    agent=researcher,
    context=[task_china, task_global]
)

current_date = datetime.now().strftime("%Y-%m-%d")
task_publish = Task(
    description=f"""
    将研究简报转换为 index.html。
    要求：
    - 标题: Daily Briefing {current_date}
    - 布局: CSS Grid 双栏 (左边China, 右边Global)
    - 交互: 使用 <details> 标签折叠长文，默认只显示摘要。
    - 仅输出 HTML 代码，不要 Markdown 标记。
    """,
    expected_output="完整的 index.html 文件内容",
    agent=editor,
    context=[task_research]
)

# 5. 执行
def run():
    news_crew = Crew(
        agents=[china_scout, global_scout, researcher, editor],
        tasks=[task_china, task_global, task_research, task_publish],
        process=Process.sequential,
        verbose=True
    )
    result = news_crew.kickoff()
    
    # 清洗并保存
    final_html = str(result)
    if "```html" in final_html:
        final_html = final_html.replace("```html", "").replace("```", "")
    
    # 写入根目录
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(final_html)

if __name__ == "__main__":
    run()
