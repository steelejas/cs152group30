from googleapiclient import discovery
import json
import os
import random
import openai

# There should be a file called 'tokens.json' inside the same folder as this file
token_path = '../DiscordBot/tokens.json'
if not os.path.isfile(token_path):
    raise Exception(f"{token_path} not found!")
with open(token_path) as f:
    # If you get an error here, it means your token is formatted incorrectly. Did you put it in quotes?
    tokens = json.load(f)
    openai.api_key = tokens['openai']



tp = 0
fp = 0
tn = 0
fn = 0


csvfile = open('cyberbullying_tweets.csv', newline='', encoding="utf8")
tweets = csvfile.readlines()
random.shuffle(tweets)

def data_process(tweets):
  result_list = (list(), list())
  for tweet in tweets:
    try:
      post, cyberbullying = tweet.strip('\n').rsplit(',', 1)
      true_label = cyberbullying != "not_cyberbullying"
      result_list[true_label].append(post)
    except:
      pass
  return result_list

tweet_list = data_process(tweets)

def checkpost(post):
  response = openai.ChatCompletion.create(
    model="gpt-3.5-turbo", # most advanced Openai model available to everyone
    max_tokens=280, # the maximum number of tokens that could be in a 280 character post
    temperature=0.0, # output will be as factual and least creative as possible. 
    
    messages = [
            {
            "role": "system",
            "content": f"""
            You will be given the text of a social media post. Say Explain if the text 
            contains harrasment. First, say "Yes" or "No" to indicate the presence of harrasment,
              then explain why.
            """,
        },
        {"role": "user", "content": post},
    ]
    )
  reply = response['choices'][0]['message']['content'] # extract model reply from api response
  if reply.startswith("Yes"):
    return True
  return False

count = 0
for index in range(len(tweet_list[0])):
    if count >= 500:
        break
    try:
      pred_label_true = checkpost(tweet_list[1][index])
      pred_label_false = checkpost(tweet_list[0][index])
      if pred_label_true:
        tp += 1
      else: 
        fn += 1
      if pred_label_false:
        fp += 1
      else: 
        tn += 1
      total = tp + fn + tn + fp
      if total %50 == 0:
          print(f"\ntp: {tp}\n")
          print(f"\nfp: {fp}\n")
          print(f"\ntn: {tn}\n")
          print(f"\nfn: {fn}\n")
      count += 1
    except Exception as e:
      print(e, tweet_list[1][index])

print(f"\ntp: {tp}\n")
print(f"\nfp: {fp}\n")
print(f"\ntn: {tn}\n")
print(f"\nfn: {fn}\n")