from mchlectures.gcalendar.service import CalendarService
from mchlectures.gcalendar.gcalendar import Lecture, ExtendedProperties
from mchlectures.commands.util.bot_errors import *

import discord
from discord.ui import View, Button, button

import arrow
from enum import Enum
from textwrap import dedent


class LectureModal(discord.ui.Modal):
    def __init__(self, service: CalendarService, *args, **kwargs):
        super().__init__(title="Lecture details", *args, **kwargs)
        self.service = service

        self.add_item(discord.ui.InputText(
            label="Title", 
            placeholder="E.g. Strings in Python",
            min_length=3, max_length=100
        ))
        self.add_item(discord.ui.InputText(
            label="Date & time", 
            placeholder="DD.MM.YYYY HH:MM (e.g. 20.02.2026 18:00)",
            min_length=16, max_length=16
        ))
        self.add_item(discord.ui.InputText(
            label="Format", 
            placeholder="E.g. whiteboard presentation",
            max_length=50
        ))
        self.add_item(discord.ui.InputText(
            label="Description", 
            style=discord.InputTextStyle.long,
            placeholder="Type a short description of your lecture here...",
            max_length=1000
        ))

    async def callback(self, interaction: discord.Interaction):
        try:
            start_time = arrow.get(self.children[1].value, "DD.MM.YYYY HH:mm")
            
            new_lecture = Lecture(
                title=self.children[0].value,
                start_time=start_time,
                duration_minutes=90,
                extended_properties=ExtendedProperties(
                    discord_userid=str(interaction.user.id),
                    discord_username=interaction.user.display_name,
                    recording_perms='NO_RECORDING',
                    lecture_format=self.children[2].value,
                    description=self.children[3].value,
                    prior_knowledge='None'
                )
            )
            await self.service.create_new_lecture(new_lecture)

            await interaction.response.send_message(f"Lecture **\"{new_lecture.title}\"** scheduled successfully!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Invalid data: {e}", ephemeral=True)


class LectureManagerView(View):
    def __init__(self, lectures: list[Lecture], user: discord.User, service: CalendarService):
        super().__init__(timeout=120)
        self.lectures = lectures
        self.service = service
        self.user = user
        self.page_index = 0

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "You cannot interact with other user's interfaces. Use `/my_lectures` to open your own UI.", 
                ephemeral=True
            )
            return False
        return True

    def create_embed(self) -> discord.Embed:
        if not self.lectures:
            embed = discord.Embed(
                title="Your lectures",
                description="You currently don't have any lectures scheduled.",
                color=discord.Color.orange()
            )
            return embed

        lecture = self.lectures[self.page_index]
        #end_time = lecture.start_time.shift(minutes=lecture.duration_minutes)
        
        embed = discord.Embed(
            title=f"Manage lecture: {lecture.title}",
            color=discord.Color.blue(),
            description=f"Page {self.page_index + 1} out of {len(self.lectures)}"
        )
        
        embed.add_field(name="Date and time", value=f"<t:{int(lecture.start_time.timestamp())}:F>", inline=False)
        embed.add_field(name="Duration", value=f"{lecture.duration_minutes} min", inline=True)
        embed.add_field(name="Format", value=lecture.extended_properties.lecture_format, inline=True)
        
        desc = lecture.extended_properties.description
        embed.add_field(name="Opis", value=(desc[:500] + '...') if len(desc) > 500 else desc, inline=False)
        
        return embed

    def update_buttons(self):
        # handle button states if user has no lectures
        self.prev_page.disabled = self.page_index <= 0
        self.next_page.disabled = self.page_index >= len(self.lectures) - 1
        has_lectures = len(self.lectures) > 0
        self.edit_lecture.disabled = not has_lectures
        self.cancel_lecture.disabled = not has_lectures

    @button(label="Previous page", style=discord.ButtonStyle.gray)
    async def prev_page(self, button: Button, interaction: discord.Interaction):
        self.page_index -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    @button(label="Next page", style=discord.ButtonStyle.gray)
    async def next_page(self, button: Button, interaction: discord.Interaction):
        self.page_index += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    @button(label="Schedule new lecture", style=discord.ButtonStyle.green, row=2)
    async def schedule_new(self, button: Button, interaction: discord.Interaction):
        modal = LectureModal(service=self.service)
        await interaction.response.send_modal(modal)

    @button(label="Modify lecture data", style=discord.ButtonStyle.primary, row=2)
    async def edit_lecture(self, button: Button, interaction: discord.Interaction):
        lecture = self.lectures[self.page_index]
        await interaction.response.send_message(f"(update functionality not implemented)")

    @button(label="Cancel lecture", style=discord.ButtonStyle.danger, row=2)
    async def cancel_lecture(self, button: Button, interaction: discord.Interaction):
        lecture = self.lectures[self.page_index]
        await interaction.response.send_message(f"(delete functionality not implemented)")


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
        embed.add_field(name="Full calendar:", value="<https://kludwisz.github.io/MCHLecturesBot/>", inline=False)
        
        await ctx.respond(embed=embed, file=file)

    @discord.slash_command(name="upcoming_lectures", description="Returns a list of N upcoming lectures")
    @discord.option(name="limit", default=3, type=int)
    @discord.option(name="query_text", default=None, type=str, required=False)
    async def upcoming_lectures(self, ctx: discord.ApplicationContext, limit: int, query_text: str):
        try:
            lectures = await self.calendar_service.get_upcoming_lectures(limit, query_text=query_text)
            list_embed = discord.Embed(title="Upcoming lectures", color=discord.Color.og_blurple())
            for lecture in lectures:
                end = lecture.start_time.shift(minutes=lecture.duration_minutes)
                lecture_now = "RIGHT NOW! " if arrow.now().is_between(lecture.start_time, end) else ""
                date_text = f"{lecture_now}<t:{int(lecture.start_time.timestamp())}:F>"

                text_contents = dedent(f"""
                                        > "{lecture.title}"
                                        > {lecture.duration_minutes} minute lecture by <@{lecture.extended_properties.discord_userid}>
                                        """)
                
                list_embed.add_field(name=date_text, value=text_contents, inline=False)

            list_embed.add_field(name="Full calendar:", value="<https://kludwisz.github.io/MCHLecturesBot/>", inline=False)
            await ctx.respond(embed=list_embed)

        except ValueError:
            await ctx.respond(embed=invalid_arg_error(message=f"limit={limit}"))

    @discord.slash_command(name="my_lectures", description="Opens an interactive lecture management UI")
    async def my_lectures(self, ctx: discord.ApplicationContext):
        try:
            user_lectures = await self.calendar_service.get_upcoming_lectures(limit=10, userid=str(ctx.author.id))
            view = LectureManagerView(user_lectures, ctx.author, self.calendar_service)
            view.update_buttons()
            await ctx.respond(embed=view.create_embed(), view=view)
        except Exception as e:
            await ctx.respond(embed=error(message=f"{e}"))


def setup(bot: discord.Bot):
    bot.add_cog(Calendar())
