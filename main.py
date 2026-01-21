import asyncio
from pprint import pprint
from gcalendar.service import CalendarService


async def main():
    cs = CalendarService()
    cs.connect()
    pprint(await cs.get_upcoming_lectures(limit=2))
    #await cs.render_calendar_to_file(scope='this-week', filename='testThisWeek.png')
    #await cs.render_calendar_to_file(scope='week', filename='testWeek.png')
    #await cs.render_calendar_to_file(scope='month', filename='testMonth.png')
    #await cs.render_calendar_to_file(scope='2-months', filename='test2Months.png')


if __name__ == '__main__':
    asyncio.run(main())