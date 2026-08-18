import asyncio
import datetime
import json
import os
import discord
import logging
import psutil
import sys

from urllib.parse import urlparse, parse_qs, unquote

from DiscordBot import UpworkDiscordBot
from Scraper import UpworkScraper
from Database import JobDatabase


# ---------------------------------------------------
# WINDOWS UTF-8 FIX
# ---------------------------------------------------

if sys.platform == "win32":
    import codecs
    if sys.stdout.encoding != 'utf-8':
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())


# ---------------------------------------------------
# LOGGING
# ---------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------
# CONFIG
# ---------------------------------------------------

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DEFAULT_ID = int(os.getenv("DISCORD_CHANNEL_ID", "1501909348312678513"))

if not TOKEN:
    raise RuntimeError("DISCORD_BOT_TOKEN environment variable is required.")


# ---------------------------------------------------
# INIT
# ---------------------------------------------------

db = JobDatabase()
scraper = UpworkScraper()
bot = UpworkDiscordBot(TOKEN, DEFAULT_ID)
active_tasks = {}


# ---------------------------------------------------
# CONFIG LOADER
# ---------------------------------------------------

def load_config():
    if not os.path.exists('config.json'):
        return {"tracked_urls": []}
    with open('config.json', 'r') as f:
        return json.load(f)


# ---------------------------------------------------
# PROCESS BATCH
# ---------------------------------------------------

async def process_batch(results, channel_id, label, url_source):
    for job in reversed(results or []):
        if not job:
            continue

        job_tile_container = job.get('jobTile') or {}
        job_tile = job_tile_container.get('job') or {}
        ciphertext = job_tile.get('ciphertext')

        # Skip restricted/private jobs
        if not ciphertext:
            continue

        title_text = job.get('title', '').lower()
        desc_text = job.get('description', '').lower()
        keyword_parts = label.lower().split()

        # Keyword matching
        if not any(k in title_text or k in desc_text for k in keyword_parts):
            continue

        job_id = job.get('id')
        if not job_id or not db.is_new_job(job_id, url_source):
            continue

        # ----------------------------------------
        # FETCH EXTRA DETAILS
        # ----------------------------------------
        details = await asyncio.to_thread(scraper.fetch_details, ciphertext)
        await asyncio.sleep(1) # Safety pause for backfill

        description = details.get('description') or job.get('description') or 'No description.'
        if not description:
            continue

        title = job.get('title', 'No Title')

        # Budget Calculation
        budget_data = job_tile.get('fixedPriceAmount') or {}
        fixed_amount = budget_data.get('amount')
        if fixed_amount:
            budget = f"${fixed_amount}"
        else:
            budget = f"${job_tile.get('hourlyBudgetMin', '?')}-${job_tile.get('hourlyBudgetMax', '?')}/hr"

        # Client Details
        client = details.get('client') or {}
        location = (client.get('location') or {}).get('country', 'N/A')
        spent = client.get('totalSpent', 0)
        proposals = (details.get('stats') or {}).get('proposals', 'N/A')

        # Job Metadata
        job_type = job_tile.get('jobType', 'N/A')
        contractor_tier = job_tile.get('contractorTier')
        tier_map = {1: "Entry", 2: "Intermediate", 3: "Expert"}
        experience_level = tier_map.get(contractor_tier, str(contractor_tier))
        published_time = job_tile.get('publishTime', 'N/A')
        
        hourly_duration = job_tile.get('hourlyEngagementDuration') or {}
        fixed_duration = job_tile.get('fixedPriceEngagementDuration') or {}
        duration = hourly_duration.get('label') or fixed_duration.get('label') or 'N/A'

        skills = job.get('ontologySkills') or []
        skill_names = [s.get('prefLabel') for s in skills if s.get('prefLabel')]
        skills_text = ", ".join(skill_names[:15]) if skill_names else "N/A"

        job_url = f"https://www.upwork.com/jobs/~{ciphertext.lstrip('~')}"

        # ----------------------------------------
        # MAIN DISCORD MESSAGE (Cleaned Up)
        # ----------------------------------------
        main_msg = f"■ **New Job Posted!**\n**Title**: {title}"

        # ----------------------------------------
        # THREAD MESSAGE (Full Info)
        # ----------------------------------------
        thread_msg = f"""
**Full Job Description**:
{description}

---

**Job Details**:
• **Budget**: {budget}
• **Experience**: {experience_level}
• **Proposals**: {proposals}
• **Job Type**: {job_type}
• **Duration**: {duration}
• **Published**: {published_time}

**Skills**: 
{skills_text}

**Client Details**:
• **Total Spent**: ${spent:,.0f}
• **Location**: {location}

---

[Apply on Upwork]({job_url})
"""

        # ----------------------------------------
        # POST TO DISCORD
        # ----------------------------------------
        if await bot.post_job(main_msg, thread_msg, f"{label}: {job_id}", target_channel_id=channel_id):
            db.mark_job_as_seen(
                job_id=job_id,
                url_source=url_source,
                title=title,
                budget=budget,
                proposals=proposals,
                location=location,
                total_spent=spent,
                description=description,
                job_type=job_type,
                experience_level=experience_level,
                duration=duration,
                published_time=published_time,
                skills=skills_text
            )
            logger.info(f"✅ Posted: {title}")
            await asyncio.sleep(1)


# ---------------------------------------------------
# WORKER
# ---------------------------------------------------

async def url_worker(url, channel_id, label):
    query_params = parse_qs(urlparse(url).query)
    query = unquote(query_params['q'][0]) if 'q' in query_params else label
    logger.info(f"👷 Worker started: {label}")

    # Backfill (200 jobs)
    for offset in [150, 100, 50, 0]:
        try:
            if await asyncio.to_thread(scraper.ensure_auth):
                results = await asyncio.to_thread(scraper.fetch_search, query, offset)
                await process_batch(results, channel_id, label, url)
        except Exception as e:
            logger.error(f"Backfill Error ({label}): {e}")
        await asyncio.sleep(2)

    # Live Loop
    while True:
        try:
            process = psutil.Process(os.getpid())
            mem = process.memory_info().rss / 1024 / 1024
            logger.info(f"📊 Memory: {mem:.2f} MB")

            if datetime.datetime.now().hour == 3 and datetime.datetime.now().minute == 0:
                db.cleanup_old_jobs()

            if await asyncio.to_thread(scraper.ensure_auth):
                results = await asyncio.to_thread(scraper.fetch_search, query, offset=0)
                await process_batch(results, channel_id, label, url)

            await asyncio.sleep(60)
        except asyncio.CancelledError:
            logger.info(f"🛑 Worker stopped: {label}")
            break
        except Exception as e:
            logger.error(f"⚠️ Worker Error ({label}): {e}")
            await asyncio.sleep(30)


# ---------------------------------------------------
# COMMANDS & EVENTS
# ---------------------------------------------------

@bot.command(name="track")
async def track(ctx, query: str, *, label: str = None):
    url = f"https://www.upwork.com/nx/search/jobs/?q={query.replace(' ', '%20')}"
    track_label = label if label else query
    await ctx.send(f"🔍 Validating `{track_label}`...")

    channel_name = track_label.lower().replace(" ", "-")
    channel = discord.utils.get(ctx.guild.text_channels, name=channel_name) or await ctx.guild.create_text_channel(channel_name)

    if await asyncio.to_thread(scraper.ensure_auth):
        results = await asyncio.to_thread(scraper.fetch_search, query)
        valid_match = any(track_label.lower() in (j.get('title', '') + j.get('description', '')).lower() for j in (results or []))
        if not valid_match:
            await ctx.send(f"❌ No public jobs found for `{track_label}`.")
            return

    config = load_config()
    config['tracked_urls'] = [t for t in config['tracked_urls'] if t['label'].lower() != track_label.lower()]
    config['tracked_urls'].append({"url": url, "channel_id": channel.id, "label": track_label})
    with open('config.json', 'w') as f:
        json.dump(config, f, indent=4)

    if track_label in active_tasks:
        active_tasks[track_label].cancel()
    active_tasks[track_label] = bot.loop.create_task(url_worker(url, channel.id, track_label))
    await ctx.send(f"🚀 Now tracking `{track_label}`!")

@bot.command(name="stop")
async def stop(ctx, *, label: str):
    config = load_config()
    if label in active_tasks:
        active_tasks[label].cancel()
        del active_tasks[label]
    config['tracked_urls'] = [t for t in config['tracked_urls'] if t['label'].lower() != label.lower()]
    with open('config.json', 'w') as f:
        json.dump(config, f, indent=4)
    await ctx.send(f"🛑 Stopped tracking `{label}`.")

@bot.event
async def on_ready():
    logger.info(f"✅ Bot online as {bot.user}")
    config = load_config()
    for t in config.get('tracked_urls', []):
        if t['label'] not in active_tasks:
            active_tasks[t['label']] = bot.loop.create_task(url_worker(t['url'], t['channel_id'], t['label']))

async def main():
    async with bot:
        await bot.start(TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Bot shut down.")
