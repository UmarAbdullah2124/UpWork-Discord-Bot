# UpWork Discord Bot

An automated Upwork job monitoring and Discord notification bot built with Python. It monitors Upwork job postings, extracts relevant listings, and delivers job notifications to Discord in real time.

## Technologies

* Python
* Discord.py
* Upwork API
* Web Scraping
* REST APIs

## Setup

1. Create and activate a virtual environment.
2. Install the dependencies:

```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and configure the required environment variables:

```env
DISCORD_BOT_TOKEN=your_discord_bot_token
DISCORD_CHANNEL_ID=your_default_channel_id
```

4. Run the bot:

```bash
python main.py
```

Runtime files such as logs, local databases, browser sessions, and authentication data are intentionally excluded from the repository.
