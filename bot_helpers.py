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

    try:
        new_tweets = api.search(q=query, count=max_tweets, since_id=str(last_id), tweet_mode="extended")
        if new_tweets:
            print("\nFound {} new Tweet(s)\n".format(len(new_tweets)))
            searched_tweets.extend(new_tweets)
            last_id = new_tweets[0].id

    except tweepy.TweepError as e:
        print("Error querying Tweets, aborting") 
        print(e)

    return new_tweets, searched_tweets, last_id

#########################################################################
# Merge multi-word tokens into a single token
#########################################################################
def merge_ents(doc):
    for ent in doc.ents:
        ent.merge(ent.root.tag_, ent.text, ent.root.ent_type_)

#########################################################################
# Hyphenate a class name for use with the cmucoursefind url
#########################################################################
def hyphenate_class(key):
    return key[0:2] + '-' + key[2:5]   

#########################################################################
# Get the class from the user's information that matches all of their
# requirements 
#########################################################################
def get_class(user_history):
    starting_phrases = ["You'll definitely like ", "Given what you've said, you might like ", "You could try ", "People like you seem to like "]
    
    if 'badresponse' not in user_history:
        response = 'However, looks like your favorite number, interests, and favorite place don\'t align well with any CMU class. '
    else: 
        possible_reponses = ["Still No luck though. ", "Still nothing though 😥 ", "Still no results though... "]
        response = random.choice(possible_reponses)
    new_suggestions = ["Maybe try a new place?", "How about a different number?", "Maybe give a more specific interest?"]
    options = ['num', 'place', 'thing']
    opt = random.choice(options)
    if opt == 'num':
        response = response + new_suggestions[1]
        user_history['waiting'] = 'num'
    elif opt == 'place':
        response = response + new_suggestions[0]
        user_history['waiting'] = 'place'
    elif opt == 'thing':
        response = response + new_suggestions[2]
        user_history['waiting'] = 'thing'

    for key in user_history['potentialClasses']:
        # if key not in user_history['badclasses']:
        if data[key]['dept'] == user_history['topic'] and user_history['place'] in data[key]['place']:
            hyphenated = hyphenate_class(key)
            response = random.choice(starting_phrases) + hyphenated + " " + data[key]['name'] + ". Check it out: https://www.cmucoursefind.xyz/courses/" + hyphenated
            user_history['waiting'] = 'NONE'
            break

    if user_history['waiting'] != 'NONE':
        user_history['badresponse'] = True

    return response, user_history 

#########################################################################
# Generate the next question or the resulting class, if applicable 
#########################################################################
def get_next_question(user_history):

    response = ''
    if user_history['interactions'] > 2:
        response, user_history = get_class(user_history)
    else:
        questions = ['num', 'place', 'thing']
        number_questions = ["What's your favorite number that's less than 1000?",
                            "Pick a random number less than 1000...",
                            "Pretend you're a computer and randomly generate me a number < 1000, please."]

        place_questions = ["What's your favorite place in the whole wide 🌎?",
                            "If you could go anywhere your little heart desired, where would it be?",
                            "If you could live anywhere in the world, where would you live?"]

        thing_questions = ["What would be your favorite thing to do if you could do anything you wanted?",
                            "Either telling the truth or not, what is one of your pastimes?",
                            "What do you like to do when not doing things you are required to do?"]
        random.shuffle(questions)
        for ques in questions:
            if ques not in user_history['asked']:
                if ques == 'num':
                    response = random.choice(number_questions)
                elif ques == 'place':
                    response = random.choice(place_questions)
                elif ques == 'thing':
                    response = random.choice(thing_questions)
                user_history['waiting'] = ques
                user_history['asked'].append(ques)
                break

    if user_history['interactions'] < 1:
        "Let's start! " + response
    user_history['interactions'] = user_history['interactions'] + 1

    return response, user_history 

#########################################################################
# Create a response given a random number 
#########################################################################
def get_class_by_num(num, user_history):
    response = ''
    found = False
    user_history['potentialClasses'] = []

    for key in data:
        if num in key:
            user_history['potentialClasses'].append(key)
            found = True

    if not found:
        # use 12 instead
        for key in data:
            if '12' in key:
                user_history['potentialClasses'].append(key)
        res, user_history = get_next_question(user_history)
        response = "Well your number kinda sucks, so I picked 12. Let's move on. " + res
    else:
        res, user_history = get_next_question(user_history)
        response = "You're in luck, there's some course numbers with " + str(num) + "! " + res

    return response, user_history 

#########################################################################
# Create a response given a place
#########################################################################
def get_class_by_place(place, user_history):
    token_place = nlp(place)
    possible_places = nlp(u'Australia San Jose Rwanda Adelaide Kigali Pittsburgh Qatar New York Pennsylvania Doha California Washington')
    merge_ents(possible_places)
    closest = ''
    most_sim = 0

    for token in possible_places:
        sim = token.similarity(token_place)
        if sim > most_sim:
            most_sim = sim
            closest = token.text

    user_history['place'] = closest
    if most_sim > 0.8:
        res, user_history = get_next_question(user_history)
        response = "Okay, there are some options in " + place + ". " + res
    else :
        res, user_history = get_next_question(user_history)
        response = place + " is pretty close to " + closest + " so let's go with that. " + res

    return response, user_history

#########################################################################
# Create a response given a thing (actvity, pastime)
#########################################################################
def get_class_by_thing(thing, noun, user_history):
    token_thing = nlp(thing)
    topics = ''
    full_thing = ''
    noun = noun.lower()
    print(noun)
    found = False 
    # first try finding the exact thing in the departments 
    for topic in data['topics']:
        if noun in (topic.lower()):
            full_thing = topic
            found= True
            break

    # otherise, semantic similarity with word2vec
    if not found:
        for topic in data['topics']:
            topics = topics + topic + ' ' 

        possible_topics = nlp(topics)
        merge_ents(possible_topics)
        merge_ents(token_thing)
        closest = ''
        most_sim = 0

        for token in possible_topics:
            sim = token.similarity(token_thing)
            if sim > most_sim:
                most_sim = sim
                closest = token.text

        for topic in data['topics']:
            if closest in topic:
                full_thing = topic
                break

        user_history['topic'] = full_thing
        if most_sim > 0.8:
            res, user_history = get_next_question(user_history)
            response = "Okay, there are some interesting options in " + full_thing + ". " + res
        else :
            res, user_history = get_next_question(user_history)
            response = "That sounds a bit like " + full_thing + ". " + res
    else:
        user_history['topic'] = full_thing
        res, user_history = get_next_question(user_history)
        response = "Okay, " + full_thing + " it is. " + res
    return response, user_history

#########################################################################
# Create a response given a tweet's text and user. Check for previous
# conversation with the user and use information from that, if applicable. 
#########################################################################
def generate_reponse(tweet_text, user):
    user_history = {}
    filename = user + '.json'
    response = ''

    try:
        with open(filename) as f:
            user_history = json.load(f)
        print("Known user: @{}".format(user))

    except OSError as e:
        print("New user: @{}".format(user))
        user_history['interactions'] = 0
        user_history['asked'] = []
        user_history['potentialClasses'] = []

    doc = nlp(tweet_text)

    places = []
    times = []
    things = []
    nouns = []
    numbers = []

    for ent in doc.ents:
        if ent.label_ == 'GPE' or ent.label_ == 'LOC':
            places.append(ent.text)
        elif ent.label_ == 'TIME':
            times.append(ent.text)
        elif ent.label_ == 'CARDINAL':
            numbers.append(ent.text)

    for chunk in doc.noun_chunks:
        things.append(chunk.text)
        nouns.append(chunk.root.text)

    if 'waiting' in user_history:
        # we were waiting for a response from the user
        waiting_for = user_history['waiting']

        if waiting_for == 'num':
            # waiting for the user's fav number
            if len(numbers) > 0:
                num = numbers.pop()
                response, user_history = get_class_by_num(num, user_history)
            else:
                possible_responses = ["🤨 How about a real number less than 1000? Is that hard?",
                                      "A number, buko...",
                                      "Just provide a number. Like 💯",
                                      "A number less than 1000..."]
                response = random.choice(possible_responses)
                user_history['waiting'] = 'num'

        elif waiting_for == 'place':
            # waiting for the user's fav place
            if len(places) > 0:
                place = places.pop()
                response, user_history = get_class_by_place(place, user_history)
            else:
                possible_responses = ["A real SPECIFIC place. Like Paris is a specific place. You can do better than this!",
                                      "Well, I need a specific place. Surely you can manage that...",
                                      "A place on 🌎 like a city or country would be most helpful...",
                                      "How about your favorite city?"]
                response = random.choice(possible_responses)
                user_history['waiting'] = 'place'

        elif waiting_for == 'thing':
            # waiting for the user's fav thing/pastime
            if len(things) > 0:
                thing = things.pop()
                noun = nouns[0]
                response, user_history = get_class_by_thing(thing, noun, user_history)
            else:
                possible_responses = ["I don't like that answer, try again lol",
                                      "Weird choice. Pick something else",
                                      "🤨 Give a different thing, that's strange.",
                                      "The question wasn't that hard! Pick something else..."]
                response = random.choice(possible_responses)
                user_history['waiting'] = 'thing'

        elif waiting_for == 'NONE':
            # the user has already been given a class
            response = "You've been given a class. Go take it!"

    else:
        response, user_history = get_next_question(user_history)
    
    with open(filename, 'w') as o:
        json.dump(user_history, o)
    # print(user_history)

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

print(generate_reponse("1", 'sarah'))

