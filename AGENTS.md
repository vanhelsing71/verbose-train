# AGENTS.md

This file provides guidance for agentic coding assistants working on the VesuvianaBot codebase.

## Build, Lint, and Test Commands

### Environment Setup
```bash
# Create and activate virtual environment
python -m venv .venv
# Windows:
.\.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Running the Application
```bash
# Windows:
.\.venv\Scripts\python VesuvianaBot.py
# Linux/macOS:
./.venv/bin/python VesuvianaBot.py
```

### Development Commands
```bash
# Check Python version compatibility
python --version

# Update dependencies
pip install -r requirements.txt --upgrade

# Check for security vulnerabilities (optional)
pip install safety
safety check

# Format code (optional - add to requirements.txt)
pip install black
black VesuvianaBot.py

# Lint code (optional - add to requirements.txt)  
pip install flake8
flake8 VesuvianaBot.py

# Type checking (optional - add to requirements.txt)
pip install mypy
mypy VesuvianaBot.py
```

### Testing
This project currently has no formal test suite. Manual testing is done by running the main script with a configured `.env` file.

## Code Style Guidelines

### File Structure and Organization
- Single-file application architecture with `VesuvianaBot.py` as the main module
- Constants defined at the top of the file
- Functions organized by purpose: utilities, web scraping, LLM integration, messaging
- Main execution block at the bottom with async entry point

### Import Style
- Standard library imports first, then third-party libraries
- Group imports logically (see lines 1-12 in VesuvianaBot.py)
- Import `os` twice in current codebase - remove duplicate import (line 10)
- Use explicit imports: `from datetime import datetime, date` rather than `from datetime import *`

### Type Hints
- Use type hints for all function signatures
- Import from `typing` module: `List`, `Dict`, `Optional`
- Use `list[dict]` syntax for Python 3.9+ compatibility (line 183)
- Always return `Optional[date]` when date parsing might fail (line 69)

### Naming Conventions
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `DEEPSEEK_API_KEY`, `EXCLUDED_KEYWORDS`)
- **Functions**: `snake_case` (e.g., `collect_infomobilita_oggi`, `parse_data_it`)
- **Variables**: `snake_case` with descriptive names (e.g., `data_notizia`, `articoli`)
- **Private helpers**: `snake_case` with clear purpose (no strict private convention needed)

### Error Handling
- Always validate required environment variables before use (lines 55-56, 200-201)
- Use specific exception types: `RuntimeError` for configuration issues, `TelegramError` for Telegram failures
- Implement graceful fallbacks for web scraping failures (lines 149-151)
- Include descriptive error messages with context
- Never log or expose sensitive information like API keys

### Async/Await Patterns
- Use async/await for I/O operations (HTTP requests, Telegram messaging)
- Main entry point should use `asyncio.run(main())` (line 282)
- All network operations should have appropriate timeouts (10s for scraping, 30s for LLM)
- Use `httpx.AsyncClient` for async HTTP requests (line 218)

### Web Scraping Guidelines
- Always set a custom User-Agent header (line 24-26)
- Implement robust error handling with `requests.exceptions.RequestException`
- Use `raise_for_status()` to catch HTTP errors (line 101)
- Navigate pagination with configurable max_pages parameter
- Stop processing when encountering dates older than current day (lines 131-135)

### LLM Integration
- Use structured prompts with clear system and user roles
- Set low temperature (0.2) for consistent, factual output (line 214)
- Limit response tokens appropriately (500 for summaries) (line 215)
- Always handle API errors with status code checks (lines 225-228)

### Telegram Integration
- Truncate messages to 4000 characters (Telegram limit) (line 63)
- Disable web page preview for cleaner messages (line 64)
- Handle `TelegramError` specifically (line 66)
- Validate both token and chat_id before sending (lines 55-56)

### Data Processing
- Use Italian locale constants (e.g., `MESI_IT`) for date parsing
- Filter news using lowercase comparison for case-insensitive matching
- Implement inclusive/exclusive keyword filtering (lines 157-163)
- Store dates in ISO format for consistency (line 173)

### Security Best Practices
- Never commit API keys or tokens to version control
- Use environment variables for all sensitive configuration
- Validate all external inputs and API responses
- Implement timeouts for all network requests
- Use HTTPS URLs for all API calls

### Documentation Style
- Write docstrings in Italian to match codebase language (lines 70-92)
- Use triple quotes for multi-line strings and prompts
- Include parameter types and return values in docstrings
- Add inline comments for complex business logic (lines 104-111, 137-155)

### Configuration Management
- Use `python-dotenv` for environment variable loading (line 14)
- Define all URLs and headers as constants (lines 23-26)
- Make filtering keywords easily configurable (lines 20-21)
- Provide sensible defaults for optional parameters (e.g., `max_pages: int = 10`)