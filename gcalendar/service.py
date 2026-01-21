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

    async def render_calendar_to_file(self, scope: str, filename: str):
        """
        :param scope: Either 'this-week', 'week', 'month', or '2-months' - defines the scope of the calendar
        :param filename: Save location of the resulting png file
        """
        if not filename.endswith('.png'):
            raise ValueError(f'filename must end with .png, got {filename}')
        
        AVAILABLE_SCOPES = {
            'this-week': lambda: (
                snap_to_week_start(arrow.now()), 
                snap_to_week_start(arrow.now()).shift(days=7, seconds=-1)
            ),
            'week': lambda: (snap_to_day_start(arrow.now()), arrow.now().shift(days=7)),
            'month': lambda: (snap_to_day_start(arrow.now()), arrow.now().shift(months=1)),
            '2-months': lambda: (snap_to_day_start(arrow.now()), arrow.now().shift(months=2))
        }
        if not scope in AVAILABLE_SCOPES.keys():
            raise ValueError(f'illegal calendar scope: {scope}')
        
        start, end = AVAILABLE_SCOPES[scope]()
        #print(start.isoformat(), end.isoformat())
        await self.renderer.render(start, end, filename)
        
    async def get_upcoming_lectures(self, limit: int = 1) -> list[Lecture]:
        """
        :param limit: the maximum number of upcoming lectures (must be positive). Default 1.
        :return: list of at most `limit` lectures that are either currently in progress or will happen in the future, sorted by the event start time.
        """
        if limit <= 0:
            raise ValueError(f"limit must be positive, got {limit}")
        
        t_now = arrow.now()
        search_start = t_now.shift(days=-1)  # to handle in-progress events
        data = await self.calendar_client.get_event_list(timeMin=search_start)
        lectures = [Lecture.from_json(item) for item in data["items"]]
        for i in range(len(lectures)):
            end = lectures[i].start_time.shift(minutes=lectures[i].duration_minutes)
            if (end - t_now).total_seconds() > 0:
                return lectures[i:min(i+limit, len(lectures))]
        return []



    