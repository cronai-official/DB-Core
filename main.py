import discord
from discord.ext import commands
from discord import app_commands
import datetime
import os
import asyncio
import io 
from PIL import Image, ImageDraw 
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

def get_user_data(user_id):
    if user_id not in user_stats:
        user_stats[user_id] = {"orders": 0, "spent": 0}
    return user_stats[user_id]

# --- HEALTH ANALYSIS LOGIC ---
def calculate_health_stats(guild):
    admin_count = len([m for m in guild.members if m.guild_permissions.administrator])
    security_score = 100 - (admin_count * 10) if admin_count < 10 else 10
    online = len([m for m in guild.members if m.status != discord.Status.offline])
    activity_score = int((online / guild.member_count) * 100) if guild.member_count > 0 else 0
    total_health = int((security_score + activity_score) / 2)
    return total_health, security_score, activity_score

# --- PAYMENT BUTTONS (MODIFIED: OPENS TICKET DIRECTLY) ---
class OrderView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Pay via PayPal 💳", style=discord.ButtonStyle.grey, custom_id="pay_paypal_btn")
    async def pay_paypal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await TicketView().open_ticket(interaction, button)

    @discord.ui.button(label="Pay via UPI 📱", style=discord.ButtonStyle.grey, custom_id="pay_upi_btn")
    async def pay_upi(self, interaction: discord.Interaction, button: discord.ui.Button):
        await TicketView().open_ticket(interaction, button)

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
        embed = discord.Embed(title="✨ Session Started", description=f"Welcome {interaction.user.mention},\nThe developer <@{OWNER_ID}> has been notified. Please state your requirements and budget below.", color=0x2b2d31)
        await channel.send(embed=embed, view=TicketActionView())
        if not interaction.response.is_done():
            await interaction.response.send_message(f"Ticket Created: {channel.mention}", ephemeral=True)
        else:
            await interaction.followup.send(f"Ticket Created: {channel.mention}", ephemeral=True)

class DB_Manager(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())

    async def setup_hook(self):
        self.add_view(TicketView())
        self.add_view(TicketActionView())
        self.add_view(OrderView())

bot = DB_Manager()

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    await bot.tree.sync()

# --- MODIFIED WELCOME SYSTEM ---
@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if not channel: return

    embed = discord.Embed(
        title="✨ A NEW GENIUS HAS ARRIVED!",
        description=f"Greetings {member.mention}, welcome to **Bots Developer**.\n\n"
                    f"**Why choose our services?**\n"
                    f"⚡ High-performance & Secure Coding.\n"
                    f"💎 Tier-based Rewards & Lifetime Discounts.\n\n"
                    f"**Getting Started:**\n"
                    f"📍 Open a ticket at <#{TICKET_CHANNEL_ID}> to discuss your ideas.\n"
                    f"📜 Read our rules to ensure a smooth transaction.\n\n"
                    f"We are now **{len(member.guild.members)}** members strong!",
        color=0x2b2d31,
        timestamp=datetime.datetime.utcnow()
    )
    
    if member.display_avatar:
        embed.set_thumbnail(url=member.display_avatar.url)
    
    embed.set_author(name=f"Welcome to {member.guild.name}", icon_url=member.guild.icon.url if member.guild.icon else None)
    embed.set_footer(text=f"User ID: {member.id} • Authorized Entrance")

    await channel.send(content=f"Welcome {member.mention}! Glad to have you with us.", embed=embed)

# --- CORE COMMANDS ---

@bot.tree.command(name="tos", description="Terms of Service for Bots Developer")
async def tos(interaction: discord.Interaction):
    embed = discord.Embed(title="📜 Terms of Service", color=0x2b2d31, timestamp=datetime.datetime.utcnow())
    embed.add_field(name="1. Usage", value="Our bots are for legal use only. Reverse engineering is prohibited.", inline=False)
    embed.add_field(name="2. Payments", value="All payments are upfront or 50-50 based on the project scale. No refunds after delivery.", inline=False)
    embed.add_field(name="3. Support", value="Lifetime bug support for premium clients. Feature additions may cost extra.", inline=False)
    embed.set_footer(text="By ordering, you agree to these terms.")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="profile", description="View your premium client profile")
async def profile(interaction: discord.Interaction, member: discord.Member = None):
    member = member or interaction.user
    data = get_user_data(member.id)
    
    trust_level = "Newbie"
    if data["orders"] > 10: trust_level = "Veteran ⭐"
    elif data["orders"] > 5: trust_level = "Trusted ✅"
    
    role_names = [role.name for role in member.roles if role.id in ROLES.values()]
    current_tier = role_names[0] if role_names else "No Tier"

    embed = discord.Embed(title=f"💠 {member.name}'s Neural Interface", color=0x2b2d31)
    embed.set_thumbnail(url=member.display_avatar.url if member.display_avatar else None)
    
    embed.add_field(name="🆔 Identity", value=f"**User:** {member.mention}\n**Tier:** `{current_tier}`", inline=True)
    embed.add_field(name="🛡️ Trust Level", value=f"`{trust_level}`", inline=True)
    embed.add_field(name="📊 Statistics", value=f"**Orders:** `{data['orders']}`\n**Spent:** `${data['spent']}`", inline=False)
    
    embed.set_footer(text="Bots Developer Premium Interface")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="order", description="Initialize a payment")
async def order(interaction: discord.Interaction):
    embed = discord.Embed(
        title="💳 Secure Payment Portal",
        description="Select your preferred payment method below.\n\n**Note:** Once payment is done, please share the screenshot in your ticket.",
        color=0x2b2d31
    )
    embed.set_footer(text="Encryption Active • Secure Transaction")
    await interaction.response.send_message(embed=embed, view=OrderView())

@bot.tree.command(name="features", description="List of all bot commands")
async def features(interaction: discord.Interaction):
    embed = discord.Embed(title="🛠️ Bot Command Interface", color=0x2b2d31)
    embed.add_field(name="User Commands", value="• `/profile` - Check your stats\n• `/order` - Get payment links\n• `/vouch` - Post feedback\n• `/tos` - View terms", inline=False)
    embed.add_field(name="Utility", value="• `/health` - Server diagnostics\n• `/setup-ticket` - Admin setup", inline=False)
    embed.set_footer(text="Developed for Bots Developer")
    await interaction.response.send_message(embed=embed)

# --- ADMIN COMMANDS ---

@bot.tree.command(name="setup-ticket", description="Setup the ticket system")
async def setup_ticket(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID: return await interaction.response.send_message("Permission Denied.", ephemeral=True)
    embed = discord.Embed(title="📥 Create a Ticket", description="Click the button below to start a conversation for development or queries.", color=0x2b2d31)
    await interaction.channel.send(embed=embed, view=TicketView())
    await interaction.response.send_message("Ticket system setup complete.", ephemeral=True)

@bot.tree.command(name="vouch", description="Submit your feedback")
async def vouch(interaction: discord.Interaction, stars: int, feedback: str):
    vouch_chan = bot.get_channel(VOUCH_CHANNEL_ID)
    if stars < 1 or stars > 5: return await interaction.response.send_message("Provide 1-5 stars.", ephemeral=True)
    embed = discord.Embed(title="⭐ Client Feedback", color=0x00ff7f, timestamp=datetime.datetime.utcnow())
    embed.add_field(name="Client", value=interaction.user.mention, inline=True)
    embed.add_field(name="Rating", value="★" * stars, inline=True)
    embed.add_field(name="Comment", value=feedback, inline=False)
    if interaction.user.display_avatar: embed.set_thumbnail(url=interaction.user.display_avatar.url)
    await vouch_chan.send(embed=embed)
    await interaction.response.send_message("Feedback posted!", ephemeral=True)

@bot.tree.command(name="set-tier", description="Assign client roles and update stats")
async def set_tier(interaction: discord.Interaction, member: discord.Member, amount: int):
    if interaction.user.id != OWNER_ID: return
    data = get_user_data(member.id)
    data["orders"] += 1
    data["spent"] += amount
    role_id = ROLES["Client"]
    if amount >= 50000: role_id = ROLES["Elite"]
    elif amount >= 20000: role_id = ROLES["Prime"]
    elif amount >= 10000: role_id = ROLES["Vested"]
    role = interaction.guild.get_role(role_id)
    if role: await member.add_roles(role)
    await interaction.response.send_message(f"✅ {member.mention} stats updated and role assigned!")

@bot.tree.command(name="health", description="Analyze server integrity")
async def health(interaction: discord.Interaction):
    await interaction.response.defer()
    score, sec_score, act_score = calculate_health_stats(interaction.guild)
    img = Image.new('RGB', (600, 350), color=(20, 20, 20))
    draw = ImageDraw.Draw(img)
    draw.text((220, 20), "SERVER DIAGNOSTICS", fill=(255, 255, 255))
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
        embed = discord.Embed(title=f"🔍 Health Analysis", color=0x2b2d31)
        embed.set_image(url="attachment://health.png")
        await interaction.followup.send(file=file, embed=embed)

keep_alive()
bot.run(TOKEN)
    
