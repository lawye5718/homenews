# agent_main.py
import os
import sys
from datetime import datetime
from crewai import Agent, Task, Crew, Process, LLM
from crewai_tools import ScrapeWebsiteTool

# 尝试多种导入方式来解决不同版本 CrewAI 的 SerperDevTool 兼容性问题
try:
    from crewai_tools import SerperDevTool
except ImportError:
    try:
        from crewai_tools.tools.serper_dev_tool import SerperDevTool
    except ImportError:
        # 模拟类，防止代码直接崩溃，提示用户配置环境
        class SerperDevTool:
            def __init__(self, api_key=None, n_results=10, country="us"):
                self.api_key = api_key
                self.n_results = n_results
                self.country = country
                print("⚠️ SerperDevTool not available. Using mock class.")
            
            def run(self, query):
                return f"Mock result for: {query}"

# 1. 配置 LLM (DeepSeek)
# 确保 DEEPSEEK_API_KEY 已在环境变量中设置
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
if not DEEPSEEK_API_KEY:
    raise ValueError("❌ DEEPSEEK_API_KEY environment variable is required!")

deepseek_llm = LLM(
    model="deepseek/deepseek-chat", 
    base_url="https://api.deepseek.com",
    api_key=DEEPSEEK_API_KEY,
    temperature=0.7 
)

# 2. 初始化工具
# 针对全球新闻，我们希望搜索结果偏向国际/美国（serper 支持 gl 参数，但在 wrapper 中通常自动处理或需在 query 中指定）
SERPER_API_KEY = os.environ.get("SERPER_API_KEY")
if not SERPER_API_KEY:
    print("⚠️ SERPER_API_KEY not set. Search functionality will be limited.")
    search_tool = None
else:
    try:
        # 默认搜索工具
        search_tool = SerperDevTool(api_key=SERPER_API_KEY)
    except Exception as e:
        print(f"⚠️ Error initializing SerperDevTool: {e}")
        search_tool = None

scrape_tool = ScrapeWebsiteTool()

# 3. 定义智能体 (Agents)

# 中国情报官 - 优化：去除大路货和通稿
china_scout = Agent(
    role='资深中国社会观察员',
    goal='挖掘中国互联网上具有真实讨论度、争议性或深度的Top 5社会热点',
    backstory="""
    你专注于微博、知乎、微信公众号等平台的深度讨论。
    你的核心原则是【去伪存真】：
    1. 严格过滤掉官方通稿、纯粹的娱乐明星八卦、以及营销号制造的虚假社会新闻。
    2. 寻找那些引发公众真实共鸣、涉及民生、法律边界或社会伦理的议题。
    3. 只有当娱乐新闻涉及重大法律或社会风向变动时才收录。
    """,
    tools=[tool for tool in [search_tool, scrape_tool] if tool is not None],
    llm=deepseek_llm,
    verbose=True
)

# 全球情报官 - 优化：强制英文信源，拒绝中文转述
global_scout = Agent(
    role='国际时政分析师 (International Affairs Analyst)',
    goal='追踪X(Twitter)、New York Times、Reuters等英文媒体上的Top 5全球核心事件',
    backstory="""
    你是一名不仅关注热度，更关注新闻价值的国际分析师。
    你的核心原则是【英文源头优先】：
    1. 必须使用英文进行搜索，直接从 NYTimes, BBC, Reuters, Bloomberg, X.com 获取信息。
    2. 绝对不要依赖中文媒体对国际新闻的转译或报道。
    3. 忽略Tiktok风格的无脑挑战或纯粹的网红八卦，关注政治、科技（AI）、经济和重大社会变革。
    4. 重点关注美国、欧洲及全球性议题。
    """,
    tools=[tool for tool in [search_tool, scrape_tool] if tool is not None],
    llm=deepseek_llm,
    verbose=True
)

# 法律新闻情报官 - 优化：关联英文判例
legal_scout = Agent(
    role='高阶法律研究员',
    goal='捕捉具有判例价值的全球Top 5法律新闻',
    backstory="""
    你专注于美国最高法院(SCOTUS)、欧盟法院及中国最高法的指导性案例。
    你的核心原则是【专业性】：
    1. 对于美国/欧洲案件，必须查找其原始英文案名和判决摘要。
    2. 关注科技监管（如AI立法、反垄断）、宪法权利及重大刑事案件。
    3. 避免琐碎的治安案件，只收录可能改变法律适用或具有里程碑意义的事件。
    """,
    tools=[tool for tool in [search_tool, scrape_tool] if tool is not None],
    llm=deepseek_llm,
    verbose=True
)

# 深度研究员 - 优化：事实核查与跨语种对比
researcher = Agent(
    role='首席调查记者',
    goal='对新闻进行严苛的事实核查(Fact Check)和深度背景关联',
    backstory="""
    你具有极高的新闻洁癖，痛恨假新闻和断章取义。
    1. 必须验证信源的可靠性。
    2. 尤其对于"网传"、"疑似"类消息保持高度警惕，必须找到权威出处。
    3. 在分析国际新闻时，直接引用英文原文的核心观点，不要自行翻译成可能有歧义的中文。
    """,
    tools=[tool for tool in [search_tool, scrape_tool] if tool is not None],
    llm=deepseek_llm,
    verbose=True
)

# 主编
editor = Agent(
    role='数字新闻主编',
    goal='生成结构化、排版精美的 HTML 单页日报',
    backstory="你擅长HTML5/CSS3，能生成适配移动端的现代化响应式网页，设计风格追求Bloomberg或端传媒的极简专业感。",
    llm=deepseek_llm,
    verbose=True
)

# 4. 定义任务 (Tasks)

# 针对中国热点任务的优化
task_china = Task(
    description="""
    1. 搜索今日中国互联网最具讨论价值的5个社会议题。
    2. 过滤规则：
       - 排除：某某明星过生日、某某剧开播、无实质内容的官方口号、明显的营销号编造故事。
       - 包含：政策变动对民生的影响、引发广泛伦理争议的社会案件、科技圈重大动态。
    3. 输出：5个热点，包含标题、核心冲突点、来源。
    """,
    expected_output="5个经过筛选的高质量中国社会热点列表",
    agent=china_scout
)

# 针对全球热点任务的优化
task_global = Task(
    description="""
    1. 使用英文关键词搜索今日全球头条 (Search queries must be in English, e.g., 'top us news today', 'global tech trends', 'breaking news nytimes').
    2. 重点关注来源：The New York Times, Reuters, Bloomberg, X (High engagement from credible users).
    3. 过滤规则：
       - 严禁使用中文搜索国际新闻。
       - 排除：纯粹的娱乐花边、未经验证的阴谋论。
    4. 重点领域：US Politics, Artificial Intelligence, Global Economy, Major Conflicts.
    5. 输出：5个全球热点，保留英文原标题，附带中文简述。
    """,
    expected_output="5个基于英文信源的全球重大新闻列表",
    agent=global_scout
)

# 针对法律热点任务的优化
task_legal = Task(
    description="""
    1. 搜索今日全球法律界关注的5大事件。
    2. 重点关注：
       - 美国最高法院 (SCOTUS) 最新裁决或口头辩论 (Search in English)。
       - 欧盟关于AI或科技巨头的最新监管处罚。
       - 中国最高法/最高检发布的指导性案例或新规。
    3. 必须提供：案件名称/法规名称、核心法律争议点、后续影响。
    """,
    expected_output="5个具有法学研究价值的新闻列表",
    agent=legal_scout
)

task_research = Task(
    description="""
    对上述15个热点进行深度核查与撰写：
    1. **信源隔离**：全球/法律新闻必须引用英文原始链接 (Origin URL)，不要引用国内搬运工的链接。
    2. **深度分析**：
       - 【中国板块】：分析舆论背后的社会心理或法律缺失。
       - 【全球板块】：引用 NYTimes/Reuters 的核心评论观点（保留一句英文金句并翻译）。
       - 【法律板块】：简述案件对相关领域的判例法意义。
    3. **格式要求**：
       - 必须包含 "Fact Check" 字段：标记为【已核实】、【争议中】或【待查证】。
    """,
    expected_output="一份包含深度分析、原始英文链接和事实核查标记的研究简报",
    agent=researcher,
    context=[task_china, task_global, task_legal]
)

current_date = datetime.now().strftime("%Y-%m-%d")
task_publish = Task(
    description=f"""
    将研究简报转换为 index.html。
    要求：
    - 标题: Daily Briefing {current_date}
    - 布局: CSS Grid 三栏布局 (China / Global / Legal)
    - 风格: 
      * 模仿 Bloomberg 或 New York Times 的专业衬线体风格。
      * 配色：黑白灰为主，辅以深蓝/深红作为强调色。
      * "Global" 版块必须保留新闻的英文原标题。
    - 交互: 使用 <details> 标签折叠长文。
    - 必须输出完整的 HTML 代码。
    """,
    expected_output="完整的 index.html 文件内容",
    agent=editor,
    context=[task_research]
)

# 5. 执行
def clean_html_from_markdown(text: str) -> str:
    """
    Extract HTML content from markdown code blocks.
    
    Args:
        text: Raw text that may contain HTML in markdown code blocks
        
    Returns:
        Cleaned HTML string
    """
    if not text:
        return ""
    
    # Try to extract from ```html block first
    if "```html" in text:
        parts = text.split("```html")
        if len(parts) > 1:
            return parts[1].split("```")[0].strip()
    
    # Try generic ``` block
    if "```" in text:
        parts = text.split("```")
        if len(parts) > 1:
            return parts[1].strip()
    
    # Return as-is if no markdown blocks found
    return text.strip()


def run() -> None:
    """
    Main execution function for the daily news agent.
    
    Raises:
        ValueError: If required API keys are missing
        IOError: If unable to write output file
    """
    print("🚀 Starting Daily News Agent (Optimized for Quality Sources)...")
    
    if not DEEPSEEK_API_KEY:
        raise ValueError("❌ DEEPSEEK_API_KEY is missing!")
    
    news_crew = Crew(
        agents=[china_scout, global_scout, legal_scout, researcher, editor],
        tasks=[task_china, task_global, task_legal, task_research, task_publish],
        process=Process.sequential,
        verbose=True
    )
    
    try:
        result = news_crew.kickoff()
        
        if not result:
            raise ValueError("❌ Crew execution returned empty result")
        
        final_html = clean_html_from_markdown(str(result))
        
        if not final_html:
            raise ValueError("❌ Failed to extract HTML content from result")
        
        output_path = "index.html"
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(final_html)
        except IOError as e:
            raise IOError(f"❌ Failed to write output file: {e}") from e
        
        print(f"✅ Report generated successfully: {output_path}")
        
    except Exception as e:
        print(f"❌ Error during execution: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run()
