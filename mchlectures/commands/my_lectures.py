from mchlectures.gcalendar.gcalendar import Lecture, ExtendedProperties
from mchlectures.gcalendar.gcalendar import RECORDING_PERMS_SHORT, RECORDING_PERMS
from mchlectures.gcalendar.service import CalendarService
from mchlectures.commands.bot_utils import *

import arrow
from enum import Enum

import discord
from discord.ui import DesignerModal, View, Button, InputText, Label


class UIState(Enum):
    MAIN = 0
    CREATE = 1
    UPDATE = 2
    DELETE = 3

# -------------------------------------------------------------------
# Modals

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

class LectureManagerBase(View):
    page_index = 0
    lectures: list[Lecture] = []
    lecture: Lecture = None
    new_lecture_data: dict[str, str] = {}
    service: CalendarService = None
    user: discord.User = None

    # buttons that require state changes are stored here
    save_data: Button = None
    prev_page: Button = None
    next_page: Button = None
    edit_lecture: Button = None
    cancel_lecture: Button = None
    schedule_new: Button = None

    def statechange(self, state: UIState): pass
    def create_embed(self): pass
    def create_buttons(self): pass
    def update_buttons(self): pass
    def handle_lecture_cancelled(self, event_id: str): pass
    def handle_lecture_created(self, new_lecture: Lecture): pass

class ViewBuilder:
    def __init__(self, view: LectureManagerBase):
        self.view = view

    def create_embed(self) -> discord.Embed:
        raise NotImplementedError("All subclasses of ViewState must implement create_embed")

    def create_buttons(self):
        raise NotImplementedError("All subclasses of ViewState must implement create_buttons")

    def update_buttons(self):
        return

# -------------------------------------------------------------------
# Lecture cancellation viewstate (done)
class LectureCancelConfirmationBuilder(ViewBuilder):
    def __init__(self, view: LectureManagerBase):
        self.view = view

    def create_embed(self) -> discord.Embed:
        return discord.Embed(
            title="Confirm lecture cancellation",
            description=f"Are you sure you want to cancel your lecture: \"{self.view.lecture.title}\"?",
            color=discord.Color.red()
        )
    
    def create_buttons(self):
        view = self.view
        async def keep_lecture(self, button: Button, interaction: discord.Interaction):
            await interaction.response.edit_message(embed=view.create_embed(), view=view)
        keep_button = Button(
            label="Keep lecture",
            style=discord.ButtonStyle.gray,
        )
        keep_button.callback = keep_lecture
        self.view.add_item(keep_button)

        async def cancel_lecture(self, button: Button, interaction: discord.Interaction):
            try:
                await view.service.delete_lecture(view.lecture)
                view.handle_lecture_cancelled(view.lecture.id)
                view.statechange(UIState.MAIN)
                await interaction.response.edit_message(embed=view.create_embed(), view=view)
            except Exception as e:
                await interaction.respond(embed=error(message=f"Something went wrong while deleting the lecture: {e}"))
        yeet_button = Button(
            label="Cancel lecture",
            style=discord.ButtonStyle.danger,
        )
        yeet_button.callback = cancel_lecture
        self.view.add_item(yeet_button)

# -------------------------------------------------------------------
# Shared viewstate for creating & editing lectures (done)
class LectureUpdateBaseBuilder(ViewBuilder):
    embed_color: discord.Color
    embed_title: str

    def create_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=self.embed_title,
            color=self.embed_color
        )
        ld = self.view.new_lecture_data
        embed.add_field(name="Lecture title (required)", value=ld["title"], inline=False)
        embed.add_field(name="Date & time (required)", value=ld["start_date"], inline=True)
        embed.add_field(name="Duration", value=f"{ld["duration_minutes"]} minutes", inline=True)

        rperms = ld["recording_perms"]
        if rperms == "CUSTOM":
            rperms = ld["custom_recording_perms"]
        else:
            rperms = RECORDING_PERMS[rperms]
        embed.add_field(name="Recording permissions", value=limit_characters(rperms, 1024), inline=False)
        
        embed.add_field(name="Lecture description", value=limit_characters(ld["description"], 1024), inline=False)
        embed.add_field(name="Lecture format", value=limit_characters(ld["format"], 1024), inline=True)
        embed.add_field(name="Recommended prior knowledge", value=limit_characters(ld["prior_knowledge"], 1024), inline=True)

        return embed
    
    def create_buttons(self):
        view = self.view

        async def edit_basic(self, button: Button, interaction: discord.Interaction):
            modal = LectureBasicInfoModal(view)
            await interaction.response.send_modal(modal)
        edit_basic_button = Button(
            label="Edit basic info",
            style=discord.ButtonStyle.primary,
        )
        edit_basic_button.callback = edit_basic
        self.view.add_item(edit_basic_button)

        async def edit_details(self, button: Button, interaction: discord.Interaction):
            modal = LectureDetailsModal(view)
            await interaction.response.send_modal(modal)
        edit_detail_button = Button(
            label="Edit details",
            style=discord.ButtonStyle.primary,
        )
        edit_detail_button.callback = edit_details
        self.view.add_item(edit_detail_button)

    def update_buttons(self):
        valid_data = self.view.new_lecture_data["title"].strip() != ""
        try:
            arrow.get(self.view.new_lecture_data["start_date"], "DD.MM.YYYY HH:mm")
        except Exception as e:
            valid_data = False

        self.view.save_data.disabled = not valid_data
        self.view.save_data.style = discord.ButtonStyle.green if valid_data else discord.ButtonStyle.gray

# -------------------------------------------------------------------
# New lecture viewstate (done)
class LectureCreateBuilder(LectureUpdateBaseBuilder):
    def __init__(self, view: View):
        super().__init__(view)
        self.embed_color = discord.Color.green()
        self.embed_title = "New lecture"
        self.view.new_lecture_data = {
            "title": "",
            "start_date": "",
            "duration_minutes": "60",
            "recording_perms": "NO_RECORDING",
            "custom_recording_perms": "",
            "format": "",
            "description": "",
            "prior_knowledge": ""
        }

    def create_buttons(self):
        super().create_buttons()
        view = self.view
        
        async def save_data(self, button: Button, interaction: discord.Interaction):
            try:
                start_time = arrow.get(view.new_lecture_data["start_date"], "DD.MM.YYYY HH:mm")

                new_lecture = Lecture(
                    title = view.new_lecture_data["title"],
                    start_time = start_time,
                    duration_minutes = int(view.new_lecture_data["duration_minutes"]),
                    extended_properties = ExtendedProperties(
                        discord_userid = str(interaction.user.id),
                        discord_username = interaction.user.display_name,
                        recording_perms = view.new_lecture_data["recording_perms"],
                        lecture_format = view.new_lecture_data["format"],
                        description = view.new_lecture_data["description"],
                        prior_knowledge = view.new_lecture_data["prior_knowledge"],
                        custom_perms = view.new_lecture_data["custom_recording_perms"]
                    )
                )
                lec_id = await view.service.create_new_lecture(new_lecture)
                new_lecture.id = lec_id
                view.handle_lecture_created(new_lecture)
                view.statechange(UIState.MAIN)
                await interaction.response.edit_message(view=view, embed=view.create_embed())
            except Exception as e:
                await interaction.response.send_message(f"Invalid data: {e}", ephemeral=True)
        
        self.view.save_data = Button(
            label="Create lecture",
            style=discord.ButtonStyle.gray,
            disabled=True
        )
        self.view.save_data.callback = save_data
        self.view.add_item(self.view.save_data)

        async def cancel(self, button: Button, interaction: discord.Interaction):
            await interaction.response.edit_message(view=view, embed=view.create_embed())
        cancel_button = Button(
            label="Cancel",
            style=discord.ButtonStyle.gray,
        )
        cancel_button.callback = cancel
        self.view.add_item(cancel_button)

# -------------------------------------------------------------------
# Update existing lecture viewstate
class LectureEditBuilder(LectureUpdateBaseBuilder):
    def __init__(self, view: View):
        super().__init__(view)
        self.embed_title = "Edit lecture"
        self.embed_color = discord.Color.blurple()
        self.view.new_lecture_data = {
            "title": self.view.lecture.title,
            "start_date": self.view.lecture.start_time.format("DD.MM.YYYY HH:mm"),
            "duration_minutes": str(self.view.lecture.duration_minutes),
            "recording_perms": self.view.lecture.extended_properties.recording_perms,
            "custom_recording_perms": self.view.lecture.extended_properties.custom_perms,
            "format": self.view.lecture.extended_properties.lecture_format,
            "description": self.view.lecture.extended_properties.description,
            "prior_knowledge": self.view.lecture.extended_properties.prior_knowledge
        }

    def create_buttons(self):
        super().create_buttons()
        view = self.view

        async def save_data(self, button: Button, interaction: discord.Interaction):
            try:
                start_time = arrow.get(view.new_lecture_data["start_date"], "DD.MM.YYYY HH:mm")

                new_lecture = Lecture(
                    id=view.lecture.id,
                    title = view.new_lecture_data["title"],
                    start_time = start_time,
                    duration_minutes = int(view.new_lecture_data["duration_minutes"]),
                    extended_properties = ExtendedProperties(
                        discord_userid = view.lecture.extended_properties.discord_userid,
                        discord_username = view.lecture.extended_properties.discord_username,
                        recording_perms = view.new_lecture_data["recording_perms"],
                        lecture_format = view.new_lecture_data["format"],
                        description = view.new_lecture_data["description"],
                        prior_knowledge = view.new_lecture_data["prior_knowledge"],
                        custom_perms = view.new_lecture_data["custom_recording_perms"]
                    )
                )
                
                await view.service.update_lecture(new_lecture)
                view.handle_lecture_cancelled(new_lecture.id)
                view.handle_lecture_created(new_lecture)
                view.statechange(UIState.MAIN)
                await interaction.response.edit_message(view=view, embed=view.create_embed())

            except Exception as e:
                await interaction.response.send_message(f"Invalid data: {e}", ephemeral=True)

        self.view.save_data = Button(
            label="Save changes",
            style=discord.ButtonStyle.green
        )
        self.view.save_data.callback = save_data
        self.view.add_item(self.view.save_data)

        async def cancel(self, button: Button, interaction: discord.Interaction):
            await interaction.response.edit_message(view=view, embed=view.create_embed())
        cancel_button = Button(
            label="Cancel",
            style=discord.ButtonStyle.gray,
        )
        cancel_button.callback = cancel
        self.view.add_item(cancel_button)

# -------------------------------------------------------------------
# Browse lectures viewstate
class LectureBrowseBuilder(ViewBuilder):
    def create_embed(self) -> discord.Embed:
        if not self.view.lectures:
            embed = discord.Embed(
                title="Your lectures",
                description="You currently don't have any lectures scheduled.",
                color=discord.Color.dark_gold()
            )
            return embed

        self.view.page_index = min(self.view.page_index, len(self.view.lectures)-1)
        lecture: Lecture = self.view.lectures[self.view.page_index]
        #end_time = lecture.start_time.shift(minutes=lecture.duration_minutes)
        
        embed = discord.Embed(
            title=f"Manage lecture: {self.view.lecture.title}",
            color=discord.Color.dark_gold(),
            description=f"Page {self.view.page_index + 1} out of {len(self.view.lectures)}"
        )
        
        embed.add_field(name="Date and time", value=f"<t:{int(lecture.start_time.timestamp())}:F>", inline=False)
        embed.add_field(name="Duration", value=f"{lecture.duration_minutes} min", inline=True)
        embed.add_field(name="Format", value=lecture.extended_properties.lecture_format, inline=True)
        
        desc = lecture.extended_properties.description
        embed.add_field(name="Description", value=limit_characters(desc, 500), inline=False)
        
        return embed
    
    def create_buttons(self):
        view = self.view

        async def prev_page(self, button: Button, interaction: discord.Interaction):
            view.page_index -= 1
            view.update_buttons()
            await interaction.response.edit_message(embed=view.create_embed(), view=view)
        view.prev_page = Button(
            label="Previous page", 
            style=discord.ButtonStyle.gray
        )
        view.prev_page.callback = prev_page
        view.add_item(view.prev_page)

        async def next_page(self, button: Button, interaction: discord.Interaction):
            view.page_index += 1
            view.update_buttons()
            await interaction.response.edit_message(embed=view.create_embed(), view=view)
        view.next_page = Button(
            label="Next page", 
            style=discord.ButtonStyle.gray
        )
        view.next_page.callback = next_page
        view.add_item(view.next_page)

        async def schedule_new(self, button: Button, interaction: discord.Interaction):
            view.statechange(UIState.CREATE)
            await interaction.response.edit_message(embed=view.create_embed(), view=view)
        view.schedule_new = Button(
            label="Schedule new lecture", 
            style=discord.ButtonStyle.green
        )
        view.schedule_new.callback = schedule_new
        view.add_item(view.schedule_new)

        async def edit_lecture(self, button: Button, interaction: discord.Interaction):
            view.lecture = view.lectures[view.page_index]
            view.statechange(UIState.UPDATE)
            await interaction.response.edit_message(embed=view.create_embed(), view=view)
        view.edit_lecture = Button(
            label="Edit lecture data", 
            style=discord.ButtonStyle.primary,
            row=2
        )
        view.edit_lecture.callback = edit_lecture
        view.add_item(view.edit_lecture)

        async def cancel_lecture(self, button: Button, interaction: discord.Interaction):
            view.lecture = view.lectures[view.page_index]
            view.statechange(UIState.DELETE)
            await interaction.response.edit_message(embed=view.create_embed(), view=view)
        view.cancel_lecture = Button(
            label="Cancel lecture", 
            style=discord.ButtonStyle.danger,
            row=2
        )
        view.cancel_lecture.callback = cancel_lecture
        view.add_item(view.cancel_lecture)

    def update_buttons(self):
        self.view.prev_page.disabled = self.view.page_index <= 0
        self.view.next_page.disabled = self.view.page_index >= len(self.view.lectures) - 1
        # handle button states if user has no lectures
        has_lectures = len(self.view.lectures) > 0
        self.view.edit_lecture.disabled = not has_lectures
        self.view.cancel_lecture.disabled = not has_lectures
        # ...and if user has too many
        has_too_many_lectures = len(self.view.lectures) >= 10
        self.view.schedule_new.disabled = has_too_many_lectures


# -------------------------------------------------------------------
# View class - handles UI display based on the current state
class LectureManagerView(LectureManagerBase):
    BUILDER_BUILDERS = {
        UIState.MAIN: lambda x: LectureBrowseBuilder(x),
        UIState.CREATE: lambda x: LectureCreateBuilder(x),
        UIState.UPDATE: lambda x: LectureEditBuilder(x),
        UIState.DELETE: lambda x: LectureCancelConfirmationBuilder(x),
    }

    def __init__(self, lectures: list[Lecture], user: discord.User, service: CalendarService):
        super().__init__(timeout=120, disable_on_timeout=True)
        self.service = service
        self.user = user
        self.page_index = 0
        
        self.lectures = lectures
        self.lecture: Lecture = lectures[self.page_index]
        self.new_lecture_data: dict[str, str] = {}

        self.current_state = UIState.MAIN
        self.view_builder = LectureBrowseBuilder(self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "You cannot interact with other user's interfaces. Use `/my_lectures` to open your own UI.", 
                ephemeral=True
            )
            return False
        return True

    def statechange(self, state: UIState):
        self.clear_items()
        self.current_state = state
        self.view_builder = self.BUILDER_BUILDERS[self.current_state](self)
        self.create_buttons()
        self.update_buttons()

    def create_embed(self):
        return self.view_builder.create_embed()
    
    def create_buttons(self):
        self.view_builder.create_buttons()

    def update_buttons(self):
        self.view_builder.update_buttons()

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
