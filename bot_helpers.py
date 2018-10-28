import tweepy 
from credentials import *
import json
import warnings
#spacy has a really annoying warning I'm getting rid of here
warnings.filterwarnings("ignore")
import spacy
import random

#Twitter bot helpers 
#A variety of functions used in tweet_bot.py 

# Authenticate 
print("Authenticating...")
try:
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)
    api = tweepy.API(auth)
    print("Successfully authenticated!\n")
except tweepy.TweepError as e:
    print("Authentication failed, aborting")
    print(e)

print("Loading EN NLP model...")
nlp = spacy.load('en')
print("Loaded model!")

print("Loading CMU course data...")
with open('spring2019classes.json') as f:
        data = json.load(f)
print("Data loaded!\n")

ongoing_conversations = []

#########################################################################
# Check for new tweets that fit the query and return a list of any that
# are found.
#########################################################################
def check_for_tweets(query, searched_tweets, max_tweets, last_id):
    new_tweets = []
    reply_tweets = []

    try:
        new_tweets = api.search(q=query, count=max_tweets, since_id=str(last_id), tweet_mode="extended")
        if new_tweets:
            print("\nFound {} new Tweet(s)\n".format(len(new_tweets)))
            searched_tweets.extend(new_tweets)
            last_id = new_tweets[-1].id

    except tweepy.TweepError as e:
        print("Error querying Tweets, aborting") 
        print(e)

    return new_tweets, searched_tweets, last_id

def get_class_by_num(num, user_history):
    starting_phrases = ["In that case, you'll like ", "You might like ", "You could try ", "Well, people like "]
    response = ''
    key_length = 0
    for key in data:
        if num in key and key not in user_history['badclasses']:
            hyphenated = key[0:2] + '-' + key[2:5]
            response = random.choice(starting_phrases) + hyphenated + " " + data[key]['name'] + ". Check it out: https://www.cmucoursefind.xyz/courses/" + hyphenated
            user_history['badclasses'].append(key)
            break
        key_length += 1
    if response == '':
        response = "Wow, there are " + str(key_length) + " classes and you can't take any of them! Sucks to be you 😆"

    return response 

def get_class_by_place(place):
    token_place = nlp(place)
    possible_places = nlp(u'Rwanda Kigali Pittsburgh Qatar New York Adelaide Australia Pennsylvania Doha California Washington')

    closest = ''
    most_sim = 0

    for token in possible_places:
        sim = token.similarity(token_place)
        if sim > most_sim:
            most_sim = sim
            closest = token.text

    if most_sim > 0.8:
        response = "Okay, there are some options in " + place
    else :
        response = place + " is pretty close to " + closest
    return response


#########################################################################
# Create a response given a tweet's text and user. Check for previous
# conversation with the user and use information from that, if applicable. 
#########################################################################
def generate_reponse(tweet_text, user):
    user_history = {}
    filename = user + '.json'
    response = ''

    if user not in ongoing_conversations:
        print("New user: @{}".format(user))
        ongoing_conversations.append(user)
        user_history['badclasses'] = []
    else:
        print("Known user: @{}".format(user))
        with open(filename) as f:
            user_history = json.load(f)

    doc = nlp(tweet_text)

    places = []
    times = []
    interests = []
    numbers = []

    for ent in doc.ents:
        if ent.label_ == 'GPE':
            places.append(ent.text)
        elif ent.label_ == 'TIME':
            times.append(ent.text)
        elif ent.label_ == 'CARDINAL':
            numbers.append(ent.text)

    if 'waiting' in user_history:
        # we were waiting for a response from the user
        waiting_for = user_history['waiting']

        if waiting_for == 'num':
            # waiting for the user's fav number
            if len(numbers) > 0:
                num = numbers.pop()
                response = get_class_by_num(num, user_history)
                user_history['waiting'] = 'NONE'
                user_history['responded'] = True
            else:
                response = "That's a weird number 🤔 Why don't you give an actual number less than 1000 this time, buko?"
                user_history['waiting'] = 'num'

        elif waiting_for == 'place':
            # waiting for the user's fav place
            if len(places) > 0:
                place = places.pop()
                response = get_class_by_place(place)
                user_history['waiting'] = 'NONE'
                user_history['responded'] = True
            else:
                possible_responses = ["A real SPECIFIC place. Like New York is a specific place. The ocean is not. You can do better than this!",
                                      "Well, I need a specific place. Surely you can manage that...",
                                      "A place on 🌎 like a city or country would be most helpful...",
                                      "How about your favorite city?"]
                response = random.choice(possible_responses)
                user_history['waiting'] = 'place'

    else:
        user_history['waiting'] = 'place'

        with open(filename, 'w') as o:
            json.dump(user_history, o)
        response = "Okay, what's your favorite number less than 1000?"

    return response


#########################################################################
# Process the contents of each tweet and create a response for each
#########################################################################
def make_tweet_responses(tweets):
    responses = []
    recipients = []
    for status in tweets:
        id = status.id_str
        name = status.author.screen_name
        text = status.full_text
        print("Processing Tweet {} from @{} with contents \'{}\'".format(id, name, text))
        recipients.append((name, id))
        response = generate_reponse(text, name)
        responses.append(response)
    
    return responses, recipients

#########################################################################
# Send a response to each corresponding recipient
#########################################################################
def respond_to_tweets(responses, recipients):
    ind = 0
    for response in responses:
        user, id_str = recipients[ind]
        response_tweet = api.update_status(response + ' @' + user, id_str)
        print("Sent response to @{} for Tweet id {}".format(user, id_str))
        ind += 1




print(generate_reponse("hey, I want to take a class", 'jimbo'))

print(generate_reponse("I've been to London, so how about that?", 'jimbo'))