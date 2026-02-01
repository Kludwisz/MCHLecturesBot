import os
import signal
import asyncio
from dotenv import dotenv_values

import discord


class MchBot(discord.Bot):
    def __init__(self):
        super().__init__()
        self.active_views: dict[int, tuple[discord.ui.View, discord.Message]] = {}

    def load_commands(self):
        for filename in os.listdir("mchlectures/commands"):
            if filename.endswith("_cog.py"):
                self.load_extension(f"mchlectures.commands.{filename[:-3]}")
            
    async def on_connect(self):
        self.load_commands()
        await super().on_connect()

    async def on_ready(self):
        print('bot ready')

    async def shutdown(self):
        for view, message in self.active_views.values():
            try:
                view.disable_all_items()
                view.stop()
                await message.edit(view=view)
            except Exception:
                pass
        self.active_views.clear()
        await self.close()


if __name__ == '__main__':
    conf = dotenv_values()
    bot = MchBot()

    # setup shutdown handlers
    loop = asyncio.get_event_loop()
    def handler(*args):
        loop.create_task(bot.shutdown())
    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)

    bot.run(conf["BOT_TOKEN"])
