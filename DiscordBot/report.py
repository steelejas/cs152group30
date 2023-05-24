from enum import Enum, auto
import discord
import re
from datetime import datetime
import uuid

reports = dict()

report_category = {1: "Harassment", 2: "Spam", 3: "Fraud", 4: "Graphic/Violent Content, Gore", 5: "Imminent Danger", 6: "Other"}

target = {1: "Against Myself", 2: "Against Someone Else", 3: "Against a group of people"}

imminent_danger_category = {1: "Credible threat of violence", 2: "Self-harm or suicidal intent", 3: "Doxxing"}

harassment_category = {1: "Organizing of Harassment", 2: "Impersonation", 3: "Hate Speech", 4: "Offensive content", 5: "Sexual Harassment", 6: "Doxxing", 7: "Spam"}

action_taken_user= {1: "Blocked the account", 2: "Slowed down the account", 3: "No action taken"}

class reported_message:
    def __init__(self, reporter, message):
        self.id = uuid.uuid4()
        self.reporter = reporter 
        self.message = message
        self.time = datetime.now()
    
    def set_type(self, abuse_type):
        self.abuse_type = abuse_type

    def set_harassment_target(self, harassment_target):
        self.harassment_target = harassment_target
    
    def set_harassment_target_details(self, harassment_target_details):
        self.harassment_target_details = harassment_target_details

    def set_harassment_type(self, harassment_type):
        self.harassment_type = harassment_type

    def set_imminent_danger(self, imminent_danger):
        self.imminent_danger = imminent_danger

    def set_other(self, other_details):
        self.other_details = other_details

    def set_action_user(self, action_user):
        self.action_user = action_user

    
class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    REPORT_COMPLETE = auto()
    HARASSMENT_TYPE = auto()
    IMMINENT_DANGER = auto()
    HARASSMENT_TARGET = auto()
    OTHER_DETAILS = auto()
    HARASSMENT_TARGET_DETAILS = auto()
    ACTION_AWAITED=auto()


class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"
    END_STRING = "Thank you for reporting. Our content moderation team will review the message and decide on the appropriate action. This may include post and/or account removal."
    
    def __init__(self, client):
        self.state = State.REPORT_START
        self.client = client
        self.message = None
        self.report = None
    
    async def handle_message(self, message):
        '''
        This function makes up the meat of the user-side reporting flow. It defines how we transition between states and what 
        prompts to offer at each of those states. You're welcome to change anything you want; this skeleton is just here to
        get you started and give you a model for working with Discord. 
        '''

        if message.content == self.CANCEL_KEYWORD:
            self.state = State.REPORT_COMPLETE
            return ["Report cancelled."]
        
        if self.state == State.REPORT_START:
            reply =  "Thank you for starting the reporting process. "
            reply += "Say `help` at any time for more information.\n\n"
            reply += "Please copy paste the link to the message you want to report.\n"
            reply += "You can obtain this link by right-clicking the message and clicking `Copy Message Link`."
            self.state = State.AWAITING_MESSAGE
            return [reply]
        
        if self.state == State.AWAITING_MESSAGE:
            reporter = message.author
            # Parse out the three ID strings from the message link
            m = re.search('/(\d+)/(\d+)/(\d+)', message.content)
            if not m:
                return ["I'm sorry, I couldn't read that link. Please try again or say `cancel` to cancel."]
            guild = self.client.get_guild(int(m.group(1)))
            if not guild:
                return ["I cannot accept reports of messages from guilds that I'm not in. Please have the guild owner add me to the guild and try again."]
            channel = guild.get_channel(int(m.group(2)))
            if not channel:
                return ["It seems this channel was deleted or never existed. Please try again or say `cancel` to cancel."]
            try:
                message = await channel.fetch_message(int(m.group(3)))
            except discord.errors.NotFound:
                return ["It seems this message was deleted or never existed. Please try again or say `cancel` to cancel."]

            # Here we've found the message - it's up to you to decide what to do next!
            self.state = State.MESSAGE_IDENTIFIED

            self.report = reported_message(reporter, message)
            self.message = message
            return ["I found this message:", "```" + message.author.name + ": " + message.content + "```", \
                    "Please select the reason for reporting the message by entering its number.", \
                    "1. Harassment", \
                    "2. Spam", \
                    "3. Fraud", \
                    "4. Graphic/Violent Content, Gore", \
                    "5. Imminent Danger", \
                    "6. Other"
                    ]
        
        if self.state == State.MESSAGE_IDENTIFIED:
            if not message.content.strip().isdigit() or int(message.content) < 1 or int(message.content) > 6: 
                return ["Please enter a number from 1 to 6 corresponding to the category of abuse.", \
                        "or say `cancel` to cancel."]
            self.report.set_type(report_category[int(message.content)])
            if int(message.content) == 1:
                self.state = State.HARASSMENT_TARGET
                return ["Please select who is being or will be harrassed by entering its number.", \
                        "1. Against Myself", \
                        "2. Against Someone Else", \
                        "3. Against a group of people"
                        ]
            elif int(message.content) == 5:
                self.state = State.IMMINENT_DANGER
                return ["Please select the type of imminent danger by entering its number.", \
                        "1. Credible threat of violence", \
                        "2. Self-harm or suicidal intent", \
                        "3. Doxxing"
                        ]
            elif int(message.content) == 6:
                self.state = State.OTHER_DETAILS
                return ["Please describe details of the type of abuse or say \"skip\" to skip."]
            else:
                self.state = State.ACTION_AWAITED
                return ["Please select further action by entering its number.", \
                    "1. Block user", \
                    "2. Slow Down the account", \
                    "3. None", \
                    ]
                # return await self.complete_report() 
            
        
        if self.state == State.OTHER_DETAILS:
            self.report.set_other(message.content)
            self.state=State.ACTION_AWAITED
            return ["Please select further action by entering its number.", \
                    "1. Block user", \
                    "2. Slow Down the account", \
                    "3. None", \
                    ]
            # return await self.complete_report()


        if self.state == State.HARASSMENT_TARGET:
            if not message.content.strip().isdigit() or int(message.content) < 1 or int(message.content) > 3: 
                return ["Please select one of the three options by entering its number.", \
                        "1. Against Myself", \
                        "2. Against Someone Else", \
                        "3. Against a group of people", \
                        "or say `cancel` to cancel.", \
                        ]
            self.report.set_harassment_target(target[int(message.content)])
            if int(message.content) == 1:
                self.state = State.HARASSMENT_TYPE
                return ["Please select the type of harassment by entering its number.", \
                        "1. Organizing of Harassment", \
                        "2. Impersonation", \
                        "3. Hate Speech", \
                        "4. Offensive content", \
                        "5. Sexual Harassment", \
                        "6. Doxxing", \
                        "7. Spam", \
                        ]
            else:
                self.report.set_harassment_target(message.content)
                self.state = State.HARASSMENT_TARGET_DETAILS
                return ["Please describe details of the targeted user or group or say \"skip\" to skip."]
            
        if self.state == State.HARASSMENT_TARGET_DETAILS:
            self.report.set_harassment_target_details(message.content)
            self.state = State.HARASSMENT_TYPE
            return ["Please select the type of harassment by entering its number.", \
                    "1. Organizing of Harassment", \
                    "2. Impersonation", \
                    "3. Hate Speech", \
                    "4. Offensive content", \
                    "5. Sexual Harassment", \
                    "6. Doxxing", \
                    "7. Spam", \
                    ]

        if self.state == State.HARASSMENT_TYPE:
            if not message.content.strip().isdigit() or int(message.content) < 1 or int(message.content) > 7: 
                return ["Please select one of the harassment types or say `cancel` to cancel."]
            else:
                self.report.set_harassment_type(message.content)
                self.state=State.ACTION_AWAITED
                return ["Please select further action by entering its number.", \
                    "1. Block user", \
                    "2. Slow Down the account", \
                    "3. None", \
                    ]
                # return await self.complete_report()
            
        if self.state == State.IMMINENT_DANGER:
            if not message.content.strip().isdigit() or int(message.content) < 1 or int(message.content) > 3: 
                return ["Please select one of the imminent danger types or say `cancel` to cancel."]
            else:
                self.report.set_imminent_danger(message.content)
                self.state=State.ACTION_AWAITED
                return ["Please select further action by entering its number.", \
                    "1. Block user", \
                    "2. Slow Down the account", \
                    "3. None", \
                    ]
                # return await self.complete_report()
        if self.state == State.ACTION_AWAITED:
            if not message.content.strip().isdigit() or int(message.content) < 1 or int(message.content) > 3: 
                return ["Please select one of the actions or say `cancel` to cancel."]
            else:
                self.report.set_action_user(action_taken_user[int(message.content)])
                return await self.complete_report()

            
    async def complete_report(self):
        # Set state to end
        self.state = State.REPORT_COMPLETE
        # Store report in list
        reports[self.report.id] = self.report
        # Forward the report to the mod channel
        reporter = self.report.reporter
        message = self.report.message
        mod_channel = self.client.mod_channels[message.guild.id]
        report_string = f'''Report {self.report.id}:
    Reported message:
    {message.author.name}: "{message.content}"
    Reporter: {reporter.name}
    Abuse Type: {self.report.abuse_type}\n'''
        if self.report.abuse_type == "Other":
            report_string += f'''Abuse Type Details: {self.report.other_details}\n'''  
        elif self.report.abuse_type == "Harassment":
            report_string += f'''Harassment Target: {self.report.harassment_target}\n'''
            if self.report.harassment_target != "Against Myself":
                report_string += f'''Harassment Target Details: {self.report.harassment_target_details}\n'''
            report_string += f'''Harassment Type: {self.report.harassment_type}\n'''
        elif self.report.abuse_type == "Imminent Danger":
            report_string += f'Imminent Danger Type: {self.report.imminent_danger}\n'
        report_string+=f'Action taken by the user: {self.report.action_user}\n'
        await mod_channel.send(report_string)
        # return endstring
        return [self.END_STRING]


    def report_complete(self):
        return self.state == State.REPORT_COMPLETE
    


    

