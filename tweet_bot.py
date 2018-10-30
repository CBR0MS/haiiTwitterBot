import time

# connect to the API and load the necessary background files
from bot_helpers import *

print("Importing Tweet IDs from previous session...")
with open('metadata.json') as f:
        meta = json.load(f)
print("Imported IDs!\n")

print("Starting loop...")
print("Checking for all tweets that mention @ABoringBot")

# search query
query = '@ABoringBot'
# list of all previous tweets that have been collected
searched_tweets = []
# max number of tweets to query each time
max_tweets = 10
# the id of the prev tweet
last_id = meta['lastID']

while True:
    tweets, searched_tweets, last_id = check_for_tweets(query, searched_tweets, max_tweets, last_id)
    meta['lastID'] = last_id
    responses, recipients = make_tweet_responses(tweets) 
    respond_to_tweets(responses, recipients)

    with open('metadata.json', 'w') as o:
        json.dump(meta, o)

    time.sleep(60)
    
