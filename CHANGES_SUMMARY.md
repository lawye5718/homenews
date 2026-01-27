# Summary of Changes to Fix 8 Critical Issues

## Overview
This document summarizes the architectural-level changes made to `agent_main.py` to address 8 critical issues in the news agent system.

## Date: 2026-01-27

## Critical Issues Fixed

### Issue 1: Old News Problem (2024/2022 instead of today's news)
**Problem**: News retrieved was from 2024, 2022, not current/today's news.

**Solution**:
- Added `timedelta` import to calculate TODAY_STR and YESTERDAY_STR precisely
- Changed from generic `CURRENT_DATE` to specific `TODAY_STR` and `YESTERDAY_STR` 
- Updated all search queries to include exact dates:
  - Chinese: `"微博热搜 争议 {TODAY_STR}"`, `"知乎 吵架 {TODAY_STR}"`
  - Global: `"Protest breaking {TODAY_STR}"`, `"Scandal controversy {TODAY_STR}"`
  - Legal: `"Lawsuit filed {TODAY_STR}"`, `"Court verdict controversial {TODAY_STR}"`
- Added strict date verification in all agent backstories
- Explicitly reject news from 2024, 2023, or earlier

**Code Changes**:
```python
# Before
CURRENT_DATE = datetime.now().strftime("%Y-%m-%d")

# After
NOW = datetime.now()
TODAY_STR = NOW.strftime("%Y-%m-%d")
YESTERDAY_STR = (NOW - timedelta(days=1)).strftime("%Y-%m-%d")
```

---

### Issue 2: Shallow Deep Analysis (placeholder text instead of real content)
**Problem**: Deep analysis was just "这里是深度分析的内容" - a placeholder, not real analysis.

**Solution**:
- Rewrote academic analyst agents (health_analyst, legal_scholar) with structured requirements
- Implemented section-by-section approach with specific word counts:
  - Abstract (300字)
  - Theoretical Framework (1000字)
  - Case Analysis (1500字)
  - Comparative Study (1000字)
  - Critical Discourse (800字)
  - Conclusion & References (200-400字)
- Added explicit context dependencies so analysts can READ previous scout outputs
- Enhanced HUMANIZER_PROTOCOL with "强制深度" and "字数铁律" requirements

**Code Changes**:
```python
# Enhanced HUMANIZER_PROTOCOL
5. **强制深度**: 
   - 分析必须达到博士论文水平，引用具体的法律条款、科学数据或社会学理论
   - 不能只是表面描述，必须深入解构背后的权力关系、经济动因、社会结构
7. **字数铁律**: 
   - 当要求 1000/5000 字时，这是硬性下限
   - 必须通过提供更多细节、引用更多案例、多角度论证来填充
   - 严禁重复凑字数或使用空洞表述
```

---

### Issue 3: Generic News (not controversial/viral topics)
**Problem**: News items were generic, not controversial topics that spark social media debates.

**Solution**:
- Changed search keywords from "News" to controversy-focused terms:
  - "争议", "冲突", "辩论", "抗议", "抵制", "舆论"
  - "Controversy", "Conflict", "Protest", "Scandal", "Debate", "Backlash"
- Updated agent roles and goals to focus on conflict:
  - China: "Chinese Social Conflict Reporter" 
  - Global: "Global Conflict & Crisis Analyst"
- Added filtering criteria to avoid entertainment gossip, promotional content
- Required stories that reflect "社会观点碰撞" or "社会本质的冲突"

**Code Changes**:
```python
# Before
role='News Editor for Chinese Media',
goal=f'Select EXACTLY {NEWS_ITEMS_PER_SECTION} controversial newsworthy stories from {CURRENT_YEAR}'

# After
role='Chinese Social Conflict Reporter',
goal=f'Find {NEWS_ITEMS_PER_SECTION} viral controversial events in China from {TODAY_STR} (Past 24h Only) that sparked massive social media debates and conflicts'
```

---

### Issue 4: Legal News Should Be Cases, Not Legislation
**Problem**: Legal news was about new regulations/laws, not actual ongoing court cases.

**Solution**:
- Renamed agent to "Litigation & Case Law Specialist"
- Added explicit prohibition of legislation searches:
  - **不要** 找 "新法律颁布" (New legislation)
  - **要找** "正在进行的庭审"、"争议性判决"、"起诉"
- Updated search keywords to focus on case format:
  - "Lawsuit filed", "Court verdict", "Supreme Court hearing"
  - "v." (plaintiff vs defendant format)
  - "判决争议", "起诉", "庭审"
- Required case structure: 原告 v. 被告

**Code Changes**:
```python
role='Litigation & Case Law Specialist',
goal=f'Find {NEWS_ITEMS_PER_SECTION} ongoing, high-profile COURT CASES or LAWSUITS from {TODAY_STR} (last 24-48h) that are causing public sensation'

**核心指令** (针对问题4：法律新闻应该是实际案例):
1. **不要** 找 "新法律颁布" (New legislation)、"新规" (New regulation)
2. **要找** 正在进行的庭审、刚刚做出的争议性判决
```

---

### Issue 5: Academic Analysis Not Related to Hot Topics
**Problem**: Academic papers/articles were not related to the hot topics found.

**Solution**:
- Made academic analysts explicitly depend on scout outputs via `context` parameter
- Required analysts to READ previous outputs and extract key legal issues
- Added "Connection to Hot Topics" section (700-900字) as mandatory component
- Updated workflow to extract entities/keywords from news first, then search academics

**Code Changes**:
```python
# task_legal_analysis now has explicit dependency
context=[task_china, task_global, task_legal]

# Added workflow requirement
Phase 1: **READ 前面的法律新闻**
- 从 task_china, task_global, task_legal 的输出中，提取 3-5 个关键争议性法律议题
- 例如：如果发现了 "AI生成内容侵权案"，提取关键词 "AI copyright", "generative AI liability"

Phase 5: **Connection to Hot Topics** (700-900字) **【关键部分】**: 
- **将文章理论应用到前面发现的热点案例上**
- 具体分析：这篇学术文章如何解释当前争议案件
```

---

### Issue 6: Word Count Requirements Not Met
**Problem**: Word count requirements (1000+ for news, 5000+ for analysis) were not enforced.

**Solution**:
- Reduced temperature from 0.7 to 0.6 to improve instruction following
- Reduced max_tokens from 32000 to 8000 to prevent truncation issues
- Added explicit word count verification in every task description
- Used section-by-section approach with per-section word counts
- Added "字数铁律" to HUMANIZER_PROTOCOL

**Code Changes**:
```python
# Before
temperature=0.7,
max_tokens=32000,

# After  
temperature=0.6,  # 降低温度以减少幻觉，增加遵循度
max_tokens=8000,  # 单次回复上限，避免截断

# Added to each task
**Word count requirement**: Each analysis report must be EXACTLY 5000 words or MORE total (verify word count - count actual content words).
```

---

### Issue 7: "Read More" Should Show Analysis, Not Links
**Problem**: "Read More" was linking to external URLs instead of expanding generated content.

**Solution**:
- Updated task_publish to use `<details>` and `<summary>` HTML tags
- Provided explicit HTML template in prompt
- Made "Read More" expand inline content, not navigate to URL
- Moved source URLs to footnote badges at bottom of each card
- Updated editor agent to emphasize this pattern

**Code Changes**:
```python
**UI 交互逻辑 (关键 - 针对问题7)**:
之前的版本 "Read More" 跳转到外部链接是**错误**的。

**正确逻辑**:
1. 外部链接 (Source URLs) 必须作为 [1][2][3] 的脚注放在文章底部
2. **"Read More" 按钮必须是一个 HTML `<details>` 标签**
3. 点击 "Read More" 后，**在当前页面向下展开**

# HTML Template
<details class="group mb-4">
    <summary class="cursor-pointer text-blue-600 font-semibold hover:underline">
        📖 阅读完整报道 / Read Deep Analysis
    </summary>
    <div class="mt-4 prose prose-sm max-w-none text-gray-800 bg-gray-50 p-4 rounded">
        [在这里插入完整的 1000字报道 或 5000字深度分析内容]
    </div>
</details>
```

---

### Issue 8: Missing Comprehensive Factual Reporting
**Problem**: Needed comprehensive 1000+ word reports synthesizing multiple sources.

**Solution**:
- Required each scout to write **1000字以上** comprehensive reports
- Mandated multi-source integration (至少 3 个信源)
- Added detailed structure requirements for news reports:
  1. 事件起因 (时间、地点、人物)
  2. 冲突爆发点 (为什么吵起来)
  3. 各方核心观点 (对立观点)
  4. 官方/法律介入
  5. 社会影响和未来走向
- Required footnoted citations for all sources

**Code Changes**:
```python
**报道要求** (针对问题8：综合性事实报道):
对每个新闻，利用 ScrapeWebsiteTool 抓取多方报道，写出 **1000字以上** 的事实综述，必须包含：
- 事件时间：{TODAY_STR} 或 {YESTERDAY_STR} 的具体时间
- 事件起因：谁做了什么，为什么引起争议
- 冲突焦点：各方的核心观点对立（官方 vs 民间、不同群体）
- 事实前因后果：整合至少 3 个信源的综合报道
- 社会影响：为什么这个事件重要，反映了什么社会问题
```

---

## Additional Improvements

### Enhanced HUMANIZER_PROTOCOL
Added comprehensive writing quality requirements:
- Prohibit AI clichés and common phrases
- Require high burstiness (混合短句和长句)
- Demand concrete examples over abstract expressions
- Enforce factual vs. opinion separation
- Add doctoral-level depth requirement

### Better Model Configuration
- Reduced temperature to 0.6 for better instruction following
- Adjusted max_tokens to 8000 to prevent truncation
- Added context window constant (CTX_WINDOW = 128000)

### Improved Task Dependencies
- Made health_analyst depend on task_health_sports via context
- Made legal_scholar depend on task_china, task_global, task_legal via context
- Ensured sequential execution with proper data flow

---

## Testing Instructions

To test these changes:

1. Set environment variables:
   ```bash
   export NVIDIA_API_KEY="your-key"
   export SERPER_API_KEY="your-key"
   ```

2. Run the agent:
   ```bash
   python agent_main.py
   ```

3. Verify output:
   - Check `index.html` is generated
   - Verify dates are {TODAY_STR}
   - Verify news items focus on controversial topics
   - Verify legal items are cases, not legislation
   - Verify "Read More" uses `<details>` tags
   - Verify source URLs appear as footnote badges
   - Verify word counts (1000+ for news, 5000+ for analysis)
   - Verify academic analyses connect to hot topics

---

## Deployment

These changes will be automatically deployed via GitHub Actions workflow:
- Scheduled daily at Beijing Time 03:00 (UTC 19:00)
- Can also be triggered manually via workflow_dispatch
- Generates `index.html` and deploys to GitHub Pages

---

## Summary

All 8 critical issues have been addressed with minimal, surgical changes to:
- Date handling and search query construction
- Agent roles, goals, and backstories
- Task descriptions and requirements
- HTML template structure
- HUMANIZER_PROTOCOL enhancements
- Model parameters (temperature, max_tokens)
- Task dependency chain via context

The changes maintain the existing architecture while significantly improving:
1. Timeliness (today's news only)
2. Relevance (controversial topics only)
3. Specificity (cases not laws)
4. Academic connection (theory applied to hot topics)
5. Depth (doctoral-level analysis with structure)
6. Completeness (word count enforcement)
7. UX (inline expansion not external links)
8. Reporting quality (comprehensive multi-source synthesis)
