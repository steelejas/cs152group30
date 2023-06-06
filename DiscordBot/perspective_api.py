from googleapiclient import discovery
import json
import os

# There should be a file called 'tokens.json' inside the same folder as this file
token_path = 'tokens.json'
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

def checkpost_perspective(post, attributes):
  analyze_request = {
    'comment': { 'text': post },
    'requestedAttributes': {'TOXICITY': {}, 'SPAM':{},'IDENTITY_ATTACK':{},'INSULT':{},'THREAT':{}}
  }
  response = client.comments().analyze(body=analyze_request).execute()
  for attribute in attributes:
    if (response["attributeScores"][attribute]["summaryScore"]["value"] > attributes[attribute]):
      return True, attribute
  return False, None
