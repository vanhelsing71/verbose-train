# VesuvianaBot

VesuvianaBot is a Python application designed to fetch, summarize, and disseminate real-time public transportation information for the "Linee Vesuviane" (Vesuvian Lines) operated by EAV srl in Italy. It scrapes official communications from the EAV website, uses a Large Language Model (LLM) to create concise summaries, and then publishes these updates to a specified Telegram chat.

## Features

- **Web Scraping:** Automatically collects the latest "Infomobilità Ferrovia" (Railway Mobility Information) from the EAV srl website.
- **Intelligent Filtering:** Filters out irrelevant news based on predefined excluded keywords, ensuring only pertinent updates are processed.
- **LLM-Powered Summarization:** Utilizes the DeepSeek API to generate brief and clear summaries of complex announcements, making them easy to digest for Telegram users.
- **Telegram Integration:** Sends the summarized mobility updates directly to a configured Telegram chat.
- **Asynchronous Operations:** Performs web scraping and API calls asynchronously for efficient operation.

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
    ```
    *(Note: You will need to create a `requirements.txt` file if it doesn't exist by running `pip freeze > requirements.txt` after installing the dependencies.)*

3.  **Configure Environment Variables:**
    Create a `.env` file in the root directory of the project with the following variables:

    ```
    DEEPSEEK_API_KEY="YOUR_DEEPSEEK_API_KEY"
    TELEGRAM_TOKEN="YOUR_TELEGRAM_BOT_TOKEN"
    CHAT_ID="YOUR_TELEGRAM_CHAT_ID"
    ```
    -   **DEEPSEEK_API_KEY**: Obtain this from the DeepSeek API platform.
    -   **TELEGRAM_TOKEN**: Get this by creating a new bot with BotFather on Telegram.
    -   **CHAT_ID**: The ID of the Telegram chat or channel where you want the messages to be sent. You can get your chat ID by forwarding a message from your chat to the `userinfobot` or by using a tool like `@getidsbot`.

## Usage

To run the bot, simply execute the main Python script:

```bash
./.venv/Scripts/python VesuvianaBot.py # On Windows
# ./.venv/bin/python VesuvianaBot.py # On Linux/macOS
```

The script will fetch the latest information, process it, and send a summary to your configured Telegram chat. It's designed to be run periodically (e.g., via a cron job or scheduled task) to provide timely updates.

## Project Structure

-   `VesuvianaBot.py`: The main script containing the scraping logic, LLM integration, and Telegram messaging.
-   `.env`: (Ignored by Git) Stores sensitive API keys and configuration.

## Dependencies

The main dependencies are:
- `requests`: For making HTTP requests to the EAV website.
- `BeautifulSoup4` (`bs4`): For parsing HTML content.
- `python-dotenv`: For loading environment variables.
- `python-telegram-bot`: For interacting with the Telegram Bot API.
- `httpx`: For making asynchronous HTTP requests to the DeepSeek API.
