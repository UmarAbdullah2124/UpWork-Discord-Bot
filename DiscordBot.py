import discord
import logging
import asyncio
from discord.ext import commands

logger = logging.getLogger("DiscordBot")

class UpworkDiscordBot(commands.Bot):
    def __init__(self, token, channel_id):
        intents = discord.Intents.default()
        intents.message_content = True 
        super().__init__(command_prefix="!", intents=intents)
        self.token = token
        self.default_channel_id = int(channel_id)

    async def post_job(self, main_text, thread_text, thread_name, target_channel_id=None):
        cid = int(target_channel_id) if target_channel_id else self.default_channel_id
        try:
            channel = self.get_channel(cid) or await self.fetch_channel(cid)
            msg = await channel.send(main_text)
            if msg:
                thread = await msg.create_thread(name=thread_name[:95], auto_archive_duration=60)
                # Split description into 1900-character chunks
                chunks = [thread_text[i:i+1900] for i in range(0, len(thread_text), 1900)]
                for chunk in chunks:
                    await thread.send(chunk)
                    await asyncio.sleep(0.5)
                return True
        except Exception as e:
            logger.error(f"❌ Discord Error: {e}")
        return False
