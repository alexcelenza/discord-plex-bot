# This is a Discord Bot that will allow users to query my Plex Server to see if a movie is in my Plex library which they can then request
# Otherwise they can request the movie which will alert me

# Import modules
import os
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View
from dotenv import load_dotenv
from plex_utils import movie_exists, PLEX_URL, PLEX_TOKEN

# Load Environment Variables
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))
USER_ID = int(os.getenv("USER_ID"))

intents = discord.Intents.default()
intents.message_content= True
bot = commands.Bot(command_prefix='!', intents=intents)

guild = discord.Object(id=GUILD_ID)

@bot.tree.command(name="query", description="Check if a movie exists in Plex", guild=guild)
@app_commands.describe(movie_name="Name of the movie you're searching for")
async def query(interaction: discord.Interaction, movie_name: str):
    print(f"Received query for: {movie_name}")
    movies = movie_exists(movie_name)

    if not movies:
        await interaction.response.send_message(f"**{movie_name}** is not in Plex. You can request it by using `/request {movie_name}`")
        return
    
    embeds = []
    for movie in movies[:10]:  # Max 10 embeds per message
        embed = discord.Embed(
            title=f"{movie['title']} ({movie['year']})",
            description=movie['summary'],
            color=discord.Color.green()
        )
        embeds.append(embed)

    await interaction.response.send_message(content=f"Found {len(movies)} result(s) for **{movie_name}**:", embeds=embeds)

class MovieSelectView(View):
    def __init__(self, movies, user):
        super().__init__(timeout=60)
        self.user = user
        for movie in movies[:5]: # Limit to 5 buttons to avoid UI overload
            label = f"{movie['title']} ({movie['year']})"
            button = Button(label=label, style=discord.ButtonStyle.primary)
            button.callback = self.make_callback(movie)
            self.add_item(button)
    
    def make_callback(self, movie):
        async def callback(interaction):
            if interaction.user != self.user:
                await interaction.response.send_message("This selection isn't for you.", ephemeral=True)
                return
            
            await interaction.response.send_message(
                f"You selected **{movie['title']} ({movie['year']})**. The request has been submitted!",
                ephemeral=True
            )

            # Notify me
            admin = await bot.fetch_user(USER_ID)
            await admin.send(
                f"**Movie Request** from {interaction.user.mention}:\n"
                f"**{movie['title']} ({movie['year']})**\n {movie['summary']}"
            )
        return callback

@bot.tree.command(name="request", description="Request a movie to be added to Plex", guild=guild)
@app_commands.describe(movie_name="Name of the movie you want to request")
async def request_movie(interaction: discord.Interaction, movie_name: str):
    print(f"Received request for: {movie_name}")
    requester = interaction.user
    movies = movie_exists(movie_name)

    if not movies:
        await interaction.response.send_message(
            f"No matches found for **{movie_name}** in Plex. Your request has still been noted."
        )
        admin = await bot.fetch_user(USER_ID)
        await admin.send(f"Movie Request from {requester.mention}: **{movie_name}** (Not Found)")
        return
    
    if len(movies) == 1:
        movie = movies[0]
        await interaction.response.send_message(
            f"Thank you {requester.mention}, your request for **{movie['title']} ({movie['year']})** has been submitted!"
        )
        admin = await bot.fetch_user(USER_ID)
        await admin.send(
            f"**Movie Request** from {requester.mention}:\n"
            f"**{movie['title']} ({movie['year']})**\n{movie['summary']}"
        )
        return
    
    # Mutiple matches, ask user to select specific movie
    view = MovieSelectView(movies, requester)
    await interaction.response.send_message(
        "Multiple matches found. Please select the correct movie:", view=view, ephemeral=True
    )

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    try:
        synced = await bot.tree.sync(guild=guild)
        print(f"Synced {len(synced)} command(s) to guild {GUILD_ID}")
    except Exception as e:
        print(f"Error syncing commands: {e}")

@bot.event
async def on_interaction(interaction):
    print(f"Interaction received: {interaction.type}")

bot.run(TOKEN)