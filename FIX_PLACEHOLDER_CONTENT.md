# Fix for Placeholder Content Issue

## Problem Description

The generated `index.html` file was containing placeholder text instead of real news content:
- Titles like "新闻标题 1", "新闻标题 2", etc.
- Summaries like "新闻摘要 1...", "新闻摘要 2...", etc.
- Content like "完整报道内容 1...", "健康与运动深度分析内容 2...", etc.
- Source URLs showing "#" instead of actual links

## Root Cause

The LLM agents (researcher and editor) were interpreting placeholder examples in task descriptions as the actual content to output rather than as templates to be filled with real data from the news gathering tasks.

## Solution

Added explicit instructions throughout the agent pipeline to prevent placeholder generation:

### 1. Editor Task (task_publish)
- Added "CRITICAL INSTRUCTION" at the beginning emphasizing use of actual content
- Modified HTML template examples to clearly mark placeholders with "REPLACE THIS: ..."
- Added multiple warnings against generating fake placeholder text
- Instructed to output errors instead of placeholders if content is missing

### 2. Researcher Agent
- Added "ABSOLUTELY CRITICAL - NO PLACEHOLDER TEXT" section
- Emphasized extracting actual content from previous tasks only
- Updated verification steps to check for real content vs placeholders (e.g., not "新闻标题 1")
- Instructed to report errors instead of generating placeholders

### 3. Research Task (task_research)
- Added "ABSOLUTELY CRITICAL - NO PLACEHOLDER TEXT" section
- Clarified that output structure should be filled with REAL content
- Emphasized using actual content from context tasks

## Files Modified

- `agent_main.py`: Updated task descriptions and agent configurations

## How to Verify the Fix

### Method 1: Run GitHub Actions Workflow
1. Go to the GitHub repository
2. Navigate to Actions tab
3. Select "Daily News Agent" workflow
4. Click "Run workflow" button
5. Wait for completion (~8-10 minutes)
6. Visit the deployed GitHub Pages site
7. Verify that:
   - News titles are descriptive and unique (not "新闻标题 1", "新闻标题 2")
   - Summaries contain real content (not "新闻摘要 1...")
   - Expandable sections contain full articles (not "完整报道内容 1...")
   - Source links point to actual URLs (not "#")

### Method 2: Local Testing (requires API keys)
```bash
# Set environment variables
export NVIDIA_API_KEY="your_key_here"
export SERPER_API_KEY="your_key_here"

# Install dependencies
pip install -r requirements.txt

# Run the agent
python agent_main.py

# Check the generated index.html
grep -i "新闻标题 1\|新闻摘要 1\|完整报道内容 1" index.html
# Should return nothing if fix is working

# Check for real content
head -100 index.html
# Should show actual news titles and content
```

## Expected Behavior After Fix

- Each news item should have a unique, descriptive title in Chinese or English
- Summaries should be 200-300 characters of actual news content
- Expandable sections should contain full 1000+ word articles or 5000+ word analyses
- Source URLs should be actual clickable links to news sources, research papers, etc.
- All content should be from the current date (2026-01-27 or latest run date)

## Backup Model Compatibility

The fix automatically applies to all three model configurations:
- Primary: `meta/llama-3.1-405b-instruct` (NVIDIA API)
- Second backup: `deepseek-chat` (DeepSeek API)
- Third backup: `nvidia/llama-3.3-nemotron-super-49b-v1.5` (NVIDIA API)

All backup tasks reference the same updated task descriptions.

## Related Issues

This fix addresses the issue reported in Chinese:
> "仔细检查最新的log文件，查找bug的问题源泉，设法纠正。目前问题在于最后pages没有任何内容，也没有标题，都是占位符，和占位文字，比如"健康与运动深度分析内容 2..."等等。"

Translation: "Carefully check the latest log files, find the root cause of the bug, and fix it. The current problem is that the final pages have no content, no titles, they are all placeholders and placeholder text, such as '健康与运动深度分析内容 2...' etc."
