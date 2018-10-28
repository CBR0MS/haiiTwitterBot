import time

# connect to the API and load the necessary background files
from bot_helpers import *

print("Starting loop...")
print("Checking for all tweets that mention @ABoringBot")

# search query
query = '@ABoringBot'
# list of all previous tweets that have been collected
searched_tweets = []
# max number of tweets to query each time
max_tweets = 10
# the id of the prev tweet
last_id = -1

while True:
    tweets, searched_tweets, last_id = check_for_tweets(query, searched_tweets, max_tweets, last_id)
    responses, recipients = make_tweet_responses(tweets) 
    respond_to_tweets(responses, recipients)
    time.sleep(60)
    
