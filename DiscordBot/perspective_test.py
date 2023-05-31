from googleapiclient import discovery
import json

API_KEY = 'AIzaSyBpFRNDjNHeT6x2laxaf9DFBYAZf8PqoYw'

client = discovery.build(
  "commentanalyzer",
  "v1alpha1",
  developerKey=API_KEY,
  discoveryServiceUrl="https://commentanalyzer.googleapis.com/$discovery/rest?version=v1alpha1",
  static_discovery=False,
)

analyze_request = {
  'comment': { 'text': 'i will kill you' },
  'requestedAttributes': {'TOXICITY': {}, 'SPAM':{}}
}

response = client.comments().analyze(body=analyze_request).execute()
print(json.dumps(response, indent=2))

print()


analyze_request = {
  'comment': { 'text': 'you are a good person' },
  'requestedAttributes': {'TOXICITY': {}}
}

response = client.comments().analyze(body=analyze_request).execute()
print(json.dumps(response, indent=2))

print()


analyze_request = {
  'comment': { 'text': 'crypto giveaway! signup and get free bitcoins' },
  'requestedAttributes': {'TOXICITY': {}, 'SPAM':{}}
}

response = client.comments().analyze(body=analyze_request).execute()
print(json.dumps(response, indent=2))

print()