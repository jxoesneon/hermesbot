import os
import dotenv
import json
import requests
import webexteamsbot
from apscheduler.schedulers.background import BackgroundScheduler as Scheduler


filepath = "peopletonotify.json"


# API vars
baseurl = "https://api.ciscospark.com/v1"
current_user = None

# Retrieve required details from environment variables
dotenv.load_dotenv()
bot_email = os.getenv("TEAMS_BOT_EMAIL")
teams_token = os.getenv("TEAMS_BOT_TOKEN")
bot_url = os.getenv("TEAMS_BOT_URL")
print(bot_url)
bot_app_name = os.getenv("TEAMS_BOT_APP_NAME")

# Create a Bot Object
bot = webexteamsbot.TeamsBot(bot_app_name,
                             teams_bot_token=teams_token,
                             teams_bot_url=bot_url,
                             teams_bot_email=bot_email)


# ####### File Management ########
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
    if current_user["id"] in stored_users["users"]:
        return True
    else:
        return False


def update_file(remove=False):
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


def get_info(personId):
    url = f"{baseurl}/people/{personId}"
    payload = {}
    headers = {'Authorization': f'Bearer {teams_token}'}
    response = requests.request("GET", url, headers=headers, data=payload)
    return response.json()


def get_user_info(incoming_msg):
    personId = incoming_msg.personId
    url = f"{baseurl}/people/{personId}"
    payload = {}
    headers = {'Authorization': f'Bearer {teams_token}'}
    response = requests.request("GET", url, headers=headers, data=payload)
    global current_user
    current_user = response.json()
    # result = str()
    # for key, value in current_user.items():
    #     result = result + f"{key}:{value}\n"
    return str(current_user)


def ping(user, message="Hi"):
    url = f"{baseurl}/messages/"
    headers = {'Authorization': f'Bearer {teams_token}'}
    payload = {'toPersonId': f"{user}", 'text': f"{message}"}
    requests.request("POST", url, headers=headers, data=payload)


def ping_single_user(user, message=None, time=None):
    if time:
        pass
    else:
        ping(user, message)


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
        user_data = get_info(sub)
        num += 1
        name = user_data["displayName"]
        email = user_data["emails"][0]
        user_entry = f"{num})\t{name} - {email}"
        subList = subList + user_entry + "\n\n"
    return subList


# Add new commands to the box.
bot.add_command("/me", "*", get_user_info)
bot.add_command("/unsubscribe", "I will stop pinging you", unsubscribe)
bot.add_command("/subscribe", "I will ping you at a specified time", subscribe)
bot.add_command("/pingall", "*", ping_all_users)
bot.add_command("/listsubs", "This will give you a list of all the people who will be pinged", list_subscribers)


if __name__ == "__main__":
    bot.set_help_message("Hello, my name is Hermes! You can use the following commands:\n")
    # Run Bot
    bot.run(host="localhost", port=8080)
