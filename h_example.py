from gpt_h import h_detector

detector = h_detector()

### example posts
post = "We should all go on her livestream and spam the chat"
# post = "We should all go on her livestream and post in the chat"
# post = "he should stop writing."
# post = "he should stop writing. His books are terrible"
# post = "he should stop writing. His art is awesome!"

### input: the post
### output: boolean indicating the presence of harrasment in the post
output = detector.check_post_for_h(post)
print(f"Contains bad stuff: {output[0]}")
print(f"Explanation: {output[1]}")
