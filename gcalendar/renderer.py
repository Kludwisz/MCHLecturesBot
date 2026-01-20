from .gcalendar import Calendar
from PIL import Image
import pprint
import arrow


def daystring(timepoint: arrow.Arrow) -> str:
    return timepoint.date().isoformat()


class Renderer:
    def __init__(self, calendar: Calendar):
        self.calendar: Calendar = calendar
        self.cache: list[tuple[str, Image.Image]] = []  # simple LRC cache
        self.MAX_CACHE_SIZE = 5
        self.CELL_WIDTH_PX = 100
        self.CELL_HEIGHT_PX = 100

    def render_day(buffer: Image.Image, lecture_data, day_of_week, week):
        pass

    async def render(self, start_date: arrow.Arrow, end_date: arrow.Arrow, filepath: str):
        render_key = daystring(start_date) + ':' + daystring(end_date)
        for key, image in self.cache:
            if key == render_key:
                image.save(filepath)  # use cache
                return
        
        # find first Monday before target date and first Sunday after last date
        cal_start = start_date.shift(days=(-start_date.isoweekday() + 1))
        cal_end = end_date.shift(days=(-end_date.isoweekday() + 7)) 
        n_weeks = ((cal_end - cal_start).days + 1) // 7
        img = Image.new("RGB", (7*self.CELL_WIDTH_PX, n_weeks*self.CELL_HEIGHT_PX))
        
        # fetch lecture data
        data = await self.calendar.get_event_list(timeMin=cal_start, timeMax=cal_end)
        lectures = data['items']
        for week in range(n_weeks):
            for day in range(7):
                self.render_day(img, lectures, day, week)

        # update cache
        if len(self.cache) == self.MAX_CACHE_SIZE:
            self.cache.pop(0)
        self.cache.append((render_key, img))