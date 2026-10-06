import discord
from discord import app_commands
from discord.ext import commands
import random
import json
import os

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

DATA_FILE = "game_data.json"
ADMIN_USERNAME = "rexa.playz"

BOXES = {
    "common": {
        "cost": 50,
        "items": {
            "Poop": {"value": 1, "chance": 60},
            "Used Sock": {"value": 5, "chance": 30},
            "Rusty Coin": {"value": 15, "chance": 10}
        }
    },
    "uncommon": {
        "cost": 150,
        "items": {
            "Pocket Knife": {"value": 50, "chance": 60},
            "Silver Ring": {"value": 120, "chance": 30},
            "Old Watch": {"value": 250, "chance": 10}
        }
    },
    "rare": {
        "cost": 500,
        "items": {
            "Gold Bar": {"value": 400, "chance": 60},
            "Diamond Ring": {"value": 800, "chance": 30},
            "Ancient Scroll": {"value": 1500, "chance": 10}
        }
    },
    "epic": {
        "cost": 2000,
        "items": {
            "Ruby Crown": {"value": 1800, "chance": 60},
            "Dragon Egg": {"value": 3500, "chance": 30},
            "Alien Tech": {"value": 7000, "chance": 10}
        }
    },
    "legendary": {
        "cost": 10000,
        "items": {
            "Meteorite Core": {"value": 9000, "chance": 60},
            "Time Crystal": {"value": 20000, "chance": 30},
            "Holy Grail": {"value": 50000, "chance": 10}
        }
    }
}

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"users": {}, "shop_stock": generate_shop_stock()}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def generate_shop_stock():
    return {
        "common": random.randint(10, 20),
        "uncommon": random.randint(5, 12),
        "rare": random.randint(2, 6),
        "epic": random.randint(1, 3),
        "legendary": random.randint(0, 1)
    }

def get_user(data, user_id):
    user_str = str(user_id)
    if user_str not in data["users"]:
        data["users"][user_str] = {"balance": 100, "boxes": {}, "inventory": {}}
    return data["users"][user_str]

def is_admin(interaction: discord.Interaction) -> bool:
    return interaction.user.name.lower() == ADMIN_USERNAME.lower()

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")

@bot.tree.command(name="cmds", description="View all available game commands")
async def cmds(interaction: discord.Interaction):
    embed = discord.Embed(title="📜 Game Commands", color=discord.Color.blue())
    embed.add_field(name="🎮 General", value="`/balance`, `/gamble <amount>`, `/inventory`, `/work`", inline=False)
    embed.add_field(name="🛒 Shop", value="`/shop`, `/refresh`, `/buy <box>`, `/open <box>`, `/sell <item>`", inline=False)
    embed.add_field(name="👑 Admin", value="`/stock`, `/give`, `/refreshadm`", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="balance", description="Check your cash balance")
async def balance(interaction: discord.Interaction):
    data = load_data()
    user = get_user(data, interaction.user.id)
    await interaction.response.send_message(f"💰 You currently have **${user['balance']}**")

@bot.tree.command(name="gamble", description="Risk money: 25% for 2x, 74% lose, 1% for 5x jackpot!")
async def gamble(interaction: discord.Interaction, amount: int):
    if amount <= 0:
        await interaction.response.send_message("Enter an amount greater than 0.", ephemeral=True)
        return
    data = load_data()
    user = get_user(data, interaction.user.id)
    if user["balance"] < amount:
        await interaction.response.send_message("You don't have enough money!", ephemeral=True)
        return
    roll = random.uniform(0, 100)
    if roll <= 1.0:
        winnings = amount * 5
        user["balance"] += winnings - amount
        msg = f"🎉 **JACKPOT!** You hit 5x and won **${winnings}**!"
    elif roll <= 26.0:
        winnings = amount * 2
        user["balance"] += winnings - amount
        msg = f"🟢 **WIN!** You hit 2x and won **${winnings}**!"
    else:
        user["balance"] -= amount
        msg = f"🔴 **LOSS!** You lost **${amount}**."
    save_data(data)
    await interaction.response.send_message(f"{msg}\nNew balance: **${user['balance']}**")

@bot.tree.command(name="work", description="Work to get extra cash")
@app_commands.checks.cooldown(1, 60)
async def work(interaction: discord.Interaction):
    earned = random.randint(15, 60)
    data = load_data()
    user = get_user(data, interaction.user.id)
    user["balance"] += earned
    save_data(data)
    await interaction.response.send_message(f"💼 You earned **${earned}**!")

@bot.tree.command(name="shop", description="View mystery boxes in stock")
async def shop(interaction: discord.Interaction):
    data = load_data()
    embed = discord.Embed(title="🏬 Mystery Box Shop", color=discord.Color.green())
    for box_name, details in BOXES.items():
        count = data["shop_stock"].get(box_name, 0)
        embed.add_field(name=f"📦 {box_name.capitalize()} Box", value=f"Price: ${details['cost']}\nStock: {count}", inline=True)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="refresh", description="Refresh the shop stock")
@app_commands.checks.cooldown(1, 300)
async def refresh(interaction: discord.Interaction):
    data = load_data()
    data["shop_stock"] = generate_shop_stock()
    save_data(data)
    await interaction.response.send_message("🔄 The shop stock has been refreshed!")

@bot.tree.command(name="buy", description="Buy a mystery box")
@app_commands.choices(box=[app_commands.Choice(name=b.capitalize(), value=b) for b in BOXES.keys()])
async def buy(interaction: discord.Interaction, box: str):
    box = box.lower()
    data = load_data()
    user = get_user(data, interaction.user.id)
    if data["shop_stock"].get(box, 0) <= 0:
        await interaction.response.send_message("Box out of stock!", ephemeral=True)
        return
    cost = BOXES[box]["cost"]
    if user["balance"] < cost:
        await interaction.response.send_message(f"You need **${cost}**!", ephemeral=True)
        return
    user["balance"] -= cost
    data["shop_stock"][box] -= 1
    user["boxes"][box] = user["boxes"].get(box, 0) + 1
    save_data(data)
    await interaction.response.send_message(f"🛒 Bought a **{box.capitalize()} Box**!")

@bot.tree.command(name="open", description="Open a mystery box")
@app_commands.choices(box=[app_commands.Choice(name=b.capitalize(), value=b) for b in BOXES.keys()])
async def open_box(interaction: discord.Interaction, box: str):
    box = box.lower()
    data = load_data()
    user = get_user(data, interaction.user.id)
    if user["boxes"].get(box, 0) <= 0:
        await interaction.response.send_message("You don't own this box!", ephemeral=True)
        return
    user["boxes"][box] -= 1
    items_pool = BOXES[box]["items"]
    item_names = list(items_pool.keys())
    weights = [items_pool[i]["chance"] for i in item_names]
    won_item = random.choices(item_names, weights=weights, k=1)[0]
    val = items_pool[won_item]["value"]
    user["inventory"][won_item] = user["inventory"].get(won_item, 0) + 1
    save_data(data)
    await interaction.response.send_message(f"🎁 Opened **{box.capitalize()} Box** and got **{won_item}** (Worth: **${val}**)!")

@bot.tree.command(name="inventory", description="View your inventory")
async def inventory(interaction: discord.Interaction):
    data = load_data()
    user = get_user(data, interaction.user.id)
    boxes_str = "\n".join([f"• **{b.capitalize()}**: {c}" for b, c in user["boxes"].items() if c > 0]) or "None"
    items_str = "\n".join([f"• **{i}**: {c}" for i, c in user["inventory"].items() if c > 0]) or "None"
    embed = discord.Embed(title=f"🎒 Inventory", color=discord.Color.purple())
    embed.add_field(name="📦 Boxes", value=boxes_str, inline=False)
    embed.add_field(name="💎 Items", value=items_str, inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="sell", description="Sell an item")
async def sell(interaction: discord.Interaction, item: str, amount: int = 1):
    data = load_data()
    user = get_user(data, interaction.user.id)
    item_data = None
    for b_data in BOXES.values():
        if item.title() in b_data["items"]:
            item_data = b_data["items"][item.title()]
            item = item.title()
            break
    if not item_data or user["inventory"].get(item, 0) < amount:
        await interaction.response.send_message("Item not found or insufficient quantity!", ephemeral=True)
        return
    total_value = item_data["value"] * amount
    user["inventory"][item] -= amount
    user["balance"] += total_value
    save_data(data)
    await interaction.response.send_message(f"💰 Sold **{amount}x {item}** for **${total_value}**!")

# ADMIN COMMANDS (@rexa.playz)
@bot.tree.command(name="stock", description="[ADMIN] Set box stock")
@app_commands.choices(box=[app_commands.Choice(name=b.capitalize(), value=b) for b in BOXES.keys()])
async def stock(interaction: discord.Interaction, box: str, count: int):
    if not is_admin(interaction):
        await interaction.response.send_message("❌ Admin access denied.", ephemeral=True)
        return
    data = load_data()
    data["shop_stock"][box.lower()] = max(0, count)
    save_data(data)
    await interaction.response.send_message(f"⚙️ Admin: Set **{box.capitalize()} Box** stock to **{count}**.")

@bot.tree.command(name="give", description="[ADMIN] Give items or boxes to a user")
async def give(interaction: discord.Interaction, user: discord.Member, item_or_box: str, amount: int = 1):
    if not is_admin(interaction):
        await interaction.response.send_message("❌ Admin access denied.", ephemeral=True)
        return
    data = load_data()
    target_user = get_user(data, user.id)
    target_name = item_or_box.lower()
    if target_name in BOXES:
        target_user["boxes"][target_name] = target_user["boxes"].get(target_name, 0) + amount
        msg = f"Gave **{amount}x {target_name.capitalize()} Box(es)** to {user.mention}."
    else:
        formatted_item = item_or_box.title()
        target_user["inventory"][formatted_item] = target_user["inventory"].get(formatted_item, 0) + amount
        msg = f"Gave **{amount}x {formatted_item}** to {user.mention}."
    save_data(data)
    await interaction.response.send_message(f"🎁 Admin: {msg}")

@bot.tree.command(name="refreshadm", description="[ADMIN] Refresh shop without cooldown")
async def refreshadm(interaction: discord.Interaction):
    if not is_admin(interaction):
        await interaction.response.send_message("❌ Admin access denied.", ephemeral=True)
        return
    data = load_data()
    data["shop_stock"] = generate_shop_stock()
    save_data(data)
    await interaction.response.send_message("⚡ Admin: Shop stock forcefully refreshed!")

token = os.environ.get("DISCORD_TOKEN")
bot.run(token)
