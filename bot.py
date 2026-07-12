import discord
from discord.ext import commands
import os
from datetime import datetime
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

USER_COOLDOWN = {}

class RolModal(discord.ui.Modal, title="Rol Değiştirme"):
    def __init__(self):
        super().__init__()
        self.rol_select = discord.ui.Select(
            placeholder="Yeni rolünü seç...",
            options=[discord.SelectOption(label=n, value=str(i)) for n, i in ROLLER.items()]
        )
        self.add_item(self.rol_select)

    async def on_submit(self, interaction: discord.Interaction):
        yeni_rol = interaction.guild.get_role(int(self.rol_select.values[0]))
        for role_id in ROLLER.values():
            old_role = interaction.guild.get_role(role_id)
            if old_role in interaction.user.roles:
                await interaction.user.remove_roles(old_role)
        await interaction.user.add_roles(yeni_rol)
        USER_COOLDOWN[interaction.user.id] = datetime.now()
        await interaction.response.send_message(f"✅ Başarıyla **{yeni_rol.name}** rolüne geçtin!", ephemeral=True)

class RolView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(placeholder="Rolünü seç...", custom_id="persistent_view:select", options=[discord.SelectOption(label=n, value=str(i)) for n, i in ROLLER.items()])
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        yeni_rol = interaction.guild.get_role(int(select.values[0]))
        if any(r.id in ROLLER.values() for r in interaction.user.roles):
            await interaction.response.send_message("❌ Zaten bir rolün var! Değiştirmek için butonu kullan.", ephemeral=True)
            return
        await interaction.user.add_roles(yeni_rol)
        select.disabled = True
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(f"✅ {yeni_rol.name} rolü verildi!", ephemeral=True)

    @discord.ui.button(label="Rol Değiştir", style=discord.ButtonStyle.secondary, custom_id="persistent_view:button")
    async def btn_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
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