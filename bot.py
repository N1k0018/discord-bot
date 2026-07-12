import discord
from discord.ext import commands
import os
from datetime import datetime, timedelta
from keep_alive import keep_alive
import json

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Rollerin
ROLLER = {
    "UFC-live": 1525780352679809125,
    "ROK-rise of kingdoms": 1525779899745308712,
    "Steam-alıcı": 1510649566972870767,
    "Sohbet": 1486012917324185600
}

# Cooldown verilerini kaydetmek için dosya
COOLDOWN_FILE = "cooldowns.json"

# Dosyadan yükleme
def load_cooldowns():
    try:
        with open(COOLDOWN_FILE, "r") as f:
            data = json.load(f)
            result = {}
            for k, v in data.items():
                result[int(k)] = {
                    "last_time": datetime.fromisoformat(v["last_time"]) if v.get("last_time") else None,
                    "used_once": v.get("used_once", False)
                }
            return result
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

# Dosyaya kaydetme
def save_cooldowns():
    with open(COOLDOWN_FILE, "w") as f:
        json.dump({
            str(k): {
                "last_time": v["last_time"].isoformat() if v["last_time"] else None,
                "used_once": v["used_once"]
            } for k, v in USER_COOLDOWN.items()
        }, f)

# 3 gün kısıtlaması için hafıza (kalıcı)
USER_COOLDOWN = load_cooldowns()

class RolView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(
        placeholder="Rolünü seç...", 
        custom_id="persistent_select_main", 
        options=[discord.SelectOption(label=n, value=str(i)) for n, i in ROLLER.items()]
    )
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        yeni_rol = interaction.guild.get_role(int(select.values[0]))
        
        # Mevcut rolleri temizle
        for role_id in ROLLER.values():
            old_role = interaction.guild.get_role(role_id)
            if old_role in interaction.user.roles:
                await interaction.user.remove_roles(old_role)
        
        await interaction.user.add_roles(yeni_rol)
        USER_COOLDOWN[interaction.user.id] = {"last_time": datetime.now(), "used_once": False}
        save_cooldowns()
        
        # Seçimi kilitle
        select.disabled = True
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(f"✅ {yeni_rol.name} rolü başarıyla verildi!", ephemeral=True)

    @discord.ui.button(label="Rol Değiştir", style=discord.ButtonStyle.secondary, custom_id="persistent_button_main")
    async def btn_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_data = USER_COOLDOWN.get(interaction.user.id, {"last_time": None, "used_once": False})

        # İlk kullanım serbest
        if not user_data["used_once"]:
            user_data["used_once"] = True
            user_data["last_time"] = datetime.now()
            USER_COOLDOWN[interaction.user.id] = user_data
            save_cooldowns()
        else:
            # 3 gün kontrolü
            if user_data["last_time"] and (datetime.now() - user_data["last_time"]) < timedelta(days=3):
                await interaction.response.send_message("❌ Rolünü tekrar değiştirmek için 3 gün beklemen gerekiyor.", ephemeral=True)
                return
            else:
                user_data["last_time"] = datetime.now()
                USER_COOLDOWN[interaction.user.id] = user_data
                save_cooldowns()

        # Menüyü tekrar aktif et
        for item in self.children:
            if isinstance(item, discord.ui.Select):
                item.disabled = False

        await interaction.response.edit_message(view=self)
        await interaction.followup.send("✅ Rol seçme menüsü tekrar açıldı, yeni rolünü seçebilirsin.", ephemeral=True)

@bot.event
async def on_ready():
    bot.add_view(RolView())
    print(f"{bot.user} olarak giriş yapıldı ve hazır!")

@bot.command()
@commands.has_permissions(administrator=True)
async def rolmenu(ctx):
    embed = discord.Embed(
        title="Rol Seçim Paneli", 
        description=(
            "• **Seçim:** Yalnızca 1 adet rol seçebilirsiniz.\n"
            "• **Değiştirme:** Rolünüzü değiştirmek için 'Rol Değiştir' butonunu kullanabilirsiniz.\n"
            "• **Kısıtlama:** İlk değişim serbesttir, sonrasında rol değiştirme işlemi **3 günde bir** yapılabilir.\n\n"
            "Hata durumlarında moderatör ile iletişime geçin."
        ),
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed, view=RolView())

keep_alive()
bot.run(os.getenv('TOKEN'))
