"""
Checks for the presence of PII in a text using gpt-3.5-turbo.
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
                    You can only respond with the word "True" or "False", where your answer indicates whether the text in the user's message contains PII.
                    Do not explain your answer, and do not use punctuation.
                    Your task is to identify whether the text extracted from your company files
                    contains sensitive PII information that should not be shared with the broader company. Here are some things to look out for:
                    - An email address that identifies a specific person in either the local-part or the domain
                    - Descriptions of where a person lives or works
                    - The postal address of a private residence (must include at least a street name)
                    - The postal address of a public place (must include either a street name or business name)
                    """,
                },
                {"role": "user", "content": post},
            ]
            )
        reply = response['choices'][0]['message']['content'] # extract model reply from api response

        if reply.startswith("True"):
            return True
        return False
