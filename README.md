# VesuvianaBot

VesuvianaBot is a Python application designed to fetch, summarize, and disseminate real-time public transportation information for the "Linee Vesuviane" (Vesuvian Lines) operated by EAV srl in Italy. It scrapes official communications from the EAV website, uses a Large Language Model (LLM) to create concise summaries, and then publishes these updates to a specified Telegram chat via an interactive bot.

## Features

- **Robust Web Scraping:** Automatically collects the latest "Infomobilità Ferrovia" by navigating pagination and following links to get full article content.
- **Intelligent Filtering:** Filters out irrelevant news based on predefined excluded keywords, ensuring only pertinent updates are processed.
- **LLM-Powered Summarization:** Utilizes the DeepSeek API to generate brief and clear summaries of complex announcements.
- **Interactive Telegram Bot:** Runs as a persistent Telegram bot that users can interact with.
- **Scheduled Updates:** Automatically fetches and sends updates twice a day (at 6:00 and 17:00) using an internal scheduler.
- **On-Demand Updates:** Allows users to manually trigger an update at any time using a simple command.
-   **Screenshot Train Timetables:** Provides real-time screenshots of train teleindicators for specific stations (Sorrento, Napoli) and routes (arrivals/departures).

## Setup and Installation

To run VesuvianaBot, you'll need Python 3.8+ and the following environment variables configured.

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/VesuvianaBot.git
    cd VesuvianaBot
    ```

2.  **Create a virtual environment and install dependencies:**
    ```bash
    python -m venv .venv
    ./.venv/Scripts/activate # On Windows
    # source .venv/bin/activate # On Linux/macOS
    pip install -r requirements.txt
    # Install Playwright browser binaries
    python -m playwright install
    ```

3.  **Configure Environment Variables:**
    Create a `.env` file in the root directory of the project with the following variables:

    ```
    DEEPSEEK_API_KEY="YOUR_DEEPSEEK_API_KEY"
    TELEGRAM_TOKEN="YOUR_TELEGRAM_BOT_TOKEN"
    CHAT_ID="YOUR_TELEGRAM_CHAT_ID"
    ```
    -   **DEEPSEEK_API_KEY**: Obtain this from the DeepSeek API platform.
    -   **TELEGRAM_TOKEN**: Get this by creating a new bot with BotFather on Telegram.
    -   **CHAT_ID**: The ID of the Telegram chat or channel where you want the messages to be sent. You can get your chat ID by forwarding a message from your chat to the `userinfobot`.

## Usage

To run the bot, simply execute the main Python script. The bot will start, stay online, and handle everything automatically.

```bash
./.venv/Scripts/python VesuvianaBot.py # On Windows
# ./.venv/bin/python VesuvianaBot.py # On Linux/macOS
```

Once running, the bot will:
- Automatically send a summary of the latest news every day at **6:00 AM** and **5:00 PM**.
- Respond to commands sent in the chat.

### Bot Commands

-   `/start`: Initializes the bot and sends a welcome message.
-   `/update`: Manually triggers a new check for mobility news, processes it, and sends the summary to the chat immediately.
-   `/psorrento`: Sends a screenshot of the departures teleindicator for Sorrento station.
-   `/asorrento`: Sends a screenshot of the arrivals teleindicator for Sorrento station.
-   `/pnapoli`: Sends a screenshot of the departures teleindicator for Napoli station.
-   `/anapoli`: Sends a screenshot of the arrivals teleindicator for Napoli station.

## Project Structure

-   `VesuvianaBot.py`: The main script containing the Telegram bot logic, scheduler, web scraper, and LLM integration.
-   `.env`: (Ignored by Git) Stores sensitive API keys and configuration.
-   `requirements.txt`: Lists all the Python dependencies for the project.

## Dependencies

The main dependencies are:
- `requests`: For making HTTP requests to the EAV website.
- `BeautifulSoup4` (`bs4`): For parsing HTML content.
- `python-dotenv`: For loading environment variables.
- `python-telegram-bot`: For interacting with the Telegram Bot API.
- `httpx`: For making asynchronous HTTP requests to the DeepSeek API.
- `APScheduler`: For scheduling the automatic daily updates.
- `playwright`: For web page rendering and taking screenshots of teleindicators.
