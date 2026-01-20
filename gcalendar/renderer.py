from .gcalendar import Calendar, Lecture
from .dateutils import *
from PIL import Image, ImageDraw, ImageFont
from math import floor, ceil
import pprint
import arrow

# Style params -------------------
CELL_WIDTH_PX = 120
CELL_HEIGHT_PX = 150
HEADER_HEIGHT_PX = 30

#ALWAYS_WRAP_WORDS = True
FONT_H1_SIZE = 20
FONT_H2_SIZE = 16
FONT_P_SIZE = 12
FONT_H1 = ImageFont.load_default(FONT_H1_SIZE)
FONT_H2 = ImageFont.load_default(FONT_H2_SIZE)
FONT_P = ImageFont.load_default(FONT_P_SIZE)

PADDING = 5
DAY_BORDER_WIDTH = 2
DAY_BORDER_COLOR = 0x4A4040
DAY_TEXT_COLOR = 0x8A8080
DAY_FONT_SIZE = 16

BACKGROUND_COLOR = 0x2A2020

LECTURE_COLOR = 0x220011
LECTURE_TEXT_COLOR = 0xFFFFFF

# --------------------------------

def wrap_text_to_fit(text: str, font: ImageFont.ImageFont, max_width: float, max_lines: int):
    full_text = ''
    line = ''
    line_w = 0
    line_no = 0
    space_size = font.getlength(' ')
    words = text.split(' ')
    wordlen = [font.getlength(w) for w in words]

    i = 0
    while i < len(words):
        if line_w + wordlen[i] <= max_width:
            if line_w != 0:
                line += ' '
                line_w += space_size
            line += words[i]
            line_w += wordlen[i]
        else:
            #if line_w == 0 or ALWAYS_WRAP_WORDS:
            for ci in range(len(words[i])-1, 0, -1):
                if line_w + space_size + font.getlength(words[i][:ci]) <= max_width:
                    if line_w != 0:
                        line += ' '
                    line += words[i][:ci]
                    words[i] = words[i][ci:]
                    wordlen[i] = font.getlength(words[i])
                    break
            line_no += 1
            if line_no == max_lines:
                full_text += line[:-3] + '...'
                return full_text
            full_text += line + '\n'
            line = ''
            line_w = 0
            i -= 1
        i += 1

    #print(words)
    #print(full_text + line)
    return full_text + line


class Renderer:
    def __init__(self, calendar: Calendar):
        self.calendar: Calendar = calendar
        self.cache: list[tuple[str, Image.Image]] = []  # simple LRC cache
        self.MAX_CACHE_SIZE = 5

    def render_lecture(self, drawer: ImageDraw.ImageDraw, lecture: Lecture, x, y):
        P = PADDING

        bbox_day = FONT_H1.getbbox('1')
        day_height = bbox_day[3] - bbox_day[1] + 2*P

        # calculate wrapped text bounding box
        time_text = lecture.start_time.format('HH:mm') + ' - '
        time_text += lecture.start_time.shift(minutes=lecture.duration_minutes).format('HH:mm')
        bbox_hour = FONT_H2.getbbox(time_text)
        hour_width = bbox_hour[2] - bbox_hour[0]
        hour_height = bbox_hour[3] - bbox_hour[1] + 2*P

        # calculate text bounding box & surrounding rect bounding box
        if lecture.start_time.date().day == 13:
            lecture.title += ' that serves as a test example and provides a unique kind of entertainment to anyone who happens to read this rather lengthy description'
        writable_width = CELL_WIDTH_PX - 4 * P
        writable_height = CELL_HEIGHT_PX - hour_height - 6*P

        bbox_summary = FONT_P.getbbox(lecture.title)
        line_height = P + bbox_summary[3] - bbox_summary[1]
        max_lines = floor(writable_height / line_height)
        multiline_text = wrap_text_to_fit(lecture.title, FONT_P, writable_width, max_lines)
        mbb = drawer.multiline_textbbox((0,0), multiline_text, FONT_P)
        total_height = mbb[3] - mbb[1] + 3*P + hour_height
        rect_bb = [x+P, y+day_height, x+CELL_WIDTH_PX - P, y+day_height + total_height]
        text_pos = [rect_bb[0]+P, rect_bb[1]+P]

        # draw 
        drawer.rectangle(rect_bb, LECTURE_COLOR)
        drawer.text((x + writable_width//2 - hour_width//2 + 2*P, y+day_height + P), time_text, LECTURE_TEXT_COLOR, FONT_H2)
        drawer.text((text_pos[0], text_pos[1]+hour_height), multiline_text, LECTURE_TEXT_COLOR, FONT_P)


    def render_day(self, drawer: ImageDraw.ImageDraw, lecture_data: list[Lecture], day_of_week, week, base_date: arrow.Arrow):
        W, H = CELL_WIDTH_PX, CELL_HEIGHT_PX
        xmin, ymin = day_of_week * W, week * H + HEADER_HEIGHT_PX
        
        # outline, day number
        drawer.rectangle([xmin, ymin, xmin+W, ymin+H], outline=DAY_BORDER_COLOR, width=DAY_BORDER_WIDTH)
        drawer.text((xmin+DAY_BORDER_WIDTH + PADDING, ymin), f'{base_date.datetime.day}', fill=DAY_TEXT_COLOR, font=FONT_H1)

        for lecture in lecture_data:
            if lecture.start_time.date() == base_date.date():
                self.render_lecture(drawer, lecture, xmin, ymin + 2*PADDING)

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
        lectures: list[Lecture] = [Lecture.from_json(lec_json) for lec_json in data['items']]
        
        # table header
        drawer = ImageDraw.Draw(img)
        for day in range(1, 8):
            day_name = DAY_NAMES[day][:3]
            bbox = FONT_H1.getbbox(day_name)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            drawer.text(
                (CELL_WIDTH_PX//2 - text_w//2 + (day-1) * CELL_WIDTH_PX, HEADER_HEIGHT_PX - 2*PADDING - text_h), 
                day_name, DAY_TEXT_COLOR, FONT_H1
            )
        # days
        for week in range(n_weeks):
            for day in range(7):
                self.render_day(drawer, lectures, day, week, cal_start.shift(days=(week*7 + day)))

        # update cache
        if len(self.cache) == self.MAX_CACHE_SIZE:
            self.cache.pop(0)
        self.cache.append((render_key, img))
        img.save(filepath)


