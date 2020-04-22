# Prod Imports
import os
import json
import datetime
import requests
import webexteamsbot
from webexteamssdk import WebexTeamsAPI
from apscheduler.schedulers.background import BackgroundScheduler as Scheduler

# Dev imports
import dotenv
from pyngrok import ngrok
from pprint import pprint


class Hermess():
    def __init__(self):
        """Webex Teams notification bot for the RCSS Graveyard Team
        
        Intended to notify agents on an hourly basis on the agent's schedule to remind them to send an email to their managers.
        
        Usage:
            Just run the hermes.py to start the bot locally, then look for it on Webex Teams, either with the name: HermessRCSS or with the full name: hermesrcss@webex.bot 
            After that, send the '/subscribe' command to set up the notification times.
        """        
        self.current_user = None  # Define current interacting user
        self.filepath = "peopletonotify.json"  # Define where to find the users file
        self.baseurl = "https://api.ciscospark.com/v1"  # API vars
        # Retrieve required details from environment variables
        dotenv.load_dotenv()
        # Open a HTTP tunnel on the default port 8080
        self.start_local_server()
        # Get enviroment details
        self.bot_email = os.getenv("TEAMS_BOT_EMAIL")
        self.teams_token = os.getenv("TEAMS_BOT_TOKEN")
        self.bot_app_name = os.getenv("TEAMS_BOT_APP_NAME")
        self.api = WebexTeamsAPI(access_token=self.teams_token)  # Start API
        # Create the Bot Object
        self.bot = webexteamsbot.TeamsBot(self.bot_app_name,
                                          teams_bot_token=self.teams_token,
                                          teams_bot_url=self.bot_url,
                                          teams_bot_email=self.bot_email,
                                          webhook_resource_event=[{"resource": "messages",
                                                                   "event": "created"},  # Handles Messages
                                                                  {"resource": "attachmentActions",
                                                                   "event": "created"}])  # Handles Adaptive cards
        self.bot.set_help_message("Hello, my name is Hermes! You can use the following commands:\n")
        self.add_commands()
        self.clear_screen()
        self.init_users_file()
        # Create the scheduler
        self.sched = Scheduler({'apscheduler.timezone': 'America/Costa_Rica'})
        self.sched.remove_all_jobs()
        self.sched.start()  # Start the scheduler
        self.schedule_subscriptions()
        self.bot.run(host="localhost", port=8080)  # Run Bot

    def clear_screen(self):
        """Function to clear the screen

        This function aims to clear the screen independently of the OS the script
        is being run on.
        """
        os.system("cls" if os.name == "nt" else "clear")

    def start_local_server(self):
        """Start a local Ngrok webhook for the bot
        
        This will check for a preexisting Ngrook server and raise an exeption if it finds one as only one instance can be running on the free version of Ngrok
        
        Raises:\n
            SystemExit: When it finds a previous Ngrook service running.
        """        
        try:
            self.bot_url = ngrok.connect(port=8080, proto="http")
            print(self.bot_url)
        except Exception:
            self.clear_screen()
            print("You need to close the current terminal, otherwise the HTTP tunnel wont connect")
            input("Press enter to exit.\n")
            raise SystemExit

    # --------- File Management --------- #

    def init_users_file(self):
        try:
            with open(self.filepath) as _:
                print("Users file found!")
        except FileNotFoundError:
            print("No users file found, creating a new one..")
            with open(self.filepath, "w+") as _:
                print("File created!")

    def write_to_file(self, data, filepath=None):
        """Write data to a file

        Simple function to write string data to a file in Json format.

        Args:
            data (str): A string containing the data to be written to a file
            filepath (str, optional): String containing the relative or full path to the file the data is going to be written to. Defaults to filepath.
        """
        with open(self.filepath, "w+") as file:
            json.dump(data, file, sort_keys=True, indent=4, separators=(",", ": "))

    def get_user_info(self, incoming_msg):
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
        self.current_user = self.api.people.get(personId)
        return str(self.current_user)

    def check_user_file(self):
        """Check if the user file exist

        Sanity check to see if the users file already exists.
        If there is no users file then it proceeds to create it.
        """
        try:
            with open(self.filepath, "r+") as file:
                json.load(file)
        except FileNotFoundError:
            print("The file has not been initialized",
                  "initializing ...",
                  sep="\n")
            self.write_to_file({"users": {self.current_user.id: self.current_user.to_dict()}})
            print("done")
        except json.JSONDecodeError:
            return {}

    def load_users(self, file=False):
        """Loads the user data in the user file.

        Returns the user data as a list of personId by default or the whole user data block if the file option is set to true.

        Args:
            file (bool, optional): If True, it returns the file data instead of just the personId list. Defaults to False.

        Returns:
            str: String containing either a list of personIds or the whole user data set.
        """
        self.check_user_file()
        id_list = []
        try:
            with open(self.filepath, "r") as file:
                data = json.load(file)
            id_list.append(list(data["users"]))
            if file:
                return data
            else:
                return id_list
        except json.JSONDecodeError:
            return {}

    def user_in_file(self):
        """Check if the current user is in the users data file

        Uses the current_user's personId to see if the user has been already added to the user data file.

        Returns:
            bool: True if the current user is in the user data file, False if not.
        """
        stored_users = self.load_users()
        return True if self.current_user.id in stored_users["users"] else False

    def update_file(self, user=None, data=None, remove=False):
        r"""Update the users file with new data

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
            stored_users = self.load_users(file=True)
            if ("users" in stored_users) and (stored_users["users"]):
                # Check if user in stored users
                if user in stored_users["users"]:
                    stored_users["users"][user]["subscription"] = data
                else:
                    raise ValueError("User not found")
            else:
                stored_users = {"users": {user: data}}
            self.write_to_file(stored_users)
            return "Updated"
        elif remove:
            if self.user_in_file():
                stored_users = self.load_users(file=True)
                stored_users["users"].pop(self.current_user.id)
                name = self.current_user.displayName
                email = self.current_user.emails[0]
                self.write_to_file(stored_users)
                return f"I have removed you {name} - {email}"
            else:
                return "You were not subscribed ..."
        elif self.user_in_file():
            return "User already in file"
        else:
            stored_users = self.load_users(file=True)
            stored_users["users"][self.current_user.id] = self.current_user
            self.write_to_file(stored_users)
            user = self.current_user.displayName
            return f"I've added you, {user}"

    # --------- Adaptive Card --------- #
    def card_subscription(self):
        with open("subscription.json") as file:
            card_json = json.load(file)
        return card_json

    def subscription_card(self, personId):
        user = personId
        txt = "If you are seeing this message you might be using teams in a web browser or an older version of the app, please switch to the desktop app or update your desktop app to subscribe. You can get the latest version here:\n\nhttps://www.webex.com/downloads"
        card = self.card_subscription()
        attachment = {'contentType': 'application/vnd.microsoft.card.adaptive',
                      'content': card}
        self.api.messages.create(toPersonId=user, text=txt, attachments=[attachment])
        return ""

    # --------- Subscriptions --------- #
    def subscribe(self, incoming_msg):
        self.get_user_info(incoming_msg)
        self.update_file(user=self.current_user.id, data=self.current_user.to_dict())
        self.subscription_card(self.current_user.id)
        return "Please fill out the subscription form."

    def unsubscribe(self, incoming_msg):
        self.get_user_info(incoming_msg)
        return self.update_file(remove=True)

    # --------- Message Management --------- #
    def get_attachment_actions(self, attachmentid):
        headers = {"content-type": "application/json; charset=utf-8",
                   "authorization": f"Bearer {self.teams_token}"}
        url = f"{self.baseurl}/attachment/actions/{attachmentid}"
        response = requests.get(url, headers=headers)
        return response.json()

    # check attachmentActions:created webhook to handle any card actions
    def handle_cards(self, api, incoming_msg):
        message = self.get_attachment_actions(incoming_msg["data"]["id"])
        # Update people to notify file
        self.update_file(user=message["personId"], data=message["inputs"])
        self.remove_messages(incoming_msg, messageId=message["messageId"])
        self.update_schedules()
        return "Form received!"

    # --------- Ping Functions --------- #
    def ping_user(self, personId, message=None):
        message = message if message else f"Hello, remember to send the hourly email!"
        self.api.messages.create(toPersonId=personId, text=message)

    def ping_all(self, message=None):
        """Ping all users in the users data file.

        Iters through the list of users and sends them a message

        Args:
            message (str, optional): Message to send all users. Defaults to None.
        """
        users_to_ping = self.load_users(file=True)["users"]
        for user in users_to_ping:
            self.ping_user(user, message=message)

    # --------- User Functions --------- #
    def ping_all_users(self, incoming_msg):
        message = f"Broadcast message requestesd by {incoming_msg.personEmail}"
        users_to_ping = self.load_users()["users"]
        responses = []
        for user in users_to_ping:
            self.api.messages.create(toPersonId=user, text=message)
            responses.append(user)
        return f"Ping sent to {len(users_to_ping)} users."

    def remove_messages(self, incoming_msg, messageId=None):
        if messageId:
            try:
                self.api.messages.delete(messageId)
            except Exception as e:
                pprint(e)
        else:
            # List all the messages the bot and the user share
            messages_with_user = self.api.messages.list(roomId=incoming_msg.roomId)
            for message in messages_with_user:
                # Delete the messages
                try:
                    self.api.messages.delete(message.id)
                except Exception:
                    pass

    def list_subscribers(self, _):
        subscribers = self.load_users()
        subList = ""
        num = 0
        for sub in subscribers["users"]:
            user_data = self.api.people.get(sub)
            num += 1
            name = user_data.displayName
            email = user_data.emails[0]
            user_entry = f"{num})\t{name} - {email}"
            subList = subList + user_entry + "\n\n"
        return subList

    # --------- Scheduler --------- #
    def get_hour_range(self, shift_start, shift_end):
        hour_list = []
        s_start = datetime.datetime.strptime(shift_start, "%H:%M").time()
        s_end = datetime.datetime.strptime(shift_end, "%H:%M",).time()
        add_start = True
        while s_start.hour != s_end.hour:
            # Add shift start
            if add_start:
                if s_start.hour == 0:
                    hour_list.append((23, 55))
                else:
                    hour_list.append(((s_start.hour - 1), 55))
                add_start = False
            hour_list.append((s_start.hour, 55))
            if s_start.hour < 23:
                s_start = datetime.time((s_start.hour + 1))
            else:
                s_start = datetime.time(0)
        return hour_list

    def schedule_subscriptions(self):
        self.check_user_file()
        stored_users = self.load_users()
        if stored_users:
            for user in stored_users["users"]:
                name = stored_users["users"][user]["nickName"].split(" ")[0] if "nickName" in stored_users["users"][user] else stored_users["users"][user]["firstName"]
                if "subscription" in stored_users["users"][user]:
                    subscription = stored_users["users"][user]["subscription"]
                    shift_start = subscription["shiftstart"]
                    shift_end = subscription["shiftend"]
                    hour_range = self.get_hour_range(shift_start, shift_end)
                    for day in subscription:
                        if subscription[day]:
                            day_num = day.split("day")[-1]
                            invalid = ["shiftstart", "shiftend"]
                            if day_num not in invalid:
                                for time in hour_range:
                                    f_hour, f_min = time
                                    self.sched.add_job(self.ping_user, "cron",
                                                       args=[user],
                                                       kwargs={"message": f"Hello {name}, remember to send the hourly email!"},
                                                       day_of_week=day_num,
                                                       hour=f_hour,
                                                       minute=f_min,
                                                       misfire_grace_time=9000,
                                                       replace_existing=True)
                else:
                    self.sched.add_job(self.ping_user,
                                       "cron",
                                       args=[user],
                                       kwargs={"message": f"Hi {name}, looks like you have not updated your subscription, plese reply with /subscribe to update it."},
                                       hour=22,
                                       misfire_grace_time=9000)
        else:
            pass

    def update_schedules(self):
        self.sched.remove_all_jobs()
        self.schedule_subscriptions()

    # --------- Bot --------- #
    def add_commands(self):
        self.bot.add_command("attachmentActions", "*", self.handle_cards)
        self.bot.add_command("/unsubscribe", "I will stop pinging you", self.unsubscribe)
        self.bot.add_command("/subscribe", "I will ping you at a specified time", self.subscribe)
        self.bot.add_command("/pingall", "*", self.ping_all_users)
        self.bot.add_command("/listsubs", "This will give you a list of all the people who will be pinged", self.list_subscribers)
        self.bot.add_command("/clean", "Removes all the meessages in the conversation", self.remove_messages)


if __name__ == "__main__":
    Hermess()
