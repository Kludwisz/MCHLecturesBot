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

from mchlectures.gcalendar.gcalendar import Lecture, ExtendedProperties
from mchlectures.gcalendar.gcalendar import RECORDING_PERMS_SHORT, RECORDING_PERMS
from mchlectures.gcalendar.service import CalendarService
from mchlectures.commands.bot_utils import *

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
            self.nav["main"].handle_lecture_cancelled(self.lecture.id)
            await interaction.response.edit_message(embed=self.nav["main"].create_embed(), view=self.nav["main"])
        except Exception as e:
            await interaction.respond(embed=error(message=f"Something went wrong while deleting the lecture: {e}"))


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
    recording_perms_input: discord.ui.Select = None
    custom_perms_input: InputText = None
    
    def __init__(self, view: View, *args, **kwargs):
        super().__init__(title="Edit lecture details", *args, **kwargs)
        self.view = view

        self.format_input = InputText(
            placeholder="E.g. whiteboard presentation",
            value=(None if view.new_lecture_data["format"] == "" else view.new_lecture_data["format"]),
            required=False,
            max_length=50
        )
        self.description_input = InputText(
            style=discord.InputTextStyle.long,
            value=(None if view.new_lecture_data["description"] == "" else view.new_lecture_data["description"]),
            required=False,
            placeholder="Type a short description of your lecture here..."
        )
        self.knowledge_input = InputText(
            style=discord.InputTextStyle.long,
            value=(None if view.new_lecture_data["prior_knowledge"] == "" else view.new_lecture_data["prior_knowledge"]),
            required=False,
            placeholder="What do participants need to know to enjoy your lecture?"
        )

        selected_perms = view.new_lecture_data["recording_perms"]
        self.recording_perms_input = discord.ui.Select(
            options=[
                discord.SelectOption(
                    label=RECORDING_PERMS_SHORT[k], 
                    value=k,
                    default=(k == selected_perms)
                ) for k in RECORDING_PERMS_SHORT.keys()
            ]
        )
        self.custom_perms_input = InputText(
            style=discord.InputTextStyle.long,
            value=(None if view.new_lecture_data["custom_recording_perms"] == "" else view.new_lecture_data["custom_recording_perms"]),
            required=False,
            placeholder="(If applicable) specify recording license for your lecture."
        )

        self.add_item(Label("Lecture format", item=self.format_input))
        self.add_item(Label("Lecture description", item=self.description_input))
        self.add_item(Label("Recommended prior knowledge", item=self.knowledge_input))
        self.add_item(Label("Recording permissions", item=self.recording_perms_input))
        self.add_item(Label("Custom recording permissions", item=self.custom_perms_input))

    async def callback(self, interaction: discord.Interaction):
        self.view.new_lecture_data["format"] = self.format_input.value
        self.view.new_lecture_data["description"] = self.description_input.value
        self.view.new_lecture_data["prior_knowledge"] = self.knowledge_input.value
        self.view.new_lecture_data["recording_perms"] = self.recording_perms_input.values[0]
        self.view.new_lecture_data["custom_recording_perms"] = self.custom_perms_input.value
        await interaction.response.edit_message(view=self.view, embed=self.view.create_embed())


# -------------------------------------------------------------------
# Modal 1
class LectureBasicInfoModal(DesignerModal):
    title_input: InputText = None
    datetime_input: InputText = None
    duration_minutes_input: discord.ui.Select = None
    

    def __init__(self, view: View, *args, **kwargs):
        super().__init__(title="Edit lecture information", *args, **kwargs)
        self.view = view

        self.title_input = discord.ui.InputText(
            value=view.new_lecture_data["title"]
        )

        self.datetime_input = discord.ui.InputText(
            placeholder="DD.MM.YYYY HH:MM (e.g. 20.02.2026 18:00)",
            value=(None if view.new_lecture_data["start_date"] == "" else view.new_lecture_data["start_date"]),
            min_length=16, max_length=16
        )

        selected_duration = int(view.new_lecture_data["duration_minutes"])
        self.duration_minutes_input = discord.ui.Select(
            options=[
                discord.SelectOption(
                    label=f"{m} minutes", 
                    value=str(m),
                    default=(m == selected_duration)
                ) for m in [30, 45, 60, 75, 90, 120]
            ]
        )

        self.add_item(discord.ui.Label("Title", item=self.title_input))
        self.add_item(discord.ui.Label("Date & time", item=self.datetime_input))
        self.add_item(discord.ui.Label("Duration", item=self.duration_minutes_input))
        

    async def callback(self, interaction: discord.Interaction):
        self.view.new_lecture_data["title"] = self.title_input.value
        self.view.new_lecture_data["start_date"] = self.datetime_input.value
        self.view.new_lecture_data["duration_minutes"] = self.duration_minutes_input.values[0]
        self.view.update_buttons()

        await interaction.response.edit_message(view=self.view, embed=self.view.create_embed())


# -------------------------------------------------------------------
# View 2
class LectureCreateView(PrivateView):
    basic_info_modal: LectureBasicInfoModal = None
    details_modal: LectureDetailsModal = None

    new_lecture_data: dict[str, str] = {
        "title": "",
        "start_date": "",
        "duration_minutes": "60",
        "recording_perms": "NO_RECORDING",
        "custom_recording_perms": "",
        "format": "",
        "description": "",
        "prior_knowledge": ""
    }

    def __init__(self, user: discord.User, service: CalendarService):
        super().__init__(timeout=120, disable_on_timeout=True)
        self.service = service
        self.user = user
        self.update_buttons()

    def create_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="New lecture",
            color=discord.Color.green()
        )
        embed.add_field(name="Lecture title (required)", value=self.new_lecture_data["title"], inline=False)
        embed.add_field(name="Date & time (required)", value=self.new_lecture_data["start_date"], inline=True)
        embed.add_field(name="Duration", value=f"{self.new_lecture_data["duration_minutes"]} minutes", inline=True)

        rperms = self.new_lecture_data["recording_perms"]
        if rperms == "CUSTOM":
            rperms = self.new_lecture_data["custom_recording_perms"]
        else:
            rperms = RECORDING_PERMS[rperms]
        embed.add_field(name="Recording permissions", value=limit_characters(rperms, 1024), inline=False)
        
        embed.add_field(name="Lecture description", value=limit_characters(self.new_lecture_data["description"], 1024), inline=False)
        embed.add_field(name="Lecture format", value=limit_characters(self.new_lecture_data["format"], 1024), inline=True)
        embed.add_field(name="Recommended prior knowledge", value=limit_characters(self.new_lecture_data["prior_knowledge"], 1024), inline=True)

        return embed

    def update_buttons(self):
        valid_data = self.new_lecture_data["title"].strip() != ""
        try:
            arrow.get(self.new_lecture_data["start_date"], "DD.MM.YYYY HH:mm")
        except Exception as e:
            valid_data = False

        self.save_data.disabled = not valid_data
        self.save_data.style = discord.ButtonStyle.green if valid_data else discord.ButtonStyle.gray

    @discord.ui.button(label="Edit basic info", style=discord.ButtonStyle.primary)
    async def edit_basic(self, button: Button, interaction: discord.Interaction):
        modal = LectureBasicInfoModal(self)
        self.basic_info_modal = modal
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Edit details", style=discord.ButtonStyle.primary)
    async def edit_details(self, button: Button, interaction: discord.Interaction):
        modal = LectureDetailsModal(self)
        self.details_modal = modal
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Create lecture", style=discord.ButtonStyle.gray)
    async def save_data(self, button: Button, interaction: discord.Interaction):
        try:
            start_time = arrow.get(self.new_lecture_data["start_date"], "DD.MM.YYYY HH:mm")

            new_lecture = Lecture(
                title = self.new_lecture_data["title"],
                start_time = start_time,
                duration_minutes = int(self.new_lecture_data["duration_minutes"]),
                extended_properties = ExtendedProperties(
                    discord_userid = str(interaction.user.id),
                    discord_username = interaction.user.display_name,
                    recording_perms = self.new_lecture_data["recording_perms"],
                    lecture_format = self.new_lecture_data["format"],
                    description = self.new_lecture_data["description"],
                    prior_knowledge = self.new_lecture_data["prior_knowledge"],
                    custom_perms = self.new_lecture_data["custom_recording_perms"]
                )
            )
            lec_id = await self.service.create_new_lecture(new_lecture)
            new_lecture.id = lec_id
            self.nav["main"].handle_lecture_created(new_lecture)
            await interaction.response.edit_message(view=self.nav["main"], embed=self.nav["main"].create_embed())

        except Exception as e:
            await interaction.response.send_message(f"Invalid data: {e}", ephemeral=True)


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

        self.page_index = min(self.page_index, len(self.lectures)-1)
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
        # ...and if user has too many
        has_too_many_lectures = len(self.lectures) >= 10
        self.schedule_new.disabled = has_too_many_lectures

    def handle_lecture_cancelled(self, event_id: str):
        for i in range(len(self.lectures)):
            if self.lectures[i].id == event_id:
                self.lectures.pop(i)
                break
        self.update_buttons()

    def handle_lecture_created(self, new_lecture: Lecture):
        # insert to match chronological order
        for i in range(len(self.lectures)):
            lec = self.lectures[i]
            if new_lecture.start_time.is_between(lec.start_time.shift(years=-1000), lec.start_time):
                self.lectures.insert(i, new_lecture)
                self.page_index = i
                self.update_buttons()
                return
        self.lectures.append(new_lecture)
        self.page_index = len(self.lectures) - 1
        self.update_buttons()

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
        view = LectureCreateView(self.user, self.service)
        view.nav["main"] = self
        await interaction.response.edit_message(embed=view.create_embed(), view=view)

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
