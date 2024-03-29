import os
import hikari
import asyncio
import resource.message_channels as message_channels
from resource.token import token
from requests import get
from importlib import reload
from time import monotonic
from mods import RedditWatcher

# POSIX optimisation from Hikari docs
if os.name != "nt":
    import uvloop
    uvloop.install()

bot = hikari.GatewayBot(token=token)
ID = hikari.applications.get_token_id(bot._token)

# Pointless dictionary just append to string
cmds ="""```md
# Add:
  * Admin, appends current channel to array.
# Remove:
  * Admin, removes current channel from array.
# Ping:
  * Everyone, returns latency information.
# About:
  * Everyone, returns information about bot.

Reddit bot: https://reddit.com/user/masterhacker_bot
Source code: https://github.com/enuf96/redditscraperbot```"""

@bot.listen(hikari.StartedEvent)
async def On_Started(event):
    global ActiveWatcher
    global StatusUpdate

    ActiveWatcher = asyncio.create_task(RedditWatcher(bot).Runner())
    StatusUpdate = asyncio.create_task(Status_Update())


@bot.listen(hikari.StoppingEvent)
async def On_Stop(event):
    ActiveWatcher.cancel()
    StatusUpdate.cancel()


async def Status_Update() -> None:
    while True:
        _guilds = await bot.rest.fetch_my_guilds()
        g_ext, c_ext = "", ""
        if len(_guilds) != 1:
            g_ext = "s"
        if len(message_channels.channels) != 1:
            c_ext = "s"
        
        try:
            await bot.update_presence(
                activity=hikari.presences.Activity(name=f"{len(_guilds)} guild{g_ext} and {len(message_channels.channels)} channel{c_ext} to send to", type=3),
                status=hikari.presences.Status(hikari.presences.Status.DO_NOT_DISTURB)
                )
        
        except:
            pass
        
        await asyncio.sleep(15)
        reload(message_channels)
        


async def Is_Admin(event) -> bool:
    '''Check if user is admin or owner.'''
    guild = event.get_guild()
    userid = event.author_id

    if userid == guild.owner_id:
        return True

    roles = await guild.fetch_roles()
    member = guild.get_member(userid)

    for i in range(0, len(roles)):
        if roles[i].id in member.role_ids \
            and roles[i].permissions & hikari.permissions.Permissions.ADMINISTRATOR:
            return True

    return False


async def Mentioned(string: str, prefix: str, alias=None) -> bool:
    '''Check if the bot was mentioned'''
    return string == f"<@!{ID}> {prefix}" or string == f"<@{ID}> {prefix}" or string == f"<@{ID}> {alias}" or string == f"<@{ID}> {alias}"


async def Validate(event, cmdName, cmdAlias=None):
    '''Validates the request if it is true or not.'''
    return not event.is_bot and event.content and await Mentioned(event.content, cmdName, cmdAlias)


@bot.listen(hikari.GuildMessageCreateEvent)
async def add_channel(event) -> None:
    if not await Validate(event, "add"):
        return

    if not await Is_Admin(event):
        return

    channel_id = int(event.channel_id)
    my_list = message_channels.channels

    if channel_id not in message_channels.channels:
        my_list.append(channel_id)
        with open("resource/message_channels.py", "w") as f:
            f.write(f"channels = {str(my_list)}")
        
        await event.message.respond(f"Added <#{channel_id}> `({channel_id})` to the channels array.", reply=True)
        reload(message_channels)

    else:
        await event.message.respond(f"Channel already in array.", reply=True)


@bot.listen(hikari.GuildMessageCreateEvent)
async def remove_channel(event) -> None:
    if not await Validate(event, "remove"):
        return

    if not await Is_Admin(event):
        return

    channel_id = int(event.channel_id)
    my_list = message_channels.channels

    if channel_id in message_channels.channels:
        my_list.remove(channel_id)
        with open("resource/message_channels.py", "w") as f:
            f.write(f"channels = {str(my_list)}")
        
        await event.message.respond(f"Removed <#{channel_id}> `({channel_id})` to the channels array.", reply=True)
        reload(message_channels)

    else:
        await event.message.respond(f"Channel doesn't exist in array.", reply=True)


@bot.listen(hikari.GuildMessageCreateEvent)
async def ping(event):
    if not await Validate(event, "ping"):
        return

    start = monotonic()
    get("https://api.reddit.com/user/masterhacker_bot")
    reddit_ping = monotonic() - start

    start = monotonic()
    message = await event.message.respond("Pinging.", reply=True)
    api_ping = monotonic() - start

    sendStr = f"Average shard heartbeat: {bot.heartbeat_latency * 1000:.2f}ms\nReddit HTTP API: {reddit_ping * 1000:.2f}ms\nDiscord HTTP API: {api_ping * 1000:.2f}ms"
    await message.edit(sendStr)


@bot.listen(hikari.GuildMessageCreateEvent)
async def about(event):
    if not await Validate(event, "about", "help"):
        return

    await event.message.respond(cmds, reply=True)


bot.run()