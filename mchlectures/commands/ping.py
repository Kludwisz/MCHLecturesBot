import discord

class Ping(discord.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command(name = "ping", description = "Check the bot's latency")
    async def ping(self, ctx: discord.ApplicationContext):
        latency = round(self.bot.latency * 1000)
        embed = discord.Embed(title="Ping", description=f"Pong! {latency}ms")
        await ctx.respond(embed=embed, ephemeral=True)
        
def setup(bot):
    bot.add_cog(Ping(bot))