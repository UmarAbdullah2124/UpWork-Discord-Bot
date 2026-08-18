# UpWork Discord Bot

Automated Upwork job monitoring and Discord notification bot built with Python, Discord.py, Upwork API, and web scraping to extract and deliver relevant job postings in real time.

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env` and set:

   ```bash
   DISCORD_BOT_TOKEN=your_discord_bot_token
   DISCORD_CHANNEL_ID=your_default_channel_id
   ```

4. Run the bot:

   ```bash
   python main.py
   ```

Runtime files such as logs, local databases, browser sessions, and auth data are intentionally ignored.
