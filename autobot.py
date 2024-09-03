# autobot.py
import os
import sqlite3
import discord
import discord.ext
import discord.ext.commands
from discord.ext import commands
from dotenv import load_dotenv
from datetime import datetime, timedelta

#region Constants

# Set up the token for connecting to discord
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Emoji to use for all reactions
EMOJI = os.getenv('AUTOBOT_EMOJI')

# Standard format to use when converting dates
DATEFORMAT = '%d/%m/%Y %H:%M:%S'

# Role restriction. All commands will be restricted to this role.
ROLE = 'Admin Bots'

# Path that will be used to store images
IMAGEPATH = './images'

# Path for db
DBPATH = './db'

#endregion

#region Setup

# Set up database connection
if not os.path.exists(DBPATH):
    os.mkdir(DBPATH)

dbCon = sqlite3.connect(os.path.join(DBPATH, 'autobot.db'))
dbCur = dbCon.cursor()

# Set up tables in the db
dbCur.execute('CREATE TABLE IF NOT EXISTS channels('
              'channelid INTEGER PRIMARY KEY, '
              'enabled INTEGER NOT NULL'
              ');'
)
dbCur.execute('CREATE TABLE IF NOT EXISTS imageMessages('
              'messageid INTEGER PRIMARY KEY, '
              'channelid INTEGER, '
              'messagedate TEXT NOT NULL, '
              'FOREIGN KEY(channelid) REFERENCES channels(channelid)'
              ');'
)

res = dbCur.execute('SELECT name FROM sqlite_master')
print(f'Database setup complete: {res.fetchall()}')

# Set up discord intents
intents = discord.Intents.default()
intents.message_content = True

# Change 'No Category' to something more meaningful
help_command = commands.DefaultHelpCommand(
    no_category = 'Commands'
)

bot = commands.Bot(
    command_prefix='$',
    description='A helper bot that organizes images that get posted to social media from the discord server.',
    help_command=help_command,
    intents=intents)

#endregion

#region Commands

@bot.command(help='Starts tracking the channel.')
@commands.has_role(ROLE)
async def track(
    ctx,
    channel: discord.TextChannel = commands.parameter(
        default=lambda ctx: ctx.channel,
        description='The text channel to track. Default is the current channel.'
    )):
    res = dbCur.execute('SELECT enabled FROM channels WHERE channelid = ?', [(channel.id)])
    channelEnabled = res.fetchone()

    if channelEnabled is None:
        dbCur.execute('INSERT INTO channels VALUES(?, ?)', [(channel.id), (True)])
        dbCon.commit()
        await ctx.send(f'{channel.mention} is now being tracked.')
    else:
        if channelEnabled:
            await ctx.send(f'{channel.mention} is already being tracked.')
        else:
            dbCur.execute('UPDATE channels SET enabled = ? WHERE channelid = ?', [(True), (channel.id)])
            await ctx.send(f'{channel.mention} is now being tracked.')

@track.error
async def track_error(ctx, error):
    if isinstance(error, commands.ChannelNotFound):
        await ctx.send('No channel was found.'
                       ' Make sure to give the full name of the channel, or just call track in the channel you wish to track.'
        )

@bot.command(help='Stops tracking the channel.')
@commands.has_role(ROLE)
async def untrack(
    ctx,
    channel_name: str = commands.parameter(
        default=lambda ctx: ctx.channel.name,
        description='The channel to stop tracking. Default is the current channel.'
    )):
    guild = ctx.guild
    channel = discord.utils.get(guild.channels, name=channel_name)
    
    if not channel:
        await ctx.send(f'{channel_name} is not a channel.'
                       ' Please enter the full name of the channel, not including the #.'
        )
    else:
        res = dbCur.execute('SELECT enabled FROM channels WHERE channelid = ?', [(channel.id)])
        channelEnabled = res.fetchone()
        if channelEnabled is None or not channelEnabled[0]:
            await ctx.send(f'{channel.mention} is not currently being tracked.')
        else:
            dbCur.execute('UPDATE channels SET enabled = ? WHERE channelid = ?', [(False), (channel.id)])
            dbCon.commit()
            await ctx.send(f'{channel.mention} is no longer being tracked.')

@bot.command(help='Lists the currently tracked channels.')
@commands.has_role(ROLE)
async def list(ctx):
    guild = ctx.guild
    channelids = get_tracked_channelids(guild)

    if not channelids:
        await ctx.send('No channels are currently being tracked.')
        return
    
    mentionList = [discord.utils.get(guild.channels, id=id).mention for id in channelids if discord.utils.get(guild.channels, id=id)]
    embed = discord.Embed(title='Tracked Channels', description='Channels currently being tracked for images.', color=0x00ff00)
    embed.add_field(name='Channels', value='\n'.join(mentionList), inline=False)
    await ctx.send(embed=embed)

@bot.command(help='Scans for images from the selected channels and saves them.')
@commands.has_role(ROLE)
async def scan(ctx: commands.Context):
    guild = ctx.guild
    channelids = get_tracked_channelids(guild)

    if not channelids:
        await ctx.send('No channels are currently being tracked.'
                       'Use the $track command to start tracking channels for images.'
        )
        return
    
    await ctx.send('Starting scan. If there are tracked channels that have never been scanned before, this will take a while. Please be patient.')

    channels = [discord.utils.get(guild.channels, id=id) for id in channelids if discord.utils.get(guild.channels, id=id)]
    threads = [thread for thread in guild.threads if thread.parent_id in channelids]

    for channel in channels:
        await ctx.send(f'Scanning channel {channel.mention}...')
        async for message in channel.history(limit=999999999, oldest_first=True):
            await pull_images_from_message(message)
    
    for thread in threads:
        await ctx.send(f'Scanning thread {thread.mention}...')
        async for message in thread.history(limit=999999999, oldest_first=True):
            await pull_images_from_message(message)

    await ctx.send('Scan complete!')

#endregion

#region Helper functions

def get_tracked_channelids(guild: discord.Guild):
    res = dbCur.execute('SELECT channelid FROM channels WHERE enabled = TRUE')
    channels = res.fetchall()
    guildChannelIds = [channel.id for channel in guild.channels]

    return [id[0] for id in channels if id[0] in guildChannelIds]

def message_contains_images(message: discord.Message):
    if len(message.attachments) > 0:
        for attachment in message.attachments:
            if attachment.content_type is not None and 'image' in attachment.content_type:
                return True
    return False

def get_message_date(message: discord.Message):
    messageDate = message.created_at
    if message.edited_at is not None:
        messageDate = message.edited_at
    return messageDate

async def pull_images_from_message(message: discord.Message):
    if message_contains_images(message):
        res = dbCur.execute('SELECT messagedate FROM imageMessages WHERE messageid = ?', [(message.id)])
        savedMessage = res.fetchone()
        if savedMessage is None:
            await save_images(message)
            messageDate = get_message_date(message)
            dbCur.execute('INSERT INTO imageMessages VALUES(?, ?, ?)', [(message.id), (message.channel.id), (messageDate.strftime(DATEFORMAT))])
            dbCon.commit()
            if len(message.reactions) < 20: # Discord has a limit of 20 reactions per message, so don't bother if there's more
                await message.add_reaction(EMOJI)

def get_first_day_of_week(date: datetime, weeksBackInTime: int = 0):
    date = date - timedelta(weeksBackInTime * 7)
    firstDay = date - timedelta((date.weekday() + 1) % 7)
    return firstDay

def get_path(message: discord.Message):
    messageDate = get_message_date(message)
    week = get_first_day_of_week(messageDate)
    author = message.author.name
    channelname = f'{message.channel.parent.name}-{message.channel.name}' if isinstance(message.channel, discord.Thread) else message.channel.name
    path = os.path.join(IMAGEPATH, week.strftime('%Y-%m-%d'), channelname, author)
    if not os.path.exists(path):
        os.makedirs(path)
    return path

def get_next_image_name(path: str, username: str):
    filecount = len(os.listdir(path))
    return f'{username}-{str(filecount)}'

async def save_images(message: discord.Message):
    path = get_path(message)
    for attachment in message.attachments:
        if 'image' in attachment.content_type:
            filename, extension = os.path.splitext(attachment.filename)
            filename = get_next_image_name(path, message.author.name)
            fullpath = os.path.join(path, f'{filename}{extension}')
            await attachment.save(fullpath)

#endregion

#region Events

@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')

# TODO: Write better error logs
#@bot.event
#async def on_error(event, *args, **kwargs):
    #with open('err.log', 'a') as f:
        #if event == 'on_message':
        #    f.write(f'Unhandled message: {args[0]}\n')
        #else:
        #    raise

@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user:
        return

    # Grab images if this is a tracked channel and the message contains images
    channelids = get_tracked_channelids(message.guild)
    if message.channel.id in channelids or (isinstance(message.channel, discord.Thread) and not message.channel.is_private() and message.channel.parent_id in channelids):
        await pull_images_from_message(message)

    await bot.process_commands(message)

@bot.event
async def on_thread_create(thread: discord.Thread):
    channelids = get_tracked_channelids(thread.guild)
    if not thread.is_private() and thread.parent_id in channelids:
        await thread.join()

#endregion

bot.run(TOKEN) 