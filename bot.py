# This is a discord bot that will allow users to query a Plex Server to see if a movie is present in that server. If the movie is present, they can then request the movie or can request that the movie be added
# When a movie is requested, it will send an alert to me as well

# Import modules
import discord
import logging
import asyncio
import re
import time
from datetime import datetime, timedelta
from collections import defaultdict
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View
from dotenv import load_dotenv
from plex_utils import movie_exists, get_plex_server, calculate_similarity
from config import Config

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Validate configuration
if not Config.validate():
    missing_vars = Config.get_missing_vars()
    logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
    exit(1)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

guild = discord.Object(id=Config.GUILD_ID)

# Cache for admin user to avoid repeated fetches
admin_user = None

# Rate limiting
rate_limits = defaultdict(list)

# Bot startup time
startup_time = None

async def get_admin_user():
    """Get cached admin user"""
    global admin_user
    if admin_user is None:
        admin_user = await bot.fetch_user(Config.USER_ID)
    return admin_user

def is_rate_limited(user_id: int) -> bool:
    """Check if user is rate limited"""
    now = datetime.now()
    user_requests = rate_limits[user_id]

    # Remove old requests outside the window
    user_requests[:] = [req_time for req_time in user_requests
                        if now - req_time < timedelta(seconds=Config.RATE_LIMIT_WINDOW)]
    
    # Check if a user has exceeded limit
    if len(user_requests) >= Config.RATE_LIMIT_MAX_REQUESTS:
        return True
    
    # Add current request
    user_requests.append(now)
    return False

def validate_movie_title(title: str) -> tuple[bool, str]:
    """Validate movie title input"""
    if not title or not title.strip():
        return False, "Movie title cannot be empty"
    
    title = title.strip()

    if len(title) < Config.MIN_MOVIE_TITLE_LENGTH:
        return False, f"Movie title must be at least {Config.MIN_MOVIE_TITLE_LENGTH} characters long"
    
    if len(title) > Config.MAX_MOVIE_TITLE_LENGTH:
        return False, f"Movie title must be less than {Config.MAX_MOVIE_TITLE_LENGTH} characters long"
    
    # Check for potentially malicious content
    if re.search(r'[<>"\']', title):
        return False, "Movie title contains invalid characters"
    
    return True, title

async def check_plex_connection() -> tuple[bool, str]:
    """Check if Plex connection is working"""
    try:
        plex = get_plex_server()
        library = plex.library.section(Config.PLEX_LIBRARY_NAME)
        # Try to get library info to test connection
        library.title
        return True, "Connected"
    except Exception as e:
        return False, f"Connection failed: {str(e)}"

@bot.tree.command(name="debug_search", description="Debug search results with similarity scores", guild=guild)
@app_commands.describe(movie_name="Name of the movie to debug search for")
async def debug_search(interaction: discord.Interaction, movie_name: str):
    """Debug command to see search results with similarity scores"""
    logger.info(f"Debug search requested for: {movie_name} from {interaction.user}")
    
    # Only allow admin to use debug command
    if interaction.user.id != Config.USER_ID:
        await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
        return
    
    # Input validation
    is_valid, result = validate_movie_title(movie_name)
    if not is_valid:
        await interaction.response.send_message(result, ephemeral=True)
        return
    
    movie_name = result
    
    await interaction.response.defer()
    
    try:
        from plexapi.server import PlexServer
        plex = get_plex_server()
        library = plex.library.section(Config.PLEX_LIBRARY_NAME)
        results = library.search(movie_name, libtype='movie')
        
        if not results:
            await interaction.followup.send(f"No raw results found for **{movie_name}**")
            return
        
        # Show all raw results with similarity scores
        debug_info = []
        for i, movie in enumerate(results[:20]):  # Limit to 20 for readability
            similarity = calculate_similarity(movie_name, movie.title)
            debug_info.append(f"{i+1}. **{movie.title}** ({movie.year}) - Score: {similarity:.3f}")
        
        embed = discord.Embed(
            title=f"🔍 Debug Search Results for '{movie_name}'",
            description="Raw Plex results with similarity scores:",
            color=discord.Color.blue()
        )
        
        # Split into chunks if too long
        chunk_size = 10
        for i in range(0, len(debug_info), chunk_size):
            chunk = debug_info[i:i+chunk_size]
            field_name = f"Results {i+1}-{min(i+chunk_size, len(debug_info))}"
            field_value = "\n".join(chunk)
            embed.add_field(name=field_name, value=field_value, inline=False)
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error in debug search: {e}")
        await interaction.followup.send(f"An error occurred: {str(e)}", ephemeral=True)

@bot.tree.command(name="health", description="Check bot and Plex server status", guild=guild)
async def health_check(interaction: discord.Interaction):
    """Health Check command for monitoring bot status"""
    logger.info(f"Health check requested by {interaction.user}")

    # Only allow admin to use the health check
    if interaction.user.id != Config.USER_ID:
        await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
        return
    
    await interaction.response.defer()

    try:
        # Check bot uptime
        uptime = datetime.now() - startup_time if startup_time else timedelta(0)
        uptime_str = str(uptime).split('.')[0] # Remove microseconds

        # Check Plex connection
        plex_ok, plex_status = await check_plex_connection()

        # Create status embed
        embed = discord.Embed(
            title="Bot Health Status",
            color=discord.Color.green() if plex_ok else discord.Color.red(),
            timestamp=datetime.now()
        )

        embed.add_field(
            name="Bot Status",
            value=f"Online\nUptime: {uptime_str}",
            inline=True
        )

        embed.add_field(
            name="Plex Connection",
            value=f"{'Connected' if plex_ok else 'Not Connected'} {plex_status}",
            inline=True
        )

        embed.add_field(
            name="Rate Limits",
            value=f"Active Users: {len(rate_limits)}",
            inline=True
        )

        embed.add_field(
            name="Configuration",
            value=f"Guild ID: {Config.GUILD_ID}\nLibrary: {Config.PLEX_LIBRARY_NAME}",
            inline=False
        )

        await interaction.followup.send(embed=embed)

    except Exception as e:
        logger.error(f"Error in health check: {e}")
        await interaction.followup.send("An error occurred while checking helath status.", ephemeral=True)

@bot.tree.command(name="query", description="Check if a movie exists in Plex", guild=guild)
@app_commands.describe(movie_name="Name of the movie you are searching for")
async def query(interaction: discord.Interaction, movie_name: str):
    logger.info(f"Received query for: {movie_name} from {interaction.user}")

    # Rate limiting
    if is_rate_limited(interaction.user.id):
        await interaction.response.send_message(
            "You are making too many requests. Please wait a moment before trying again.",
            ephemeral=True
        )
        return
    
    # Input validation
    is_valid, result = validate_movie_title(movie_name)
    if not is_valid:
        await interaction.response.send_message(result, ephemeral=True)
        return
    
    movie_name = result

    # Defer respoinse for longer operations
    await interaction.response.defer()

    try:
        movies = movie_exists(movie_name)

        if not movies:
            await interaction.followup.send(f"**{movie_name}** is not in Plex. You can request it by using '/request {movie_name}")
            return
        
        embeds = []
        for movie in movies[:Config.MAX_EMBEDS_PER_MESSAGE]:
            embed = discord.Embed(
                title=f"{movie['title']} ({movie['year']})",
                description=movie['summary'],
                color=discord.Color.green()
            )
            embeds.append(embed)

        await interaction.followup.send(content=f"Found {len(movies)} result(s) for **{movie_name}**:", embeds=embeds)
    except Exception as e:
        logger.error(f"Error in query command: {e}")
        await interaction.followup.send("An error occurred while searching for the movie. Please try again later.", ephemeral=True)

class MovieSelectView(View):
    def __init__(self, movies, user):
        super().__init__(timeout=Config.BUTTON_TIMEOUT)
        self.user = user
        for movie in movies[:Config.MAX_BUTTONS_PER_VIEW]:
            label = f"{movie['title']} ({movie['year']})"
            button = Button(label=label, style=discord.ButtonStyle.primary)
            button.callback = self.make_callback(movie)
            self.add_item(button)

    def make_callback(self, movie):
        async def callback(interaction):
            if interaction.user != self.user:
                await interaction.response.send_message("This selection isn't for you.", ephemeral=True)
                return
            
            try:
                await interaction.response.send_message(
                    f"You selected **{movie['title']} ({movie['year']})**. The request has been submitted!",
                    ephemeral=True
                )

                # Notify admin
                admin = await get_admin_user()
                await admin.send(
                    f"**Movie Request** from {interaction.user.mention}:\n"
                    f"**{movie['title']} ({movie['year']})**\n{movie['summary']}"
                )
            except Exception as e:
                logger.error(f"Error in movie selection callback:{e}")
                await interaction.response.send_message("An error occurred while processing your request.", ephemeral=True)
        return callback
    
@bot.tree.command(name="request", description="Request a movie to be added to Plex", guild=guild)
@app_commands.describe(movie_name="Name and year of the movie you want to request")
async def request_movie(interaction: discord.Interaction, movie_name: str):
    logger.info(f"Received request for: {movie_name} from {interaction.user}")

    # Rate limiting
    if is_rate_limited(interaction.user.id):
        await interaction.response.send_message(
            "You're making too many requests. Please wait a moment before trying again.",
            ephemeral=True
        )
        return
    
    # Input validation
    is_valid, result = validate_movie_title(movie_name)
    if not is_valid:
        await interaction.response.send_message(result, ephemeral=True)
        return
    
    movie_name = result

    # Defer response for longer operations
    await interaction.response.defer()

    try:
        requester = interaction.user
        movies = movie_exists(movie_name)

        if not movies:
            await interaction.followup.send(
                f"No matches found for **{movie_name}** in Plex. Your request has still been noted."
            )
            admin = await get_admin_user()
            await admin.send(f"Movie Request from {requester.mention}: **{movie_name}** (Not Found)")
            return
        
        if len(movies) == 1:
            movie = movies[0]
            await interaction.followup.send(
                f"Thank you {requester.mention}, your request for **{movie['title']} ({movie['year']})** has been submitted!"
            )
            admin = await get_admin_user()
            await admin.send(
                f"**Movie Request** from {requester.mention}:\n"
                f"**{movie['title']} ({movie['year']})**\n{movie['summary']}"
            )
            return
        
        # Multiple matches, ask user to select specific movie
        view = MovieSelectView(movies, requester)
        await interaction.followup.send(
            "Multiple matches found. Please selected the correct movie:", view=view, ephemeral=True
        )
    except Exception as e:
        logger.error(f"Error in request command: {e}")
        await interaction.followup.send("An error occurred while processing your request. Please try again later.", ephemeral=True)

@bot.event
async def on_ready():
    global startup_time
    startup_time = datetime.now()
    logger.info(f'Logged in as {bot.user}')
    try:
        synced = await bot.tree.sync(guild=guild)
        logger.info(f"Synced {len(synced)} command(s) to guild {Config.GUILD_ID}")
    except Exception as e:
        logger.error(f"Error syncing commands: {e}")

@bot.event
async def on_interaction(interaction):
    logger.debug(f"Interaction received: {interaction.type}")

if __name__ == "__main__":
    bot.run(Config.DISCORD_TOKEN)