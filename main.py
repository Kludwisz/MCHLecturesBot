import os
from dotenv import dotenv_values
import discord
from pprint import pprint


class MchBot(discord.Bot):
    def __init__(self):
        super().__init__()

    def load_commands(self):
        for filename in os.listdir("mchlectures/commands"):
            if filename.endswith("cog.py"):
                self.load_extension(f"mchlectures.commands.{filename[:-3]}")
            
    async def on_connect(self):
        self.load_commands()
        await super().on_connect()

    async def on_ready(self):
        print('bot ready')


if __name__ == '__main__':
    conf = dotenv_values()
    bot = MchBot()
    bot.run(conf["BOT_TOKEN"])


# async def main():
#     cs = CalendarService()
#     cs.connect()
#     pprint(await cs.get_upcoming_lectures(limit=2))
#     await cs.render_calendar_to_file(scope='this-week', filename='testThisWeek.png')
#     await cs.render_calendar_to_file(scope='week', filename='testWeek.png')
#     await cs.render_calendar_to_file(scope='month', filename='testMonth.png')
#     await cs.render_calendar_to_file(scope='2-months', filename='test2Months.png')
# if __name__ == '__main__':
#     asyncio.run(main())