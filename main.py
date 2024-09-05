import os
import json
import requests
import discord
from discord import app_commands
from discord.ext import tasks, commands
from twitchAPI.twitch import Twitch
from discord.utils import get
from dotenv import load_dotenv

#discord token
load_dotenv()
token = os.getenv('DISCORD_TOKEN')
application_id = os.getenv('DISCORD_CLIENT_ID')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


#twitch authentication
client_id = os.getenv('TWITCH_CLIENT_ID')
client_secret = os.getenv('TWITCH_CLIENT_SECRET')
access_token = os.getenv('TWITCH_ACCESS_TOKEN')

token_url = "https://id.twitch.tv/oauth2/token"

params = {
    'client_id': client_id,
    'client_secret': client_secret,
    'grant_type': 'client_credentials'
}

# Make a POST request to get the access token
response = requests.post(token_url, params=params)
response_data = response.json()

access_token = response_data['access_token']

TWITCH_USER_API_ENDPOINT = "https://api.twitch.tv/helix/users"
TWITCH_STREAM_API_ENDPOINT = "https://api.twitch.tv/helix/streams"
API_HEADERS = {
    'Authorization': f'Bearer {access_token}',
    'Client-ID': client_id,
}

def get_user_id(user):
    response = requests.get(TWITCH_USER_API_ENDPOINT, headers=API_HEADERS, params={'login': user})
    data = response.json()
    if 'data' in data and len(data['data']) > 0:
        return data['data'][0]['id']
    return None

def check_user(user):
    user_id = get_user_id(user)
    if not user_id:
        print(f"User '{user}' not found")
        return False

    response = requests.get(TWITCH_STREAM_API_ENDPOINT, headers=API_HEADERS, params={'user_id': user_id})
    data = response.json()

    if 'data' in data and len(data['data']) > 0:
        return True
    else:
        return False

## Example usage
#user_to_check = 'razordewotttest'
#is_streaming = check_user(user_to_check)
#print(f"Is {user_to_check} streaming? {is_streaming}")

@client.event
async def on_ready():
    await tree.sync()  # Synchronize commands with Discord
    print("Bot is online")
    print("---------------")
    live_notifs_loop.start()

@tasks.loop(seconds=10)
async def live_notifs_loop():
    # opens and reads the json file
    with open("streamers.json", 'r') as file:
        streamers = json.load(file)
        json_string = json.dumps(streamers)
    # makes sure that the json is not empty before continuing
    if streamers is not None:
        # gets the guild (server), 'twitch streams' channel
        #guild = client.get_guild(813311787016388608) this is obsolete
        channel = client.get_channel(1281050045906681966) #this is hard coded 
        # loops through the json and gets the key, value (user_id and twitch_name)
        for user_id, twitch_name in streamers.items():
            status = check_user(twitch_name)
            if status is True:
                print(1)
                # checks to see if the live message has already been sent in the channel
                # First, retrieve all messages from the channel's history
                messages = [message async for message in channel.history(limit=200)]
                # Check if there are no messages in the channel
                if not messages:
                    print(2)
                    await channel.send(
                        f":red_circle: **LIVE** \n{twitch_name} is now streaming on Twitch!\n"
                        f"https://www.twitch.tv/{twitch_name}"
                    )
                else:
                    # Process each message if there are messages in the channel
                    for message in messages:
                        if message.content:
                            # Split message content into words
                            words = message.content.split()
                            # if streamer removed themselves from file and is still streaming, remove their notif from channel
                            if words[2] not in json_string:
                                await message.delete()

                            # if streamer is already streaming and already has a notif, do nothing
                            elif twitch_name in words and "is now streaming on Twitch!" in message.content:
                                break
                        else:
                            print(4)
                            # if streamer is in file and they are streaming, send notif
                            await channel.send(
                                f":red_circle: **LIVE** \n{twitch_name} is now streaming on Twitch!\n"
                                f"https://www.twitch.tv/{twitch_name}"
                            )
                            break
            #if streamer is not live
            else:
                print(5)
                #if NOW LIVE message was sent before, delete it once offline
                async for message in channel.history(limit=200):
                    if twitch_name in message.content and "is now streaming" in message.content:
                        await message.delete()
    #if no streamers in json file, delete notifs message (wipes whole channel of notifs)
    #lowkey will never need this should probably delete it even haha why would i ever do this
    else:
        async for message in channel.history(limit=200):
            if "is now streaming on Twitch! https://www.twitch.tv/" in message.content:
                await message.delete()

@tree.command(name="addtwitch")
async def add_twitch(ctx: discord.Interaction, twitch_name:str):
    if not ctx.user.guild_permissions.administrator:
        print("You do not have permission to run this command")
        return
    # Ensure the file exists before opening
    elif not os.path.exists('streamers.json'):
        with open('streamers.json', 'w') as file:
            json.dump({}, file)

    # Open and read the JSON file
    with open('streamers.json', 'r') as file:
        try:
            streamers = json.load(file)
        except json.JSONDecodeError:
            streamers = {}

    # gets the user's name that called the command
    #print(ctx.user.id)
    #print(ctx.user)
    #print(ctx.guild.members)
    user_name = str(ctx.user)
    # assigns their given twitch_name to their discord username and adds it to streamers.json
    streamers[user_name] = twitch_name

    # adds the changes we made to the json file
    with open('streamers.json', "w") as file:
        json.dump(streamers, file, indent=4)

    # tells the user it worked
    await ctx.channel.send(f"Added {twitch_name} for {ctx.user} to the notifications list")

@tree.command(name="removetwitch")
async def remove_twitch(ctx: discord.Interaction, twitch_name:str):
    if not ctx.user.guild_permissions.administrator:
        print("You do not have permission to run this command")
        return
    # Ensure the file exists before opening
    elif not os.path.exists('streamers.json'):
        await ctx.send("No Twitch accounts are currently registered.")
        return

    # Open and read the JSON file
    with open('streamers.json', 'r') as file:
        try:
            streamers = json.load(file)
        except json.JSONDecodeError:
            streamers = {}

    # Get the user's ID that called the command
    user_name = str(ctx.user)
    #print("ctx.author.id: " + ctx.author.id + "\n")
    # Check if the user_id is in the streamers dictionary and if it matches the given twitch_name
    if user_name in streamers and streamers[user_name] == twitch_name:
        del streamers[user_name]

        # Save the changes to the JSON file
        with open('streamers.json', "w") as file:
            json.dump(streamers, file, indent=4)

        # Notify the user of the successful removal
        await ctx.channel.send(f"Removed {twitch_name} for {ctx.user} from the notifications list")
    else:
        # Notify the user if the Twitch name was not found
        await ctx.channel.send(f"{twitch_name} is not registered for {ctx.user}")

client.run(token)
