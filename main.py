import discord
from discord.ext import commands
from discord import app_commands
import datetime
import os
from flask import Flask
from threading import Thread

# --- WEB SERVER FOR RENDER (KEEP ALIVE) ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run():
    # Render provides PORT environment variable automatically
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
OWNER_ID = 1243980401890951310

# ROLES
ROLES = {
    "Elite": 1471888279447015646,
    "Prime": 1471888313060294706,
    "Vested": 1471888357276516362,
    "Client": 1471888403514523739
}

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
        
        channel = await guild.create_text_channel(
            name=f"ticket-{interaction.user.name}",
            category=category,
            overwrites=overwrites
        )
        
        embed = discord.Embed(
            title="✨ Session Started",
            description=f"Welcome {interaction.user.mention},\n\nThe developer <@{OWNER_ID}> has been notified. Please state your requirements and budget below.",
            color=0x2b2d31
        )
        embed.set_footer(text="Discord Bots • Professional Service")
        await channel.send(embed=embed)
        await interaction.response.send_message(f"Ticket Created: {channel.mention}", ephemeral=True)

class DB_Manager(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())

    async def setup_hook(self):
        self.add_view(TicketView())

bot = DB_Manager()

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    await bot.tree.sync()

# 1. Setup Ticket
@bot.tree.command(name="setup-ticket", description="Setup the ticket system")
async def setup_ticket(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID:
        return await interaction.response.send_message("Permission Denied: Only the Owner can run this.", ephemeral=True)
    
    embed = discord.Embed(
        title="📥 Create a Ticket",
        description="Click the button below to start a conversation for development or queries.",
        color=0x2b2d31
    )
    await interaction.channel.send(embed=embed, view=TicketView())
    await interaction.response.send_message("Ticket system setup complete.", ephemeral=True)

# 2. Vouch System
@bot.tree.command(name="vouch", description="Submit your feedback")
async def vouch(interaction: discord.Interaction, stars: int, feedback: str):
    vouch_chan = bot.get_channel(VOUCH_CHANNEL_ID)
    
    if stars < 1 or stars > 5:
        return await interaction.response.send_message("Please provide a rating between 1 and 5 stars.", ephemeral=True)
    
    embed = discord.Embed(title="⭐ Client Feedback", color=0x00ff7f, timestamp=datetime.datetime.utcnow())
    embed.add_field(name="Client", value=interaction.user.mention, inline=True)
    embed.add_field(name="Rating", value="★" * stars, inline=True)
    embed.add_field(name="Comment", value=feedback, inline=False)
    
    if interaction.user.display_avatar:
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        
    embed.set_footer(text="Verified Order • Discord Bots")
    
    await vouch_chan.send(embed=embed)
    await interaction.response.send_message("Thank you! Your feedback has been posted.", ephemeral=True)

# 3. Set Tier
@bot.tree.command(name="set-tier", description="Assign client roles based on payment")
async def set_tier(interaction: discord.Interaction, member: discord.Member, amount: int):
    if interaction.user.id != OWNER_ID:
        return await interaction.response.send_message("Permission Denied.", ephemeral=True)
    
    role_id = ROLES["Client"]
    tier_name = "Client"
    
    if amount >= 50000: 
        role_id = ROLES["Elite"]
        tier_name = "Elite"
    elif amount >= 20000: 
        role_id = ROLES["Prime"]
        tier_name = "Prime"
    elif amount >= 10000: 
        role_id = ROLES["Vested"]
        tier_name = "Vested"
        
    role = interaction.guild.get_role(role_id)
    if role:
        await member.add_roles(role)
        await interaction.response.send_message(f"✅ {member.mention} has been promoted to **{tier_name}** ({amount} INR).")
    else:
        await interaction.response.send_message("Role not found. Please check Role IDs.", ephemeral=True)

# 4. Features (40-50 Items List)
@bot.tree.command(name="features", description="List of all bot capabilities")
async def features(interaction: discord.Interaction):
    embed = discord.Embed(title="🛠️ Advanced Bot Capabilities", color=0x2b2d31)
    embed.add_field(name="Automation", value="• Web Scraping & Data Extraction\n• Social Media API Integration\n• Auto-Moderation & Verification\n• Webhook & Data Syncing\n• Intelligent Auto-Responders", inline=True)
    embed.add_field(name="Economy Systems", value="• Multi-Currency Economy\n• Shop & Inventory Logic\n• Gambling & Game Modules\n• Daily/Weekly Reward Systems\n• Secure Trading Mechanisms", inline=True)
    embed.add_field(name="Security & Utility", value="• Anti-Spam & Anti-Nuke Protection\n• Advanced Captcha Verification\n• Invitation & Role Tracking\n• Detailed Transaction Logging\n• Database Integration (MySQL/SQLite)", inline=False)
    embed.add_field(name="Enterprise Features", value="• Custom API Wrapper Development\n• Multi-Language Support\n• High-Performance Persistent Tickets\n• Advanced Analytic Dashboards\n• Automated Deployment Scripts", inline=False)
    embed.set_footer(text="Equipped with 50+ custom modular solutions.")
    await interaction.response.send_message(embed=embed)

# Start Web Server then Bot
keep_alive()
bot.run(TOKEN)
                                                       
