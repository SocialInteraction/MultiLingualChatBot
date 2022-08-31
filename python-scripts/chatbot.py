import requests, json, uuid

language_dict = {"as": "Assamese", "bn": "Bangla", "en": "English", "gu": "Gujarati", "hi": "Hindi", "kn": "Kannada",
                 "ml": "Malayalam", "mr": "Marathi", "or": "Odia", "pa": "Punjabi", "ta": "Tamil", "te": "Telugu",
                 "ur": "Urdu"}

def esc(code):
        return f'\033[{code}m'

def listen(sender_id, callback_url, chatbot_tracker_url, rasa_headers):
    response_text = {}
    chatbot_slots = {}
    stop_bot = False
    pause_bot = False
    get_response = requests.get(url=callback_url, params={'sender': sender_id})

    if get_response.text!='':
        chatbot_response = json.loads(get_response.text)
    else:
        chatbot_response = {}

    if 'custom' in chatbot_response:
        response_text['recipient_id'] = chatbot_response['recipient_id']
        response_text['text'] = chatbot_response['custom']['text']

        if chatbot_response['custom'].get('pause') == True:
            pause_bot = True
        
        if chatbot_response['custom'].get('stop') == True:
            stop_bot = True
    else:
        response_text = chatbot_response

    tracker_res = requests.get(url=chatbot_tracker_url, headers=rasa_headers)
    chatbot_slots = json.loads(tracker_res.text)['slots']

    return (response_text, stop_bot, pause_bot, chatbot_slots)

def talk_and_listen(sender_id, chatbot_url, callback_url, chatbot_tracker_url, rasa_headers, data_to_be_passed):
    response_text = {}
    chatbot_slots = {}
    stop_bot = False
    pause_bot = False
    res = requests.post(chatbot_url, data=json.dumps(data_to_be_passed))

    if res.text=='success':
        get_response = requests.get(url=callback_url, params={'sender': sender_id})
        chatbot_response = json.loads(get_response.text)
        request_failed = False
    else:
        request_failed = True
        return (response_text, request_failed, stop_bot, chatbot_slots)

    if 'custom' in chatbot_response:
        response_text['recipient_id'] = chatbot_response['recipient_id']
        response_text['text'] = chatbot_response['custom']['text']

        if chatbot_response['custom'].get('pause') == True:
            pause_bot = True
        
        if chatbot_response['custom'].get('stop') == True:
            stop_bot = True
    else:
        response_text = chatbot_response

    tracker_res = requests.get(url=chatbot_tracker_url, headers=rasa_headers)
    chatbot_slots = json.loads(tracker_res.text)['slots']

    return (response_text, request_failed, stop_bot, pause_bot, chatbot_slots)

def translate(from_lang, to_lang, text, url, headers):
    if from_lang=='en' and to_lang=='en':
        return None
    
    if len(text)>65:
        print(esc('31;1;4') + "Text too big to translate" + esc(0))

    translator_params = {'api-version': '3.0',
                         'from': from_lang,
                         'to': [to_lang]}
    body = [{'text': text}]
    request = requests.post(url, params=translator_params, headers=headers, json=body)
    non_english_response_text = request.json()
    
    return non_english_response_text[0]['translations'][0]['text']

def print_responses(en_text, language_choice, url, headers):
    print(esc('31;1;4') + "English response: " + en_text + esc(0))
    non_english_response_text = translate('en', language_choice, en_text, url, headers)
    
    if non_english_response_text is not None:
        print(esc('31;4;4')+language_dict[language_choice]+" response: "+non_english_response_text+esc(0))


def start_conversation(username='default', language_choice='en'):
    rasa_headers = {'Content-type': "application/json"}
    callback_params = {"output_channel": "latest"}
    chatbot_url = "http://0.0.0.0:5005/webhooks/callback/webhook"
    intent_trigger_url = "http://localhost:5005/conversations/{conversation_id}/trigger_intent".format(conversation_id=username)
    callback_url = "http://localhost:5034/bot"
    chatbot_tracker_url = "http://localhost:5005/conversations/{conversation_id}/tracker".format(conversation_id=username)
    
    translator_key = 'Azure Translator Resource Key'
    translator_endpoint = 'https://api.cognitive.microsofttranslator.com/'
    azure_location = 'centralindia'
    translator_path = '/translate'
    translator_url = translator_endpoint + translator_path
    translator_headers = {'Ocp-Apim-Subscription-Key': translator_key,
                          'Ocp-Apim-Subscription-Region': azure_location,
                          'Content-type': 'application/json',
                          'X-ClientTraceId': str(uuid.uuid4())}

    print("\nBot started\n")

    if username=='default':
        initial_data = {"name": "EXTERNAL_greet",
                        "entities": {"name": 'default',
                                     "name_provided": "false"}}
    else:
        initial_data = {"name": "EXTERNAL_greet",
                        "entities": {"name": username,
                                     "name_provided": "true"}}

    response_text = {}
    stop_bot = False
    pause_bot = False
    chatbot_slots = {}

    res = requests.post(url=intent_trigger_url, data=json.dumps(initial_data), params=callback_params, headers=rasa_headers)
    response_text = json.loads(res.text)['messages'][0]
    print_responses(response_text['text'], language_choice, translator_url, translator_headers)

    tracker_res = requests.get(url=chatbot_tracker_url, headers=rasa_headers)
    chatbot_slots = json.loads(tracker_res.text)['slots']

    while(True):
        if stop_bot==True:
            return {}
        
        if pause_bot==True:
            break

        user_utterance = input()

        if user_utterance=="/stop":
            return {}
        
        if language_choice!='en':
            user_utterance = translate(language_choice, 'en', user_utterance, translator_url, translator_headers)

        data_to_be_passed={
            "sender": username,
            "message": user_utterance}

        response_text_new, stop_bot, pause_bot, chatbot_slots = listen(username, callback_url, chatbot_tracker_url, rasa_headers)

        if stop_bot!=True and pause_bot!=True:
            response_text, request_failed, stop_bot, pause_bot, chatbot_slots = talk_and_listen(username, chatbot_url, callback_url, chatbot_tracker_url, rasa_headers, data_to_be_passed)
        else:
            response_text = response_text_new
            request_failed=False

        if request_failed == True:
            break

        if "buttons" in response_text:
            print("\nSelect what you meant by typing Yes or No")
            print(response_text["buttons"][0]["title"] + ": " + response_text["buttons"][0]["payload"])
            print(response_text["buttons"][1]["title"] + ": " + response_text["buttons"][1]["payload"] + "\n")
            choice = input()

            if choice == response_text["buttons"][0]["title"].casefold():
                data_to_be_passed={
                    "sender": username,
                    "message": response_text["buttons"][0]["payload"]}
            elif choice == response_text["buttons"][1]["title"].casefold():
                data_to_be_passed={
                    "sender": username,
                    "message": response_text["buttons"][1]["payload"]}

            response_text, request_failed, stop_bot, pause_bot, chatbot_slots = talk_and_listen(username, chatbot_url, callback_url, chatbot_tracker_url, rasa_headers, data_to_be_passed)
            
            if request_failed==True:
                break

        print_responses(response_text['text'], language_choice, translator_url, translator_headers)
    
    return chatbot_slots

if __name__=="__main__":
    start_conversation()