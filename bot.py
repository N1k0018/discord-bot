import discord
from discord.ext import commands
import os
from datetime import datetime, timedelta
from keep_alive import keep_alive

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

# 3 gün kısıtlaması için hafıza
USER_COOLDOWN = {}

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
        USER_COOLDOWN[interaction.user.id] = datetime.now()
        
        # Seçimi kilitle
        select.disabled = True
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(f"✅ {yeni_rol.name} rolü başarıyla verildi!", ephemeral=True)

    @discord.ui.button(label="Rol Değiştir", style=discord.ButtonStyle.secondary, custom_id="persistent_button_main")
    async def btn_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        last_time = USER_COOLDOWN.get(interaction.user.id)
        
        # 3 gün (72 saat) kontrolü
        if last_time and (datetime.now() - last_time) < timedelta(days=3):
            await interaction.response.send_message("❌ Rolünü tekrar değiştirmek için 3 gün beklemen gerekiyor.", ephemeral=True)
            return
        
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
            "• **Kısıtlama:** Rol değiştirme işlemi **3 günde bir** yapılabilir.\n\n"
            "Hata durumlarında moderatör ile iletişime geçin."
        ),
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed, view=RolView())

keep_alive()
bot.run(os.getenv('TOKEN'))