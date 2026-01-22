import discord


class HelloWorld(discord.Cog):
    @discord.slash_command(name="hello", description="hello world command test")
    async def hello(self, ctx: discord.ApplicationContext):
        embed = discord.Embed(title="Hello", description=f"Hello, {ctx.author.display_name}!")
        await ctx.respond(embed=embed)


def setup(bot: discord.Bot):
    bot.add_cog(HelloWorld())
