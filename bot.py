import discord
from discord.ext import commands
import os
from keep_alive import keep_alive # 7/24 çalışması için

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Rol ID'lerin
ROLLER = {
    "UFC-live": 1525780352679809125,
    "ROK-rise of kingdoms": 1525779899745308712,
    "Steam-alıcı": 1510649566972870767,
    "Sohbet": 1486012917324185600
}

class RolMenu(discord.ui.Select):
    def __init__(self):
        options = [discord.SelectOption(label=n, value=str(i)) for n, i in ROLLER.items()]
        super().__init__(placeholder="Rolünü seç...", options=options)

    async def callback(self, interaction: discord.Interaction):
        yeni_rol = interaction.guild.get_role(int(self.values[0]))
        
        user_roles = [role.id for role in interaction.user.roles]
        if any(role_id in user_roles for role_id in ROLLER.values()):
            await interaction.response.send_message("❌ Zaten bir rol seçmişsin!", ephemeral=True)
            return

        await interaction.user.add_roles(yeni_rol)
        
        # Seçim yapıldıktan sonra menüyü pasif yap
        self.disabled = True
        self.placeholder = "Rolünüzü seçtiniz."
        
        # Mesajı güncelle ve butonu pasif haliyle göster
        await interaction.response.edit_message(view=self.view)
        await interaction.followup.send(f"✅ {yeni_rol.name} rolü verildi!", ephemeral=True)

class RolView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(RolMenu())

@bot.event
async def on_ready():
    print(f"{bot.user} olarak giriş yapıldı ve hazır!")

@bot.command()
async def rolmenu(ctx):
    await ctx.send("Rol seçimi:", view=RolView())

keep_alive() # Web sunucusunu başlatır
bot.run(os.getenv('TOKEN'))