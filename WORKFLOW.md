# HomeNews AI Agent Workflow

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         HomeNews AI Agent System                    │
│                    (Powered by NVIDIA DeepSeek-V3.2 + CrewAI)      │
└─────────────────────────────────────────────────────────────────────┘

                              ┌─────────────┐
                              │   Start     │
                              └──────┬──────┘
                                     │
        ┌────────────────────────────┼────────────────────────────┐
        │                            │                            │
        ▼                            ▼                            ▼
┌───────────────┐          ┌───────────────┐          ┌───────────────┐
│ China Scout   │          │ Global Scout  │          │ Legal Scout   │
│               │          │               │          │               │
│ 微博/知乎/百度 │          │ NYT/Reuters/  │          │ SCOTUS/EU/    │
│               │          │ Bloomberg     │          │ China Courts  │
└───────┬───────┘          └───────┬───────┘          └───────┬───────┘
        │                          │                          │
        │ Top 5 China             │ Top 5 Global            │ Top 5 Legal
        │ News Items              │ News Items              │ News Items
        │                          │                          │
        └────────────────┬─────────┴──────────┬───────────────┘
                         │                    │
        ┌────────────────┴────────┐          │
        ▼                         ▼          │
┌───────────────┐     ┌──────────────────┐   │
│ Health/Sports │     │ Legal Scholar    │   │
│ Scout         │     │                  │   │
│               │     │ Identifies key   │   │
│ Sci American  │     │ legal issues     │   │
│ Nature/Science│     │ from US-China    │   │
│ JAMA/Lancet   │     │ hot topics       │   │
└───────┬───────┘     └────────┬─────────┘   │
        │                      │              │
        │ Top 5 Health        │ Search law   │
        │ News Items          │ reviews from │
        │                     │ Top 10 US    │
        ▼                     │ law schools  │
┌───────────────┐             │              │
│ Health        │             ▼              │
│ Analyst       │   ┌──────────────────┐     │
│               │   │ 3 Law Review     │     │
│ Selects Top 3 │   │ Articles:        │     │
│ Stories       │   │                  │     │
│               │   │ • Yale           │     │
│ Generates     │   │ • Harvard        │     │
│ 300-500 word  │   │ • Stanford       │     │
│ deep analysis │   │ etc.             │     │
│ for each      │   │                  │     │
└───────┬───────┘   └────────┬─────────┘     │
        │                    │               │
        │ 3 Analysis        │ 3 Article     │
        │ Reports           │ Analyses      │
        │                   │ (800-1000w ea)│
        │                    │               │
        └────────────────────┼───────────────┘
                             │
                             ▼
                    ┌────────────────┐
                    │  Researcher    │
                    │                │
                    │  Aggregates &  │
                    │  Fact Checks   │
                    │  ALL 5 Sections│
                    └────────┬───────┘
                             │
                             │ Markdown Report
                             │ with 5 sections
                             ▼
                    ┌────────────────┐
                    │    Editor      │
                    │                │
                    │  Converts to   │
                    │  HTML with     │
                    │  Responsive    │
                    │  Layout        │
                    └────────┬───────┘
                             │
                             ▼
                    ┌────────────────┐
                    │  index.html    │
                    │                │
                    │  5 Sections:   │
                    │  1. China      │
                    │  2. Global     │
                    │  3. Legal      │
                    │  4. Health     │
                    │  5. Law Review │
                    └────────┬───────┘
                             │
                             ▼
                    ┌────────────────┐
                    │ GitHub Pages   │
                    │  (Deployed)    │
                    └────────────────┘
```

## Task Execution Sequence

1. **task_china** - China Scout collects domestic news
2. **task_global** - Global Scout collects international news  
3. **task_legal** - Legal Scout collects legal news
4. **task_health_sports** - Health/Sports Scout collects scientific news
5. **task_health_analysis** - Health Analyst creates deep analysis (depends on #4)
6. **task_legal_analysis** - Legal Scholar analyzes law reviews (depends on #1,#2,#3)
7. **task_research** - Researcher aggregates all outputs (depends on #1-#6)
8. **task_publish** - Editor generates HTML (depends on #7)

## Agent Details

### Information Gathering Agents
- **china_scout**: Chinese social media analyst
- **global_scout**: International news analyst (English sources only)
- **legal_scout**: Legal researcher (courts & regulations)
- **health_sports_scout**: Science journalist (peer-reviewed sources)

### Analysis Agents
- **health_analyst**: Science writer (explains complex research)
- **legal_scholar**: Comparative law expert (US-China focus)

### Synthesis Agents
- **researcher**: Chief editor (fact-checking & aggregation)
- **editor**: Frontend developer (HTML generation)

## Output Sections

### 1. China News
- Top 5 Chinese social issues
- Focus on public value, not celebrity gossip
- Sources: Weibo, Zhihu, Caixin

### 2. Global News  
- Top 5 international events
- English sources only (NYT, Reuters, Bloomberg)
- Tech, politics, economy focus

### 3. Legal News
- Top 5 legal developments
- SCOTUS, EU regulations, China courts
- Case names and legal implications

### 4. Health & Sports News + Deep Analysis
- Top 5 scientific health/sports news
- Sources: Scientific American, Nature, Science, JAMA, Lancet
- **Top 3 Deep Analysis Reports** (300-500 words each):
  * Scientific background
  * Research methodology
  * Key findings
  * Public health implications
  * Practical applications
  * Limitations & caveats

### 5. Legal Analysis & Law Review Articles
- AI-identified key legal issues from US-China topics
- **3 Law Review Articles** from top 10 US law schools
- **Comprehensive Analysis** for each (800-1000 words):
  * Article overview & thesis
  * Legal framework & precedents
  * Key arguments explained
  * Connection to current events
  * Real-world implications

## Deployment

### GitHub Actions Workflow
- **Trigger**: Daily at UTC 23:00 (Beijing 7:00 AM)
- **Runtime**: ~15-30 minutes (depending on search/analysis)
- **Output**: index.html deployed to GitHub Pages
- **Required Secrets**:
  - NVIDIA_API_KEY
  - SERPER_API_KEY

### Environment
- Python 3.11
- CrewAI framework
- NVIDIA DeepSeek-V3.2 LLM
- SerperDev search API
