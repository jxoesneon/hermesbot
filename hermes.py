import concurrent.futures as confut
import json
import os
import threading
import time
from pprint import pprint

import requests
from future.utils import iterkeys
from webexteamsbot import TeamsBot


def notify():
    pass

# def ping_time(hour, min):
#     schedule.every().day.at(f"{hour}:{min}").do(notify,'It is 01:00')
#     threading.time(60, ping_time).start() # wait one minute

filepath = "peopletonotify.json"

# API vars
baseurl = "https://api.ciscospark.com/v1/"
current_user = None

# Retrieve required details from environment variables
bot_email = os.getenv("TEAMS_BOT_EMAIL")
teams_token = os.getenv("TEAMS_BOT_TOKEN")
bot_url = os.getenv("TEAMS_BOT_URL")
bot_app_name = os.getenv("TEAMS_BOT_APP_NAME")

# Create a Bot Object
bot = TeamsBot(bot_app_name,teams_bot_token=teams_token,teams_bot_url=bot_url,teams_bot_email=bot_email,)


######## File Management ########
def write_to_file(data):
    with open(filepath, "w+") as file:
        json.dump(data, file)
        
def parse_user():
    data = current_user
    data = str(data).replace("'",'"')
    data = f"[{data}]"
    return data
        
def check_user_file():
    try:
        with open(filepath, "r+") as file:
            number_of_users = len(json.load(file))
    except FileNotFoundError:
        print("The file has not been initialized",
              "initializing ...",
              sep="\n")
        data = parse_user()
        write_to_file(data)
        print("done")
        
def load_users(file=False):
    check_user_file()
    id_list = []
    with open(filepath, "r") as file:
        data = json.load(file)
    for entry in data:
        if len(data) > 1:
            id_list.append(entry["id"])
        else:
            id_list.append(entry[0])
    if file:
        return data
    else:
        return id_list

def user_in_file():
    stored_users = load_users()
    if current_user["id"] in stored_users:
        return True
    else:
        return False
    

def update_file():
    if user_in_file():
        return "User already in file"
    else:
        stored_users = load_users(file=True)
        stored_users.append(current_user)
        write_to_file(stored_users)
        user = current_user["displayName"]
        return f"I've added you, {user}"
        
######## ######## ########

# A simple command that returns a basic string that will be sent as a reply
def do_something(incoming_msg):
    """
    Sample function to do some action.
    :param incoming_msg: The incoming message object from Teams
    :return: A text or markdown based reply
    """
    return f"I did what you said - {incoming_msg.text}"

def get_user_info(incoming_msg):
    personId= incoming_msg.personId
    url = f"{baseurl}people/{personId}"
    payload  = {}
    headers = {'Authorization': f'Bearer {teams_token}'}
    response = requests.request("GET", url, headers=headers, data = payload)
    global current_user
    current_user = response.json()
    print(type(current_user))
    # result = str()
    # for key, value in current_user.items():
    #     result = result + f"{key}:{value}\n"
    return str(current_user)
     
def subscribe(incoming_msg):
    get_user_info(incoming_msg)
    return update_file()

def unsubscribe(incoming_msg):
    pass

# Add new commands to the box.
bot.add_command("/dosomething", "help for do something", do_something)
bot.add_command("/sub", "I will ping you at a specified time", subscribe)
bot.add_command("/unsubscribe", "I will stop pinging you", unsubscribe)
bot.add_command("/me", "your data", get_user_info)



if __name__ == "__main__":
    bot.set_help_message("Hello, my name is Hermes! You can use the following commands:\n")
    # Run Bot
    bot.run(host="localhost", port=8080)
