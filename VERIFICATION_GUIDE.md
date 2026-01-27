# VERIFICATION GUIDE - Fix for Data Integrity Error

## Quick Summary

**Problem Fixed:** Agents were not using their search and scrape tools, resulting in no news data being collected and a "Critical Data Integrity Error" page being generated.

**Solution:** Added `allow_delegation=False` to all agents and explicit tool usage instructions.

## How to Verify the Fix Works

### Step 1: Trigger a New Workflow Run

You have two options:

#### Option A: Manual Trigger (Recommended for Testing)
1. Go to: https://github.com/lawye5718/homenews/actions
2. Click on "Daily News Agent" workflow (left sidebar)
3. Click the "Run workflow" button (top right)
4. Select branch: `copilot/fix-critical-data-integrity-error`
5. Click "Run workflow" (green button)

#### Option B: Wait for Scheduled Run
- The workflow runs automatically at 19:00 UTC (03:00 Beijing time) daily
- Next automatic run will pick up the changes after this PR is merged to `master`

### Step 2: Monitor the Workflow Execution

1. Click on the running workflow to view logs
2. Look for these SUCCESS indicators in the logs:

**✅ Signs the fix is working:**
```
- Agents should show tool usage: "Action: Search the internet"
- Search queries should be executed: "Search Query: 微博热搜 争议 after:2026-01-26"
- URLs should be scraped: "Action: Read website content"
- Task outputs should contain actual data (not just "I will search...")
```

**❌ Signs the fix didn't work:**
```
- Agents just say "I will search" and complete immediately
- No "Action: Search the internet" in logs
- Task outputs are empty or placeholder text
- Researcher agent says "我无法访问...context tasks"
```

### Step 3: Check the Generated HTML

After the workflow completes (~5-10 minutes):

1. Visit: https://lawye5718.github.io/homenews/
2. The page should be updated within a few minutes

**✅ SUCCESS - Fix Worked:**
- Page shows current date (2026-01-27 or later)
- 5 columns with news content visible
- Each section has 5 news items (or 3 for analyses)
- News titles are real and descriptive (NOT "新闻标题 1", "新闻标题 2")
- Clicking "Read More" expands to show full article content
- Source links [1][2][3] at bottom are clickable URLs
- No error banner at the top

**❌ FAILURE - Fix Didn't Work:**
- Red error banner: "Content Integrity Alert"
- Heading: "Critical Data Integrity Error"
- Message about waiting for valid data input
- Placeholder layout boxes with no content
- Footer says "Status: Halted"

### Step 4: Deep Verification (Optional)

If you want to verify the fix in detail:

```bash
# 1. Check the deployed HTML source
curl https://lawye5718.github.io/homenews/ > deployed.html

# 2. Look for placeholder text (should find NONE):
grep -i "新闻标题 1\|新闻摘要 1\|完整报道内容 1" deployed.html
# Expected: No output (empty result)

# 3. Look for actual news titles (should find MANY):
grep -i '<h3 class="font-bold' deployed.html | head -10
# Expected: Real Chinese/English news titles

# 4. Check for real source URLs (should find MANY):
grep -i 'href="http' deployed.html | grep -v 'cdn.tailwindcss\|fonts.googleapis' | head -10
# Expected: Real news source URLs
```

## What to Do If Fix Didn't Work

If the workflow still produces the error page:

### Diagnostic Steps:

1. **Check the workflow logs** for specific errors:
   - API key issues: "NVIDIA_API_KEY not found"
   - Rate limiting: "429 Too Many Requests"
   - Model errors: "Content Risk", "Token limit exceeded"

2. **Check if tools were used**:
   ```bash
   # Download the workflow log
   # Search for "Action: Search" or "Tool: SerperDevTool"
   grep -i "action.*search\|serper\|scrape" workflow.log
   ```

3. **Verify API keys are configured**:
   - Go to: https://github.com/lawye5718/homenews/settings/secrets/actions
   - Confirm these secrets exist:
     - `NVIDIA_API_KEY`
     - `SERPER_API_KEY`
     - (Optional) `DEEPSEEK_API_KEY`

### Potential Additional Fixes:

If tools still aren't being used, we may need to:

1. **Increase LLM temperature** to encourage more creative tool usage:
   ```python
   primary_llm = LLM(
       # ...
       temperature=0.6,  # Increase from 0.4 to 0.6
   )
   ```

2. **Add function calling enforcement** (if CrewAI supports it):
   ```python
   agent = Agent(
       # ...
       function_calling_llm=True,  # Force function calling mode
   )
   ```

3. **Simplify task descriptions** to make tool usage more obvious

4. **Add tool usage validation** that fails the task if no tools were used

## Timeline

- **Fix committed**: 2026-01-27 12:XX UTC
- **Expected first test run**: Within 24 hours (manual trigger) or at next scheduled run
- **Results available**: ~10 minutes after workflow starts

## Success Metrics

After fix is verified working, you should see:
- ✅ No more "Critical Data Integrity Error" pages
- ✅ Fresh news content daily
- ✅ All 5 sections populated with real news
- ✅ 1000+ word summaries for each news item
- ✅ 5000+ word analyses for health/legal topics
- ✅ Working source URL footnotes

## Contact

If you encounter issues or need help verifying:
1. Check the GitHub Actions logs first
2. Look at the deployed page source
3. Review FIX_AGENTS_NOT_USING_TOOLS.md for technical details
4. Create an issue with:
   - Link to failed workflow run
   - Screenshot of deployed page
   - Relevant log excerpts

---

**Last Updated**: 2026-01-27
**Branch**: copilot/fix-critical-data-integrity-error  
**Status**: ✅ Fix implemented, awaiting verification
