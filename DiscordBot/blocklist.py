from enum import Enum, auto
from badwordlist import bad_word_list

blocklist = {"fuck"}

blocklist = bad_word_list

blockregex = set()
    
class State(Enum):
    BLOCKLIST_START = auto()
    AWAITING_COMMAND = auto()
    ADD_BLOCKLIST = auto()
    ADD_BLOCKREGEX = auto()
    REMOVE_BLOCKLIST = auto()
    REMOVE_BLOCKREGEX = auto()
    BLOCKLIST_COMPLETE = auto()


class BlocklistInteraction:
    START_KEYWORD = "blocklist"
    CANCEL_KEYWORD = "cancel"

    INTRO_COMMAND_STRING = '''Please select the action you'd like to do by entering its number. Say `cancel` to cancel.
1. View blocklist
2. Add to blocklist
3. Remove from blocklist
4. View blocked regex
5. Add to blocked regex
6. Remove from blocked regex'''

    AWAIT_COMMAND_STRING = "Are there any other action you'd like to take? " + INTRO_COMMAND_STRING
    
    def __init__(self, client):
        self.state = State.BLOCKLIST_START
        self.client = client
    
    async def handle_message(self, message):
        '''
        This function defines how we transition between states and what prompts to offer at each of those states. 
        '''

        if message.content == self.CANCEL_KEYWORD:
            self.state = State.BLOCKLIST_COMPLETE
            return ["Blocklist Interaction cancelled."]
        
        if self.state == State.BLOCKLIST_START:
            reply =  "What would you like to do with the blocklist? "
            reply += "Say `help` at any time for more information.\n\n"
            reply += "Please copy paste the link to the message you want to report.\n"
            reply += "You can obtain this link by right-clicking the message and clicking `Copy Message Link`."
            self.state = State.AWAITING_COMMAND
            return [self.AWAIT_COMMAND_STRING]
      
        if self.state == State.AWAITING_COMMAND:
            if not message.content.strip().isdigit() or int(message.content) < 1 or int(message.content) > 6: 
                return ['''Please enter a number from 1 to 6 corresponding to an action or say `cancel` to cancel.''']

            if int(message.content) == 1:
                self.state = State.AWAITING_COMMAND
                return_string = 'The list of blocked words are:\n'
                if len(blocklist) > 0:
                    return_string += ",\n".join(blocklist)
                else:
                    return_string += "There are currently nothing in the blocklist."
                return_string += "\n\n"
                return_string += self.AWAIT_COMMAND_STRING
                return [return_string]
            elif int(message.content) == 2:
                self.state = State.ADD_BLOCKLIST
                return ["Please type the words or expressions you'd like to add to the blocklist. Please separate them by shift-enter."]
            elif int(message.content) == 3:
                self.state = State.REMOVE_BLOCKLIST
                return ["Please type the words or expressions you'd like to remove from the blocklist. Please separate them by shift-enter."]
            elif int(message.content) == 4:
                self.state = State.AWAITING_COMMAND
                return_string = 'The list of blocked regex expressions are:\n'
                if len(blocklist) > 0:
                    return_string += ",\n".join(blockregex)
                else:
                    return_string += "There are currently no regex expressions blocked."
                return_string += "\n\n"
                return_string += self.AWAIT_COMMAND_STRING
                return [return_string]
            elif int(message.content) == 5:
                self.state = State.ADD_BLOCKREGEX
                return ["Please type the regex expressions you'd like to add to the list of blocked regex expressions. Please separate them by shift-enter."]
            elif int(message.content) == 6:
                self.state = State.REMOVE_BLOCKREGEX
                return ["Please type the regex expressions you'd like to remove from the list of blocked regex expressions. Please separate them by shift-enter."]
        

        if self.state == State.ADD_BLOCKLIST:
            added_words = list()
            already_in_blocklist = list()
            if message.content:
                words = message.content.splitlines()
                for word in words:
                    if word.strip().lower() in blocklist:
                        already_in_blocklist.append(word)
                    else:
                        blocklist.add(word.strip().lower())
                        added_words.append(word)
            self.state = State.AWAITING_COMMAND
            return_string = ''
            if len(added_words) > 0:
                return_string += "Successfully added: \n" + ",\n".join(added_words) + "\n\n"
            if len(already_in_blocklist) > 0:
                return_string += "These words: \n" + ",\n".join(already_in_blocklist) + "\nare already in the blocklist.\n\n"
            return_string += self.AWAIT_COMMAND_STRING
            return [return_string]

        if self.state == State.REMOVE_BLOCKLIST:
            removed_words = list()
            not_in_blocklist = list()
            if message.content:
                words = message.content.splitlines()
                for word in words:
                    if word.strip().lower() in blocklist:
                        blocklist.remove(word.strip().lower())
                        removed_words.append(word)
                    else:
                        not_in_blocklist.append(word)
            self.state = State.AWAITING_COMMAND
            return_string = ''
            if len(removed_words) > 0:
                return_string += "Successfully removed: \n" + ",\n".join(removed_words) + "\n\n"
            if len(not_in_blocklist) > 0:
                return_string += "These words: \n" + ",\n".join(not_in_blocklist) + "\nwere not in the blocklist.\n\n"
            return_string += self.AWAIT_COMMAND_STRING
            return [return_string]
        

        if self.state == State.ADD_BLOCKREGEX:
            added_regex = list()
            already_in_blockregex = list()
            if message.content:
                regexes = message.content.splitlines()
                for regex in regexes:
                    if regex in blockregex:
                        already_in_blockregex.append(regex)
                    else:
                        blockregex.add(regex)
                        added_regex.append(regex)
            self.state = State.AWAITING_COMMAND
            return_string = ''
            if len(added_regex) > 0:
                return_string += "Successfully added: \n" + ",\n".join(added_regex) + "\n\n"
            if len(already_in_blockregex) > 0:
                return_string += "These words: \n" + ",\n".join(already_in_blockregex) + "\nare already in the list of blocked regex expressions.\n\n"
            return_string += self.AWAIT_COMMAND_STRING
            return [return_string]

        if self.state == State.REMOVE_BLOCKREGEX:
            removed_regex = list()
            not_in_blockregex = list()
            if message.content:
                regexes = message.content.splitlines()
                for regex in regexes:
                    if regex in blockregex:
                        blockregex.remove(regex)
                        removed_regex.append(regex)
                    else:
                        not_in_blockregex.append(regex)
            self.state = State.AWAITING_COMMAND
            return_string = ''
            if len(removed_regex) > 0:
                return_string += "Successfully removed: \n" + ",\n".join(removed_regex) + "\n\n"
            if len(not_in_blockregex) > 0:
                return_string += "These words: \n" + ",\n".join(not_in_blockregex) + "\nwere not in the list of blocked regex expressions.\n\n"
            return_string += self.AWAIT_COMMAND_STRING
            return [return_string]

    def blocklist_complete(self):
        return self.state == State.BLOCKLIST_COMPLETE