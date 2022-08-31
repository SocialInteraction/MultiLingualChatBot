"""To set the state machine to interrupt the conversation after 60s,
uncomment the lines to start and join the battery_thread."""

import rospy
import smach
import chatbot
import requests, json
from threading import Thread
from time import sleep

# returns escape sequence to format output text
def esc(code):
        return f'\033[{code}m'

class Conversing(smach.State):
    def __init__(self):
        super().__init__(outcomes=['end conversation', 'fetch something', 'close something', 'battery low'],
                         input_keys=['name', 'known', 'language_choice', 'speech'],
                         output_keys=['lunch', 'object_name', 'closable_object', 'name', 'known'])

    def execute(self, userdata):
        if userdata.known=='true':
            chatbot_slots = chatbot.start_conversation(username=userdata.name, language_choice=userdata.language_choice, speech=userdata.speech)
        else:
            chatbot_slots = chatbot.start_conversation(language_choice=userdata.language_choice, speech=userdata.speech)
            if chatbot_slots.get('name') is not None:
                if chatbot_slots['name'] != 'default':
                    userdata.known = 'true'
                    userdata.name = chatbot_slots['name']

        if chatbot_slots.get('battery_low'):
            return 'battery low'
        elif chatbot_slots.get('lunch_selection') is None and chatbot_slots.get('object_to_be_fetched') is not None:
            userdata.lunch = False
            userdata.object_name = chatbot_slots['object_to_be_fetched']
            return 'fetch something'
        elif chatbot_slots.get('lunch_selection') is not None and chatbot_slots.get('object_to_be_fetched') is None:
            userdata.lunch = True
            userdata.object_name = chatbot_slots['lunch_selection']
            return 'fetch something'
        elif chatbot_slots.get('object_to_be_closed') is not None:
            userdata.closable_object = chatbot_slots['object_to_be_closed']
            return 'close something'
        
        return 'end conversation'

class Fetching(smach.State):
    def __init__(self):
        super().__init__(outcomes=['conversing'],
                         input_keys=['lunch', 'object_name', 'name', 'known'])

    def execute(self, userdata):
        if userdata.known == 'true':
            if userdata.lunch==True:
                print(esc('96;1;4') + "Robot fetching lunch for " + userdata.name + ". " + "Selected lunch item: " + userdata.object_name + esc(0))
            else:
                print(esc('96;1;4') + "Robot fetching object for " + userdata.name + ". " + "Object: " + userdata.object_name + esc(0))
        else:
            if userdata.lunch==True:
                print(esc('96;1;4') + "Robot fetching lunch. Selected lunch item: " + userdata.object_name + esc(0))
            else:
                print(esc('96;1;4') + "Robot fetching object. Object: " + userdata.object_name + esc(0))
        return 'conversing'

class Closing(smach.State):
    def __init__(self):
        super().__init__(outcomes=['conversing'],
                         input_keys=['closable_object'])

    def execute(self, userdata):
        print(esc('96;1;4') + "Robot closing the following: ", userdata.closable_object + esc(0))
        return 'conversing'

class BatteryLow(smach.State):
    def __init__(self):
        super().__init__(outcomes=['charging'])

    def execute(self, userdata):
        print(esc('96;1;4') + "Robot charging" + esc(0))
        return 'charging'

def battery_low_signal(conversation_id):
    intent_trigger_url = "http://localhost:5005/conversations/{conversation_id}/trigger_intent".format(conversation_id=conversation_id)
    callback_params = {"output_channel": "latest"}
    rasa_headers = {'Content-type': "application/json"}
    battery_data = {"name": "EXTERNAL_battery_low",
                            "entities": {"battery_low": True}}

    sleep(60)

    res = requests.post(url=intent_trigger_url, data=json.dumps(battery_data), params=callback_params, headers=rasa_headers)


def main():
    rospy.init_node('robot_state_machine')

    sm = smach.StateMachine(outcomes=['end conversation', 'continue', 'charging'], input_keys=['known', 'name'])
    print("Enter if person detected is known")
    sm.userdata.known = input().casefold()
    if sm.userdata.known == 'true':
        print("Enter name")
        sm.userdata.name = input()
    
    print("\nWhich language do you want to chat in?\n\nAssamese: as\nBangla: bn\nEnglish: en\nGujarati: gu\nHindi: hi\n"
          "Kannada: kn\nMalayalam: ml\nMarathi: mr\nOdia: or\nPunjabi: pa\nTamil: ta\nTelugu: te\nUrdu: ur\n\nEnter the"
          " language code")
    sm.userdata.language_choice = input()

    if chatbot.language_dict[sm.userdata.language_choice]['voice'] is None:
        print("Speech not supported for this language")
        sm.userdata.speech = False
    else:
        print("Do you want to enable speech? Type True to enable")
        sm.userdata.speech = True if input().casefold()=='true' else False

    if sm.userdata.known=='true':
        battery_thread = Thread(target=battery_low_signal, args=[sm.userdata.name])
    else:
        battery_thread = Thread(target=battery_low_signal, args=["default"])

    #battery_thread.start()

    with sm:
        smach.StateMachine.add(label='conversing',
                               state=Conversing(),
                               transitions={'end conversation': 'end conversation',
                                            'fetch something': 'fetching',
                                            'close something': 'closing',
                                            'battery low': 'battery low'},
                               remapping={'known': 'known',
                                          'name': 'name',
                                          'language_choice': 'language_choice',
                                          'speech': 'speech'})
        
        smach.StateMachine.add(label='fetching',
                               state=Fetching(),
                               transitions={'conversing': 'conversing'},
                               remapping={'lunch': 'lunch',
                                          'object_name': 'object_name',
                                          'name': 'name',
                                          'known': 'known'})
        
        smach.StateMachine.add(label='closing',
                               state=Closing(),
                               transitions={'conversing': 'conversing'},
                               remapping={'closable_object': 'closable_object'})
        
        smach.StateMachine.add(label='battery low',
                               state=BatteryLow(),
                               transitions={'charging': 'charging'})

    outcome = sm.execute()
    print(esc('96;1;4') + "Final outcome of state machine: " + outcome + esc(0))
    #battery_thread.join()

if __name__ == '__main__':
    main()