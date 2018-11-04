import tweepy 
from credentials import *
import json
import warnings
#spacy has a really annoying warning I'm getting rid of here
warnings.filterwarnings("ignore")
import spacy
import random
import re

#Twitter bot helpers 
#A variety of functions used in tweet_bot.py 

# Authenticate 
print("Authenticating...", end=" ")
try:
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)
    api = tweepy.API(auth)
    print("Successfully authenticated!\nLoading EN_CORE_LG NLP model...", end=" ")
except tweepy.TweepError as e:
    print("Authentication failed, aborting")
    print(e)

nlp = spacy.load('en_core_web_lg')
print("Loaded model!")

print("Loading CMU course data...", end=" ")
with open('spring2019classes.json') as f:
        data = json.load(f)
print("Data loaded!")

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
        if data[key]['dept'] == user_history['topic'] and 'place' in data[key] and user_history['place'] in data[key]['place']:
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

        place_questions = ["What's your favorite place in the whole 🌎?",
                            "Pick someplace in the world that you'd like to go...",
                            "If you could live anywhere in the world, where would you live?"]

        thing_questions = ["Name something you like to do...",
                            "What do you like to do for fun?",
                            "What do you enjoy doing?"]
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
    #print(noun)
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
        user_history['waitFast']['dept'] = full_thing
        res, user_history = get_next_question(user_history)
        response = "Okay, " + full_thing + " it is. " + res
    return response, user_history


#########################################################################
# Check if the question contains main keywords that have an easy answer
#########################################################################
def check_for_main_topics(text, places, times, dates, things, nouns, numbers, user_history):

    day = user_history['waitFast']['day']
    time = user_history['waitFast']['time']
    dept = user_history['waitFast']['dept']

    day_complete = ''
    for thing in things:
        if thing.lower() in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
            day_complete = thing
            thing = thing.lower()
            if thing == 'monday':
                day = 'M'
            elif thing == 'tuesday':
                day = 'T'
            elif thing == 'wednesday':
                day = 'W'
            elif thing == 'thursday':
                day = 'R'
            elif thing == 'friday':
                day = 'F'
            elif thing == 'saturday':
                day = 'S'
            elif thing == 'sunday':
                day = 'U'

    if len(times) > 0:
        time = times[0]
    
    most_match = 400
    percent_overlap = 0

    #print(things)
    for thing in things:
        if thing.title() in data['topics']:
            dept = thing.title()

    if dept == '':
        for thing in things:
            splits = thing.split(" ")
            for word in splits:
                for topic in data['topics']:
                    if word.lower() in topic.lower():
                        #print("word: {}, topic: {}".format(word, topic))
                        split_topic = (topic.lower()).split(word.lower())
                        remainder = len(split_topic[0]) + len(split_topic[1])
                        if remainder < most_match:
                            most_match = remainder
                            dept = topic
    if dept != '':
        percent_overlap = most_match / len(dept)
    if percent_overlap < 0.2:
        dept = ''

    if dept == '' and day == '' and time == '': # have nothing, return 
        return False, user_history
    elif dept == '' and day == '' and time != '': # have time
        user_history['waitFast']["time"] = time
        return "Something at " + time + ", got it. What day and what department?", user_history
    elif dept == '' and day != '' and time == '': # have day
        user_history['waitFast']['day'] = day
        if day_complete == '':
            return "Ok, what department and time?", user_history
        return "Something on " + day_complete + ", got it. What department and time?", user_history
    elif dept != '' and day == '' and time == '': # have dept 
        user_history['waitFast']['dept'] = dept
        return "Something in " + dept + ", got it. What day and time?", user_history
    elif dept == '' and day != '' and time != '': # have time and day
        user_history['waitFast']['time'] = time
        user_history['waitFast']['day'] = day
        if day_complete == '':
            return "Something at " + time + ". What department?", user_history
        return "Something on " + day_complete + " at " + time + ". What department?", user_history
    elif dept != '' and day != '' and time == '':  # have dept and day 
        user_history['waitFast']['dept'] = dept
        user_history['waitFast']['day'] = day
        if day_complete == '':
            return "Something in " + dept + ". What time?", user_history
        return "Something in " + dept + " on " + day_complete + ". What time?", user_history
    elif dept != '' and day == '' and time != '': # have dept and time
        user_history['waitFast']['dept'] = dept
        user_history['waitFast']['time'] = time
        return "Something in " + dept + " at " + time + ". What day?", user_history
    else: # have all three
        #return "Something in " + dept + " at " + time + " on " + day + ", got it!", user_history
        user_history['waitFast']['dept'] = dept
        user_history['waitFast']['time'] = time
        user_history['waitFast']['day'] = day
        
        for key in data:
        # if key not in user_history['badclasses']:
            if key.isnumeric() and data[key]['dept'] == dept:

                for section in data[key]['sections']:
                    if time in section['start'] and day in section['start']:
                        user_history['potentialClasses'].append(key)
                        
        if len(user_history['potentialClasses']) > 0:
            key = random.choice(user_history['potentialClasses'])
            hyphenated = hyphenate_class(key)
            return  "Ok, found a class that works! " + hyphenated + " " + data[key]['name'] + ". Check it out: https://www.cmucoursefind.xyz/courses/" + hyphenated, user_history
        else:
            possible_endings = ["How about a different time?", "Maybe try a different time?", "How about a different day?", "Perhaps a different day?"]
            res = "Looks like that particular combination doesn't work... " + random.choice(possible_endings)
            return res, user_history

    return False, user_history

#########################################################################
# Create a response given a tweet's text and user. Check for previous
# conversation with the user and use information from that, if applicable. 
#########################################################################
def generate_reponse(tweet_text, user):
    user_history = {}
    filename = 'users/' + user + '.json'
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
        user_history['waitFast'] = {}
        user_history['waitFast']['time'] = ''
        user_history['waitFast']['day'] = ''
        user_history['waitFast']['dept'] = ''

    doc = nlp(tweet_text)

    places = []
    times = []
    things = []
    nouns = []
    numbers = []
    dates = []

    for ent in doc.ents:
        if ent.label_ == 'GPE' or ent.label_ == 'LOC':
            places.append(ent.text)
        elif ent.label_ == 'TIME':
            times.append(ent.text)
        elif ent.label_ == 'CARDINAL':
            numbers.append(ent.text)
        elif ent.label == 'DATE':
            dates.append(ent.text)

    for chunk in doc.noun_chunks:
        things.append(chunk.text)
        nouns.append(chunk.root.text)

    other_times = re.findall(r'\d{1,2}(?:(?:am|pm)|(?::\d{1,2})(?:am|pm)?)', tweet_text)
    times.extend(other_times)

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
                possible_responses = ["A real SPECIFIC place. Like Pittsburgh is a specific place. You can do better than this!",
                                      "Well, I need a specific place. Surely you can manage that...",
                                      "A place on 🌎 like a city or country would be most helpful...",
                                      "How about your favorite city?"]
                response = random.choice(possible_responses)
                user_history['waiting'] = 'place'

        elif waiting_for == 'thing':
            # waiting for the user's fav thing/pastime
            max_len = 0
            index = 0
            if len(things) > 0:
                for i in range(0, len(things)):
                    if len(things[i]) > max_len:
                        max_len = len(things[i])
                        index = i
                thing = things[i]
                noun = nouns[i]
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
            keyword_response, user_history = check_for_main_topics(tweet_text, places, times, dates, things, nouns, numbers, user_history)
            if not keyword_response:
                response = "You've been given a class. Go take it! If you want to take something else, provide a day, time, or different department."
            else:
                response = keyword_response

    else:
        # see if the user is requesting specific information 
        keyword_response, user_history = check_for_main_topics(tweet_text, places, times, dates, things, nouns, numbers, user_history)
        if not keyword_response:
            response, user_history = get_next_question(user_history)
        else:
            response = keyword_response
    
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

#print(generate_reponse("find a class in Design next semester", 'jane'))

