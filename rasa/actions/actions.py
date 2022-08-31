from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import FollowupAction, Restarted, BotUttered, SlotSet, AllSlotsReset

class ActionGreet(Action):
    def name(self) -> Text:
        return "action_greet"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        name_provided = next(tracker.get_latest_entity_values("name_provided"), "false")
        name = next(tracker.get_latest_entity_values("name"), "default")
        
        if name_provided=='true' and name!='default':
            dispatcher.utter_message(f"Hi {name}! How may I help you")
        else:
            return [Restarted(),
                    AllSlotsReset(),
                    SlotSet(key='name_provided', value=False),
                    BotUttered(text="Hi, nice to meet you! What's your name"),
                    FollowupAction(name='name_form')]

        return []

class ActionBatteryLow(Action):
    def name(self) -> Text:
        return "action_battery_low"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        dispatcher.utter_message(text="Sorry, my battery is running low. I need to recharge now!",
                                 json_message={'pause': True,
                                                'text': "Sorry, my battery is running low. I need to recharge now!"})

        return []
