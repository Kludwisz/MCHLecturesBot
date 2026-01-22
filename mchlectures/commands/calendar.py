from mchlectures.gcalendar.service import CalendarService

import discord
from enum import Enum


class CalendarScope(Enum):
    THIS_WEEK = "this-week"
    WEEK = "week"
    MONTH = "month"
    TWO_MONTHS = "2-months"


class Calendar(discord.Cog):
    def __init__(self):
        self.calendar_service = CalendarService()
        self.calendar_service.connect()

    @discord.slash_command(name="calendar", description="Renders a selected view of the lecture calendar")
    @discord.option(name="scope", default=CalendarScope.WEEK, type=CalendarScope)
    async def calendar(self, ctx: discord.ApplicationContext, scope: CalendarScope):
        await self.calendar_service.render_calendar_to_file(scope=scope.value, filename="calendar.png")
        
        file = discord.File("calendar.png")
        embed = discord.Embed(title=f"Lecture calendar")
        embed.set_image(url="attachment://calendar.png")
        
        await ctx.respond(embed=embed, file=file)


def setup(bot: discord.Bot):
    bot.add_cog(Calendar())
