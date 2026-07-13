import discord
from discord.ext import commands, tasks
import os
import json
from datetime import datetime, timedelta
from keep_alive import keep_alive

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ----------------- ROLLER VE DİLLER -----------------
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

def load_data():
    if not os.path.exists(DATA_FILE): return {}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            return json.loads(content) if content else {}
    except: return {}

def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(USER_DATA, f, ensure_ascii=False, indent=2)

USER_DATA = load_data()

# --- MEVCUT ROL SİSTEMİ FONKSİYONLARI ---
def get_user_state(guild_id: int, user_id: int):
    if "rol_data" not in USER_DATA: USER_DATA["rol_data"] = {}
    guild_key = str(guild_id)
    user_key = str(user_id)
    guild_data = USER_DATA["rol_data"].setdefault(guild_key, {})
    if user_key not in guild_data:
        guild_data[user_key] = {"first_selection_made": False, "free_change_used": False, "last_change_time": None}
    return guild_data[user_key]

# --- YENİ DİL SİSTEMİ FONKSİYONLARI ---
def get_dil_state(guild_id: int, user_id: int):
    if "dil_data" not in USER_DATA: USER_DATA["dil_data"] = {}
    key = f"{guild_id}-{user_id}"
    if key not in USER_DATA["dil_data"]:
        USER_DATA["dil_data"][key] = {"last_change": None}
    return USER_DATA["dil_data"][key]

# ----------------- ROL VIEW (ESKİ SİSTEM) -----------------
class RolView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(placeholder="Rolünü seç...", custom_id="persistent_select_main", 
                       options=[discord.SelectOption(label=n, value=str(i)) for n, i in ROLLER.items()])
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        yeni_rol = interaction.guild.get_role(int(select.values[0]))
        state = get_user_state(interaction.guild.id, interaction.user.id)
        
        # Senin orijinal rol kontrol mantığın buraya gelecek
        await interaction.response.defer()
        await interaction.user.add_roles(yeni_rol)
        select.disabled = True
        await interaction.edit_original_response(view=self)
        await interaction.followup.send(f"✅ {yeni_rol.name} rolü başarıyla verildi!", ephemeral=True)

    @discord.ui.button(label="Rol Değiştir", style=discord.ButtonStyle.secondary, custom_id="persistent_button_main")
    async def btn_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        for item in self.children:
            if isinstance(item, discord.ui.Select): item.disabled = False
        await interaction.response.edit_message(view=self)

# ----------------- DİL VIEW (YENİ SİSTEM) -----------------
class DilView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(placeholder="Dilini seç...", custom_id="persistent_select_dil", 
                       options=[discord.SelectOption(label=n, value=str(i)) for n, i in DILLER.items()])
    async def dil_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        state = get_dil_state(interaction.guild.id, interaction.user.id)
        if state["last_change"]:
            if datetime.now() - datetime.fromisoformat(state["last_change"]) < timedelta(minutes=5):
                await interaction.response.send_message("❌ Dilini değiştirmek için 5 dakika beklemen gerekiyor.", ephemeral=True)
                return

        yeni_dil = interaction.guild.get_role(int(select.values[0]))
        eski_roller = [r for r in interaction.user.roles if r.id in DILLER.values()]
        await interaction.user.remove_roles(*eski_roller)
        await interaction.user.add_roles(yeni_dil)
        
        state["last_change"] = datetime.now().isoformat()
        save_data()
        
        select.disabled = True
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(f"✅ Dilin {yeni_dil.name} olarak ayarlandı!", ephemeral=True)

    @discord.ui.button(label="Dil Değiştir", style=discord.ButtonStyle.danger, custom_id="persistent_button_dil")
    async def dil_btn_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        for item in self.children:
            if isinstance(item, discord.ui.Select): item.disabled = False
        await interaction.response.edit_message(view=self)

# ----------------- BOT EVENT & KOMUTLAR -----------------
@bot.event
async def on_ready():
    bot.add_view(RolView())
    bot.add_view(DilView())
    print(f"{bot.user} hazır!")

@bot.command()
@commands.has_permissions(administrator=True)
async def dilmenu(ctx):
    embed = discord.Embed(
        title="🌍 Dil Seçim Paneli",
        description="Lütfen konuşmak istediğin dili seç.\n\n⚠️ **Kural:** Seçim yaptıktan sonra 5 dakika boyunca dilini değiştiremezsin.",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed, view=DilView())

# ... (Diğer tüm heartbeat, rolmenu vb. kodların burada kalmaya devam edecek)
keep_alive()
bot.run(os.getenv("TOKEN"))