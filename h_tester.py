"""
Evaluates the performace of gpt_h on a dataset of tweets containg or not containing cyberbullying.
"""

from gpt_h import h_detector
import csv
import random


# Shuffle dataset lines to create a mix of True/False examples of harrassment
fid = open('labeled_data.csv', "r")
li = fid.readlines()
fid.close()

random.shuffle(li)

fid = open('labeled_data.csv', "w")
fid.writelines(li)
fid.close()



# init measurement values

tp=0 # true positive
fp=0 # false positive
tn=0 # true negative
fn=0 # false negative


# create harassment detector
detector = h_detector()


# perform the evaluation
with open('labeled_data.csv') as csv_file:
    csv_reader = csv.reader(csv_file, delimiter=',')
    post_num = 0
    for row in csv_reader:
        post = row[0]
        if post_num <=1000:
            try: # sometimes the api bounces the request and says it is busy
                output = detector.check_post_for_h(post)
                if output[0]: # GPT says there is harrasmment
                    if row[1] != "not_cyberbullying": # there is actual cyberbullying
                        tp += 1
                    else: # there is not actual cyberbullying
                        fp += 1
                else: # GPT says there is not harrasmment
                    if row[1] != "not_cyberbullying": # there is actual cyberbullying
                        fn += 1
                    else:  # there is not actual cyberbullying
                        tn += 1
                total = tp + fn + tn + fp
                if total %50 == 0:
                    print(f"\ntp: {tp}\n")
                    print(f"\nfp: {fp}\n")
                    print(f"\ntn: {tn}\n")
                    print(f"\nfn: {fn}\n")
            except:
                print(f"\ntp: {tp}\n")
                print(f"\nfp: {fp}\n")
                print(f"\ntn: {tn}\n")
                print(f"\nfn: {fn}\n")
        else:
            break
        print(f"num={post_num}")
        post_num +=1
print(f"\ntp: {tp}\n")
print(f"\nfp: {fp}\n")
print(f"\ntn: {tn}\n")
print(f"\nfn: {fn}\n")