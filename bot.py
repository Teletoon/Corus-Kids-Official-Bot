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
    description="Send a text message"
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
    description="Send an image"
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

@bot.tree.command(
    name="edit-message",
    description="Edit a message sent by the bot"
)
async def edit_message(
    interaction: discord.Interaction,
    message_id: str,
    text: str
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

	allowed_mentions = discord.AllowedMentions(
            users=True,
            roles=False,
            everyone=False
        )

        await message.edit(
           content=text,
           allowed_mentions=allowed_mentions
        )

        await interaction.response.send_message(
            "Message edited.",
            ephemeral=True
        )

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
    description="Warn a user about a rule they broke"
)
@app_commands.checks.has_permissions(moderate_members=True)
async def warn(
    interaction: discord.Interaction,
    user: discord.Member,
    rule_broken: str
):
    await interaction.response.send_message(
        f"⚠️ {user.mention} has been warned.\n"
        f"**Rule broken:** {rule_broken}",
        allowed_mentions=discord.AllowedMentions(users=True)
    )


# --------------------------------------------------
# /timeout
# --------------------------------------------------

@bot.tree.command(
    name="timeout",
    description="Timeout a user for up to 1 week"
)
@app_commands.describe(
    user="User to timeout",
    duration="Duration (max 30 days): s=seconds, m=minutes, h=hours, d=days, w=weeks",
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

        await interaction.response.send_message(
            f"⏱️ {user.mention} is timed out. "
            f"**{duration}**.\n"
            f"Reason: {reason or 'No reason provided.'}"
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
    description="Remove a user's timeout"
)
@app_commands.checks.has_permissions(moderate_members=True)
async def remove_timeout(
    interaction: discord.Interaction,
    user: discord.Member
):
    try:

        await interaction.response.send_message(
            f"✅ **{user}** has been removed from timeout."
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
    description="Jail a user to Cow Jail or Donkey Jail"
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
            "Invalid duration. Use `30s`, `10m`, `2h`, `3d`, `1w`, etc. Maximum jail time is 30 days.",
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
                reason=f"Jailed by {interaction.user}: {reason or 'No reason provided'}"
            )

        # Remove existing jail roles
        if baqara and baqara in user.roles:
            await user.remove_roles(baqara)

        if himarroon and himarroon in user.roles:
            await user.remove_roles(himarroon)

        # Add selected jail role
        await user.add_roles(
            jail_role,
            reason=f"Sent to {jail_name} by {interaction.user}: {reason or 'No reason provided'}"
        )

        await interaction.response.send_message(
            f"⛓️ {user.mention} is jailed to **{jail_name}**.\n"
            f" Duration: **{duration}**\n"
            f" Reason: **{reason or 'No reason provided'}**"
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
    description="Kick a user from the server"
)
@app_commands.checks.has_permissions(kick_members=True)
async def kick(
    interaction: discord.Interaction,
    user: discord.Member,
    reason: Optional[str] = None
):
    try:
        await user.kick(reason=reason)

        await interaction.response.send_message(
            f"🦿 **{user}** is kicked.\n"
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
    description="Ban an user"
)
@app_commands.describe(
    user="User to ban",
    reason="Reason for the ban",
    delete_messages="Delete message history"
)
@app_commands.choices(
    delete_messages=[
        app_commands.Choice(name="Don't delete messages", value=0),
        app_commands.Choice(name="1 day", value=86400),
        app_commands.Choice(name="3 days", value=259200),
        app_commands.Choice(name="7 days", value=604800)
    ]
)
@app_commands.checks.has_permissions(ban_members=True)
async def ban(
    interaction: discord.Interaction,
    user: discord.Member,
    reason: str,
    delete_messages: Optional[app_commands.Choice[int]] = None
):
    # Default = don't delete messages
    delete_seconds = delete_messages.value if delete_messages else 0

    try:
        await user.ban(
            reason=reason,
            delete_message_seconds=delete_seconds
        )

        delete_text = (
            delete_messages.name
            if delete_messages
            else "Don't delete messages"
        )

        await interaction.response.send_message(
            f"🚫 **{user}** is banned.\n"
            f"Reason: **{reason}**\n"
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "I cannot ban this user. Check my permissions and role position.",
            ephemeral=True
        )


# --------------------------------------------------
# /unban
# --------------------------------------------------

@bot.tree.command(
    name="unban",
    description="Unban a user by their Discord user ID"
)
@app_commands.checks.has_permissions(ban_members=True)
async def unban(
    interaction: discord.Interaction,
    user_id: str
):
    try:
        user = await bot.fetch_user(int(user_id))

        await interaction.response.send_message(
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
# /avatar
# --------------------------------------------------

@bot.tree.command(
    name="avatar",
    description="Show a user's avatar"
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
    description="Show the server icon"
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
# /clear
# --------------------------------------------------

@bot.tree.command(
    name="clear",
    description="Clear messages from a specified member"
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

    await interaction.response.defer(ephemeral=False)

    messages = []

    async for message in interaction.channel.history(limit=100):
        if message.author.id == member.id:
            messages.append(message)

            if len(messages) >= amount:
                break

    for message in messages:
        await message.delete()

    await interaction.followup.send(
        f"🧹 Deleted **{len(messages)} message(s)** from **{member}**.",
        ephemeral=False
    )


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