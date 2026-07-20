# Social Keyword Monitor

An automated pipeline that monitors TikTok and Instagram for keyword and hashtag mentions, and logs matching results into Google Sheets on a recurring schedule.

## Overview

The system reads a set of target keywords for each platform, searches for recent matching content, filters results by recency, language, and relevance, and writes new findings to a dedicated worksheet tab — without duplicating content it has already logged. The entire process runs unattended on a fixed schedule via GitHub Actions.

## Features

- Platform-specific collectors for TikTok and Instagram, each implementing a shared collector interface
- Independent keyword lists per platform, read from separate documents
- Automatic English-language filtering, with per-platform configuration
- Deduplication both within a single run and against previously logged results
- Separate output tabs per platform within a single Google Sheet
- Configurable lookback windows and cost controls, tunable without code changes
- Fully automated scheduling with manual trigger support

## Schedule

The pipeline runs automatically every two days at 7:00 AM Eastern Time, with no manual intervention required. A manual trigger is also available for on-demand runs.

The schedule targets every odd-numbered day of the month. Run dates are highlighted below.

**July 2026**

| Su | Mo | Tu | We | Th | Fr | Sa |
|---|---|---|---|---|---|---|
| | | | <span style="color:#0F6E56"><b>1</b></span> | 2 | <span style="color:#0F6E56"><b>3</b></span> | 4 |
| <span style="color:#0F6E56"><b>5</b></span> | 6 | <span style="color:#0F6E56"><b>7</b></span> | 8 | <span style="color:#0F6E56"><b>9</b></span> | 10 | <span style="color:#0F6E56"><b>11</b></span> |
| 12 | <span style="color:#0F6E56"><b>13</b></span> | 14 | <span style="color:#0F6E56"><b>15</b></span> | 16 | <span style="color:#0F6E56"><b>17</b></span> | 18 |
| <span style="color:#0F6E56"><b>19</b></span> | 20 | <span style="color:#0F6E56"><b>21</b></span> | 22 | <span style="color:#0F6E56"><b>23</b></span> | 24 | <span style="color:#0F6E56"><b>25</b></span> |
| 26 | <span style="color:#0F6E56"><b>27</b></span> | 28 | <span style="color:#0F6E56"><b>29</b></span> | 30 | <span style="color:#0F6E56"><b>31</b></span> | |

**August 2026**

| Su | Mo | Tu | We | Th | Fr | Sa |
|---|---|---|---|---|---|---|
| | | | | | | <span style="color:#0F6E56"><b>1</b></span> |
| 2 | <span style="color:#0F6E56"><b>3</b></span> | 4 | <span style="color:#0F6E56"><b>5</b></span> | 6 | <span style="color:#0F6E56"><b>7</b></span> | 8 |
| <span style="color:#0F6E56"><b>9</b></span> | 10 | <span style="color:#0F6E56"><b>11</b></span> | 12 | <span style="color:#0F6E56"><b>13</b></span> | 14 | <span style="color:#0F6E56"><b>15</b></span> |
| 16 | <span style="color:#0F6E56"><b>17</b></span> | 18 | <span style="color:#0F6E56"><b>19</b></span> | 20 | <span style="color:#0F6E56"><b>21</b></span> | 22 |
| <span style="color:#0F6E56"><b>23</b></span> | 24 | <span style="color:#0F6E56"><b>25</b></span> | 26 | <span style="color:#0F6E56"><b>27</b></span> | 28 | <span style="color:#0F6E56"><b>29</b></span> |
| 30 | <span style="color:#0F6E56"><b>31</b></span> | | | | | |


## Output

Results are written to two dedicated worksheet tabs, one per platform, each containing:

| Column | Description |
|---|---|
| Timestamp | When the original post or comment was published |
| Collected At | When the pipeline retrieved it |
| Person/Handle | Author of the content |
| Platform | Source platform |
| Type | Post or Comment (validated dropdown) |
| Matched Keyword | The keyword or hashtag that triggered the match |
| Content Snippet | A truncated preview of the content |
| URL | Direct link to the original post |

---

## Project Structure

```text
social-keyword-monitor/
│
├── src/
│   ├── main.py                    # Pipeline orchestrator
│   ├── keyword_extractor.py       # Reads keyword documents
│   ├── sheets_writer.py           # Writes results into Google Sheets
│   │
│   └── collectors/
│       ├── base.py                # Shared collector interface
│       ├── tiktok_collector.py    # TikTok data collection
│       └── instagram_collector.py # Instagram data collection
│
├── data/
│   ├── tiktok_keywords.docx
│   ├── instagram_keywords.docx
│   └── service_account.json       # Google Service Account credentials
│                                  # (Excluded from version control)
│
├── .github/
│   └── workflows/
│       └── daily-run.yml          # GitHub Actions schedule
│
├── reqs.txt                       # Python dependencies
└── README.md
```

---
## Setup

1. Install dependencies:
```bash
   pip install -r reqs.txt
```

2. Populate keyword lists in `data/tiktok_keywords.docx` and `data/instagram_keywords.docx`, one entry per line. Instagram entries must begin with `#`, as that collector operates on hashtag-based discovery only.

3. Create a Google Cloud service account, enable the Sheets and Drive APIs, and share the target spreadsheet with the service account's email address. Save the generated key as `data/service_account.json`.

4. Copy `.env.example` to `.env` and populate the required values (Sheet ID, search-provider credentials).

5. Run locally to verify configuration:
```bash
   python src/main.py
```

6. For automated scheduling, push the repository to GitHub and configure the required secrets under Settings -> Secrets and variables -> Actions. The workflow defined in `.github/workflows/daily-run.yml` handles the rest.

## Configuration

The following are configurable via environment variables, requiring no code changes:

| Variable pattern | Purpose |
|---|---|
| `*_TARGET_MATCHES_PER_KEYWORD` | Target number of genuine matches to retrieve per keyword |
| `*_MAX_RAW_RESULTS_PER_KEYWORD` | Upper bound on raw results requested, bounding cost regardless of match rate |
| `*_LANGUAGE_FILTER` | Restricts results to a single language |
| `*_LOOKBACK_HOURS` / `*_LOOKBACK_DAYS` | Controls how far back each platform searches |
| `*_COLLECT_COMMENTS` | Enables or disables comment-level collection |

## Security

Credentials (`.env`, `data/service_account.json`) are excluded from version control via `.gitignore` and never committed to the repository. All secrets used in automated runs are stored as encrypted GitHub Actions secrets.
