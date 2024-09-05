#OAUTH2 AUTHORIZATION FLOW
#basically run this if you want to add the bot to a server thru discord dev portal

from flask import Flask, request, redirect, url_for
from discord.utils import get
from dotenv import load_dotenv
import requests
import os

app = Flask(__name__)
load_dotenv()
client_id = os.getenv('DISCORD_CLIENT_ID')
client_secret = os.getenv('DISCORD_CLIENT_SECRET')
redirect_uri = 'http://localhost:5000/callback'
bot_token = os.getenv('DISCORD_TOKEN')


@app.route('/')
def home():
    return f'<a href="https://discord.com/api/oauth2/authorize?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code&scope=bot%20identify%20guilds">Authorize Bot</a>'

@app.route('/callback')
def callback():
    code = request.args.get('code')
    data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': redirect_uri
    }
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    response = requests.post('https://discord.com/api/oauth2/token', data=data, headers=headers)
    if response.status_code != 200:
        return f"Authorization failed. Error: {response.text}", 400
    response_data = response.json()
    access_token = response_data.get('access_token')

    if access_token:
        headers = {
            'Authorization': f'Bearer {access_token}'
        }
        user_response = requests.get('https://discord.com/api/users/@me', headers=headers)
        user_data = user_response.json()
        return f"Hello, {user_data['username']}! Your bot is authorized."
    else:
        return "Authorization failed."

if __name__ == '__main__':
    app.run(debug=True)
