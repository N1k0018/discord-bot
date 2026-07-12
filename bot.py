import discord
from discord.ext import commands
import os
import json
from datetime import datetime, timedelta
from keep_alive import keep_alive

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

DATA_FILE = "user_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

class RolView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(
        placeholder="Rolünü seç...", 
        custom_id="persistent_select_main", 
        options=[discord.SelectOption(label=n, value=str(i)) for n, i in ROLLER.items()]
    )
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        user_id = str(interaction.user.id)
        data = load_data()
        yeni_rol = interaction.guild.get_role(int(select.values[0]))
        
        for role_id in ROLLER.values():
            old_role = interaction.guild.get_role(role_id)
            if old_role in interaction.user.roles:
                await interaction.user.remove_roles(old_role)
        
        await interaction.user.add_roles(yeni_rol)
        
        # Eğer zaten kayıtlıysa (daha önce rol aldıysa), değişim zamanını güncelle
        if user_id in data:
            data[user_id] = datetime.now().isoformat()
        else:
            # İlk defa rol alıyor, ilk zamanı None veya başlangıç gibi tut
            data[user_id] = datetime.now().isoformat()
            
        save_data(data)
        
        select.disabled = True
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(f"✅ {yeni_rol.name} rolü başarıyla verildi!", ephemeral=True)

    @discord.ui.button(label="Rol Değiştir", style=discord.ButtonStyle.secondary, custom_id="persistent_button_main")
    async def btn_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = str(interaction.user.id)
        data = load_data()
        
        if user_id in data:
            last_change = datetime.fromisoformat(data[user_id])
            if (datetime.now() - last_change) < timedelta(days=3):
                await interaction.response.send_message("❌ Rolünüzü değiştirmek için 3 gün beklemeniz gerekiyor.", ephemeral=True)
                return
        
        for item in self.children:
            if isinstance(item, discord.ui.Select):
                item.disabled = False
        
        await interaction.response.edit_message(view=self)
        await interaction.followup.send("✅ Değişim modu aktif, yeni rolünü seçebilirsin.", ephemeral=True)

@bot.event
async def on_ready():
    bot.add_view(RolView())
    print(f"{bot.user} hazır!")

@bot.command()
@commands.has_permissions(administrator=True)
async def rolmenu(ctx):
    embed = discord.Embed(
        title="Rol Seçim Paneli", 
        description=(
            "• **Seçim:** Yalnızca 1 adet rol seçebilirsiniz.\n"
            "• **Değiştirme:** Rolünüzü değiştirmek için 'Rol Değiştir' butonunu kullanabilirsiniz.\n"
            "• **Kısıtlama:** Rol değiştirme işlemi **3 günde bir** yapılabilir.\n\n"
            "Hata durumlarında moderatör ile iletişime geçin."
        ),
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed, view=RolView())

keep_alive()
bot.run(os.getenv('TOKEN'))