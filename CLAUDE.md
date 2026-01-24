# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

VesuvianaBot is a Python application that scrapes transportation updates from the EAV srl website (Linee Vesuviane railway in Italy), summarizes them using the DeepSeek LLM API, and sends summaries to a Telegram chat. The bot is designed to run periodically (e.g., via cron job or scheduled task) to provide timely mobility updates.

## Environment Setup

### Dependencies

Install dependencies:
```bash
pip install -r requirements.txt
```

### Environment Variables

The bot requires a `.env` file in the project root with:

- `DEEPSEEK_API_KEY` - API key for DeepSeek LLM service
- `TELEGRAM_TOKEN` - Telegram bot token from BotFather
- `CHAT_ID` - Telegram chat/channel ID where messages are sent

## Running the Bot

Execute the main script:

**Windows:**
```bash
.\.venv\Scripts\python VesuvianaBot.py
```

**Linux/macOS:**
```bash
./.venv/bin/python VesuvianaBot.py
```

The script runs once and exits. It's intended for scheduled execution.

## Architecture

### Data Flow

The bot follows a pipeline architecture:

1. **Web Scraping** (`collect_infomobilita_oggi`) - Scrapes EAV website for today's railway mobility news
2. **Content Filtering** - Filters out news based on excluded keywords and categories
3. **LLM Summarization** (`summarize_with_llm`) - Sends collected news to DeepSeek API for summarization
4. **Telegram Publishing** (`send_telegram_message`) - Sends summary to configured Telegram chat

### Key Components

**Web Scraping Logic (`collect_infomobilita_oggi`):**
- Navigates paginated results (up to `max_pages` parameter)
- Extracts articles with class selectors for "Infomobilità Ferrovia" content
- Follows "Leggi di più" (Read more) links to fetch full article text
- Stops when encountering dates older than today
- Filters by excluded keywords (line 19: `EXCLUDED_KEYWORDS`) and category relevance

**Date Parsing (`parse_data_it`):**
- Converts Italian date format "20 GEN 2026" to Python date objects
- Uses `MESI_IT` dictionary for Italian month abbreviations

**LLM Integration (`deepseek_chat`):**
- Asynchronous HTTP calls using `httpx`
- Uses system prompt to instruct LLM on summarization behavior
- User prompt template at line 36-48 defines summarization rules

**Telegram Integration (`send_telegram_message`):**
- Asynchronous using `python-telegram-bot`
- Truncates messages at 4000 characters (Telegram limit)
- Disables web page preview

### Filtering Strategy

The bot filters news by:
- **Date**: Only today's news (date comparison at line 131-134)
- **Keywords**: Excludes news containing station names in `EXCLUDED_KEYWORDS` (line 19)
- **Categories**: Only "Infomobilità Ferrovia" or "Linee Vesuviane" content (line 165-168)

### Asynchronous Operations

- Main entry point uses `asyncio.run(main())` (line 281)
- Both DeepSeek API calls and Telegram messaging are async
- Web scraping is synchronous (uses `requests` library)

## Configuration Notes

**URL Structure:**
- Base URL: `https://www.eavsrl.it/infomobilita-ferrovia/`
- Pagination: `/page/{page_number}/`

**User Agent:**
- Custom UA string: "Mozilla/5.0 (compatible; DailyLLMAgent/1.0)" (line 24)

**LLM Parameters:**
- Model: `deepseek-chat`
- Temperature: 0.2 (low for consistent, factual summaries)
- Max tokens: 500

## Modifying Filters

To adjust which railway lines are monitored, edit `EXCLUDED_KEYWORDS` (line 19). The commented `INCLUDED_KEYWORDS` (line 20) shows a whitelist approach that can be re-enabled if needed.
