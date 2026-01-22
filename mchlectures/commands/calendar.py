from mchlectures.gcalendar.service import CalendarService
from mchlectures.commands.util.bot_errors import *
from mchlectures.gcalendar.dateutils import month_name_short

import discord
import arrow
from enum import Enum
from textwrap import dedent


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
    @discord.option(name="query", optional=True)
    async def calendar(self, ctx: discord.ApplicationContext, scope: CalendarScope):
        await self.calendar_service.render_calendar_to_file(scope=scope.value, filename="calendar.png")
        
        file = discord.File("calendar.png")
        embed = discord.Embed(title=f"Lecture calendar")
        embed.set_image(url="attachment://calendar.png")
        
        await ctx.respond(embed=embed, file=file)

    @discord.slash_command(name="upcoming_lectures", description="Returns a list of N upcoming lectures")
    @discord.option(name="limit", default=1, type=int)
    async def upcoming_lectures(self, ctx: discord.ApplicationContext, limit: int):
        try:
            lectures = await self.calendar_service.get_upcoming_lectures(limit)
            list_embed = discord.Embed(title="Upcoming lectures", color=discord.Color.og_blurple())
            for lecture in lectures:
                end = lecture.start_time.shift(minutes=lecture.duration_minutes)
                lecture_now = "RIGHT NOW! " if arrow.now().is_between(lecture.start_time.shift(days=-7), end) else ""
                date_text = f"{lecture_now}<t:{int(lecture.start_time.timestamp())}:F>"
                lecturer = await ctx.interaction.client.fetch_user(414097996956041236)
                text_contents = dedent(f"""
                                        > "{lecture.title}"
                                        > {lecture.duration_minutes} minute lecture by {lecturer.display_name}
                                        """)
                
                list_embed.add_field(name=date_text, value=text_contents, inline=False)
            await ctx.respond(embed=list_embed)

        except ValueError:
            await ctx.respond(embed=invalid_arg_error(message=f"limit={limit}"))


def setup(bot: discord.Bot):
    bot.add_cog(Calendar())
