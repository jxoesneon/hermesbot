# Prod Imports
import json
import os
import datetime

# Dev imports
from pprint import pprint
import dotenv
import requests
import webexteamsbot
from apscheduler.schedulers.background import BackgroundScheduler as Scheduler
from pyngrok import ngrok
# from datetime import datetime
from webexteamssdk import WebexTeamsAPI

# from pyadaptivecards.actions import *
# from pyadaptivecards.card import *
# from pyadaptivecards.components import *
# from pyadaptivecards.container import *
# from pyadaptivecards.inputs import *


def clearscreen():
    """Function to clear the screen

    This function aims to clear the screen independently of the OS the script
    is being run on.
    """
    os.system('cls' if os.name == 'nt' else 'clear')


clearscreen()


# Define where to find the users file
filepath = "peopletonotify.json"

# API vars
baseurl = "https://api.ciscospark.com/v1"

# Define current interacting user
current_user = None

# Retrieve required details from environment variables
dotenv.load_dotenv()

# ----------- set up local http server -----------
# Open a HTTP tunnel on the default port 80
try:
    bot_url = ngrok.connect(port=8080, proto="http")
    print(bot_url)
except Exception:
    clearscreen()
    print("You need to close the current terminal, otherwise the HTTP tunnel wont connect")
    input("Press enter to exit.\n")
    raise SystemExit

# Get enviroment details
bot_email = os.getenv("TEAMS_BOT_EMAIL")
teams_token = os.getenv("TEAMS_BOT_TOKEN")
bot_app_name = os.getenv("TEAMS_BOT_APP_NAME")

# Start API
api = WebexTeamsAPI(access_token=teams_token)

# Create the Bot Object
bot = webexteamsbot.TeamsBot(bot_app_name,
                             teams_bot_token=teams_token,
                             teams_bot_url=bot_url,
                             teams_bot_email=bot_email,
                             webhook_resource_event=[{"resource": "messages",
                                                      "event": "created"},  # Handles Messages
                                                     {"resource": "attachmentActions",
                                                      "event": "created"}])  # Handles Adaptive cards


# --------- File Management ---------
def write_to_file(data, filepath=filepath):
    """Write data to a file

    Simple function to write string data to a file in Json format.

    Args:
        data (str): A string containing the data to be written to a file
        filepath (str, optional): String containing the relative or full path to the file the data is going to be written to. Defaults to filepath.
    """
    with open(filepath, "w+") as file:
        json.dump(data, file, sort_keys=True, indent=4, separators=(',', ': '))


def check_user_file():
    """Check if the user file exist

    Sanity check to see if the users file already exists.
    If there is no users file then it proceeds to create it.
    """
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
    """Loads the user data in the user file.

    Returns the user data as a list of personId by default or the whole user data block if the file option is set to true.

    Args:
        file (bool, optional): If True, it returns the file data instead of just the personId list. Defaults to False.

    Returns:
        str: String containing either a list of personIds or the whole user data set.
    """
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
    """Check if the current user is in the users data file

    Uses the current_user's personId to see if the user has been already added to the user data file.

    Returns:
        bool: True if the current user is in the user data file, False if not.
    """
    stored_users = load_users()
    return True if current_user.id in stored_users["users"] else False


def update_file(user=None, data=None, remove=False):
    """Update the users file with new data

    Allows to add or remove a user from the users file.
    By default it uses the global current_user to check if the user is in the users file and adds it if not.
    If a custom data set is to be added a personId must be passed to the user arg, as well as a data dict, if either are missing it will not update.

    Usage:
        To add the current user:
            update_file()

        To remove the current user:
            update_file(remove=True)

        To add custom data to a user:
            update_file(user=personId, data=dict)

    Args:
        user (personId, optional): A string containig the personId to change/add. Defaults to None.
        data (str, optional): A string containing the data to add to the user. Defaults to None.
        remove (bool, optional): If true removes the current user from the users data file. Defaults to False.

    Returns:
        str: A string informing of the action taken, either updated, created or removed.
    """
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
    """Sets the curren_user global variable using id of the incomming message.

    Uses the personId from the incomming message to gather the user data by making an API call,
    then it sets the global current_user variable.
    Should be called before any actions that require the current_user variable to ensure it is populated.

    Args:
        incoming_msg (Message): Message data received by the API.

    Returns:
        str: A string containing all the user data gathered.
    """
    personId = incoming_msg.personId
    global current_user
    current_user = api.people.get(personId)
    return str(current_user)


def ping_single_user(user, message="Hi", time=None):
    """Send a message to a user.

    Uses the required personId to send a direct message to that user.

    Args:
        user (personId): Id of the user who will be messaged.
        message (str, optional): Message to send the user. Defaults to "hi".
        time (tuple, optional): Time in (hour, minute) format for when the user should be pinged. Defaults to None.
    """
    if time:
        hour, minute = time
        m_args = f"toPersonId={user}, text={message}"
        sched.add_job(api.messages.create, "cron", hour=hour, minute=minute, kwargs=m_args)
    else:
        api.messages.create(toPersonId=user, text=message)


def ping_all(message=None):
    """Ping all users in the users data file.

    Iters through the list of users and sends them a message

    Args:
        message (str, optional): Message to send all users. Defaults to None.
    """
    users_to_ping = load_users(file=True)["users"]
    for user in users_to_ping:
        user_info = users_to_ping[user]
        name = user_info["displayName"]
        message = message if message else f"Hello {name}, remember to send the hourly email!"
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


def get_hour_range(shift_start, shift_end):
    hour_list = []
    s_start = datetime.datetime.strptime(shift_start, "%H:%M").time()
    s_end = datetime.datetime.strptime(shift_end, "%H:%M",).time()
    add_start = True
    while s_start.hour != s_end.hour:
        # Add shift start
        if add_start:
            hour_list.append(((s_start.hour - 1),55))
            add_start = False
        hour_list.append((s_start.hour, 55))
        if s_start.hour < 23:
            s_start = datetime.time((s_start.hour + 1))
        else:
            s_start = datetime.time(0)
            
    return hour_list


def schedule_subscription():
    stored_users = load_users()
    for user in stored_users["users"]:
        subscription = stored_users["users"][user]["subscription"]
        shift_start = subscription["shiftstart"]
        shift_end = subscription["shiftend"]
        hour_range = get_hour_range(shift_start, shift_end)

        for day in subscription:
            if subscription[day]:
                day_num = day.split("day")[-1]
                invalid = ["shiftstart", "shiftend"]
                if day_num not in invalid:
                    for f_hour, f_min in hour_range:
                        sched.add_job(ping_all, "cron",
                                      day_of_week=day_num,
                                      hour=f_hour,
                                      minute=f_min,
                                      misfire_grace_time=9000)


schedule_subscription()

pprint(sched.get_jobs())


# Schedule ping times
# hours = []
# for h in range(21, 24):
#     hours.append(h)
# for h in range(6):
#     hours.append(h)
# for hour in hours:
#     sched.add_job(ping_all, "cron", hour=hour, minute=55)
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
# def days():
#     day = ["Sunday", "Monday", "Tuesday", "Wednesday",
#            "Thursday", "Friday", "Saturday"]
#     dayid = [f"day{num}" for num in range(7)]
#     day_dict = dict(zip(dayid, day))
#     day_list = []
#     for d_id in day_dict:
#         day_list.append(Toggle(day_dict[d_id], d_id))
#     return day_list


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
    return None


def get_attachment_actions(attachmentid):
    headers = {'content-type': 'application/json; charset=utf-8',
               'authorization': f'Bearer {teams_token}'}
    url = f'{baseurl}/attachment/actions/{attachmentid}'
    response = requests.get(url, headers=headers)
    return response.json()


# check attachmentActions:created webhook to handle any card actions
def handle_cards(api, incoming_msg):
    message = get_attachment_actions(incoming_msg["data"]["id"])
    # Update people to notify file
    update_file(user=message["personId"], data=message["inputs"])
    remove_message(message["messageId"])
    return "Form received!"

######


# Add new commands to the box.
bot.add_command("/me", "*", get_user_info)
bot.add_command('attachmentActions', '*', handle_cards)
bot.add_command("/unsubscribe", "I will stop pinging you", unsubscribe)
bot.add_command("/subscribe", "I will ping you at a specified time", subscribe)
bot.add_command("/pingall", "*", ping_all_users)
bot.add_command("/listsubs", "This will give you a list of all the people who will be pinged", list_subscribers)
# bot.add_command("/t", "test", days)
bot.add_command("/card", "sends sub card", sub_card)
bot.add_command("/clean", "Removes all the meessages in the conversation", remove_all_messages)


if __name__ == "__main__":
    bot.set_help_message("Hello, my name is Hermes! You can use the following commands:\n")
    # Run Bot
    bot.run(host="localhost", port=8080)
