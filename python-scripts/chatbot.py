import requests, json, uuid
import azure.cognitiveservices.speech as speechsdk

azure_speech_key = "azure speech key"               # replace this with an azure speech resource key
azure_translator_key = "azure translator key"       # replace this with an azure translator resource key

language_dict = {"as": {"name": "Assamese", "voice": None},
                 "bn": {"name": "Bengali", "voice": "bn-IN-TanishaaNeural"},
                 "en": {"name": "English", "voice": "en-IN-NeerjaNeural"},
                 "gu": {"name": "Gujarati", "voice": "gu-IN-DhwaniNeural"},
                 "hi": {"name": "Hindi", "voice": "hi-IN-SwaraNeural"},
                 "kn": {"name": "Kannada", "voice": "kn-IN-SapnaNeural"},
                 "ml": {"name": "Malayalam", "voice": None},
                 "mr": {"name": "Marathi", "voice": "mr-IN-AarohiNeural"},
                 "or": {"name": "Odia", "voice": None},
                 "pa": {"name": "Punjabi", "voice": None},
                 "ta": {"name": "Tamil", "voice": "ta-IN-PallaviNeural"},
                 "te": {"name": "Telugu", "voice": "te-IN-ShrutiNeural"},
                 "ur": {"name": "Urdu", "voice": None}}

# returns escape sequence to format output text
def esc(code):
        return f'\033[{code}m'

"""Reads the current data in the callback server and sets pause_bot and stop_bot accordingly.
It also queries the chatbot for its current slot values."""
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

"""Sends the user input to the callback server and then does the same as the listen method."""
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
        return non_english_response_text
    
    return en_text

def speech_to_text(language_choice):
    speech_config = speechsdk.SpeechConfig(subscription=azure_speech_key, region="centralindia")
    speech_config.speech_recognition_language = f"{language_choice}-IN"
    audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)
    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
    print("Speak into your microphone")
    speech_recognition_result = speech_recognizer.recognize_once_async().get()

    if speech_recognition_result.reason == speechsdk.ResultReason.RecognizedSpeech:
        print("Text recognized: {}".format(speech_recognition_result.text))
        return speech_recognition_result.text
    elif speech_recognition_result.reason == speechsdk.ResultReason.NoMatch:
        print("No speech could be recognized: {}".format(speech_recognition_result.no_match_details))
    elif speech_recognition_result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = speech_recognition_result.cancellation_details
        print("Speech Recognition canceled: {}".format(cancellation_details.reason))
        if cancellation_details.reason == speechsdk.CancellationReason.Error:
            print("Error details: {}".format(cancellation_details.error_details))
    
    return '/stop'

def text_to_speech(text, language_choice):
    speech_config = speechsdk.SpeechConfig(subscription=azure_speech_key, region="centralindia")
    audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=True)
    speech_config.speech_synthesis_voice_name=language_dict[language_choice]['voice']
    speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
    speech_synthesis_result = speech_synthesizer.speak_text_async(text).get()

    if speech_synthesis_result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = speech_synthesis_result.cancellation_details
        print("Speech synthesis canceled: {}".format(cancellation_details.reason))
        if cancellation_details.reason == speechsdk.CancellationReason.Error:
            if cancellation_details.error_details:
                print("Error details: {}".format(cancellation_details.error_details))

def start_conversation(username='default', language_choice='en', speech=False):
    rasa_headers = {'Content-type': "application/json"}
    callback_params = {"output_channel": "latest"}
    chatbot_url = "http://0.0.0.0:5005/webhooks/callback/webhook"
    intent_trigger_url = "http://localhost:5005/conversations/{conversation_id}/trigger_intent".format(conversation_id=username)
    callback_url = "http://localhost:5034/bot"
    chatbot_tracker_url = "http://localhost:5005/conversations/{conversation_id}/tracker".format(conversation_id=username)
    
    translator_key = azure_translator_key
    translator_endpoint = 'https://api.cognitive.microsofttranslator.com/'
    azure_location = 'centralindia'
    translator_path = '/translate'
    translator_url = translator_endpoint + translator_path
    translator_headers = {'Ocp-Apim-Subscription-Key': translator_key,
                          'Ocp-Apim-Subscription-Region': azure_location,
                          'Content-type': 'application/json',
                          'X-ClientTraceId': str(uuid.uuid4())}

    print("\nBot started\n")

    """For the bot to start the conversation on its own, a trigger intent is sent to the bot.
    The parameters of the trigger intent are defined below."""
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

    # the trigger intent is sent to the chatbot's server
    res = requests.post(url=intent_trigger_url, data=json.dumps(initial_data), params=callback_params, headers=rasa_headers)
    response_text = json.loads(res.text)['messages'][0]
    text_to_be_spoken =  print_responses(response_text['text'], language_choice, translator_url, translator_headers)

    if speech:
        text_to_speech(text=text_to_be_spoken, language_choice=language_choice)

    tracker_res = requests.get(url=chatbot_tracker_url, headers=rasa_headers)
    chatbot_slots = json.loads(tracker_res.text)['slots']

    while(True):
        if stop_bot==True:
            return {}
        
        if pause_bot==True:
            break

        if speech:
            user_utterance = speech_to_text(language_choice=language_choice)
        else:
            user_utterance = input()

        if user_utterance=="/stop":
            return {}
        
        if language_choice!='en':
            user_utterance = translate(language_choice, 'en', user_utterance, translator_url, translator_headers)

        data_to_be_passed={
            "sender": username,
            "message": user_utterance}

        """The current data in the callback server is checked before sending the user input to it.
        If the current data has stop_bot or pause_bot set then the user input is not sent since the bot will pause/stop."""

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

        text_to_be_spoken = print_responses(response_text['text'], language_choice, translator_url, translator_headers)

        if speech:
            text_to_speech(text=text_to_be_spoken, language_choice=language_choice)
    
    return chatbot_slots

if __name__=="__main__":
    start_conversation()