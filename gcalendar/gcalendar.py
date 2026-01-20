import dataclasses

# import pprint
import httpx
import asyncio
import arrow

from textwrap import dedent
from google.oauth2 import service_account
from google.auth.transport.requests import Request

'''
properties {
    "discord_userid": "userid",
    "recording_perms": "enum value or CUSTOM for custom recording permission",
    "custom_perms": "description of custom permission thing"
}

/add_event --> open dialog with a form
/my_events --> sends a message with dropdowns and args (update existing, delete existing, browse)
/upcoming_events num_events:int --> pages of events & buttons for nav
/calendar --> renders the whole month (link to calendar embedded in browser?)
Post-MVP: /notifyme (event)?
'''


RECORDING_PERMS = {
    'NO_RECORDING': 'This is a live event. Audio-visual recording of the lecture is forbidden.',
    'MCH_UNLISTED_RECORDING': 'This lecture will be recorded and uploaded as unlisted to the MC@H Lectures YouTube channel. Providing access is at the discrepancy of the host.',
    'MCH_PUBLIC_RECORDING': 'This lecture will be recorded and published on the MC@H Lectures YouTube channel. Uploading it elsewhere is forbidden.',
    'ALL_RECORDING_OK': 'The host has permitted all participants to record and share the recording of this lecture freely. It will also be made available on the MC@H Lectures channel.',
    'CUSTOM': 'Custom permissions, see extra properties'
}


@dataclasses.dataclass
class ExtendedProperties:
    discord_userid: str
    discord_username: str
    recording_perms: str
    lecture_format: str
    description: str
    prior_knowledge: str
    custom_perms: str = ''


@dataclasses.dataclass
class Lecture:
    extended_properties: ExtendedProperties
    start_time: arrow.Arrow
    duration_minutes: int
    title: str
    id: str | None = None

    def get_description(self) -> str:
        return dedent(
            f"""
            1. Lecture description
            Lecture host: {self.extended_properties.discord_username}
            Format: {self.extended_properties.lecture_format}
            {self.extended_properties.description}
                
            2. Recommended prior knowledge
            {self.extended_properties.prior_knowledge}
            
            3. Notice about recording
            {self.extended_properties.custom_perms if self.extended_properties.recording_perms == 'CUSTOM' else RECORDING_PERMS[self.extended_properties.recording_perms]}
            """)

    def to_json(self):
        event = {
            "summary": self.title,
            "description": self.get_description(),
            "start": {
                "dateTime": self.start_time.to("utc").isoformat(),
                "timeZone": "UTC"
            },
            "end": {
                "dateTime": (self.start_time.shift(minutes=self.duration_minutes)).to("utc").isoformat(),
                "timeZone": "UTC"
            },
            "extendedProperties": {"private": dataclasses.asdict(self.extended_properties)}
        }
        return event

    @staticmethod
    def from_json(lecture_json):
        #pprint.pprint(lecture_json)
        ident = lecture_json["id"]
        title = lecture_json["summary"]
        start = arrow.get(lecture_json["start"]["dateTime"])
        end = arrow.get(lecture_json["end"]["dateTime"])
        ext_properties = ExtendedProperties(**lecture_json["extendedProperties"]["private"])
        duration = int((end-start).total_seconds() / 60)
        return Lecture(id=ident, extended_properties=ext_properties,
                       start_time=start, duration_minutes=duration, title=title)


class Calendar:
    def __init__(self, calendar_id, service_account_file):
        self.id = calendar_id
        self.credentials = service_account.Credentials.from_service_account_file(
            service_account_file,
            scopes=["https://www.googleapis.com/auth/calendar.events"]
        )
        self.credentials.refresh(Request())
        self.access_token = self.credentials.token
        self.client = httpx.AsyncClient(headers={
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        })

    async def create_event(self, lecture: Lecture):
        event = lecture.to_json()
        url = f"https://www.googleapis.com/calendar/v3/calendars/{self.id}/events"
        response = await self.client.post(url, json=event)
        response.raise_for_status()
        print("Event created:", response.json()["id"])
        return response.json()["id"]

    async def get_event(self, event_id):
        url = f"https://www.googleapis.com/calendar/v3/calendars/{self.id}/events/{event_id}"
        response = await self.client.get(url)
        print("Event fetched from calendar:", response.json())

    async def get_event_list(self, discord_userid=None, timeMin: arrow.Arrow = None, timeMax: arrow.Arrow = None, query_text: str = None):
        private_property_filters = []
        params = {}
        if discord_userid:
            private_property_filters.append(f"discord_userid={discord_userid}")
        if timeMin:
            params["timeMin"] = timeMin.to("utc").isoformat()
        if timeMax:
            params["timeMax"] = timeMax.to("utc").isoformat()
        if query_text:
            params["q"] = query_text

        if private_property_filters:
            params["privateExtendedProperty"] = "&".join(private_property_filters)
        url = f"https://www.googleapis.com/calendar/v3/calendars/{self.id}/events"
        response = await self.client.get(url, params=params)
        return response.json()

    async def update_event(self, lecture: Lecture):
        event = lecture.to_json()
        url = f"https://www.googleapis.com/calendar/v3/calendars/{self.id}/events/{lecture.id}"
        response = await self.client.put(url, json=event)
        response.raise_for_status()
        print("Event updated:", response.json())

    async def delete_event(self, event_id):
        url = f"https://www.googleapis.com/calendar/v3/calendars/{self.id}/events/{event_id}"
        response = await self.client.delete(url)
        response.raise_for_status()
        print(f"Event {event_id} deleted.")


async def main():
    calendar = Calendar(
        'd67a2948d8390dc9d5fcd55773bb8e4de342a7d234cc6c278a0ee59a6dcc1e22@group.calendar.google.com',
        'secrets/service_account.json'
    )
    lec = Lecture(
        extended_properties=ExtendedProperties(
            discord_userid='12345', discord_username='Scriptline', recording_perms='MCH_UNLISTED_RECORDING',
            lecture_format='whiteboard presentation', description='Some description in the past', prior_knowledge='none'),
        start_time=arrow.get("2026-01-07T18:00"),
        duration_minutes=90,
        title='Interesting Lecture'
    )
    await calendar.create_event(lec)
    events = await calendar.get_event_list(query_text="past")

    event = Lecture.from_json(events["items"][0])
    event.start_time = event.start_time.shift(days=-1)
    event.duration_minutes += 180
    event.title += ' (modified)'
    await calendar.update_event(event)
    await calendar.client.aclose()


if __name__ == '__main__':
    asyncio.run(main())