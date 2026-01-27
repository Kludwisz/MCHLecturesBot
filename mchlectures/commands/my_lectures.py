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

import arrow

import discord
from discord.ui import DesignerModal, View, Button, InputText, Label


# -------------------------------------------------------------------
# View 3
class OperationStatusView(View):
    pass

# -------------------------------------------------------------------
# View 5
class LectureCancelConfirmationView(View):
    pass

# -------------------------------------------------------------------
# View 4
class LectureModificationView(View):
    pass

# -------------------------------------------------------------------
# Modal 2
class LectureDetailsModal(DesignerModal):
    def __init__(self, service: CalendarService, first_modal: DesignerModal, *args, **kwargs):
        super().__init__(title="Lecture details", *args, **kwargs)
        self.service = service
        self.first_modal = first_modal

        format_input = InputText(
            placeholder="E.g. whiteboard presentation",
            max_length=50
        )
        description_input = InputText(
            style=discord.InputTextStyle.long,
            placeholder="Type a short description of your lecture here..."
        )
        knowledge_input = InputText(
            style=discord.InputTextStyle.long,
            placeholder="What do participants need to know to enjoy your lecture?"
        )

        self.add_item(Label("Lecture format", item=format_input))
        self.add_item(Label("Lecture description", item=description_input))
        self.add_item(Label("Recommended prior knowledge", item=knowledge_input))

    async def callback(self, interaction: discord.Interaction):
        try:
            basic_info = self.first_modal.children
            details = self.children

            start_time = arrow.get(basic_info[1].value, "DD.MM.YYYY HH:mm")
            new_lecture = Lecture(
                title = basic_info[0].value,
                start_time = start_time,
                duration_minutes = int(basic_info[2].value),
                extended_properties = ExtendedProperties(
                    discord_userid = str(interaction.user.id),
                    discord_username = interaction.user.display_name,
                    recording_perms = basic_info[3],
                    lecture_format = details[0].value,
                    description = details[1].value,
                    prior_knowledge = details[2].value
                )
            )
            await self.service.create_new_lecture(new_lecture)
            await interaction.response.send_message(f"Lecture **\"{new_lecture.title}\"** scheduled successfully!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Invalid data: {e}", ephemeral=True)


# -------------------------------------------------------------------
# Modal 1
class LectureBasicInfoModal(DesignerModal):
    def __init__(self, service: CalendarService, *args, **kwargs):
        super().__init__(title="Lecture information", *args, **kwargs)
        self.service = service

        title_input = discord.ui.InputText(
            placeholder="E.g. Strings in Python"
        )
        datetime_input = discord.ui.InputText(
           placeholder="DD.MM.YYYY HH:MM (e.g. 20.02.2026 18:00)",
           min_length=16, max_length=16
        )
        minutes_duration_input = discord.ui.Select(
            options=[
                discord.SelectOption(label=f"{m} minutes", value=str(m)) for m in [
                    30, 45, 60, 75, 90, 120
                ]
            ]
        )
        recording_perms_input = discord.ui.Select(
            options=[
                discord.SelectOption(label=RECORDING_PERMS_SHORT[k], value=k) for k in RECORDING_PERMS_SHORT.keys()
            ]
        )

        self.add_item(discord.ui.Label("Title", item=title_input))
        self.add_item(discord.ui.Label("Date & time", item=datetime_input))
        self.add_item(discord.ui.Label("Duration", item=minutes_duration_input))
        self.add_item(discord.ui.Label("Recording permissions", item=recording_perms_input))

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
class LectureManagerView(View):
    def __init__(self, lectures: list[Lecture], user: discord.User, service: CalendarService):
        super().__init__(timeout=120, disable_on_timeout=True)
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
        embed.add_field(name="Description", value=(desc[:500] + '...') if len(desc) > 500 else desc, inline=False)
        
        return embed

    def update_buttons(self):
        # handle button states if user has no lectures
        self.prev_page.disabled = self.page_index <= 0
        self.next_page.disabled = self.page_index >= len(self.lectures) - 1
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

    @discord.ui.button(label="Schedule new lecture", style=discord.ButtonStyle.green, row=2)
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
        await interaction.response.send_message(f"(delete functionality not implemented)")
