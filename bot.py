import discord
from discord.ext import commands
import os
from datetime import datetime, timedelta
from keep_alive import keep_alive

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Rol ID'lerin (Sohbet olanı istediğin gibi ayarladım)
ROLLER = {
    "UFC-live": 1525780352679809125,
    "ROK-rise of kingdoms": 1525779899745308712,
    "Steam-alıcı": 1510649566972870767,
    "Sohbet": 1486012917324185600
}

# 14 günlük süre takibi için
USER_COOLDOWN = {}

class RolModal(discord.ui.Modal, title="Rol Değiştir"):
    def __init__(self):
        super().__init__()
        self.rol_select = discord.ui.Select(
            placeholder="Yeni rolünü seç...",
            options=[discord.SelectOption(label=n, value=str(i)) for n, i in ROLLER.items()]
        )
        self.add_item(self.rol_select)

    async def on_submit(self, interaction: discord.Interaction):
        yeni_rol_id = int(self.rol_select.values[0])
        yeni_rol = interaction.guild.get_role(yeni_rol_id)
        
        # Kullanıcının mevcut rollerini temizle
        for role_id in ROLLER.values():
            old_role = interaction.guild.get_role(role_id)
            if old_role in interaction.user.roles:
                await interaction.user.remove_roles(old_role)
        
        await interaction.user.add_roles(yeni_rol)
        USER_COOLDOWN[interaction.user.id] = datetime.now()
        await interaction.response.send_message(f"✅ Başarıyla {yeni_rol.name} rolüne geçtin!", ephemeral=True)

class RolView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        # Menü
        self.select = discord.ui.Select(
            placeholder="Rolünü seç...",
            options=[discord.SelectOption(label=n, value=str(i)) for n, i in ROLLER.items()],
            custom_id="rol_menu"
        )
        self.select.callback = self.menu_callback
        self.add_item(self.select)
        
        # Değiştir Butonu
        self.btn_degistir = discord.ui.Button(label="Rol Değiştir", style=discord.ButtonStyle.secondary, custom_id="degistir")
        self.btn_degistir.callback = self.btn_callback
        self.add_item(self.btn_degistir)

    async def menu_callback(self, interaction: discord.Interaction):
        yeni_rol = interaction.guild.get_role(int(self.select.values[0]))
        if any(r.id in ROLLER.values() for r in interaction.user.roles):
            await interaction.response.send_message("❌ Zaten bir rolün var! Değiştirmek için 'Rol Değiştir' butonunu kullan.", ephemeral=True)
            return
        await interaction.user.add_roles(yeni_rol)
        await interaction.response.send_message(f"✅ {yeni_rol.name} rolü verildi!", ephemeral=True)

    async def btn_callback(self, interaction: discord.Interaction):
        last_time = USER_COOLDOWN.get(interaction.user.id)
        if last_time and (datetime.now() - last_time).days < 14:
            await interaction.response.send_message("❌ Rolünü değiştirmek için en son değişimden itibaren 14 gün geçmesi gerekir.", ephemeral=True)
            return
        await interaction.response.send_modal(RolModal())

@bot.event
async def on_ready():
    bot.add_view(RolView())
    print(f"{bot.user} olarak giriş yapıldı!")

@bot.command()
@commands.has_permissions(administrator=True)
async def rolmenu(ctx):
    embed = discord.Embed(
        title="Rol Seçim Paneli", 
        description=(
            "• **Seçim:** Yalnızca 1 adet rol seçebilirsiniz.\n"
            "• **Değiştirme:** Rolünüzü değiştirmek için 'Rol Değiştir' butonunu kullanabilirsiniz.\n"
            "• **Kısıtlama:** Rol değiştirme işlemi **14 günde bir** yapılabilir.\n\n"
            "Birden fazla rol almak veya hata durumlarında lütfen bir moderatör ile iletişime geçin."
        ),
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed, view=RolView())

keep_alive()
bot.run(os.getenv('TOKEN'))