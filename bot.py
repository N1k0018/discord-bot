import discord
from discord.ext import commands
import os
import sqlite3
from datetime import datetime, timedelta
from keep_alive import keep_alive

intents = discord.Intents.default()
intents.members = True
# message_content intent removed: the bot never reads message content,
# so this privileged intent isn't needed and doesn't need to be enabled
# in the Discord Developer Portal.

bot = commands.Bot(command_prefix="!", intents=intents)

ROLLER = {
    "UFC-live": 1525780352679809125,
    "ROK-rise of kingdoms": 1525779899745308712,
    "Steam-alıcı": 1510649566972870767,
    "Sohbet": 1486012917324185600,
}

COOLDOWN_DAYS = 3
DB_PATH = "role_state.db"


# ---------------------------------------------------------------------------
# Persistence layer (SQLite) — survives restarts/redeploys, unlike plain dicts.
# Keyed by (guild_id, user_id) so state doesn't leak across servers.
# ---------------------------------------------------------------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS role_state (
            guild_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            first_selection_made INTEGER NOT NULL DEFAULT 0,
            last_change_time TEXT,
            PRIMARY KEY (guild_id, user_id)
        )
        """
    )
    conn.commit()
    conn.close()


def get_state(guild_id: int, user_id: int):
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT first_selection_made, last_change_time FROM role_state "
        "WHERE guild_id = ? AND user_id = ?",
        (guild_id, user_id),
    ).fetchone()
    conn.close()
    if row is None:
        return False, None
    first_selection_made, last_change_time = row
    last_change = (
        datetime.fromisoformat(last_change_time) if last_change_time else None
    )
    return bool(first_selection_made), last_change


def mark_first_selection(guild_id: int, user_id: int):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        INSERT INTO role_state (guild_id, user_id, first_selection_made, last_change_time)
        VALUES (?, ?, 1, NULL)
        ON CONFLICT(guild_id, user_id) DO UPDATE SET first_selection_made = 1
        """,
        (guild_id, user_id),
    )
    conn.commit()
    conn.close()


def set_last_change_time(guild_id: int, user_id: int, when: datetime):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        INSERT INTO role_state (guild_id, user_id, first_selection_made, last_change_time)
        VALUES (?, ?, 1, ?)
        ON CONFLICT(guild_id, user_id) DO UPDATE SET last_change_time = excluded.last_change_time
        """,
        (guild_id, user_id, when.isoformat()),
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# View
# ---------------------------------------------------------------------------
class RolView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(
        placeholder="Rolünü seç...",
        custom_id="persistent_select_main",
        options=[
            discord.SelectOption(label=n, value=str(i)) for n, i in ROLLER.items()
        ],
    )
    async def select_callback(
        self, interaction: discord.Interaction, select: discord.ui.Select
    ):
        yeni_rol = interaction.guild.get_role(int(select.values[0]))

        # Guard: role ID missing/deleted/renamed on the server.
        if yeni_rol is None:
            await interaction.response.send_message(
                "❌ Bu rol sunucuda bulunamadı. Lütfen bir yetkiliye bildirin.",
                ephemeral=True,
            )
            return

        try:
            for role_id in ROLLER.values():
                old_role = interaction.guild.get_role(role_id)
                if old_role and old_role in interaction.user.roles:
                    await interaction.user.remove_roles(old_role)

            await interaction.user.add_roles(yeni_rol)
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Rol verme iznim yok. Lütfen rolümün, verilecek rollerden "
                "üstte olduğundan ve 'Rolleri Yönet' iznine sahip olduğundan emin olun.",
                ephemeral=True,
            )
            return
        except discord.HTTPException:
            await interaction.response.send_message(
                "❌ Rol verilirken bir hata oluştu, lütfen tekrar deneyin.",
                ephemeral=True,
            )
            return

        guild_id = interaction.guild.id
        user_id = interaction.user.id
        first_selection_made, _ = get_state(guild_id, user_id)

        if first_selection_made:
            set_last_change_time(guild_id, user_id, datetime.now())
        else:
            mark_first_selection(guild_id, user_id)

        select.disabled = True
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(
            f"✅ {yeni_rol.name} rolü başarıyla verildi!", ephemeral=True
        )

    @discord.ui.button(
        label="Rol Değiştir",
        style=discord.ButtonStyle.secondary,
        custom_id="persistent_button_main",
    )
    async def btn_callback(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        guild_id = interaction.guild.id
        user_id = interaction.user.id
        _, last_time = get_state(guild_id, user_id)

        if last_time and (datetime.now() - last_time) < timedelta(days=COOLDOWN_DAYS):
            remaining = timedelta(days=COOLDOWN_DAYS) - (datetime.now() - last_time)
            hours_left = max(int(remaining.total_seconds() // 3600), 1)
            await interaction.response.send_message(
                f"❌ Rolünüzü değiştirmek için yaklaşık {hours_left} saat daha "
                f"beklemeniz gerekiyor.",
                ephemeral=True,
            )
            return

        for item in self.children:
            if isinstance(item, discord.ui.Select):
                item.disabled = False

        await interaction.response.edit_message(view=self)
        await interaction.followup.send(
            "✅ Değişim hakkınız onaylandı, yeni rolünüzü seçin.", ephemeral=True
        )

    async def on_error(
        self,
        interaction: discord.Interaction,
        error: Exception,
        item: discord.ui.Item,
    ):
        # Catch-all so a bad interaction never fails silently.
        print(f"RolView error on {item}: {error}")
        if interaction.response.is_done():
            await interaction.followup.send(
                "❌ Beklenmedik bir hata oluştu.", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "❌ Beklenmedik bir hata oluştu.", ephemeral=True
            )


@bot.event
async def on_ready():
    init_db()
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
            f"• **Kısıtlama:** Rol değiştirme işlemi **{COOLDOWN_DAYS} günde bir** yapılabilir."
        ),
        color=discord.Color.blue(),
    )
    await ctx.send(embed=embed, view=RolView())


keep_alive()
bot.run(os.getenv("TOKEN"))