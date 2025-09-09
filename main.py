import os
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone

# Grab token from environment
TOKEN = os.getenv("DISCORD_TOKEN")
print("TOKEN present:", bool(TOKEN))  # debug check in Render logs

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# In-memory time log
time_log = {}  # {user_id: {"in": datetime, "job": str}}

# ------------------------
# Simple health check
# ------------------------
@bot.tree.command(description="Ping the bot to see if it is working")
async def hello(interaction: discord.Interaction):
    await interaction.response.send_message(
        f"Hello {interaction.user.mention}, the bot is online ✅",
        ephemeral=True
    )

# ------------------------
# Check-in
# ------------------------
@bot.tree.command(description="Clock in with an optional job code.")
@app_commands.describe(job="Job code or project name")
async def checkin(interaction: discord.Interaction, job: str = "general"):
    uid = interaction.user.id
    if uid in time_log and "in" in time_log[uid]:
        return await interaction.response.send_message("⚠️ You’re already checked in.", ephemeral=True)
    time_log[uid] = {"in": datetime.now(timezone.utc), "job": job}
    ts = int(time_log[uid]["in"].timestamp())
    await interaction.response.send_message(
        f"✅ Checked in to **{job}** at <t:{ts}:t>.",
        ephemeral=True
    )

# ------------------------
# Check-out
# ------------------------
@bot.tree.command(description="Clock out and see your time worked.")
async def checkout(interaction: discord.Interaction):
    uid = interaction.user.id
    if uid not in time_log or "in" not in time_log[uid]:
        return await interaction.response.send_message("⚠️ You’re not checked in.", ephemeral=True)

    start = time_log[uid]["in"]
    job = time_log[uid].get("job", "general")
    end = datetime.now(timezone.utc)
    hours = round((end - start).total_seconds() / 3600, 2)
    time_log.pop(uid, None)

    await interaction.response.send_message(
        f"✅ Checked out of **{job}**. Time worked: **{hours}h** "
        f"(from <t:{int(start.timestamp())}:t> to <t:{int(end.timestamp())}:t>).",
        ephemeral=True
    )

# ------------------------
# Confirmation buttons
# ------------------------
class ConfirmView(discord.ui.View):
    def __init__(self, requester_id: int, label_yes="Confirm", label_no="Decline", timeout=300):
        super().__init__(timeout=timeout)
        self.requester_id = requester_id
        self.value = None
        self.children[0].label = f"✅ {label_yes}"
        self.children[1].label = f"❌ {label_no}"

    @discord.ui.button(style=discord.ButtonStyle.success)
    async def yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.requester_id:
            return await interaction.response.send_message("This isn’t for you.", ephemeral=True)
        self.value = True
        await interaction.response.edit_message(content="Confirmed ✅", view=None)
        self.stop()

    @discord.ui.button(style=discord.ButtonStyle.danger)
    async def no(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.requester_id:
            return await interaction.response.send_message("This isn’t for you.", ephemeral=True)
        self.value = False
        await interaction.response.edit_message(content="Declined ❌", view=None)
        self.stop()

# ------------------------
# Self-confirmation
# ------------------------
@bot.tree.command(description="Send yourself a YES/NO confirmation.")
async def confirm_me(interaction: discord.Interaction):
    view = ConfirmView(requester_id=interaction.user.id)
    await interaction.response.send_message("Please confirm:", view=view, ephemeral=True)

# ------------------------
# Assign confirmation
# ------------------------
@bot.tree.command(description="Send a confirmation request to a contractor.")
@app_commands.describe(user="Who needs to confirm", note="Context (e.g., Shift 9/10 8am at Omni)")
async def assign(interaction: discord.Interaction, user: discord.User, note: str):
    view = ConfirmView(requester_id=user.id, label_yes="Accept", label_no="Decline")
    content = f"{user.mention}, please confirm assignment: **{note}**"
    await interaction.response.send_message(content, view=view)

# ------------------------
# On Ready
# ------------------------
@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} commands. Logged in as {bot.user} (ID: {bot.user.id})")
    except Exception as e:
        print("❌ Slash command sync failed:", e)

bot.run(TOKEN)
