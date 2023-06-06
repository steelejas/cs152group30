from googleapiclient import discovery, errors
import json
import os
import random
import time
import openai

# There should be a file called 'tokens.json' inside the same folder as this file
token_path = '../DiscordBot/tokens.json'
if not os.path.isfile(token_path):
    raise Exception(f"{token_path} not found!")
with open(token_path) as f:
    # If you get an error here, it means your token is formatted incorrectly. Did you put it in quotes?
    tokens = json.load(f)
    perspective_token=tokens['perspective']
    openai.api_key = tokens['openai']


client = discovery.build(
  "commentanalyzer",
  "v1alpha1",
  developerKey=perspective_token,
  discoveryServiceUrl="https://commentanalyzer.googleapis.com/$discovery/rest?version=v1alpha1",
  static_discovery=False,
)

perspective_attributes = {"TOXICITY":0.8,"IDENTITY_ATTACK":0.8,"INSULT":0.8}


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

def checkpost_perspective(client, post, attributes):
  analyze_request = {
    'comment': { 'text': post },
    'requestedAttributes': {'TOXICITY': {}, 'IDENTITY_ATTACK':{}, 'INSULT':{}}
  }
  response = client.comments().analyze(body=analyze_request).execute()
  for attribute in attributes:
    if (response["attributeScores"][attribute]["summaryScore"]["value"] > attributes[attribute]):
      return True
  return False

def checkpost_openai(post):
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

# tp = [0, 0, 0, 0]
# fp = [0, 0, 0, 0]
# tn = [0, 0, 0, 0]
# fn = [0, 0, 0, 0]
# count = 0

# for tweet in tweets:
#     if count >= 1000:
#         break
#     try:
#       #this is to keep it under quota
#       time.sleep(1)
#       if len(tweet.strip('\n').rsplit(',', 1)) != 2:
#          continue
#       post, cyberbullying = tweet.strip('\n').rsplit(',', 1)
#       true_label = cyberbullying != "not_cyberbullying"
#       pred_label_perspective = checkpost_perspective(client, post, perspective_attributes)
#       pred_label_openai = checkpost_openai(post)
#       for i in range(4):
#         if i == 0:
#             pred_label = pred_label_perspective and pred_label_openai
#         elif i == 1:
#             pred_label = pred_label_perspective
#         elif i == 2:
#             pred_label = pred_label_openai
#         elif i == 3:
#             pred_label = pred_label_perspective or pred_label_openai
#         if pred_label and true_label:
#             tp[i] += 1
#         elif pred_label and not true_label: 
#             fp[i] += 1
#         elif not pred_label and true_label:
#             fn[i] += 1
#         elif not pred_label and not true_label: 
#             tn[i] += 1
#       count += 1
#     except Exception as e:
#       if type(e) == errors.HttpError:
#         error_details = e.error_details[0]
#         if 'reason' in error_details and error_details['reason'] == 'RATE_LIMIT_EXCEEDED':
#           time.sleep(60)

# for i in range(4):
#     print(f"\ni: {i}\n")
#     print(f"\ntp: {tp[i]}\n")
#     print(f"\nfp: {fp[i]}\n")
#     print(f"\ntn: {tn[i]}\n")
#     print(f"\nfn: {fn[i]}\n")

tp = [0, 0, 0, 0]
fp = [0, 0, 0, 0]
tn = [0, 0, 0, 0]
fn = [0, 0, 0, 0]
count = 0

tweet_list = data_process(tweets)

for index in range(len(tweet_list[0])):
    if count >= 500:
        break
    try:
      #this is to keep it under quota
      time.sleep(2)
      pred_label_true_perspective = checkpost_perspective(client, tweet_list[1][index], perspective_attributes)
      pred_label_false_perspective = checkpost_perspective(client, tweet_list[0][index], perspective_attributes)
      pred_label_true_openai = checkpost_openai(tweet_list[1][index])
      pred_label_false_openai = checkpost_openai(tweet_list[0][index])
      for i in range(4):
        if i == 0:
          pred_label_true = pred_label_true_perspective and pred_label_true_openai
          pred_label_false = pred_label_false_perspective and pred_label_false_openai
        elif i == 1:
            pred_label_true = pred_label_true_perspective
            pred_label_false = pred_label_false_perspective
        elif i == 2:
            pred_label_true = pred_label_true_openai
            pred_label_false = pred_label_false_openai
        elif i == 3:
          pred_label_true = pred_label_true_perspective or pred_label_true_openai
          pred_label_false = pred_label_false_perspective or pred_label_false_openai
        if pred_label_true:
            tp[i] += 1
        else: 
            fn[i] += 1
        if pred_label_false:
            fp[i] += 1
        else: 
            tn[i] += 1
        total = tp[i] + fn[i] + tn[i] + fp[i]
        if total % 50 == 0:
            print(f"\ni: {i}\n")
            print(f"\ntp: {tp[i]}\n")
            print(f"\nfp: {fp[i]}\n")
            print(f"\ntn: {tn[i]}\n")
            print(f"\nfn: {fn[i]}\n")
      count += 1
    except Exception as e:
        print(e)
        if type(e) == errors.HttpError:
            error_details = e.error_details[0]
            if 'reason' in error_details and error_details['reason'] == 'RATE_LIMIT_EXCEEDED':
                time.sleep(60)

for i in range(4):
    print(f"\ni: {i}\n")
    print(f"\ntp: {tp[i]}\n")
    print(f"\nfp: {fp[i]}\n")
    print(f"\ntn: {tn[i]}\n")
    print(f"\nfn: {fn[i]}\n")