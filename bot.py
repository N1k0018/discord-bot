import discord
from discord.ext import commands
import os
import json
from datetime import datetime, timedelta
from keep_alive import keep_alive

# --- AYARLAR ---
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

ROLLER = {
    "UFC-live": 1525780352679809125,
    "ROK-rise of kingdoms": 1525779899745308712,
    "Steam-alıcı": 1510649566972870767,
    "Sohbet": 1486012917324185600
}

DILLER = {
    "Azerbaycanca": 1526232723029758073,
    "Türkçe": 1526233376678481920,
    "İngilizce": 1526233442616868974,
    "İspanyolca": 1526233508610310256,
    "Fransızca": 1526233568043602062,
    "Çince": 1526233733752033411,
    "Hintçe": 1526233677053562890,
    "Arapça": 1526233633650901132
}

COOLDOWN_DAYS = 3
DATA_FILE = "user_data.json"

# --- VERİ YÖNETİMİ ---
def load_data():
    if not os.path.exists(DATA_FILE): return {"rol_data": {}, "dil_data": {}}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

USER_DATA = load_data()

def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(USER_DATA, f, ensure_ascii=False, indent=2)

# --- PANEL ---
class BirlesikPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    # 1. ROL SEÇİMİ (3 GÜN COOLDOWN)
    @discord.ui.select(placeholder="Rolünü seç...", custom_id="persistent_role", 
                       options=[discord.SelectOption(label=n, value=str(i)) for n, i in ROLLER.items()])
    async def role_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        user_id = str(interaction.user.id)
        state = USER_DATA["rol_data"].setdefault(user_id, {"first_made": False, "last_time": None})
        
        # 3 Günlük kontrol
        if state["first_made"] and state["last_time"]:
            last_time = datetime.fromisoformat(state["last_time"])
            if datetime.now() - last_time < timedelta(days=COOLDOWN_DAYS):
                await interaction.response.send_message(f"❌ Rol değiştirmek için {COOLDOWN_DAYS} gün beklemen gerekiyor.", ephemeral=True)
                return

        yeni_rol = interaction.guild.get_role(int(select.values[0]))
        await interaction.user.add_roles(yeni_rol)
        
        state["first_made"] = True
        state["last_time"] = datetime.now().isoformat()
        save_data()
        
        await interaction.response.send_message(f"✅ {yeni_rol.name} rolü verildi!", ephemeral=True)

    # 2. DİL SEÇİMİ (5 DAKİKA COOLDOWN)
    @discord.ui.select(placeholder="Dilini seç...", custom_id="persistent_dil", 
                       options=[discord.SelectOption(label=n, value=str(i)) for n, i in DILLER.items()])
    async def dil_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        user_id = str(interaction.user.id)
        state = USER_DATA["dil_data"].setdefault(user_id, {"last_time": None})
        
        # 5 Dakikalık kontrol
        if state["last_time"]:
            last_time = datetime.fromisoformat(state["last_time"])
            if datetime.now() - last_time < timedelta(minutes=5):
                await interaction.response.send_message("❌ Dilini değiştirmek için 5 dakika beklemen gerekiyor.", ephemeral=True)
                return

        yeni_dil = interaction.guild.get_role(int(select.values[0]))
        eski_roller = [r for r in interaction.user.roles if r.id in DILLER.values()]
        await interaction.user.remove_roles(*eski_roller)
        await interaction.user.add_roles(yeni_dil)
        
        state["last_time"] = datetime.now().isoformat()
        save_data()
        
        await interaction.response.send_message(f"✅ Dilin {yeni_dil.name} olarak ayarlandı!", ephemeral=True)

@bot.event
async def on_ready():
    bot.add_view(BirlesikPanel())
    print(f"{bot.user} hazır!")

@bot.command()
@commands.has_permissions(administrator=True)
async def rolmenu(ctx):
    await ctx.message.delete()
    embed = discord.Embed(title="Panel", description="Rol ve Dil seçimlerini aşağıdan yapabilirsin.", color=0x00ff00)
    await ctx.send(embed=embed, view=BirlesikPanel())

keep_alive()
bot.run(os.getenv("TOKEN"))