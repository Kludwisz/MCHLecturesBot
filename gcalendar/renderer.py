from .gcalendar import Calendar
from .dateutils import *
from PIL import Image, ImageDraw, ImageFont
import pprint
import arrow

# Style params -------------------
CELL_WIDTH_PX = 150
CELL_HEIGHT_PX = 100
HEADER_HEIGHT_PX = 30

FONT_H1_SIZE = 20
FONT_H2_SIZE = 16
FONT_P_SIZE = 14
FONT_H1 = ImageFont.load_default(FONT_H1_SIZE)
FONT_H2 = ImageFont.load_default(FONT_H2_SIZE)
FONT_P = ImageFont.load_default(FONT_P_SIZE)

PADDING = 5
DAY_BORDER_WIDTH = 2
DAY_BORDER_COLOR = 0x4A4040
DAY_TEXT_COLOR = 0x8A8080
DAY_FONT_SIZE = 16

BACKGROUND_COLOR = 0x2A2020

# --------------------------------


class Renderer:
    def __init__(self, calendar: Calendar):
        self.calendar: Calendar = calendar
        self.cache: list[tuple[str, Image.Image]] = []  # simple LRC cache
        self.MAX_CACHE_SIZE = 5

    def render_day(self, drawer: ImageDraw.ImageDraw, lecture_data, day_of_week, week, base_date: arrow.Arrow):
        W, H = CELL_WIDTH_PX, CELL_HEIGHT_PX
        xmin, ymin = day_of_week * W, week * H + HEADER_HEIGHT_PX
        
        # outline, day number
        drawer.rectangle([xmin, ymin, xmin+W, ymin+H], outline=DAY_BORDER_COLOR, width=DAY_BORDER_WIDTH)
        drawer.text((xmin+DAY_BORDER_WIDTH + PADDING, ymin), f'{base_date.datetime.day}', fill=DAY_TEXT_COLOR, font=FONT_H1)

        # table header
        for day in range(1, 8):
            day_name = DAY_NAMES[day][:3]
            bbox = FONT_H1.getbbox(day_name)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            drawer.text(
                (W//2 - text_w//2 + (day-1) * W, HEADER_HEIGHT_PX - 2*PADDING - text_h), 
                day_name, DAY_TEXT_COLOR, FONT_H1
            )

        for lecture in lecture_data:
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
        img = Image.new("RGB", (7*CELL_WIDTH_PX, n_weeks*CELL_HEIGHT_PX + HEADER_HEIGHT_PX), BACKGROUND_COLOR)
        
        # fetch lecture data
        data = await self.calendar.get_event_list(timeMin=cal_start, timeMax=cal_end)
        lectures = data['items']

        drawer = ImageDraw.Draw(img)
        for week in range(n_weeks):
            for day in range(7):
                self.render_day(drawer, lectures, day, week, cal_start.shift(days=(week*7 + day)))

        # update cache
        if len(self.cache) == self.MAX_CACHE_SIZE:
            self.cache.pop(0)
        self.cache.append((render_key, img))
        img.save(filepath)


