"""
Checks text for doxxing that describes the home adress of someone gpt-3.5-turbo.
Adapted from https://github.com/openai/chatgpt-retrieval-plugin/blob/main/services/pii_detection.py
"""

import openai


OPENAI_API_KEY = "REPLACE_WITH_API_KEY"

class pii_detector:
    def __init__(self):
        openai.api_key = OPENAI_API_KEY


    def check_post_for_pii(self, post):

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo", # most advanced Openai model available to everyone
            max_tokens=280, # the maximum number of tokens that could be in a 280 character post
            temperature=0.0, # output will be as factual and least creative as possible. 
            
            messages = [
                {
                    "role": "system",
                    "content": f"""
                    You can only respond with the word "True" or "False", where your answer indicates whether the text describes someone else's home street adress.
                    Do not explain your answer, and do not use punctuation.
                    Your task is to identify whether the text from social media posts
                    contains a street address of someone who is not the author of the post. Here are some things to look out for:
                    - A street address
                    - A description of the house or apartment someone lives in
                    """,
                },
                {"role": "user", "content": post},
            ]
            )
        reply = response['choices'][0]['message']['content'] # extract model reply from api response

        if reply.startswith("True"):
            return True
        return False
