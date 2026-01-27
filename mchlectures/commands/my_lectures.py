'''
Views & modals available in /my_lectures:

base command (read)
- view #1: pages of lecture data, with nav buttons and buttons linking to C,U,D functionalities (done)

new lecture flow (create):
- modal #1: fill in first set of fields -> submit
- view #2: display filled-in data, button to edit that data, fill in remaining stuff, cancel
- if edit go back to modal #1
- if continue modal #2 -> submit
- view #3: success / failure

modify lecture flow (update):
- view #4: display details, button to edit basic info, button to edit details, button to cancel, button to save
- if edit basic info: modal #1
- if edit details: modal #2
- if cancel: back to view #1
- if save: view #3 (operation can fail if lecture conflict for example)

cancel lecture flow (delete):
- view #5: "Are you sure you want to cancel", button "Keep lecture", button "Cancel lecture"
- if keep: back to view #1
- if cancel: invoke api call -> view #3 (i guess this operation could fail too)
'''

from mchlectures.gcalendar.gcalendar import Lecture, ExtendedProperties, RECORDING_PERMS_SHORT
from mchlectures.gcalendar.service import CalendarService
from mchlectures.commands.bot_errors import *

import arrow

import discord
from discord.ui import DesignerModal, View, Button, InputText, Label


class PrivateView(View):
    # stores views that this view can go back to when needed
    nav: dict[str, View] = {}

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "You cannot interact with other user's interfaces. Use `/my_lectures` to open your own UI.", 
                ephemeral=True
            )
            return False
        return True

# -------------------------------------------------------------------
# View 3
class OperationStatusView(View):
    pass

# -------------------------------------------------------------------
# View 5
class LectureCancelConfirmationView(PrivateView):
    def __init__(self, lecture: Lecture, user: discord.User, service: CalendarService):
        super().__init__(timeout=120, disable_on_timeout=True)
        self.lecture = lecture
        self.service = service
        self.user = user

    def create_embed(self) -> discord.Embed:
        return discord.Embed(
            title="Confirm lecture cancellation",
            description=f"Are you sure you want to cancel your lecture: \"{self.lecture.title}\"?",
            color=discord.Color.red()
        )
        
    @discord.ui.button(label="Keep lecture", style=discord.ButtonStyle.gray)
    async def keep_lecture(self, button: Button, interaction: discord.Interaction):
        await interaction.response.edit_message(embed=self.nav["main"].create_embed(), view=self.nav["main"])

    @discord.ui.button(label="Cancel lecture", style=discord.ButtonStyle.danger)
    async def cancel_lecture(self, button: Button, interaction: discord.Interaction):
        try:
            await self.service.delete_lecture(self.lecture)
            await interaction.response.edit_message(embed=self.nav["main"].create_embed(), view=self.nav["main"])
        except Exception as e:
            await interaction.respond(embed=error(message=f"Something went wrong while deleting the lecture: {e}"))

# -------------------------------------------------------------------
# View 2
class LectureCreateIntermediateView(PrivateView):
    pass

# -------------------------------------------------------------------
# View 4
class LectureModificationView(PrivateView):
    pass


# -------------------------------------------------------------------
# Modal 2
class LectureDetailsModal(DesignerModal):
    format_input: InputText = None
    description_input: InputText = None
    knowledge_input: InputText = None
    
    def __init__(self, service: CalendarService, first_modal: DesignerModal, *args, **kwargs):
        super().__init__(title="Lecture details", *args, **kwargs)
        self.service = service
        self.first_modal = first_modal

        self.format_input = InputText(
            placeholder="E.g. whiteboard presentation",
            max_length=50
        )
        self.description_input = InputText(
            style=discord.InputTextStyle.long,
            placeholder="Type a short description of your lecture here..."
        )
        self.knowledge_input = InputText(
            style=discord.InputTextStyle.long,
            placeholder="What do participants need to know to enjoy your lecture?"
        )

        self.add_item(Label("Lecture format", item=self.format_input))
        self.add_item(Label("Lecture description", item=self.description_input))
        self.add_item(Label("Recommended prior knowledge", item=self.knowledge_input))

    async def callback(self, interaction: discord.Interaction):
        try:
            # print('data:')
            # print(self.first_modal.title_input.value)
            # print(self.first_modal.datetime_input.value)
            # print(self.first_modal.duration_minutes_input.values[0])
            # print(self.first_modal.recording_perms_input.values[0])
            # print(self.format_input.value)
            # print(self.description_input.value)
            # print(self.knowledge_input.value)

            start_time = arrow.get(self.first_modal.datetime_input.value, "DD.MM.YYYY HH:mm")
            new_lecture = Lecture(
                title = self.first_modal.title_input.value,
                start_time = start_time,
                duration_minutes = int(self.first_modal.duration_minutes_input.values[0]),
                extended_properties = ExtendedProperties(
                    discord_userid = str(interaction.user.id),
                    discord_username = interaction.user.display_name,
                    recording_perms = self.first_modal.recording_perms_input.values[0],
                    lecture_format = self.format_input.value,
                    description = self.description_input.value,
                    prior_knowledge = self.knowledge_input.value
                )
            )
            await self.service.create_new_lecture(new_lecture)
            await interaction.response.send_message(f"Lecture **\"{new_lecture.title}\"** scheduled successfully!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Invalid data: {e}", ephemeral=True)


# -------------------------------------------------------------------
# Modal 1
class LectureBasicInfoModal(DesignerModal):
    title_input: InputText = None
    datetime_input: InputText = None
    duration_minutes_input: discord.ui.Select = None
    recording_perms_input: discord.ui.Select = None

    def __init__(self, service: CalendarService, *args, **kwargs):
        super().__init__(title="Lecture information", *args, **kwargs)
        self.service = service

        self.title_input = discord.ui.InputText(
            placeholder="E.g. Strings in Python"
        )
        self.datetime_input = discord.ui.InputText(
           placeholder="DD.MM.YYYY HH:MM (e.g. 20.02.2026 18:00)",
           min_length=16, max_length=16
        )
        self.duration_minutes_input = discord.ui.Select(
            options=[
                discord.SelectOption(label=f"{m} minutes", value=str(m)) for m in [
                    30, 45, 60, 75, 90, 120
                ]
            ]
        )
        self.recording_perms_input = discord.ui.Select(
            options=[
                discord.SelectOption(label=RECORDING_PERMS_SHORT[k], value=k) for k in RECORDING_PERMS_SHORT.keys()
            ]
        )

        self.add_item(discord.ui.Label("Title", item=self.title_input))
        self.add_item(discord.ui.Label("Date & time", item=self.datetime_input))
        self.add_item(discord.ui.Label("Duration", item=self.duration_minutes_input))
        self.add_item(discord.ui.Label("Recording permissions", item=self.recording_perms_input))

    async def callback(self, interaction: discord.Interaction):
        view = View()
        button = Button(label="Almost done! Click here to continue...", style=discord.ButtonStyle.green)
        view.add_item(button)

        async def button_callback(interaction: discord.Interaction):
            modal = LectureDetailsModal(service=self.service, first_modal=self)
            await interaction.response.send_modal(modal)
        button.callback = button_callback

        await interaction.respond(view=view)
        

# -------------------------------------------------------------------
# View 1
class LectureManagerView(PrivateView):
    def __init__(self, lectures: list[Lecture], user: discord.User, service: CalendarService):
        super().__init__(timeout=120, disable_on_timeout=True)
        self.lectures = lectures
        self.service = service
        self.user = user
        self.page_index = 0

    def create_embed(self) -> discord.Embed:
        if not self.lectures:
            embed = discord.Embed(
                title="Your lectures",
                description="You currently don't have any lectures scheduled.",
                color=discord.Color.blue()
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
        embed.add_field(name="Description", value=(desc[:500] + '...') if len(desc) > 500 else desc, inline=False)
        
        return embed

    def update_buttons(self):
        self.prev_page.disabled = self.page_index <= 0
        self.next_page.disabled = self.page_index >= len(self.lectures) - 1
        # handle button states if user has no lectures
        has_lectures = len(self.lectures) > 0
        self.edit_lecture.disabled = not has_lectures
        self.cancel_lecture.disabled = not has_lectures

    @discord.ui.button(label="Previous page", style=discord.ButtonStyle.gray)
    async def prev_page(self, button: Button, interaction: discord.Interaction):
        self.page_index -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    @discord.ui.button(label="Next page", style=discord.ButtonStyle.gray)
    async def next_page(self, button: Button, interaction: discord.Interaction):
        self.page_index += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    @discord.ui.button(label="Schedule new lecture", style=discord.ButtonStyle.green)
    async def schedule_new(self, button: Button, interaction: discord.Interaction):
        modal = LectureBasicInfoModal(service=self.service)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Modify lecture data", style=discord.ButtonStyle.primary, row=2)
    async def edit_lecture(self, button: Button, interaction: discord.Interaction):
        lecture = self.lectures[self.page_index]
        await interaction.response.send_message(f"(update functionality not implemented)")

    @discord.ui.button(label="Cancel lecture", style=discord.ButtonStyle.danger, row=2)
    async def cancel_lecture(self, button: Button, interaction: discord.Interaction):
        lecture = self.lectures[self.page_index]
        view = LectureCancelConfirmationView(lecture, self.user, self.service)
        view.nav["main"] = self
        await interaction.response.edit_message(embed=view.create_embed(), view=view)
