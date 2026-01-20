from gcalendar.gcalendar import Calendar, Lecture, ExtendedProperties
from gcalendar.renderer import Renderer
from dotenv import dotenv_values
import arrow
import asyncio


async def add_lectures(cal: Calendar):
    lec = Lecture(
        extended_properties=ExtendedProperties(
            discord_userid='12549827142014', discord_username='someone',
            recording_perms='NO_RECORDING', lecture_format='whiteboard',
            description='A throrough explanation & analysis on why Minecraft: Java Edition is way better than Bedrock Edition.',
            prior_knowledge='Minecraft basics'
        ),
        start_time=arrow.get('2026-01-16 12:45'),
        duration_minutes=45, title='Why Java Edition is way better than Bedrock Edition'
    )
    #await cal.create_event(lec)
    lec.start_time = arrow.get('2026-01-04 08:00')
    lec.duration_minutes = 90
    lec.title = 'Why Java Edition is way better than Bedrock Edition'
    #await cal.create_event(lec)
    lec.start_time = arrow.get('2026-01-29 21:15')
    lec.duration_minutes = 45
    lec.title = 'Why Java Edition is way better than Bedrock Edition'
    #await cal.create_event(lec)


async def main():
    config = dotenv_values(".env")

    cal = Calendar(
        config["ACCOUNT_EMAIL"],
        config["SERVICE_ACCOUNT_SECRET"]
    )
    #await cal.delete_event('nola7050t27d6u0pj7f72vs0lg')
    #await add_lectures(cal)

    ren = Renderer(cal)
    await ren.render(arrow.get('2026-01-01'), arrow.get('2026-02-28'), 'test.png')

if __name__ == '__main__':
    asyncio.run(main())