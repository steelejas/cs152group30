import json
import os
import openai

# There should be a file called 'tokens.json' inside the same folder as this file
token_path = 'tokens.json'
if not os.path.isfile(token_path):
    raise Exception(f"{token_path} not found!")
with open(token_path) as f:
    # If you get an error here, it means your token is formatted incorrectly. Did you put it in quotes?
    tokens = json.load(f)
    openai.api_key = tokens['openai']

def checkpost_openai(post):
    try:
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
    except:
        return False
