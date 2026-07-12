
# bot.py
import discord, os, json
from discord.ext import commands
from datetime import datetime, timedelta

intents=discord.Intents.default()
intents.members=True
intents.message_content=True
bot=commands.Bot(command_prefix="!",intents=intents)

ROLE_CHANNEL_ID=1525646617582244001
DATA_FILE="user_data.json"

ROLES={
    "UFC-live":1525780352679809125,
    "ROK-rise of kingdoms":1525779899745308712,
    "Steam-alıcı":1510649566972870767,
    "Sohbet":1486012917324185600
}

def load():
    if not os.path.exists(DATA_FILE): return {}
    try:
        with open(DATA_FILE,"r",encoding="utf8") as f: return json.load(f)
    except: return {}

def save(d):
    with open(DATA_FILE,"w",encoding="utf8") as f: json.dump(d,f,indent=2)

class RoleView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(
        custom_id="role_select",
        placeholder="Rolünü seç...",
        options=[discord.SelectOption(label=k,value=str(v)) for k,v in ROLES.items()]
    )
    async def select(self,interaction:discord.Interaction,select:discord.ui.Select):
        data=load()
        uid=str(interaction.user.id)
        info=data.get(uid,{"first_change_used":False,"last_change":None})
        chosen=int(select.values[0])
        current=[r.id for r in interaction.user.roles if r.id in ROLES.values()]
        if current and not info["first_change_used"]:
            # first free change
            pass
        elif current:
            if info["last_change"]:
                last=datetime.fromisoformat(info["last_change"])
                left=timedelta(days=3)-(datetime.now()-last)
                if left.total_seconds()>0:
                    d=left.days
                    h=left.seconds//3600
                    await interaction.response.send_message(f"Rol değiştirmek için {d} gün {h} saat beklemelisin.",ephemeral=True)
                    return
        for rid in ROLES.values():
            role=interaction.guild.get_role(rid)
            if role in interaction.user.roles:
                await interaction.user.remove_roles(role)
        role=interaction.guild.get_role(chosen)
        await interaction.user.add_roles(role)
        if current:
            if not info["first_change_used"]:
                info["first_change_used"]=True
                info["last_change"]=datetime.now().isoformat()
            else:
                info["last_change"]=datetime.now().isoformat()
        data[uid]=info
        save(data)
        await interaction.response.send_message(f"✅ {role.name} rolü verildi.",ephemeral=True)

    @discord.ui.button(label="Rol Değiştir",style=discord.ButtonStyle.secondary,custom_id="role_change_info")
    async def btn(self,interaction:discord.Interaction,button:discord.ui.Button):
        await interaction.response.send_message("Yeni rolünü açılır menüden seçebilirsin. İlk değişiklik ücretsizdir. Sonraki değişiklikler 3 gün bekleme süresine tabidir.",ephemeral=True)

@bot.event
async def on_ready():
    bot.add_view(RoleView())
    print(f"{bot.user} aktif!")

@bot.command()
@commands.has_permissions(administrator=True)
async def rolmenu(ctx):
    if ctx.channel.id!=ROLE_CHANNEL_ID:
        return
    e=discord.Embed(title="Rol Seçim Paneli",
    description="• İlk rol seçimi ücretsiz.\n• İlk rol değişikliği ücretsiz.\n• Sonraki değişiklikler 3 gün bekleme süresine tabidir.",
    color=discord.Color.blue())
    await ctx.send(embed=e,view=RoleView())

bot.run(os.getenv("TOKEN")
