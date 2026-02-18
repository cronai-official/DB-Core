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

# --- WEB SERVER ---
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
msg_cooldown = {} # Anti-spam

def get_user_data(user_id):
    if user_id not in user_stats:
        user_stats[user_id] = {"orders": 0, "spent": 0, "balance": 0, "msg_count": 0}
    return user_stats[user_id]

# --- TICKET CORE FUNCTION (FIXED BUG) ---
async def create_ticket_logic(interaction: discord.Interaction, title="Session Started", reason="General Query"):
    guild = interaction.guild
    category = guild.get_channel(TICKET_CATEGORY_ID)
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }
    channel = await guild.create_text_channel(name=f"ticket-{interaction.user.name}", category=category, overwrites=overwrites)
    
    embed = discord.Embed(title=f"✨ {title}", description=f"Welcome {interaction.user.mention},\nReason: **{reason}**\n\nThe developer <@{OWNER_ID}> has been notified.", color=0x2b2d31)
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
        await create_ticket_logic(interaction, "PayPal Payment", "Initiating PayPal Transaction")

    @discord.ui.button(label="Pay via UPI 📱", style=discord.ButtonStyle.grey, custom_id="pay_upi_btn")
    async def pay_upi(self, interaction, button):
        await create_ticket_logic(interaction, "UPI Payment", "Initiating UPI Transaction")

class TicketActionView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Close Ticket 🔒", style=discord.ButtonStyle.red, custom_id="close_ticket_btn")
    async def close_ticket(self, interaction, button):
        await interaction.channel.set_permissions(interaction.user, send_messages=False, read_messages=True)
        await interaction.response.send_message(embed=discord.Embed(description="🔒 **Ticket Closed.**", color=0xff0000))
    @discord.ui.button(label="Delete 🗑️", style=discord.ButtonStyle.grey, custom_id="delete_ticket_btn")
    async def delete_ticket(self, interaction, button):
        await interaction.response.send_message("🗑️ **Deleting...**")
        await asyncio.sleep(3)
        await interaction.channel.delete()

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

# --- ECONOMY & SPAM PROOF ---
@bot.event
async def on_message(message):
    if message.author.bot: return
    user_id = message.author.id
    now = datetime.datetime.now()
    
    # Anti-Spam: 5 seconds gap
    if user_id in msg_cooldown:
        if (now - msg_cooldown[user_id]).total_seconds() < 5:
            await bot.process_commands(message)
            return
            
    msg_cooldown[user_id] = now
    data = get_user_data(user_id)
    data["msg_count"] += 1
    
    if data["msg_count"] >= 2:
        data["balance"] += 1
        data["msg_count"] = 0
    await bot.process_commands(message)

# --- ECONOMY COMMANDS ---
@bot.tree.command(name="wallet", description="View your Neural Credits balance")
async def wallet(interaction: discord.Interaction):
    data = get_user_data(interaction.user.id)
    embed = discord.Embed(title="💠 Neural Interface: Wallet", color=0x2b2d31)
    embed.add_field(name="Balance", value=f"💠 `{data['balance']} Credits`", inline=True)
    embed.add_field(name="Activity", value="`2 msgs = 1 Credit`", inline=True)
    embed.set_footer(text="Earn credits by being active in chat.")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="gamble", description="Risk your credits to double them")
async def gamble(interaction: discord.Interaction, amount: int):
    data = get_user_data(interaction.user.id)
    if amount <= 0 or data["balance"] < amount:
        return await interaction.response.send_message("Invalid amount or insufficient credits!", ephemeral=True)
    
    win = random.choice([True, False])
    if win:
        data["balance"] += amount
        await interaction.response.send_message(f"🎰 **JACKPOT!** You won `{amount}` Credits! Total: `{data['balance']}`")
    else:
        data["balance"] -= amount
        await interaction.response.send_message(f"📉 **LOST!** You lost `{amount}` Credits. Total: `{data['balance']}`")

@bot.tree.command(name="withdraw", description="Redeem credits for a free custom bot")
async def withdraw(interaction: discord.Interaction, amount: int):
    data = get_user_data(interaction.user.id)
    if amount < 1000:
        return await interaction.response.send_message("Minimum withdrawal for a bot is 1000 Credits!", ephemeral=True)
    if data["balance"] < amount:
        return await interaction.response.send_message("Insufficient Credits!", ephemeral=True)
    
    data["balance"] -= amount
    await create_ticket_logic(interaction, "Withdrawal Request", f"Redeeming {amount} Credits for a Custom Bot.")

# --- REST OF THE CODE (No Changes) ---
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f'Logged in as {bot.user}')

@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if not channel: return
    embed = discord.Embed(title="✨ A NEW GENIUS HAS ARRIVED!", description=f"Greetings {member.mention}, welcome to **Bots Developer**.\n\n📍 Open a ticket at <#{TICKET_CHANNEL_ID}> to discuss ideas.\nWe are now **{len(member.guild.members)}** members strong!", color=0x2b2d31)
    if member.display_avatar: embed.set_thumbnail(url=member.display_avatar.url)
    await channel.send(content=f"Welcome {member.mention}!", embed=embed)

@bot.tree.command(name="order")
async def order(interaction: discord.Interaction):
    embed = discord.Embed(title="💳 Secure Payment Portal", description="Select method below. Each button opens a secure ticket.", color=0x2b2d31)
    await interaction.response.send_message(embed=embed, view=OrderView())

@bot.tree.command(name="features")
async def features(interaction: discord.Interaction):
    embed = discord.Embed(title="🛠️ Bot Interface", color=0x2b2d31)
    embed.add_field(name="Economy", value="`/wallet`, `/gamble`, `/withdraw`", inline=False)
    embed.add_field(name="Services", value="`/order`, `/profile`, `/tos`", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="profile")
async def profile(interaction: discord.Interaction, member: discord.Member = None):
    member = member or interaction.user
    data = get_user_data(member.id)
    embed = discord.Embed(title=f"💠 {member.name}'s Profile", color=0x2b2d31)
    embed.add_field(name="Stats", value=f"Orders: `{data['orders']}`\nCredits: `{data['balance']}`", inline=True)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="setup-ticket")
async def setup_ticket(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID: return
    await interaction.channel.send(embed=discord.Embed(title="📥 Create a Ticket", color=0x2b2d31), view=TicketView())
    await interaction.response.send_message("Setup complete.", ephemeral=True)

keep_alive()
bot.run(TOKEN)
                                                                   
