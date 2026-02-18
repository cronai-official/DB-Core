import discord
from discord.ext import commands
from discord import app_commands
import datetime
import os
import asyncio
import io 
import random
from PIL import Image, ImageDraw, ImageFont
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
msg_cooldown = {}

def get_user_data(user_id):
    if user_id not in user_stats:
        user_stats[user_id] = {"orders": 0, "spent": 0, "balance": 0, "msg_count": 0}
    return user_stats[user_id]

# --- TICKET LOGIC ---
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
        await create_ticket_logic(interaction, "PayPal Payment", "Initiating PayPal Payment Request")
    @discord.ui.button(label="Pay via UPI 📱", style=discord.ButtonStyle.grey, custom_id="pay_upi_btn")
    async def pay_upi(self, interaction, button):
        await create_ticket_logic(interaction, "UPI Payment", "Initiating UPI Payment Request")

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

# --- ECONOMY SYSTEM ---
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

# --- WELCOME EVENT FIX ---
@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if not channel: return
    embed = discord.Embed(title="✨ A NEW GENIUS HAS ARRIVED!", description=f"Greetings {member.mention}, welcome to **Bots Developer**.\n\n⚡ High-performance & Secure Coding.\n💎 Tier-based Rewards & Lifetime Discounts.\n\n**Getting Started:**\n📍 Open a ticket at <#1471887200487608362> to discuss your ideas.\n📜 Read our rules to ensure a smooth transaction.\n\nWe are now **{len(member.guild.members)}** members strong!", color=0x2b2d31, timestamp=datetime.datetime.utcnow())
    if member.display_avatar: embed.set_thumbnail(url=member.display_avatar.url)
    await channel.send(content=f"Welcome {member.mention}!", embed=embed)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}'); await bot.tree.sync()

# --- PROFILE COMMAND ---
@bot.tree.command(name="profile", description="View your 4D Neural Profile Interface")
async def profile(interaction: discord.Interaction, member: discord.Member = None):
    await interaction.response.defer()
    member = member or interaction.user
    data = get_user_data(member.id)
    width, height = 800, 450
    img = Image.new('RGB', (width, height), color=(10, 10, 15))
    draw = ImageDraw.Draw(img)
    for i in range(height):
        color = (15 + i//20, 15 + i//30, 25 + i//10)
        draw.line([(0, i), (width, i)], fill=color)
    try:
        avatar_asset = member.display_avatar.with_format("png")
        avatar_data = await avatar_asset.read()
        avatar_img = Image.open(io.BytesIO(avatar_data)).convert("RGBA").resize((180, 180))
        mask = Image.new('L', (180, 180), 0)
        draw_mask = ImageDraw.Draw(mask)
        draw_mask.ellipse((0, 0, 180, 180), fill=255)
        img.paste(avatar_img, (50, 100), mask)
    except: pass
    draw.text((260, 100), f"{member.name.upper()}", fill=(255, 255, 255))
    draw.text((260, 150), f"CREDITS: 💠 {data['balance']}", fill=(0, 200, 255))
    draw.text((260, 190), f"TOTAL ORDERS: {data['orders']}", fill=(200, 200, 200))
    draw.rectangle([260, 240, 700, 260], fill=(40, 40, 50))
    progress = min((data['balance'] / 1000) * 440, 440) 
    draw.rectangle([260, 240, 260 + progress, 260], fill=(0, 255, 150))
    draw.text((260, 270), f"REDEEM PROGRESS: {int((progress/440)*100)}%", fill=(255, 255, 255))
    with io.BytesIO() as b:
        img.save(b, 'PNG'); b.seek(0)
        await interaction.followup.send(file=discord.File(fp=b, filename='profile.png'))

# --- OTHER COMMANDS ---
@bot.tree.command(name="order", description="Initialize a payment & open a ticket")
async def order(interaction: discord.Interaction):
    embed = discord.Embed(title="💳 Neural Payment Portal", description="Select your payment method. Clicking a button will automatically open a secure ticket for your order.", color=0x2b2d31)
    embed.set_footer(text="Secure Transaction • Bots Developer")
    await interaction.response.send_message(embed=embed, view=OrderView())

@bot.tree.command(name="vouch", description="Submit feedback (1-5 Stars)")
async def vouch(interaction: discord.Interaction, stars: int, feedback: str):
    if not (1 <= stars <= 5): return await interaction.response.send_message("❌ Error: Rating must be 1-5 stars!", ephemeral=True)
    vouch_chan = bot.get_channel(VOUCH_CHANNEL_ID)
    embed = discord.Embed(title="⭐ New Client Vouch", color=0x00ff7f, timestamp=datetime.datetime.utcnow())
    embed.add_field(name="Rating", value="★" * stars, inline=True)
    embed.add_field(name="Feedback", value=f"```\n{feedback}\n```", inline=False)
    await vouch_chan.send(embed=embed)
    await interaction.response.send_message("✅ Recorded!", ephemeral=True)

@bot.tree.command(name="tos", description="Strict Terms of Service")
async def tos(interaction: discord.Interaction):
    embed = discord.Embed(title="📜 Official Terms of Service", color=0x2b2d31)
    embed.add_field(name="⚖️ Usage", value="Bots are for authorized use only.", inline=False)
    embed.add_field(name="💸 Payments", value="Non-refundable. 50% advance required.", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="features", description="Detailed Command List")
async def features(interaction: discord.Interaction):
    embed = discord.Embed(title="🛠️ Neural Command Interface", color=0x2b2d31)
    embed.add_field(name="User", value="`/profile`, `/wallet`, `/vouch`", inline=False)
    embed.add_field(name="Economy", value="`/gamble`, `/withdraw`, `/order`", inline=False)
    embed.add_field(name="Legal", value="`/tos`", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="wallet", description="View your credits")
async def wallet(interaction: discord.Interaction):
    data = get_user_data(interaction.user.id)
    await interaction.response.send_message(f"💠 **Balance:** `{data['balance']} Neural Credits` | **Mining:** `{data['msg_count']}/2` msgs")

@bot.tree.command(name="gamble", description="Gamble credits with animation")
async def gamble(interaction: discord.Interaction, amount: int):
    data = get_user_data(interaction.user.id)
    if amount <= 0 or data["balance"] < amount: return await interaction.response.send_message("Insufficient funds!", ephemeral=True)
    await interaction.response.send_message("🎰 **ROLLING...**")
    await asyncio.sleep(2)
    if random.choice([True, False]):
        data["balance"] += amount
        await interaction.edit_original_response(content=f"✅ **WIN!** New Balance: `{data['balance']}` 💠")
    else:
        data["balance"] -= amount
        await interaction.edit_original_response(content=f"❌ **LOST!** New Balance: `{data['balance']}` 💠")

@bot.tree.command(name="withdraw", description="Redeem credits")
async def withdraw(interaction: discord.Interaction, amount: int):
    data = get_user_data(interaction.user.id)
    if amount < 1000: return await interaction.response.send_message("Min 1000 Credits!", ephemeral=True)
    if data["balance"] < amount: return await interaction.response.send_message("No balance!", ephemeral=True)
    data["balance"] -= amount
    await create_ticket_logic(interaction, "Withdrawal", f"Redeeming {amount} Credits")

@bot.tree.command(name="setup-ticket", description="Setup tickets")
async def setup_ticket(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID: return
    await interaction.channel.send(view=TicketView())
    await interaction.response.send_message("Done.", ephemeral=True)

keep_alive()
bot.run(TOKEN)
    
