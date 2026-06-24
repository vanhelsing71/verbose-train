# AGENTS.md

Guidance for agentic coding assistants working on VesuvianaBot.

## What this is

Single-file Python app (`VesuvianaBot.py`, ~634 lines) that scrapes EAV railway news, summarizes them via DeepSeek LLM, and posts text + Playwright screenshots to a Telegram chat. It runs as a **long-running bot** (not a one-shot script) with an embedded APScheduler.

## Setup

```bash
python -m venv .venv
.\.venv\Scripts\activate          # Windows
pip install -r requirements.txt
python -m playwright install      # REQUIRED — screenshots fail without browser binaries
```

Requires a `.env` (gitignored) with:
- `DEEPSEEK_API_KEY`
- `TELEGRAM_TOKEN`
- `CHAT_ID`

Python 3.9+ required (`list[dict]` syntax at line 327). README says 3.8+ — that is wrong.

## Run

```bash
.\.venv\Scripts\python VesuvianaBot.py   # Windows
./.venv/bin/python VesuvianaBot.py       # Linux/macOS
```

The process stays alive: Telegram polling + APScheduler in one event loop.

## Tests / lint

None configured. No `pytest`, `black`, `flake8`, or `mypy` in `requirements.txt` — do not run these assuming they exist. Manual verification = run the bot and watch the console output.

## Architecture (single file, top-to-bottom order)

1. **Constants & prompts** (lines 1–58): `EXCLUDED_KEYWORDS`, `BASE_URL`, `MESI_IT`, `SYSTEM_PROMPT`, `USER_PROMPT_TEMPLATE`.
2. **`take_screenshot`** (Playwright, async) — renders teleindicator/alilauro pages to PNG.
3. **`send_telegram_message`** — async, truncates at 4000 chars, disables preview.
4. **`parse_data_it`** — parses Italian dates like "20 GEN 2026" via `MESI_IT`.
5. **`collect_infomobilita_oggi`** — **synchronous** `requests` + BeautifulSoup, paginates `BASE_URL/page/N/`, stops at dates older than today.
6. **`deepseek_chat` / `summarize_with_llm`** — async `httpx`, temperature 0.2, 500 max tokens.
7. **Telegram handlers** — `/start`, `/update`, `/psorrento`, `/asorrento`, `/pnapoli`, `/anapoli`, `/alilauro`.
8. **`scheduled_morning` (6:15), `scheduled_morning2` (7:00), `scheduled_evening` (17:00)** — cron jobs added in `post_init`.
9. **`main()`** — builds `Application`, registers handlers, starts scheduler, runs polling.

> Note: `README.md` claims scheduling at 6:00 and 17:00 only — stale. Real times: 6:15, 7:00, 17:00.
> Note: `CLAUDE.md` claims the script "runs once and exits" — wrong, it is a persistent bot.

## Conventions

- Docstrings and inline comments are in **Italian** — match this when editing.
- `snake_case` functions/variables, `UPPER_SNAKE_CASE` constants.
- Scraping is sync (`requests`); LLM + Telegram are async (`httpx`, `python-telegram-bot`). Don't mix — keep scraping in `collect_infomobilita_oggi` and wrap with `asyncio.to_thread` if needed from async code.
- All URLs/headers live as module constants; do not inline.
- Filter logic: `EXCLUDED_KEYWORDS` (blocklist, active) vs `INCLUDED_KEYWORDS` (whitelist, commented out at line 30).

## Gotchas

- `.gitignore` does **not** cover `__pycache__/` or `.playwright-mcp/` — avoid committing them. Stage files explicitly.
- `send_teleindicatori_screenshot` parameters (`station_id`, `train_type`, `station_name`) are edited directly in `scheduled_*` functions — there is no config table, changes require code edits.
- Commit messages in this repo are short, imperative, often one logical change per commit (e.g. `Updated evening scheduled teleindicatori station to Meta`).

## References

- `README.md` — user-facing setup/commands (partially stale on schedule times).
- `CLAUDE.md` — older agent doc, partially stale (claims one-shot execution); prefer this file.
