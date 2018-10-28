from credentials import *
import tweepy
from textblob import TextBlob
from textblob.sentiments import NaiveBayesAnalyzer
import os, json
import warnings
#spacy has a really annoying warning I'm getting rid of here
warnings.filterwarnings("ignore")

import spacy
import markovify

# word parsing using spacy in the markov chain generator
nlp = spacy.load("en")
class POSifiedText(markovify.Text):
    def word_split(self, sentence):
        return ["::".join((word.orth_, word.pos_)) for word in nlp(sentence)]

    def word_join(self, words):
        sentence = " ".join(word.split("::")[0] for word in words)
        return sentence

def analyze_sentiment(text):
    tokens = TextBlob(text, analyzer=NaiveBayesAnalyzer())
    res = tokens.sentiment
    pol_neg = abs(res.p_pos)
    pol_pos = abs(res.p_neg)
    if pol_neg > pol_pos:
        pol = pol_neg
    else:
        pol = pol_pos
    return res.classification, res.p_pos, res.p_neg, pol

print("Authenticating...")
try:
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)
    api = tweepy.API(auth)
    print("Successfuly authenticated!\n")
except tweepy.TweepError as e:
    print("Authentication failed, aborting")
    print(e)

query = 'doing today OR do today -filter:retweets AND -filter:replies'
max_tweets = 200

user_name = '@realDonaldTrump' 
####
# Do the search
#####
searched_tweets = []
last_id = -1
while len(searched_tweets) < max_tweets:
    count = max_tweets - len(searched_tweets)
    try:
        print("Collecting Tweets...")
        # new_tweets = api.search(q=query, count=count, max_id=str(last_id - 1), tweet_mode="extended")
        new_tweets = api.user_timeline(screen_name=user_name, count=count,  tweet_mode="extended")
        if not new_tweets:
            break
        searched_tweets.extend(new_tweets)
        last_id = new_tweets[-1].id
        print("Done, collected {} Tweets\n".format(count))
    except tweepy.TweepError as e:
        print("Failed to retrieve Tweets, aborting")
        print(e)
        # depending on TweepError.code, one may want to retry or wait                                                                                                                 
        # to keep things simple, we will give up on an error                                                                                                                          
        break
####
# Iterate over the search
#####
tokenized_tweets = []
train_data = []
for status in searched_tweets:
    train_data.append(status.full_text)

user_id = api.get_user(screen_name=user_name)
user_id = user_id.id
filename = str(user_id) + '.json'

if os.path.isfile(filename):
    print("Opening previous model from json...")
    with open(filename) as f:
        model_json = json.load(f)
    model = markovify.Text.from_json(model_json)
    print("Done, opened and loaded model\n")
else :
    print("Training model...")
    model = markovify.Text(train_data)
    print("Done, model trained\n")
    model_json = model.to_json()
    with open(filename, 'w') as outfile:
        json.dump(model_json, outfile)

seeds = ['I', 'I am', 'Squirrel Hill']
found_response_tweet = False
possible_sentences = []
iterations = 0
max_iterations = len(seeds)
seed = seeds.pop()

while not found_response_tweet and iterations < max_iterations:
    print("Generating responses with seed: \'{}\'".format(seed))
    for i in range(5):
        sentence = model.make_sentence_with_start(seed, strict=False)
        if sentence != None:
            found_response_tweet = True
            possible_sentences.append(sentence)
            print(sentence)

    if not found_response_tweet and iterations < max_iterations:
        seed = seeds.pop()
        iterations += 1
        print("Failed to create a response, trying with new seed...\n")
    else:
        if not found_response_tweet:
            print("Failed to create a response, aborting")

response = ''
largest_pol = 0
print("\nAnalyzing sentiment of possible responses...")
for sent in possible_sentences:
    agregate, pos, neg, pol = analyze_sentiment(sent)
    if pol > largest_pol:
        largest_pol = pol
        response = sent

print("Response decided with polarity of {}:".format(largest_pol))
print(response)




  # do something with all these tweets    
  # print(status.full_text)   
    # tokens = TextBlob(status.text) 
    # for word, pos in tokens.tags:
    #     if pos == 'VB':
    #         print(en.verb.future(word))
    #     elif pos == 'NN':
    #         print(word)

    # grammar = ('''
    #     NP: {<DT>?<JJ>*<NN>} # NP
    #     ''')

    # chunkParser = nltk.RegexpParser(grammar)
    # tagged = nltk.pos_tag(nltk.word_tokenize(status.full_text))
    # tree = chunkParser.parse(tagged)
    # getNodes(tree)
    # print(status.full_text)
    # nlp = spacy.load('en')
    # doc = nlp(status.full_text)
    # for token in doc:
    #     if token.head.pos_ == 'VERB':
    #         print(token.text,
    #             [child for child in token.children])

    # parser = nltk.ChartParser(groucho_grammar)
    # for tree in parser.parse(nltk.word_tokenize(status.full_text)):
    #     print(tree)
    # for subtree in tree.subtrees():
    #     print(subtree)

        
        



 # print (word.pluralize())                                                                                                                                        
 #  tokenized_tweets.append(tokens)
 #  print(tokens.verbs)





