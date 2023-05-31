"""
Checks for the presence of harasment in social media post using gpt-3.5-turbo.
Adapted from https://github.com/openai/chatgpt-retrieval-plugin/blob/main/services/pii_detection.py

"""

import openai


# OPENAI_API_KEY = "REPLACE_WITH_API_KEY"

class h_detector:
    def __init__(self):
        openai.api_key = OPENAI_API_KEY


    def check_post_for_h(self, post):

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
            return True, reply
        return False, reply
