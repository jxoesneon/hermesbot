from pyadaptivecards.actions import Submit
from pyadaptivecards.card import AdaptiveCard
from pyadaptivecards.components import TextBlock
from pyadaptivecards.inputs import Number, Text
from webexteamssdk import WebexTeamsAPI
import json

greeting = TextBlock("Hey hello there! I am a adaptive card")
first_name = Text('first_name', placeholder="First Name")
age = Number('age', placeholder="Age")

submit = Submit(title="Send me!")

card = AdaptiveCard(body=[greeting, first_name, age], actions=[submit])

with open("subscription.json") as file:
    active = json.load(file)
    
# Create a webex teams api connection
api = WebexTeamsAPI(access_token='MmM1ZTZlYmItZWI4Zi00NzgyLTgxYzctN2E5MDYyMTNhNzJmYTNkMjQ3OGYtM2Ex_PF84_1eb65fdf-9643-417f-9974-ad72cae0e10f')
room_id = "Y2lzY29zcGFyazovL3VzL1JPT00vMWNiYWMyN2ItNjEwYi0zNjBkLThhMTMtNjYzYTIxYjFlOTA2"
# Create a dict that will contain the card as well as some meta information
attachment = {
    "contentType": "application/vnd.microsoft.card.adaptive",
    "content": active,
}
api.messages.create(roomId=room_id, text="Fallback", attachments=[attachment])
