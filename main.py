from calendar import Calendar, Lecture
from dotenv import dotenv_values

config = dotenv_values(".env")

cal = Calendar(
    config["ACCOUNT_EMAIL"],
    config["SERVICE_ACCOUNT_SECRET"]
)