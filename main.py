import discord
from discord.ext import commands
from discord import app_commands
import datetime
import os
import asyncio
import io 
import random
from PIL import Image, ImageDraw 
from flask import Flask
from threading import Thread

# --- WEB SERVER FOR RENDER (KEEP ALIVE) ---
app = Flask('')
@app.route('/')
def home(): return "Bot is running!"
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
TICKET_CHANNEL_ID = 1471887200487608362 
OWNER_ID = 1243980401890951310

ROLES = {
    "Elite": 1471888279447015646,
    "Prime": 1471888313060294706,
    "Vested": 1471888357276516362,
    "Client": 1471888403514523739
}

# --- DATABASE SIMULATION ---
user_stats = {} 
msg_cooldown = {} # Anti-spam for Credits

def get_user_data(user_id):
    if user_id not in user_stats:
        user_stats[user_id] = {"orders": 0, "spent": 0, "balance": 0, "msg_count": 0}
    return user_stats[user_id]

# --- HEALTH ANALYSIS LOGIC ---
def calculate_health_stats(guild):
    admin_count = len([m for m in guild.members if m.guild_permissions.administrator])
    security_score = 100 - (admin_count * 10) if admin_count < 10 else 10
    online = len([m for m in guild.members if m.status != discord.Status.offline])
    activity_score = int((online / guild.member_count) * 100) if guild.member_count > 0 else 0
    total_health = int((security_score + activity_score) / 2)
    return total_health, security_score, activity_score

# --- TICKET CORE FUNCTION (FIXED BUTTON BUG) ---
async def create_ticket_logic(interaction: discord.Interaction, title="Session Started", reason="General Query"):
    guild = interaction.guild
    category = guild.get_channel(TICKET_CATEGORY_ID)
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }
    channel = await guild.create_text_channel(name=f"ticket-{interaction.user.name}", category=category, overwrites=overwrites)
    embed = discord.Embed(title=f"✨ {title}", description=f"Welcome {interaction.user.mention},\nReason: **{reason}**\nThe developer <@{OWNER_ID}> has been notified.", color=0x2b2d31)
    await channel.send(embed=embed, view=TicketActionView())
    if not interaction.response.is_done():
        await interaction.response.send_message(f"Ticket Created: {channel.mention}", ephemeral=True)
    else:
        await interaction.followup.send(f"Ticket Created: {channel.mention}", ephemeral=True)

# --- VIEWS ---
class OrderView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Pay via PayPal 💳", style=discord.ButtonStyle.grey, custom_id="pay_paypal_btn")
    async def pay_paypal(self, interaction, button):
        await create_ticket_logic(interaction, "PayPal Payment", "Initiating PayPal Payment")
    @discord.ui.button(label="Pay via UPI 📱", style=discord.ButtonStyle.grey, custom_id="pay_upi_btn")
    async def pay_upi(self, interaction, button):
        await create_ticket_logic(interaction, "UPI Payment", "Initiating UPI Payment")

class TicketActionView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Close Ticket 🔒", style=discord.ButtonStyle.red, custom_id="close_ticket_btn")
    async def close_ticket(self, interaction, button):
        await interaction.channel.set_permissions(interaction.user, send_messages=False, read_messages=True)
        await interaction.response.send_message(embed=discord.Embed(description="🔒 **Ticket Closed.**", color=0xff0000))
    @discord.ui.button(label="Delete 🗑️", style=discord.ButtonStyle.grey, custom_id="delete_ticket_btn")
    async def delete_ticket(self, interaction, button):
        await interaction.response.send_message("🗑️ **Deleting...**")
        await asyncio.sleep(3); await interaction.channel.delete()

class TicketView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Open Ticket 🎟️", style=discord.ButtonStyle.grey, custom_id="open_ticket_btn")
    async def open_ticket(self, interaction, button):
        await create_ticket_logic(interaction)

class DB_Manager(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(TicketView()); self.add_view(TicketActionView()); self.add_view(OrderView())

bot = DB_Manager()

# --- ECONOMY & SPAM PROOF MINING ---
@bot.event
async def on_message(message):
    if message.author.bot: return
    user_id = message.author.id
    now = datetime.datetime.now()
    if user_id in msg_cooldown:
        if (now - msg_cooldown[user_id]).total_seconds() < 5:
            await bot.process_commands(message); return
    msg_cooldown[user_id] = now
    data = get_user_data(user_id)
    data["msg_count"] += 1
    if data["msg_count"] >= 2:
        data["balance"] += 1; data["msg_count"] = 0
    await bot.process_commands(message)

# --- BOT EVENTS ---
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}'); await bot.tree.sync()

@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if not channel: return
    embed = discord.Embed(title="✨ A NEW GENIUS HAS ARRIVED!", description=f"Greetings {member.mention}, welcome to **Bots Developer**.\n📍 Open a ticket at <#{TICKET_CHANNEL_ID}> to discuss ideas.\nWe are now **{len(member.guild.members)}** members strong!", color=0x2b2d31, timestamp=datetime.datetime.utcnow())
    if member.display_avatar: embed.set_thumbnail(url=member.display_avatar.url)
    await channel.send(content=f"Welcome {member.mention}!", embed=embed)

# --- CORE COMMANDS (ORIGINAL) ---
@bot.tree.command(name="tos", description="Terms of Service for Bots Developer")
async def tos(interaction: discord.Interaction):
    embed = discord.Embed(title="📜 Terms of Service", color=0x2b2d31)
    embed.add_field(name="1. Usage", value="Our bots are for legal use only.", inline=False)
    embed.add_field(name="2. Payments", value="Upfront or 50-50. No refunds.", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="profile", description="View your premium client profile")
async def profile(interaction: discord.Interaction, member: discord.Member = None):
    member = member or interaction.user
    data = get_user_data(member.id)
    embed = discord.Embed(title=f"💠 {member.name}'s Profile", color=0x2b2d31)
    embed.add_field(name="Identity", value=f"Credits: 💠 `{data['balance']}`\nOrders: `{data['orders']}`", inline=True)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="order", description="Initialize a payment")
async def order(interaction: discord.Interaction):
    embed = discord.Embed(title="💳 Secure Payment Portal", description="Select method below.", color=0x2b2d31)
    await interaction.response.send_message(embed=embed, view=OrderView())

@bot.tree.command(name="features", description="List of all bot commands")
async def features(interaction: discord.Interaction):
    embed = discord.Embed(title="🛠️ Bot Command Interface", color=0x2b2d31)
    embed.add_field(name="Commands", value="`/profile`, `/order`, `/vouch`, `/tos`, `/health`, `/wallet`, `/gamble`, `/withdraw`", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="vouch", description="Submit your feedback")
async def vouch(interaction: discord.Interaction, stars: int, feedback: str):
    vouch_chan = bot.get_channel(VOUCH_CHANNEL_ID)
    embed = discord.Embed(title="⭐ Client Feedback", color=0x00ff7f); embed.add_field(name="Rating", value="★" * stars); embed.add_field(name="Comment", value=feedback, inline=False)
    await vouch_chan.send(embed=embed); await interaction.response.send_message("Feedback posted!", ephemeral=True)

@bot.tree.command(name="health", description="Analyze server integrity")
async def health(interaction: discord.Interaction):
    await interaction.response.defer()
    score, sec, act = calculate_health_stats(interaction.guild)
    img = Image.new('RGB', (600, 300), color=(20, 20, 20)); draw = ImageDraw.Draw(img)
    draw.text((230, 250), f"SCORE: {score}/100", fill=(255,255,255))
    with io.BytesIO() as b:
        img.save(b, 'PNG'); b.seek(0)
        await interaction.followup.send(file=discord.File(fp=b, filename='h.png'))

# --- NEW ECONOMY COMMANDS (WITH ANIMATION) ---
@bot.tree.command(name="wallet", description="View your Neural Credits balance")
async def wallet(interaction: discord.Interaction):
    data = get_user_data(interaction.user.id)
    await interaction.response.send_message(f"💠 **Wallet:** `{data['balance']} Credits` | 📩 **Progress:** `{data['msg_count']}/2` msgs")

@bot.tree.command(name="gamble", description="Risk your credits to double them")
async def gamble(interaction: discord.Interaction, amount: int):
    data = get_user_data(interaction.user.id)
    if amount <= 0 or data["balance"] < amount: return await interaction.response.send_message("Insufficient credits!", ephemeral=True)
    
    await interaction.response.send_message(f"🎰 **Spinning the Neural Reel...** (Bet: {amount} 💠)")
    await asyncio.sleep(2) # Animation delay
    
    if random.choice([True, False]):
        data["balance"] += amount
        await interaction.edit_original_response(content=f"📈 **WIN!** Your credits doubled! Balance: `{data['balance']}` 💠")
    else:
        data["balance"] -= amount
        await interaction.edit_original_response(content=f"📉 **LOSS!** Better luck next time. Balance: `{data['balance']}` 💠")

@bot.tree.command(name="withdraw", description="Redeem credits for a free bot")
async def withdraw(interaction: discord.Interaction, amount: int):
    data = get_user_data(interaction.user.id)
    if amount < 1000: return await interaction.response.send_message("Minimum 1000 Credits needed!", ephemeral=True)
    if data["balance"] < amount: return await interaction.response.send_message("Insufficient credits!", ephemeral=True)
    data["balance"] -= amount
    await create_ticket_logic(interaction, "Withdrawal Request", f"Redeeming {amount} Credits for Bot Services.")

@bot.tree.command(name="setup-ticket", description="Setup the ticket system")
async def setup_ticket(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID: return
    await interaction.channel.send(embed=discord.Embed(title="📥 Create a Ticket", color=0x2b2d31), view=TicketView())
    await interaction.response.send_message("Setup complete.", ephemeral=True)

keep_alive()
bot.run(TOKEN)
    
