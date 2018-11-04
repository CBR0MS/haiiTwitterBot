import time
import sys

# connect to the API and load the necessary background files
from bot_helpers import *

print("Importing Tweet IDs from previous session...", end=" ")
with open('metadata.json') as f:
        meta = json.load(f)
print("Imported IDs!\n")

print("Starting loop...")
print("Checking for all tweets that mention @iwannaclass")

# search query
query = '@iwannaclass'
# list of all previous tweets that have been collected
searched_tweets = []
# max number of tweets to query each time
max_tweets = 10
# the id of the prev tweet
last_id = meta['lastID']

while True:
    tweets, searched_tweets, last_id = check_for_tweets(query, searched_tweets, max_tweets, last_id)
    meta['lastID'] = last_id

    try:
        responses, recipients = make_tweet_responses(tweets) 
        respond_to_tweets(responses, recipients)
    except:
        print("Something went wrong! Letting the users know.")

    with open('metadata.json', 'w') as o:
        json.dump(meta, o)

    for i in range(1,61,1):
        rounded_percent = round(i/0.6)
        formatted = str(rounded_percent).zfill(2)
        print("▓  {}%".format(formatted), end="\b\b\b\b\b")
        sys.stdout.flush()
        time.sleep(1)
    print("\x1b[2K\r", end="")
    
