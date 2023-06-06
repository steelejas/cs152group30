from gpt_pii import pii_detector

detector = pii_detector()

# example post
post = "He lives on maple street"

# input: the post
# output: boolean indicating the presence of PII in the post
output = detector.check_post_for_pii(post)
print(f"Contains PII: {output}")
