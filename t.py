import json
from hermes import current_user, get_user_info


def write_to_file(data):
    with open("peopletonotify.json", "w+") as file:
        file.write(json.dumps(data))

def check_user_file():
    try:
        with open("peopletonotify.json", "r+") as file:
            number_of_users = len(json.load(file))
    except FileNotFoundError:
        print("The file has not been initialized",
              "initializing ...",
              sep="\n")
        write_to_file(json.dumps(current_user))
        print("done")
    

check_user_file()
