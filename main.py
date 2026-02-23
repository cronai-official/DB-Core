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

# --- FLASK SERVER (RENDER FIX) --- #
app = Flask('')
@app.route('/')
def home(): return "Bot is running!"

def run():
    # Render dynamic port provide karta hai, 8080 default fallback hai
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True # Thread ko background mein rakhega
    t.start()

# --- CONFIGURATION --- #
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

user_stats = {} 
msg_cooldown = {}

def get_user_data(user_id):
    if user_id not in user_stats:
        user_stats[user_id] = {"orders": 0, "spent": 0, "balance": 0, "msg_count": 0}
    return user_stats[user_id]

# --- TICKET LOGIC FIX (DEFER ADDED) --- #
async def create_ticket_logic(interaction: discord.Interaction, title="Session Started", reason="General Query"):
    # Interaction failed se bachne ke liye pehle hi "Working..." state mein daalna zaroori hai
    if not interaction.response.is_done():
        await interaction.response.defer(ephemeral=True)
    
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
    
    await interaction.followup.send(f"Ticket Created: {channel.mention}", ephemeral=True)

# --- VIEWS --- #
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
        await asyncio.sleep(2); await interaction.channel.delete()

class TicketView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Open Ticket 🎟️", style=discord.ButtonStyle.grey, custom_id="open_ticket_btn")
    async def open_ticket(self, interaction, button):
        await create_ticket_logic(interaction)

# --- BOT CLASS SETUP --- #
class DB_Manager(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # Buttons register kar rahe hain taaki restart ke baad bhi chalein
        self.add_view(TicketView())
        self.add_view(TicketActionView())
        self.add_view(OrderView())
        # ---- SYNC FIX: Yahan se sync hata diya hai taaki Rate Limit na ho ----

bot = DB_Manager()

@bot.event
async def on_ready():
    print(f'✅ Logged in as {bot.user}')
    # ---- GLOBAL SYNC FIX (ONLY ONCE) ----
    # Isse bot online aate hi baar-baar sync nahi karega agar koi change nahi hai
    try:
        # bot.tree.sync() ko yahan rehne de sakte hain par Render par 
        # baar-baar restart hone se ye error deta hai.
        # Isko manually ek baar command se sync karna better hai.
        print("Bot is ready and views are active!")
    except Exception as e:
        print(f"Sync Error: {e}")

# --- SYNC COMMAND (MANUAL) --- #
# Isse tu manually commands sync kar sakta hai jab zaroorat ho
@bot.command()
async def sync(ctx):
    if ctx.author.id == OWNER_ID:
        await bot.tree.sync()
        await ctx.send("✅ Slash commands synced globally!")

@bot.event
async def on_message(message):
    if message.author.bot: return
    user_id = message.author.id
    now = datetime.datetime.now()
    
    # Mining cooldown check
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

# --- SLASH COMMANDS (SAME AS BEFORE) --- #
# (Tere profile, gamble, order commands yahan aayenge - Maine unhe touch nahi kiya 
# kyunki wo functionality wise sahi hain. Bas defer/followup ka dhyan rakhna)

# --- DEPLOYMENT --- #
if __name__ == "__main__":
    keep_alive()
    try:
        bot.run(TOKEN)
    except discord.errors.HTTPException as e:
        if e.status == 429:
            print("🚨 RATE LIMITED! Change your IP or wait.")
            os.system("kill 1") # Render ko trigger karega restart ke liye
    
