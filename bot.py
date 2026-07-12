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

ROLLER = {
    "UFC-live": 1525780352679809125,
    "ROK-rise of kingdoms": 1525779899745308712,
    "Steam-alıcı": 1510649566972870767,
    "Sohbet": 1486012917324185600
}

COOLDOWN_DAYS = 3
DATA_FILE = "user_data.json"

# ---------------------------------------------------------------------------
# JSON persistence katmanı
# Yapı:
# {
#   "<guild_id>": {
#       "<user_id>": {
#           "first_selection_made": bool,
#           "free_change_used": bool,
#           "last_change_time": "ISO-8601 string" veya null
#       }
#   }
# }
# ---------------------------------------------------------------------------
def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return {}
            return json.loads(content)
    except (json.JSONDecodeError, OSError):
        return {}


def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(USER_DATA, f, ensure_ascii=False, indent=2)


USER_DATA = load_data()


def get_user_state(guild_id: int, user_id: int) -> dict:
    guild_key = str(guild_id)
    user_key = str(user_id)

    guild_data = USER_DATA.setdefault(guild_key, {})
    if user_key not in guild_data:
        guild_data[user_key] = {
            "first_selection_made": False,
            "free_change_used": False,
            "last_change_time": None
        }
    return guild_data[user_key]


def get_last_change_time(state: dict):
    if state["last_change_time"] is None:
        return None
    return datetime.fromisoformat(state["last_change_time"])


def format_remaining(remaining: timedelta) -> str:
    total_seconds = int(remaining.total_seconds())
    if total_seconds < 0:
        total_seconds = 0
    days, rem = divmod(total_seconds, 86400)
    hours, _ = divmod(rem, 3600)
    return f"{days} gün {hours} saat"


def get_cooldown_status(state: dict):
    """
    Kullanıcının şu an rol değiştirip değiştiremeyeceğini belirler.
    Döner: (izinli: bool, kalan_sure_mesaji: str veya None)
    """
    # Hiç rol seçmediyse: tamamen serbest.
    if not state["first_selection_made"]:
        return True, None

    # İlk değişimini henüz kullanmadıysa: bu değişim ücretsiz.
    if not state["free_change_used"]:
        return True, None

    # Artık cooldown uygulanır.
    last_time = get_last_change_time(state)
    if last_time is None:
        return True, None

    elapsed = datetime.now() - last_time
    if elapsed < timedelta(days=COOLDOWN_DAYS):
        remaining = timedelta(days=COOLDOWN_DAYS) - elapsed
        return False, format_remaining(remaining)

    return True, None


def apply_selection_state(state: dict):
    """
    Başarılı bir rol seçiminden/değişiminden sonra durumu günceller.
    """
    if not state["first_selection_made"]:
        # İlk seçim: serbest, cooldown başlamaz.
        state["first_selection_made"] = True
    elif not state["free_change_used"]:
        # İlk değişim: serbest ama bundan sonra cooldown başlar.
        state["free_change_used"] = True
        state["last_change_time"] = datetime.now().isoformat()
    else:
        # Normal değişim: cooldown yeniden başlar.
        state["last_change_time"] = datetime.now().isoformat()

    save_data()


class RolView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(
        placeholder="Rolünü seç...",
        custom_id="persistent_select_main",
        options=[discord.SelectOption(label=n, value=str(i)) for n, i in ROLLER.items()]
    )
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        if interaction.guild is None:
            await interaction.response.send_message("❌ Bu işlem yalnızca sunucu içinde kullanılabilir.", ephemeral=True)
            return

        yeni_rol = interaction.guild.get_role(int(select.values[0]))
        if yeni_rol is None:
            await interaction.response.send_message(
                "❌ Bu rol sunucuda bulunamadı. Lütfen bir yetkiliye bildirin.",
                ephemeral=True
            )
            return

        state = get_user_state(interaction.guild.id, interaction.user.id)

        # Kullanıcının şu an sahip olduğu (listedeki) rolü bul.
        mevcut_rol = None
        for role_id in ROLLER.values():
            rol = interaction.guild.get_role(role_id)
            if rol and rol in interaction.user.roles:
                mevcut_rol = rol
                break

        # Aynı rolü tekrar seçmeye çalışıyorsa.
        if mevcut_rol and mevcut_rol.id == yeni_rol.id:
            await interaction.response.send_message("Zaten bu role sahipsiniz.", ephemeral=True)
            return

        # UI durumuna güvenme: cooldown, canlı rol tespitine değil,
        # kayıtlı duruma (state) göre kontrol edilir. Böylece rol önbelleği
        # anlık olarak güncel değilse bile cooldown atlanamaz.
        if state["first_selection_made"]:
            izinli, kalan_mesaj = get_cooldown_status(state)
            if not izinli:
                await interaction.response.send_message(
                    f"❌ Rolünüzü tekrar değiştirmek için {kalan_mesaj} beklemeniz gerekiyor.",
                    ephemeral=True
                )
                return

        try:
            if mevcut_rol is not None:
                await interaction.user.remove_roles(mevcut_rol)
            await interaction.user.add_roles(yeni_rol)
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Rol verme iznim yok. Botun rolünün, verilecek rollerden üstte "
                "olduğundan ve 'Rolleri Yönet' iznine sahip olduğundan emin olun.",
                ephemeral=True
            )
            return
        except discord.HTTPException:
            await interaction.response.send_message(
                "❌ Rol verilirken bir hata oluştu, lütfen tekrar deneyin.",
                ephemeral=True
            )
            return

        apply_selection_state(state)

        select.disabled = True
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(f"✅ {yeni_rol.name} rolü başarıyla verildi!", ephemeral=True)

    @discord.ui.button(label="Rol Değiştir", style=discord.ButtonStyle.secondary, custom_id="persistent_button_main")
    async def btn_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.guild is None:
            await interaction.response.send_message("❌ Bu işlem yalnızca sunucu içinde kullanılabilir.", ephemeral=True)
            return

        state = get_user_state(interaction.guild.id, interaction.user.id)
        izinli, kalan_mesaj = get_cooldown_status(state)

        if not izinli:
            await interaction.response.send_message(
                f"❌ Rolünüzü değiştirmek için {kalan_mesaj} beklemeniz gerekiyor.",
                ephemeral=True
            )
            return

        for item in self.children:
            if isinstance(item, discord.ui.Select):
                item.disabled = False

        await interaction.response.edit_message(view=self)
        await interaction.followup.send("✅ Değişim hakkınız onaylandı, yeni rolünüzü seçin.", ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item):
        print(f"RolView hata ({item}): {error}")
        try:
            if interaction.response.is_done():
                await interaction.followup.send("❌ Beklenmedik bir hata oluştu.", ephemeral=True)
            else:
                await interaction.response.send_message("❌ Beklenmedik bir hata oluştu.", ephemeral=True)
        except discord.HTTPException:
            pass


@tasks.loop(minutes=3)
async def heartbeat():
    # Discord gateway bağlantısının canlılığını loglarda görünür kılar.
    # Not: Render'ın ücretsiz planındaki "sleep" sorunu HTTP trafiği eksikliğinden
    # kaynaklanır; bunu asıl çözen keep_alive.py'ye giden dış ping'lerdir (ör. UptimeRobot).
    # Bu döngü onun yerine geçmez, yalnızca bağlantının koptuğunu erken fark etmeyi sağlar.
    print(f"[heartbeat] bağlantı aktif — gecikme: {round(bot.latency * 1000)}ms", flush=True)


@heartbeat.before_loop
async def before_heartbeat():
    await bot.wait_until_ready()


@bot.event
async def on_ready():
    bot.add_view(RolView())
    if not heartbeat.is_running():
        heartbeat.start()
    print(f"{bot.user} hazır!", flush=True)


@bot.event
async def on_error(event_method, *args, **kwargs):
    # Herhangi bir event handler içinde yakalanmayan istisnalar için genel güvenlik ağı.
    import traceback
    print(f"[on_error] '{event_method}' içinde beklenmedik hata:", flush=True)
    traceback.print_exc()


@bot.event
async def on_command_error(ctx, error):
    # Komut seviyesindeki hataları (ör. yetkisiz kullanıcı) sessizce yutmak yerine bildirir.
    if isinstance(error, commands.MissingPermissions):
        try:
            await ctx.send("❌ Bu komutu kullanmak için yönetici yetkisine sahip olmalısınız.", delete_after=10)
        except discord.HTTPException:
            pass
        return

    if isinstance(error, commands.CommandNotFound):
        return

    print(f"[on_command_error] '{ctx.command}' komutunda hata: {error}", flush=True)


@bot.command()
@commands.has_permissions(administrator=True)
async def rolmenu(ctx):
    # Komut mesajını sil (kanalı temiz tutmak için). Botun "Mesajları Yönet"
    # iznine sahip olması gerekir; yoksa veya mesaj zaten silindiyse sessizce geç.
    try:
        await ctx.message.delete()
    except (discord.Forbidden, discord.NotFound, discord.HTTPException):
        pass

    embed = discord.Embed(
        title="Rol Seçim Paneli",
        description=(
            "• **Seçim:** Yalnızca 1 adet rol seçebilirsiniz.\n"
            "• **Değiştirme:** Rolünüzü değiştirmek için 'Rol Değiştir' butonunu kullanabilirsiniz.\n"
            f"• **Kısıtlama:** İlk değişiminiz ücretsizdir, sonrasında rol değiştirme işlemi **{COOLDOWN_DAYS} günde bir** yapılabilir."
        ),
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed, view=RolView())


keep_alive()
bot.run(os.getenv("TOKEN"))