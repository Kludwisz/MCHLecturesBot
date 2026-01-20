from gcalendar.gcalendar import Calendar
from gcalendar.renderer import Renderer
from dotenv import dotenv_values
import arrow
import asyncio


async def main():
    config = dotenv_values(".env")

    cal = Calendar(
        config["ACCOUNT_EMAIL"],
        config["SERVICE_ACCOUNT_SECRET"]
    )
    ren = Renderer(cal)
    await ren.render(arrow.get('2024-01-10'), arrow.get('2026-01-20'), 'a')

if __name__ == '__main__':
    asyncio.run(main())