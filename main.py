import discord
from discord.ext import commands
from discord import app_commands
import datetime
import os
import asyncio
import io # Added for Image processing
from PIL import Image, ImageDraw # Added for Graphics
from flask import Flask
from threading import Thread

# --- WEB SERVER FOR RENDER (KEEP ALIVE) ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- SETTINGS ---
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = 1471883562004516924
VOUCH_CHANNEL_ID = 1471887232708382730
TICKET_CATEGORY_ID = 1471891813106188574
WELCOME_CHANNEL_ID = 1472275010709098705
OWNER_ID = 1243980401890951310

ROLES = {
    "Elite": 1471888279447015646,
    "Prime": 1471888313060294706,
    "Vested": 1471888357276516362,
    "Client": 1471888403514523739
}

# --- HEALTH ANALYSIS LOGIC ---
def calculate_health_stats(guild):
    # 1. Security Score: Admins vs Total Members ratio
    admin_count = len([m for m in guild.members if m.guild_permissions.administrator])
    security_score = 100 - (admin_count * 10) if admin_count < 10 else 10
    
    # 2. Activity Score: Online/Idle members ratio
    online = len([m for m in guild.members if m.status != discord.Status.offline])
    activity_score = int((online / guild.member_count) * 100) if guild.member_count > 0 else 0
    
    # 3. Final Health Score
    total_health = int((security_score + activity_score) / 2)
    return total_health, security_score, activity_score

# --- TICKET ACTIONS ---
class TicketActionView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close Ticket 🔒", style=discord.ButtonStyle.red, custom_id="close_ticket_btn")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.channel.set_permissions(interaction.user, send_messages=False, read_messages=True)
        embed = discord.Embed(description="🔒 **Ticket Closed.** \nStaff can now delete this channel.", color=0xff0000)
        await interaction.response.send_message(embed=embed)

    @discord.ui.button(label="Delete 🗑️", style=discord.ButtonStyle.grey, custom_id="delete_ticket_btn")
    async def delete_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🗑️ **Deleting ticket in 3 seconds...**")
        await asyncio.sleep(3)
        await interaction.channel.delete()

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Open Ticket 🎟️", style=discord.ButtonStyle.grey, custom_id="open_ticket_btn")
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        category = guild.get_channel(TICKET_CATEGORY_ID)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        channel = await guild.create_text_channel(name=f"ticket-{interaction.user.name}", category=category, overwrites=overwrites)
        embed = discord.Embed(title="✨ Session Started", description=f"Welcome {interaction.user.mention},\nThe developer <@{OWNER_ID}> has been notified.", color=0x2b2d31)
        await channel.send(embed=embed, view=TicketActionView())
        await interaction.response.send_message(f"Ticket Created: {channel.mention}", ephemeral=True)

class DB_Manager(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())

    async def setup_hook(self):
        self.add_view(TicketView())
        self.add_view(TicketActionView())

bot = DB_Manager()

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    await bot.tree.sync()

@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if not channel: return
    embed = discord.Embed(title="✨ A NEW GENIUS ARRIVED!", description=f"Greetings {member.mention}, welcome to **Bots Developer**.", color=0x2b2d31)
    if member.display_avatar: embed.set_thumbnail(url=member.display_avatar.url)
    await channel.send(content=f"Welcome {member.mention}!", embed=embed)

# 1. Setup Ticket
@bot.tree.command(name="setup-ticket", description="Setup the ticket system")
async def setup_ticket(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID: return await interaction.response.send_message("Denied.", ephemeral=True)
    embed = discord.Embed(title="📥 Create a Ticket", description="Click below to start.", color=0x2b2d31)
    await interaction.channel.send(embed=embed, view=TicketView())
    await interaction.response.send_message("Setup complete.", ephemeral=True)

# 2. Vouch System
@bot.tree.command(name="vouch", description="Submit your feedback")
async def vouch(interaction: discord.Interaction, stars: int, feedback: str):
    vouch_chan = bot.get_channel(VOUCH_CHANNEL_ID)
    embed = discord.Embed(title="⭐ Client Feedback", color=0x00ff7f)
    embed.add_field(name="Rating", value="★" * stars)
    embed.add_field(name="Comment", value=feedback)
    await vouch_chan.send(embed=embed)
    await interaction.response.send_message("Feedback posted!", ephemeral=True)

# 3. Set Tier
@bot.tree.command(name="set-tier", description="Assign client roles")
async def set_tier(interaction: discord.Interaction, member: discord.Member, amount: int):
    if interaction.user.id != OWNER_ID: return
    role_id = ROLES["Client"]
    if amount >= 50000: role_id = ROLES["Elite"]
    elif amount >= 20000: role_id = ROLES["Prime"]
    elif amount >= 10000: role_id = ROLES["Vested"]
    role = interaction.guild.get_role(role_id)
    await member.add_roles(role)
    await interaction.response.send_message(f"✅ {member.mention} promoted!")

# 4. Features
@bot.tree.command(name="features", description="List of all bot capabilities")
async def features(interaction: discord.Interaction):
    embed = discord.Embed(title="🛠️ Advanced Bot Capabilities", color=0x2b2d31)
    embed.add_field(name="Modules", value="• Web Scraping\n• Economy\n• Security\n• AI Integration", inline=False)
    await interaction.response.send_message(embed=embed)

# 5. --- THE DAMNNN HEALTH COMMAND (IMAGE BASED ANALYSIS) ---
@bot.tree.command(name="health", description="Analyze server integrity and activity visually")
async def health(interaction: discord.Interaction):
    await interaction.response.defer()
    
    score, sec_score, act_score = calculate_health_stats(interaction.guild)

    # Creating the Image
    img = Image.new('RGB', (600, 350), color=(20, 20, 20))
    draw = ImageDraw.Draw(img)

    # Design
    draw.text((220, 20), "SERVER DIAGNOSTICS", fill=(255, 255, 255))
    
    # Bars
    def draw_stat(y, label, val, color):
        draw.text((50, y-20), f"{label}: {val}%", fill=(200, 200, 200))
        draw.rectangle([50, y, 550, y+15], fill=(40, 40, 40))
        draw.rectangle([50, y, 50+(val*5), y+15], fill=color)

    draw_stat(100, "Security Integrity", sec_score, (255, 80, 80))
    draw_stat(180, "User Activity", act_score, (80, 150, 255))
    draw_stat(260, "Overall Vitality", score, (0, 255, 127))

    draw.text((230, 310), f"FINAL SCORE: {score}/100", fill=(255, 255, 255))

    with io.BytesIO() as image_binary:
        img.save(image_binary, 'PNG')
        image_binary.seek(0)
        file = discord.File(fp=image_binary, filename='health.png')
        
        embed = discord.Embed(title=f"🔍 Health Analysis: {interaction.guild.name}", color=0x2b2d31)
        embed.set_image(url="attachment://health.png")
        await interaction.followup.send(file=file, embed=embed)

# Start
keep_alive()
bot.run(TOKEN)
                         
