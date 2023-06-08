from googleapiclient import discovery, errors
import json
import os
import random
import time

# There should be a file called 'tokens.json' inside the same folder as this file
token_path = '../DiscordBot/tokens.json'
if not os.path.isfile(token_path):
    raise Exception(f"{token_path} not found!")
with open(token_path) as f:
    # If you get an error here, it means your token is formatted incorrectly. Did you put it in quotes?
    tokens = json.load(f)
    perspective_token=tokens['perspective']


client = discovery.build(
  "commentanalyzer",
  "v1alpha1",
  developerKey=perspective_token,
  discoveryServiceUrl="https://commentanalyzer.googleapis.com/$discovery/rest?version=v1alpha1",
  static_discovery=False,
)

perspective_attributes = {"TOXICITY":0.5,"IDENTITY_ATTACK":0.5,"INSULT":0.5}

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

#tweet_list = data_process(tweets)

def checkpost(client, post, attributes):
  analyze_request = {
    'comment': { 'text': post },
    'requestedAttributes': {'TOXICITY': {}, 'IDENTITY_ATTACK':{}, 'INSULT':{}}
  }
  response = client.comments().analyze(body=analyze_request).execute()
  for attribute in attributes:
    if (response["attributeScores"][attribute]["summaryScore"]["value"] > attributes[attribute]):
      return True
  return False

count = 0

for tweet in tweets:
    if count >= 1000:
        break
    try:
      #this is to keep it under quota
      time.sleep(1)
      if len(tweet.strip('\n').rsplit(',', 1)) != 2:
         continue
      post, cyberbullying = tweet.strip('\n').rsplit(',', 1)
      true_label = cyberbullying != "not_cyberbullying"
      pred_label = checkpost(client, post, perspective_attributes)
      if pred_label and true_label:
        tp += 1
      elif pred_label and not true_label: 
        fp += 1
      elif not pred_label and true_label:
        fn += 1
      elif not pred_label and not true_label: 
        tn += 1
      total = tp + fn + tn + fp
      if total %50 == 0:
          print(f"\ntp: {tp}\n")
          print(f"\nfp: {fp}\n")
          print(f"\ntn: {tn}\n")
          print(f"\nfn: {fn}\n")
      count += 1
    except Exception as e:
      if type(e) == errors.HttpError:
        error_details = e.error_details[0]
        if 'reason' in error_details and error_details['reason'] == 'RATE_LIMIT_EXCEEDED':
          time.sleep(60)

# count = 0
# for index in range(len(tweet_list[0])):
#     if count >= 500:
#         break
#     try:
#
#       #this is to keep it under quota
#       time.sleep(2)
#       pred_label_true = checkpost(client, tweet_list[1][index], perspective_attributes)
#       pred_label_false = checkpost(client, tweet_list[0][index], perspective_attributes)
#       if pred_label_true:
#         tp += 1
#       else: 
#         fn += 1
#       if pred_label_false:
#         fp += 1
#       else: 
#         tn += 1
#       total = tp + fn + tn + fp
#       if total %50 == 0:
#           print(f"\ntp: {tp}\n")
#           print(f"\nfp: {fp}\n")
#           print(f"\ntn: {tn}\n")
#           print(f"\nfn: {fn}\n")
#       count += 1
#     except Exception as e:
#        if type(e) == errors.HttpError:
  #       error_details = e.error_details[0]
  #       if 'reason' in error_details and error_details['reason'] == 'RATE_LIMIT_EXCEEDED':
  #         time.sleep(60)

print(f"\ntp: {tp}\n")
print(f"\nfp: {fp}\n")
print(f"\ntn: {tn}\n")
print(f"\nfn: {fn}\n")