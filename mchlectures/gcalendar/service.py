'''
/add_event --> open dialog with a form
/my_events --> sends a message with dropdowns and args (update existing, delete existing, browse)
/upcoming_events num_events:int --> pages of events & buttons for nav
(implemented) /calendar [this-week|week|month|2-months] --> renders the requested calendar (link to calendar embedded in browser?)
Post-MVP: /notifyme (event)?
'''

from .gcalendar import Lecture, Calendar
from .renderer import Renderer
from .dateutils import *
from dotenv import dotenv_values
from io import BytesIO
import arrow


class CalendarService:
    def __init__(self):
        self.config = dotenv_values(".env")
        self.calendar_client: Calendar
        self.renderer: Renderer
        
    def connect(self):
        self.calendar_client = Calendar(
            self.config["ACCOUNT_EMAIL"],
            self.config["SERVICE_ACCOUNT_SECRET"]
        )
        self.renderer = Renderer(self.calendar_client)

    async def render_calendar_to_file(self, scope: str) -> BytesIO:
        """
        :param scope: Either 'this-week', 'week', 'month', or '2-months' - defines the scope of the calendar
        :return: a byte buffer containing the png file
        """
        AVAILABLE_SCOPES = {
            'this-week': lambda: (
                snap_to_week_start(arrow.now()), 
                snap_to_week_start(arrow.now()).shift(days=7, seconds=-1)
            ),
            'week': lambda: (snap_to_day_start(arrow.now()), arrow.now().shift(days=7)),
            'month': lambda: (snap_to_day_start(arrow.now()), arrow.now().shift(months=1)),
            '2-months': lambda: (snap_to_day_start(arrow.now()), arrow.now().shift(months=2))
        }
        CELL_SIZES = {
            'this-week': None,
            'week': None,
            'month': (120, 120),
            '2-months': (120, 100)
        }
        if not scope in AVAILABLE_SCOPES.keys():
            raise ValueError(f'illegal calendar scope: {scope}')
        
        # render to in-memory buffer
        buffer = BytesIO()
        start, end = AVAILABLE_SCOPES[scope]()
        if CELL_SIZES[scope] is not None:
            await self.renderer.render(start, end, buffer, *CELL_SIZES[scope])
        else:
            await self.renderer.render(start, end, buffer)
        buffer.seek(0)
        return buffer
        
    async def get_upcoming_lectures(self, limit: int = 1, userid: str = None, query_text: str = None) -> list[Lecture]:
        """
        :param limit: the maximum number of upcoming lectures (must be positive). Default 1.
        :return: list of at most `limit` lectures that are either currently in progress or will happen in the future, sorted by the event start time.
        """
        if limit <= 0:
            raise ValueError(f"limit must be positive, got {limit}")
        
        t_now = arrow.now()
        search_start = t_now.shift(days=-1)  # to handle in-progress events
        data = await self.calendar_client.get_event_list(timeMin=search_start, discord_userid=userid, query_text=query_text)
        lectures = [Lecture.from_json(item) for item in data["items"]]
        for i in range(len(lectures)):
            end = lectures[i].start_time.shift(minutes=lectures[i].duration_minutes)
            if (end - t_now).total_seconds() > 0:
                return lectures[i:min(i+limit, len(lectures))]
        return []

    async def assert_event_valid(self, data: Lecture):
        """
        Checks whether the provided lecture can be scheduled according to internally defined business rules.
        Returns gracefully if no conflicts are detected and raises a descriptive ValueError otherwise
        """
        # no other lectures within N days of the scheduled one
        CONFLICT_THRESHOLD = 1  # days
        filter_start = data.start_time.shift(days=-CONFLICT_THRESHOLD)
        filter_end = data.start_time.shift(days=CONFLICT_THRESHOLD)
        potential_conflicts = await self.calendar_client.get_event_list(timeMin=filter_start, timeMax=filter_end)
        
        confl_count = len(potential_conflicts["items"])
        if confl_count == 0:
            return
        if confl_count > 1:
            raise ValueError("lectures can't be scheduled within 24 hours of other lectures")
        
        conflicting = Lecture.from_json(potential_conflicts["items"][0])
        if conflicting.id != data.id:
            raise ValueError("lectures can't be re-scheduled within 24 hours of other lectures")

    async def create_new_lecture(self, data: Lecture) -> str:
        """
        :param data: The data of the requested lecture
        :type data: Lecture
        :return: the ID of the created lecture
        """
        await self.assert_event_valid(data)
        return await self.calendar_client.create_event(data)

    async def delete_lecture(self, lecture: Lecture):
        await self.calendar_client.delete_event(lecture.id)

    async def update_lecture(self, data: Lecture):
        await self.assert_event_valid(data)
        await self.calendar_client.update_event(data)
    