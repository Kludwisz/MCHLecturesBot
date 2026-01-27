import discord


def error(title: str = "Error", message: str = "Something went wrong, and the devs didn't expect it. DM Kris on Discord") -> discord.Embed:
    return discord.Embed(title=title, description=message)


def invalid_arg_error(message: str) -> discord.Embed:
    return discord.Embed(title="Error", description=f"Invalid command argument: {message}")


def limit_characters(text: str, limit: int) -> str:
    if len(text) > limit:
        return text[:(limit-3)] + "..."
    else:
        return text
