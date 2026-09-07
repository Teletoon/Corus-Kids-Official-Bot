import os
import asyncio
import random
import re
from datetime import timedelta

import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional


TOKEN = os.getenv("TOKEN")

# Change these names if your Discord roles have different names.
VERIFIED_ROLE_ID = 1214631038718967909
BAQARA_ROLE_ID = 1141706454269698180
HIMARROON_ROLE_ID = 1149719680701964308


intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

bot = commands.Bot(command_prefix="!", intents=intents)


# --------------------------------------------------
# HELPERS
# --------------------------------------------------

def parse_duration(duration: str, max_seconds: Optional[int] = None):
    """
    Accepts:
    60s = 60 seconds
    10m = 10 minutes
    2h  = 2 hours
    3d  = 3 days
    1w  = 1 week
    """

    match = re.fullmatch(r"(\d+)([smhdw])", duration.lower().strip())

    if not match:
        return None

    amount = int(match.group(1))
    unit = match.group(2)

    multipliers = {
        "s": 1,
        "m": 60,
        "h": 60 * 60,
        "d": 60 * 60 * 24,
        "w": 60 * 60 * 24 * 7
    }

    seconds = amount * multipliers[unit]

    if max_seconds is not None and seconds > max_seconds:
        return None

    return seconds


async def temporary_unban(
    guild: discord.Guild,
    user_id: int,
    seconds: int
):
    await asyncio.sleep(seconds)

    try:
        user = await bot.fetch_user(user_id)
        await guild.unban(
            user,
            reason="Temporary ban expired."
        )
    except discord.NotFound:
        pass
    except discord.Forbidden:
        pass


# --------------------------------------------------
# READY
# --------------------------------------------------

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")


# --------------------------------------------------
# /say
# --------------------------------------------------

say_group = app_commands.Group(
    name="say",
    description="Send a message"
)


# --------------------------------------------------
# /say text
# --------------------------------------------------

@say_group.command(
    name="text",
    description="Send a text message."
)
@app_commands.describe(
    text="Message to send",
    color="Optional — choose a colour or leave empty for normal text"
)
@app_commands.choices(
    color=[
        app_commands.Choice(name="Blue", value="blue"),
        app_commands.Choice(name="Red", value="red"),
        app_commands.Choice(name="Green", value="green")
    ]
)
async def say_text(
    interaction: discord.Interaction,
    text: str,
    color: Optional[app_commands.Choice[str]] = None
):
    allowed_mentions = discord.AllowedMentions(
        users=True,
        roles=False,
        everyone=False
    )

    if color:
        colors = {
            "blue": discord.Color.blue(),
            "red": discord.Color.red(),
            "green": discord.Color.green()
        }

        embed = discord.Embed(
            description=text,
            color=colors[color.value]
        )

        await interaction.channel.send(
            embed=embed,
            allowed_mentions=allowed_mentions
        )

    else:
        await interaction.channel.send(
            text,
            allowed_mentions=allowed_mentions
        )

    await interaction.response.send_message(
        "Message sent.",
        ephemeral=True
    )  


# --------------------------------------------------
# /say image
# --------------------------------------------------

@say_group.command(
    name="image",
    description="Send an image."
)
async def say_image(
    interaction: discord.Interaction,
    image: discord.Attachment,
    text: Optional[str] = None
):
    await interaction.channel.send(
        content=text,
        file=await image.to_file()
    )

    await interaction.response.send_message(
        "Image sent.",
        ephemeral=True
    )


bot.tree.add_command(say_group)


# --------------------------------------------------
# /edit-message
# --------------------------------------------------

class EditMessageModal(discord.ui.Modal):
    def __init__(self, message: discord.Message):
        super().__init__(
            title="Edit Message"
        )

        self.message = message

        # Coloured embed message
        if message.embeds and message.embeds[0].description:
            current_text = message.embeds[0].description

        # Normal text message
        else:
            current_text = message.content

        self.text_input = discord.ui.TextInput(
            label="Message",
            style=discord.TextStyle.paragraph,
            default=current_text,
            required=True,
            max_length=2000
        )

        self.add_item(self.text_input)

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):
        allowed_mentions = discord.AllowedMentions(
            users=True,
            roles=False,
            everyone=False
        )

        new_text = self.text_input.value

        # If the bot message uses an embed,
        # edit the embed instead of adding normal text above it.
        if self.message.embeds:
            old_embed = self.message.embeds[0]

            new_embed = discord.Embed(
                description=new_text,
                color=old_embed.color
            )

            await self.message.edit(
                content=None,
                embed=new_embed,
                allowed_mentions=allowed_mentions
            )

        # Normal message
        else:
            await self.message.edit(
                content=new_text,
                allowed_mentions=allowed_mentions
            )

        await interaction.response.send_message(
            "Message edited.",
            ephemeral=True
        )


@bot.tree.command(
    name="edit-message",
    description="Edit a message sent by the bot."
)
async def edit_message(
    interaction: discord.Interaction,
    message_id: str
):
    try:
        message = await interaction.channel.fetch_message(
            int(message_id)
        )

        if message.author.id != bot.user.id:
            await interaction.response.send_message(
                "I can only edit Corus Kids Official Bot's messages.",
                ephemeral=True
            )
            return

        modal = EditMessageModal(message)

        await interaction.response.send_modal(modal)

    except discord.NotFound:
        await interaction.response.send_message(
            "Message not found.",
            ephemeral=True
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "I don't have permission to edit this message.",
            ephemeral=True
        )

    except ValueError:
        await interaction.response.send_message(
            "Invalid message ID.",
            ephemeral=True
        )


# --------------------------------------------------
# /warn
# --------------------------------------------------

@bot.tree.command(
    name="warn",
    description="Warn a user about a rule they broke."
)
@app_commands.checks.has_permissions(moderate_members=True)
async def warn(
    interaction: discord.Interaction,
    user: discord.Member,
    rule_broken: str
):
    # Private confirmation to the moderator
    await interaction.response.send_message(
        "Warning sent.",
        ephemeral=True
    )

    # Public warning from the bot itself
    await interaction.channel.send(
        f"⚠️ {user.mention} has been warned.\n"
        f"**Rule broken:** {rule_broken}",
        allowed_mentions=discord.AllowedMentions(
            users=True,
            roles=False,
            everyone=False
        )
    )


# --------------------------------------------------
# /timeout
# --------------------------------------------------

@bot.tree.command(
    name="timeout",
    description="Timeout a user for up to 1 week."
)
@app_commands.describe(
    user="User to timeout",
    duration="Duration (max 1 week): s=seconds, m=minutes, h=hours, d=days, w=weeks",
    reason="Reason for the timeout (optional)"
)
@app_commands.checks.has_permissions(moderate_members=True)
async def timeout(
    interaction: discord.Interaction,
    user: discord.Member,
    duration: str,
    reason: Optional[str] = None
):
    seconds = parse_duration(
        duration,
        max_seconds=7 * 24 * 60 * 60
    )

    if seconds is None:
        await interaction.response.send_message(
            "Invalid duration. Use something like `60s`, `10m`, `2h`, "
            "`3d`, or `1w`. Maximum: 1 week.",
            ephemeral=True
        )
        return

    try:
        await user.timeout(
            timedelta(seconds=seconds),
            reason=reason
        )

        # Private confirmation
        await interaction.response.send_message(
            "Timeout applied.",
            ephemeral=True
        )

        # Public message from CK Bot
        await interaction.channel.send(
            f"⏱️ {user.mention} is timed out. "
            f"**{duration}**.\n"
            f"Reason: {reason or 'No reason provided.'}",
            allowed_mentions=discord.AllowedMentions(
                users=True,
                roles=False,
                everyone=False
            )
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "I cannot timeout this user. Check my role and permissions.",
            ephemeral=True
        )


# --------------------------------------------------
# /remove-timeout
# --------------------------------------------------

@bot.tree.command(
    name="remove-timeout",
    description="Remove a user's timeout."
)
@app_commands.checks.has_permissions(moderate_members=True)
async def remove_timeout(
    interaction: discord.Interaction,
    user: discord.Member
):
    try:
        # Actually remove the timeout
        await user.timeout(
            None,
            reason=f"Timeout removed by {interaction.user}"
        )

        # Private confirmation
        await interaction.response.send_message(
            "Timeout removed.",
            ephemeral=True
        )

        # Public message from CK Bot
        await interaction.channel.send(
            f"🔊 **{user}** has been removed from timeout."
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "I cannot remove this user's timeout.",
            ephemeral=True
        )


# --------------------------------------------------
# /jail
# --------------------------------------------------

@app_commands.choices(
    jail_type=[
        app_commands.Choice(
            name="🐄 Cow Jail",
            value="cow"
        ),
        app_commands.Choice(
            name="🫏 Donkey Jail",
            value="donkey"
        )
    ]
)
@bot.tree.command(
    name="jail",
    description="Jail a user to Cow Jail or Donkey Jail."
)
@app_commands.describe(
    user="User to jail",
    jail_type="Select Cow Jail or Donkey Jail",
    duration="Duration (max 30 days): s=seconds, m=minutes, h=hours, d=days, w=weeks",
    reason="Reason for the jail (optional)"
)
@app_commands.checks.has_permissions(manage_roles=True)
async def jail(
    interaction: discord.Interaction,
    user: discord.Member,
    jail_type: app_commands.Choice[str],
    duration: str,
    reason: Optional[str] = None
):
    guild = interaction.guild

    seconds = parse_duration(
        duration,
        max_seconds=30 * 24 * 60 * 60
    )

    if seconds is None:
        await interaction.response.send_message(
            "Invalid duration. Use `30s`, `10m`, `2h`, `3d`, `1w`, etc. "
            "Maximum jail time is 30 days.",
            ephemeral=True
        )
        return

    verified = guild.get_role(VERIFIED_ROLE_ID)
    baqara = guild.get_role(BAQARA_ROLE_ID)
    himarroon = guild.get_role(HIMARROON_ROLE_ID)

    if not verified:
        await interaction.response.send_message(
            "I couldn't find the Verified Member role.",
            ephemeral=True
        )
        return

    if jail_type.value == "cow":
        jail_role = baqara
        jail_name = "🐄⛓️ Cow Jail"
    else:
        jail_role = himarroon
        jail_name = "🫏⛓️ Donkey Jail"

    if not jail_role:
        await interaction.response.send_message(
            "I couldn't find the selected jail role.",
            ephemeral=True
        )
        return

    try:
        # Remove Verified
        if verified in user.roles:
            await user.remove_roles(
                verified,
                reason=(
                    f"Jailed by {interaction.user}: "
                    f"{reason or 'No reason provided'}"
                )
            )

        # Remove existing jail roles
        if baqara and baqara in user.roles:
            await user.remove_roles(
                baqara
            )

        if himarroon and himarroon in user.roles:
            await user.remove_roles(
                himarroon
            )

        # Add selected jail role
        await user.add_roles(
            jail_role,
            reason=(
                f"Sent to {jail_name} by {interaction.user}: "
                f"{reason or 'No reason provided'}"
            )
        )

        # Private confirmation to the moderator
        await interaction.response.send_message(
            "User jailed.",
            ephemeral=True
        )

        # Public announcement from CK Bot
        await interaction.channel.send(
            f"⛓️ {user.mention} is jailed to **{jail_name}**.\n"
            f"Duration: **{duration}**\n"
            f"Reason: **{reason or 'No reason provided'}**",
            allowed_mentions=discord.AllowedMentions(
                users=True,
                roles=False,
                everyone=False
            )
        )

        # Wait until jail duration expires
        await asyncio.sleep(seconds)

        # Check that the member is still in the server
        member = guild.get_member(user.id)

        if member is None:
            return

        # Remove both possible jail roles
        if baqara and baqara in member.roles:
            await member.remove_roles(
                baqara,
                reason="Jail duration expired"
            )

        if himarroon and himarroon in member.roles:
            await member.remove_roles(
                himarroon,
                reason="Jail duration expired"
            )

        # Restore Verified
        if verified not in member.roles:
            await member.add_roles(
                verified,
                reason="Jail duration expired"
            )

    except discord.Forbidden:
        if interaction.response.is_done():
            await interaction.followup.send(
                "I can't change this user's roles. Make sure my bot role "
                "is above Verified, BAQARA, HimarRoon, and the user's roles.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "I can't change this user's roles. Make sure my bot role "
                "is above Verified, BAQARA, HimarRoon, and the user's roles.",
                ephemeral=True
            )


# --------------------------------------------------
# /kick
# --------------------------------------------------

@bot.tree.command(
    name="kick",
    description="Kick a user from the server."
)
@app_commands.checks.has_permissions(kick_members=True)
async def kick(
    interaction: discord.Interaction,
    user: discord.Member,
    reason: Optional[str] = None
):
    try:
        user_name = str(user)

        await user.kick(reason=reason)

        # Private confirmation to the moderator
        await interaction.response.send_message(
            "User kicked.",
            ephemeral=True
        )

        # Public announcement from CK Bot
        await interaction.channel.send(
            f"🦿 **{user_name}** is kicked.\n"
            f"Reason: {reason or 'No reason provided.'}"
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "I cannot kick this user. Check the role hierarchy.",
            ephemeral=True
        )


# --------------------------------------------------
# /ban
# --------------------------------------------------

@bot.tree.command(
    name="ban",
    description="Ban a user inside or outside the server."
)
@app_commands.describe(
    user="Username or User ID",
    reason="Reason for the ban",
    delete_messages="Delete message history"
)
@app_commands.choices(
    delete_messages=[
        app_commands.Choice(
            name="Don't delete messages",
            value=0
        ),
        app_commands.Choice(
            name="1 day",
            value=86400
        ),
        app_commands.Choice(
            name="3 days",
            value=259200
        ),
        app_commands.Choice(
            name="7 days",
            value=604800
        )
    ]
)
@app_commands.checks.has_permissions(ban_members=True)
async def ban(
    interaction: discord.Interaction,
    user: str,
    reason: str,
    delete_messages: Optional[app_commands.Choice[int]] = None
):
    await interaction.response.defer(ephemeral=True)

    delete_seconds = (
        delete_messages.value
        if delete_messages
        else 0
    )

    guild = interaction.guild

    try:
        target = None
        entered_user = user.strip()

        # User mention
        if entered_user.startswith("<@") and entered_user.endswith(">"):
            entered_user = (
                entered_user
                .replace("<@", "")
                .replace("!", "")
                .replace(">", "")
            )

        # User ID
        if entered_user.isdigit():
            user_id = int(entered_user)

            # First check if they're currently in the server
            target = guild.get_member(user_id)

            # If not, fetch their Discord account
            if target is None:
                target = await bot.fetch_user(user_id)

        # Username
        else:
            search = entered_user.lower()

            for member in guild.members:
                if (
                    member.name.lower() == search
                    or member.display_name.lower() == search
                    or str(member).lower() == search
                ):
                    target = member
                    break

            if target is None:
                await interaction.followup.send(
                    "❌ I couldn't find that username in this server. "
                    "If the user is outside the server, use their User ID.",
                    ephemeral=True
                )
                return

        user_name = str(target)

        await guild.ban(
            target,
            reason=reason,
            delete_message_seconds=delete_seconds
        )

        await interaction.followup.send(
            "User banned.",
            ephemeral=True
        )

        await interaction.channel.send(
            f"🚫 **{user_name}** is banned.\n"
            f"Reason: **{reason}**"
        )

    except discord.NotFound:
        await interaction.followup.send(
            "❌ I couldn't find a Discord account with that User ID.",
            ephemeral=True
        )

    except discord.Forbidden:
        await interaction.followup.send(
            "❌ I cannot ban this user. Check my Ban Members "
            "permission and role position.",
            ephemeral=True
        )

    except discord.HTTPException as error:
        await interaction.followup.send(
            f"❌ Discord rejected the ban: `{error}`",
            ephemeral=True
        )


# --------------------------------------------------
# /unban
# --------------------------------------------------

@bot.tree.command(
    name="unban",
    description="Unban a user by their Discord user ID."
)
@app_commands.checks.has_permissions(ban_members=True)
async def unban(
    interaction: discord.Interaction,
    user_id: str
):
    try:
        user = await bot.fetch_user(int(user_id))

        # Actually unban the user
        await interaction.guild.unban(user)

        # Private confirmation to the moderator
        await interaction.response.send_message(
            "User unbanned.",
            ephemeral=True
        )

        # Public announcement from CK Bot
        await interaction.channel.send(
            f"✅ **{user}** has been unbanned."
        )

    except ValueError:
        await interaction.response.send_message(
            "Invalid user ID.",
            ephemeral=True
        )

    except discord.NotFound:
        await interaction.response.send_message(
            "That user is not currently banned.",
            ephemeral=True
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "I don't have permission to unban users.",
            ephemeral=True
        )


# --------------------------------------------------
# /clear
# --------------------------------------------------

@bot.tree.command(
    name="clear",
    description="Clear messages from a specified member."
)
@app_commands.describe(
    amount="Amount of messages to delete (1-20)",
    member="Member whose messages will be deleted"
)
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(
    interaction: discord.Interaction,
    amount: int,
    member: discord.Member
):
    if amount < 1 or amount > 20:
        await interaction.response.send_message(
            "❌ You can only delete between **1 and 20 messages**.",
            ephemeral=True
        )
        return

    # Private acknowledgement — hides "used /clear"
    await interaction.response.defer(
        ephemeral=True
    )

    messages = []

    async for message in interaction.channel.history(limit=100):
        if message.author.id == member.id:
            messages.append(message)

            if len(messages) >= amount:
                break

    for message in messages:
        await message.delete()

    # Public message sent normally by CK Bot
    await interaction.channel.send(
        f"🧹 Deleted **{len(messages)} message(s)** from **{member}**."
    )


# --------------------------------------------------
# /avatar
# --------------------------------------------------

@bot.tree.command(
    name="avatar",
    description="Show a user's avatar."
)
async def avatar(
    interaction: discord.Interaction,
    user: Optional[discord.Member] = None
):
    user = user or interaction.user

    embed = discord.Embed(
        title=f"{user.display_name}'s Avatar",
        color=discord.Color.green()
    )

    embed.set_image(
        url=user.display_avatar.url
    )

    await interaction.response.send_message(embed=embed)


# --------------------------------------------------
# /server-icon
# --------------------------------------------------

@bot.tree.command(
    name="server-icon",
    description="Show the server icon."
)
async def server_icon(
    interaction: discord.Interaction
):
    guild = interaction.guild

    if guild.icon is None:
        await interaction.response.send_message(
            "This server does not have an icon.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title=f"{guild.name} Server Icon",
        color=discord.Color.green()
    )

    embed.set_image(url=guild.icon.url)

    await interaction.response.send_message(embed=embed)


# --------------------------------------------------
# /help
# --------------------------------------------------

@bot.tree.command(
    name="help",
    description="Show all Corus Kids Bot commands."
)
async def help_command(
    interaction: discord.Interaction
):
    embed = discord.Embed(
        title="🤖 Corus Kids Official Bot — Help",
        description=(
            "Here is the list of available Corus Kids Bot commands.\n"
            "Some moderation commands require staff permissions."
        ),
        color=discord.Color.green()
    )

    embed.add_field(
        name="💬 Messages",
        value=(
            "**/say text** — Send a text message through Corus Kids Bot.\n"
            "**/say image** — Send an image through Corus Kids Bot.\n"
            "**/edit-message** — Edit a message previously sent by Corus Kids Bot."
        ),
        inline=False
    )

    embed.add_field(
        name="🛡️ Moderation",
        value=(
            "**/warn** — Warn a member for breaking a rule.\n"
            "**/timeout** — Timeout a member for up to 1 week.\n"
            "**/remove-timeout** — Remove a member's timeout.\n"
            "**/jail** — Jail a member to Cow Jail or Donkey Jail up to 30 days.\n"
            "**/kick** — Kick a member from the server.\n"
            "**/ban** — Ban a member from the server.\n"
            "**/unban** — Unban a member using their Discord user ID.\n"
            "**/clear** — Delete 1–20 messages from a selected member."
        ),
        inline=False
    )

    embed.add_field(
        name="👤 Server & User",
        value=(
	    "**/server-icon** — Show the server's icon.\n"
             "**/avatar** — Show a user's avatar."
        ),
        inline=False
    )

    embed.add_field(
        name="🎨 Colour Games",
        value=(
            "**/game colour** — Mix 2 or 3 colours using "
            "Additive RGB or Subtractive CMY."
        ),
        inline=False
    )

    embed.set_footer(
        text="Corus Kids Official Bot • Corus Kids Bot"
    )

    await interaction.response.send_message(
        embed=embed
    )


# ==================================================
# /game colour
# ==================================================

game_group = app_commands.Group(
    name="game",
    description="Play Corus Kids Bot games"
)


# --------------------------------------------------
# Colour helpers
# --------------------------------------------------

def rgb_to_hex(rgb):
    r, g, b = rgb
    return f"#{r:02X}{g:02X}{b:02X}"


def colour_name(rgb):
    known_colours = {
        (255, 0, 0): "Red 🔴",
        (0, 255, 0): "Green 🟢",
        (0, 0, 255): "Blue 🔵",
        (0, 255, 255): "Cyan 🩵",
        (255, 0, 255): "Magenta 🟣",
        (255, 255, 0): "Yellow 🟡",
        (255, 255, 255): "White ⚪",
        (0, 0, 0): "Black ⚫"
    }

    return known_colours.get(rgb, "Colour 🎨")


def mix_additive(colours):
    r = min(255, sum(colour[0] for colour in colours))
    g = min(255, sum(colour[1] for colour in colours))
    b = min(255, sum(colour[2] for colour in colours))

    return (r, g, b)


def mix_subtractive(colours):
    cyan_total = 0
    magenta_total = 0
    yellow_total = 0

    for r, g, b in colours:
        cyan_total += 255 - r
        magenta_total += 255 - g
        yellow_total += 255 - b

    cyan_total = min(255, cyan_total)
    magenta_total = min(255, magenta_total)
    yellow_total = min(255, yellow_total)

    r = 255 - cyan_total
    g = 255 - magenta_total
    b = 255 - yellow_total

    return (r, g, b)


# --------------------------------------------------
# Base view
# --------------------------------------------------

class ColourGameView(discord.ui.View):
    def __init__(self, player_id: int):
        super().__init__(timeout=180)
        self.player_id = player_id

    async def interaction_check(
        self,
        interaction: discord.Interaction
    ):
        if interaction.user.id != self.player_id:
            await interaction.response.send_message(
                "This colour game belongs to another player.",
                ephemeral=True
            )
            return False

        return True


# --------------------------------------------------
# Choose Additive or Subtractive
# --------------------------------------------------

class ColourModelView(ColourGameView):

    @discord.ui.button(
        label="Additive RGB",
        emoji="🌈",
        style=discord.ButtonStyle.primary
    )
    async def additive(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        embed = discord.Embed(
            title="🌈 Additive RGB",
            description=(
                "Choose how many **different colours** you want to mix.\n\n"
                "🔴 Red `#FF0000`\n"
                "🟢 Green `#00FF00`\n"
                "🔵 Blue `#0000FF`"
            ),
            color=discord.Color.blue()
        )

        await interaction.response.edit_message(
            embed=embed,
            view=ColourAmountView(
                self.player_id,
                "additive"
            )
        )

    @discord.ui.button(
        label="Subtractive CMY",
        emoji="🎨",
        style=discord.ButtonStyle.secondary
    )
    async def subtractive(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        embed = discord.Embed(
            title="🎨 Subtractive CMY",
            description=(
                "Choose how many **different colours** you want to mix.\n\n"
                "🩵 Cyan `#00FFFF`\n"
                "🟣 Magenta `#FF00FF`\n"
                "🟡 Yellow `#FFFF00`"
            ),
            color=discord.Color.magenta()
        )

        await interaction.response.edit_message(
            embed=embed,
            view=ColourAmountView(
                self.player_id,
                "subtractive"
            )
        )


# --------------------------------------------------
# Choose 2 or 3 colours
# --------------------------------------------------

class ColourAmountView(ColourGameView):
    def __init__(
        self,
        player_id: int,
        mode: str
    ):
        super().__init__(player_id)
        self.mode = mode

    @discord.ui.button(
        label="2 Colours",
        emoji="2️⃣",
        style=discord.ButtonStyle.success
    )
    async def two_colours(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await start_colour_selection(
            interaction,
            self.player_id,
            self.mode,
            2
        )

    @discord.ui.button(
        label="3 Colours",
        emoji="3️⃣",
        style=discord.ButtonStyle.success
    )
    async def three_colours(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await start_colour_selection(
            interaction,
            self.player_id,
            self.mode,
            3
        )


async def start_colour_selection(
    interaction,
    player_id,
    mode,
    amount
):
    embed = make_selection_embed(
        mode,
        amount,
        []
    )

    await interaction.response.edit_message(
        embed=embed,
        view=ColourSelectionView(
            player_id,
            mode,
            amount,
            []
        )
    )


# --------------------------------------------------
# Colour select menu
# --------------------------------------------------

class ColourSelect(discord.ui.Select):
    def __init__(
        self,
        player_id,
        mode,
        amount,
        selected_colours
    ):
        self.player_id = player_id
        self.mode = mode
        self.amount = amount
        self.selected_colours = selected_colours

        already_selected = {
            colour["value"]
            for colour in selected_colours
        }

        if mode == "additive":
            all_options = [
                ("Red", "red", "🔴", "#FF0000"),
                ("Green", "green", "🟢", "#00FF00"),
                ("Blue", "blue", "🔵", "#0000FF")
            ]

        else:
            all_options = [
                ("Cyan", "cyan", "🩵", "#00FFFF"),
                ("Magenta", "magenta", "🟣", "#FF00FF"),
                ("Yellow", "yellow", "🟡", "#FFFF00")
            ]

        options = []

        for label, value, emoji, hex_value in all_options:
            if value not in already_selected:
                options.append(
                    discord.SelectOption(
                        label=label,
                        value=value,
                        emoji=emoji,
                        description=hex_value
                    )
                )

        number = len(selected_colours) + 1

        super().__init__(
            placeholder=f"Choose colour {number} of {amount}",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(
        self,
        interaction: discord.Interaction
    ):
        selected = self.values[0]

        colour_values = {
            "red": {
                "name": "🔴 Red",
                "rgb": (255, 0, 0)
            },
            "green": {
                "name": "🟢 Green",
                "rgb": (0, 255, 0)
            },
            "blue": {
                "name": "🔵 Blue",
                "rgb": (0, 0, 255)
            },
            "cyan": {
                "name": "🩵 Cyan",
                "rgb": (0, 255, 255)
            },
            "magenta": {
                "name": "🟣 Magenta",
                "rgb": (255, 0, 255)
            },
            "yellow": {
                "name": "🟡 Yellow",
                "rgb": (255, 255, 0)
            }
        }

        colour = colour_values[selected]

        new_colours = self.selected_colours.copy()

        new_colours.append(
            {
                "value": selected,
                "name": colour["name"],
                "rgb": colour["rgb"]
            }
        )

        await continue_colour_game(
            interaction,
            self.player_id,
            self.mode,
            self.amount,
            new_colours
        )


class ColourSelectionView(ColourGameView):
    def __init__(
        self,
        player_id,
        mode,
        amount,
        selected_colours
    ):
        super().__init__(player_id)

        self.add_item(
            ColourSelect(
                player_id,
                mode,
                amount,
                selected_colours
            )
        )


# --------------------------------------------------
# Continue game
# --------------------------------------------------

async def continue_colour_game(
    interaction,
    player_id,
    mode,
    amount,
    selected_colours
):
    if len(selected_colours) >= amount:
        embed = make_result_embed(
            mode,
            selected_colours
        )

        await interaction.response.edit_message(
            embed=embed,
            view=PlayAgainView(player_id)
        )
        return

    embed = make_selection_embed(
        mode,
        amount,
        selected_colours
    )

    await interaction.response.edit_message(
        embed=embed,
        view=ColourSelectionView(
            player_id,
            mode,
            amount,
            selected_colours
        )
    )


# --------------------------------------------------
# Selection embed
# --------------------------------------------------

def make_selection_embed(
    mode,
    amount,
    selected_colours
):
    if mode == "additive":
        title = "🌈 Additive RGB"
        choices = (
            "🔴 Red `#FF0000`\n"
            "🟢 Green `#00FF00`\n"
            "🔵 Blue `#0000FF`"
        )
        embed_colour = discord.Color.blue()

    else:
        title = "🎨 Subtractive CMY"
        choices = (
            "🩵 Cyan `#00FFFF`\n"
            "🟣 Magenta `#FF00FF`\n"
            "🟡 Yellow `#FFFF00`"
        )
        embed_colour = discord.Color.magenta()

    selected_text = ""

    if selected_colours:
        selected_text = "\n\n**Selected:**\n"

        for number, colour in enumerate(
            selected_colours,
            start=1
        ):
            selected_text += (
                f"{number}. {colour['name']} "
                f"`{rgb_to_hex(colour['rgb'])}`\n"
            )

    next_number = len(selected_colours) + 1

    return discord.Embed(
        title=title,
        description=(
            f"Mixing **{amount} different colours**.\n\n"
            f"{choices}"
            f"{selected_text}\n\n"
            f"Choose **colour {next_number} of {amount}**."
        ),
        color=embed_colour
    )


# --------------------------------------------------
# Result embed
# --------------------------------------------------

def make_result_embed(
    mode,
    selected_colours
):
    rgb_values = [
        colour["rgb"]
        for colour in selected_colours
    ]

    if mode == "additive":
        result = mix_additive(rgb_values)
        system_name = "Additive RGB 🌈"

    else:
        result = mix_subtractive(rgb_values)
        system_name = "Subtractive CMY 🎨"

    result_hex = rgb_to_hex(result)

    r, g, b = result

    colour_int = (
        (r << 16)
        + (g << 8)
        + b
    )

    mixed_text = " + ".join(
        colour["name"]
        for colour in selected_colours
    )

    embed = discord.Embed(
        title="🎨 Colour Mix Result",
        description=(
            f"**{system_name}**\n\n"
            f"{mixed_text}\n\n"
            f"➡️ **{colour_name(result)}**\n\n"
            f"**RGB:** `{r}, {g}, {b}`\n"
            f"**HEX:** `{result_hex}`"
        ),
        color=discord.Color(colour_int)
    )

    return embed


# --------------------------------------------------
# Mix again
# --------------------------------------------------

class PlayAgainView(ColourGameView):

    @discord.ui.button(
        label="Mix Again",
        emoji="🔄",
        style=discord.ButtonStyle.success
    )
    async def play_again(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        embed = discord.Embed(
            title="🎨 Colour Mix",
            description=(
                "Choose a colour mixing system.\n\n"
                "🌈 **Additive RGB**\n"
                "🔴 Red • 🟢 Green • 🔵 Blue\n\n"
                "🎨 **Subtractive CMY**\n"
                "🩵 Cyan • 🟣 Magenta • 🟡 Yellow"
            ),
            color=discord.Color.blurple()
        )

        await interaction.response.edit_message(
            embed=embed,
            view=ColourModelView(
                self.player_id
            )
        )


# --------------------------------------------------
# /game colour
# --------------------------------------------------

@game_group.command(
    name="colour",
    description="Mix basic additive RGB or subtractive CMY colours"
)
async def game_colour(
    interaction: discord.Interaction
):
    embed = discord.Embed(
        title="🎨 Colour Mix",
        description=(
            "Choose a colour mixing system.\n\n"
            "🌈 **Additive RGB**\n"
            "🔴 Red • 🟢 Green • 🔵 Blue\n\n"
            "🎨 **Subtractive CMY**\n"
            "🩵 Cyan • 🟣 Magenta • 🟡 Yellow\n\n"
            "Mix **2 different colours** or **all 3 colours**."
        ),
        color=discord.Color.blurple()
    )

    await interaction.response.send_message(
        "🎨 Colour Mix started.",
        ephemeral=True
    )

    await interaction.channel.send(
        embed=embed,
        view=ColourModelView(
            interaction.user.id
        )
    )


bot.tree.add_command(game_group)


# --------------------------------------------------
# ERROR HANDLER
# --------------------------------------------------

@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError
):
    if isinstance(
        error,
        app_commands.errors.MissingPermissions
    ):
        message = "❌ You don't have permission to use this command."

    else:
        print(f"Command error: {error}")
        message = "❌ Something went wrong while running this command."

    if interaction.response.is_done():
        await interaction.followup.send(
            message,
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            message,
            ephemeral=True
        )


bot.run(TOKEN)