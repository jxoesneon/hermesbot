# Prod Imports
import json
import os
import pprint
# Dev imports
from pprint import pprint

import dotenv
import requests
import webexteamsbot
from pyngrok import ngrok
from pyadaptivecards.card import *
from pyadaptivecards.inputs import *
from pyadaptivecards.actions import *
from pyadaptivecards.container import *
from pyadaptivecards.components import *
from webexteamssdk import WebexTeamsAPI
from apscheduler.schedulers.background import BackgroundScheduler as Scheduler

# Open a SSH tunnel
# ssh_url = ngrok.connect(22, "tcp")

filepath = "peopletonotify.json"

# API vars
baseurl = "https://api.ciscospark.com/v1"
current_user = None

# Retrieve required details from environment variables
dotenv.load_dotenv()
# ----------- set up local http server -----------
# Open a HTTP tunnel on the default port 80
try:
    bot_url = ngrok.connect(port=8080, proto="http")
    print(bot_url)
except Exception:
    raise SystemExit

bot_email = os.getenv("TEAMS_BOT_EMAIL")
teams_token = os.getenv("TEAMS_BOT_TOKEN")
bot_app_name = os.getenv("TEAMS_BOT_APP_NAME")

# Start API
api = WebexTeamsAPI(access_token=teams_token)

# Create a Bot Object
bot = webexteamsbot.TeamsBot(bot_app_name,
                             teams_bot_token=teams_token,
                             teams_bot_url=bot_url,
                             teams_bot_email=bot_email,
                             webhook_resource_event=[{"resource": "messages",
                                                      "event": "created"},
                                                     {"resource": "attachmentActions",
                                                      "event": "created"}])

# --------- File Management ---------
def write_to_file(data):
    with open(filepath, "w+") as file:
        json.dump(data, file, sort_keys=True, indent=4, separators=(',', ': '))

def check_user_file():
    try:
        with open(filepath, "r+") as file:
            _ = len(json.load(file))
    except FileNotFoundError:
        print("The file has not been initialized",
              "initializing ...",
              sep="\n")
        write_to_file({"users": {current_user["id"]: current_user}})
        print("done")

def load_users(file=False):
    check_user_file()
    id_list = []
    with open(filepath, "r") as file:
        data = json.load(file)
    id_list.append(list(data["users"]))
    if file:
        return data
    else:
        return id_list

def user_in_file():
    stored_users = load_users()
    if current_user.id in stored_users["users"]:
        return True
    else:
        return False

def update_file(user=None, data=None, remove=False):
    if user and data:
        stored_users = load_users(file=True)
        stored_users["users"][user]["subscription"] = data
        write_to_file(stored_users)
        return "Updated"
    if remove:
        if user_in_file():
            stored_users = load_users(file=True)
            stored_users["users"].pop(current_user["id"])
            name = current_user["displayName"]
            email = current_user["emails"][0]
            write_to_file(stored_users)
            return f"I have removed you {name} - {email}"
        else:
            return "You were not subscribed ..."
    else:
        if user_in_file():
            return "User already in file"
        else:
            stored_users = load_users(file=True)
            stored_users["users"][current_user["id"]] = current_user
            write_to_file(stored_users)
            user = current_user["displayName"]
            return f"I've added you, {user}"
# ####### ######## ########

def get_user_info(incoming_msg):
    personId = incoming_msg.personId
    global current_user
    current_user = api.people.get(personId)
    return str(current_user)

def ping_single_user(user, message=None, time=None):
    if time:
        pass
    else:
        api.messages.create(toPersonId=user, text=message)

def ping_all():
    users_to_ping = load_users(file=True)["users"]
    for user in users_to_ping:
        user_info = users_to_ping[user]
        name = user_info["displayName"]
        message = f"Hello {name}, remember to send the hourly email!"
        ping_single_user(user, message)

def ping_all_users(incoming_msg):
    message = f"Broadcast message requestesd by {incoming_msg.personEmail}"
    users_to_ping = load_users()["users"]
    responses = []
    for user in users_to_ping:
        ping_single_user(user, message)
        responses.append(user)
    return f"Ping sent to {len(users_to_ping)} users."

# Start the scheduler
sched = Scheduler()
sched.remove_all_jobs()
sched.start()

# Schedule ping times
hours = []
for h in range(21, 24):
    hours.append(h)
for h in range(6):
    hours.append(h)
for hour in hours:
    sched.add_job(ping_all, "cron", hour=hour, minute=55)
# for minute in range(60):
#     sched.add_job(ping_all, "cron", minute=minute)

def subscribe(incoming_msg):
    get_user_info(incoming_msg)
    return update_file()

def unsubscribe(incoming_msg):
    get_user_info(incoming_msg)
    return update_file(remove=True)

def list_subscribers(_):
    subscribers = load_users()
    subList = ""
    num = 0
    for sub in subscribers["users"]:
        user_data = api.people.get(sub)
        num += 1
        name = user_data.displayName
        email = user_data.emails[0]
        user_entry = f"{num})\t{name} - {email}"
        subList = subList + user_entry + "\n\n"
    return subList

def remove_message(message_id):
    api.messages.delete(message_id)

def remove_all_messages(incoming_msg):
    # List all the messages the bot and the user share
    messages_with_user = api.messages.list(roomId=incoming_msg.roomId)
    for message in messages_with_user:
        # Delete the messages
        try:
            api.messages.delete(message.id)
        except Exception:
            pass

# Create Adaptive Cards
# Create Days
def days():
    day = ["Sunday","Monday","Tuesday","Wednesday",
                "Thursday","Friday","Saturday"]
    dayid = [f"day{num}" for num in range(7)]
    day_dict = dict(zip(dayid, day))
    day_list = []
    for d_id in day_dict:
        day_list.append(Toggle(day_dict[d_id],d_id))
    return day_list

# Create Subscription card
def card_subscription():
    # user = current_user.displayName
    # # Title
    # title = TextBlock("Hello {user}, Let's set up your subscription!")
    # # Left Column
    # days_txt = TextBlock("please select the days you work:")
    # day_list = days()
    # title_cont = Container(title)
    # # Right Column
    # start_tile = TextBlock("Shift Start:")
    # shift_star = Time("shiftstart",)
    # end_tile = TextBlock("Shift Start:")
    # shift_end = Time("shiftend",)
    # # Bottom
    # submit = Submit(title="All set!")
    # # Aggregate all
    # row_cont1 = Column(items=[days_txt,*day_list])
    # row_cont2 = Column(items=[start_tile, shift_star,end_tile,shift_end])
    # body = ColumnSet(columns=[row_cont1, row_cont2])
    # body_cont = Container([title_cont,body])
    # card = AdaptiveCard(body=[body_cont], actions=[submit])
    # card_json = card.to_json()
    # pprint(card_json)
    with open("subscription.json") as file:
        card_json = json.load(file)
    return card_json

def sub_card(incoming_msg):
    get_user_info(incoming_msg)
    user = incoming_msg.personId
    txt = "cardmsg"
    card = card_subscription()
    attachment = {'contentType': 'application/vnd.microsoft.card.adaptive',
                  'content': card}
    api.messages.create(toPersonId=user, text=txt, attachments=[attachment])
    return  None

def get_attachment_actions(attachmentid):
    headers = {'content-type': 'application/json; charset=utf-8',
               'authorization': f'Bearer {teams_token}'}
    url = f'{baseurl}/attachment/actions/{attachmentid}'
    response = requests.get(url, headers=headers)
    return response.json()

# check attachmentActions:created webhook to handle any card actions
def handle_cards(api, incoming_msg):
    m = get_attachment_actions(incoming_msg["data"]["id"])
    # Update people to notify file
    update_file(user=m["personId"], data=m["inputs"])
    remove_message(m["messageId"])
    return "Form received!"

######


# Add new commands to the box.
bot.add_command("/me", "*", get_user_info)
bot.add_command('attachmentActions', '*', handle_cards)
bot.add_command("/unsubscribe", "I will stop pinging you", unsubscribe)
bot.add_command("/subscribe", "I will ping you at a specified time", subscribe)
bot.add_command("/pingall", "*", ping_all_users)
bot.add_command("/listsubs", "This will give you a list of all the people who will be pinged", list_subscribers)
bot.add_command("/t", "test", days)
bot.add_command("/card", "sends sub card", sub_card)
bot.add_command("/clean", "Removes all the meessages in the conversation", remove_all_messages)


if __name__ == "__main__":
    bot.set_help_message("Hello, my name is Hermes! You can use the following commands:\n")
    # Run Bot
    bot.run(host="localhost", port=8080)
