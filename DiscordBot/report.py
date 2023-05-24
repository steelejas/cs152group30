from enum import Enum, auto
import discord
import re
from datetime import datetime
import uuid
import globals


report_category = {1: "Harassment", 2: "Spam", 3: "Fraud", 4: "Graphic/Violent Content, Gore", 5: "Imminent Danger", 6: "Other"}

target = {1: "Against Myself", 2: "Against Someone Else", 3: "Against a group of people"}

imminent_danger_category = {1: "Credible threat of violence", 2: "Self-harm or suicidal intent", 3: "Doxxing"}

harassment_category = {1: "Organizing of Harassment", 2: "Impersonation", 3: "Hate Speech", 4: "Offensive content", 5: "Sexual Harassment", 6: "Doxxing", 7: "Spam"}

class reported_message:
    def __init__(self, reporter, message):
        self.id = uuid.uuid4()
        self.reporter = reporter 
        self.message = message
        self.time = datetime.now()
        self.safety_mode = False
        self.block_user = list()
    
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

    def set_safety(self):
        self.safety_mode = True
    
    def set_block_user(self, blocked_user):
        self.block_user.append(blocked_user)

    
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
    BLOCK_AWAITED=auto()
    SAFETY_MODE = auto()


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
                return await self.block()
            
        
        if self.state == State.OTHER_DETAILS:
            self.report.set_other(message.content)
            return await self.block()


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
            self.report.set_harassment_type(harassment_category[int(message.content)])
            if self.report.harassment_target == "Against Myself":
                self.state = State.SAFETY_MODE
                return ["Do you want to turn on safety mode for your account?", \
                        "This limits the people who can DM you or leave a message on your profile", \
                        "This also slows down the number of message that can be left on your profile or sent to you", \
                    "1. Yes", \
                    "2. No", \
                    ]
            else:
                return await self.block()

        if self.state == State.SAFETY_MODE:
            if not message.content.strip().isdigit() or int(message.content) < 1 or int(message.content) > 2: 
                return ["Please select either 1 (Yes) or 2 (No)."]
            channel = message.channel
            if int(message.content) == 1:
                await channel.send('We have activated safety mode on your account.')
                self.report.set_safety()
            return await self.block()

            
        if self.state == State.IMMINENT_DANGER:
            if not message.content.strip().isdigit() or int(message.content) < 1 or int(message.content) > 3: 
                return ["Please select one of the imminent danger types or say `cancel` to cancel."]
            else:
                self.report.set_imminent_danger(imminent_danger_category[int(message.content)])
                return await self.complete_report()

        if self.state == State.BLOCK_AWAITED:
            if not message.content.strip().isdigit() or int(message.content) < 1 or int(message.content) > 2: 
                return ["Please select either 1 (Yes) or 2 (No)."]
            channel = message.channel
            if int(message.content) == 1:
                await channel.send(f'We have blocked {self.report.message.author.name} for you.')
                self.report.set_block_user(self.report.message.author.name)
            return await self.complete_report()

    async def block(self):
        self.state = State.BLOCK_AWAITED
        return ["Do you wish to block the person you are reporting?", \
                "1. Yes", \
                "2. No", \
                ]
            
    async def complete_report(self):
        # Set state to end
        self.state = State.REPORT_COMPLETE
        # Store report in list
        globals.reports[self.report.id] = self.report
        # Forward the report to the mod channel
        reporter = self.report.reporter
        message = self.report.message
        mod_channel = self.client.mod_channels[message.guild.id]
        report_string = f'''Report {self.report.id} at time {self.report.time}:
\tReported message:
\t{message.author.name}: "{message.content}"
\tReporter: {reporter.name}
\tAbuse Type: {self.report.abuse_type}\n'''
        if self.report.abuse_type == "Other":
            report_string += f'''\t\tAbuse Type Details: {self.report.other_details}\n'''  
        elif self.report.abuse_type == "Harassment":
            report_string += f'''\t\tHarassment Target: {self.report.harassment_target}\n'''
            if self.report.harassment_target != "Against Myself":
                report_string += f'''\t\t\tHarassment Target Details: {self.report.harassment_target_details}\n'''
            report_string += f'''\t\tHarassment Type: {self.report.harassment_type}\n'''
        elif self.report.abuse_type == "Imminent Danger":
            report_string += f'\t\tImminent Danger Type: {self.report.imminent_danger}\n'
        report_string += f'\tHas reporter turned on safety mode: {self.report.safety_mode}\n'
        report_string += f'\tHas reporter blocked message sender: {self.report.message.author.name in self.report.block_user}\n'
        report_string += '''Press ⏱️ to place abuser under slow mode.
Press 🛑 to block abuser for reporter.
Press ❗ to send strike and warning to abuser.
Press ❌ to ban abuser.
Press ❔ to strike reporter for false report. (Only strike if false report is intentional)'''
        sent_report = await mod_channel.send(report_string)
        await sent_report.add_reaction(emoji="⏱️")
        await sent_report.add_reaction(emoji="🛑")
        await sent_report.add_reaction(emoji="❗")
        await sent_report.add_reaction(emoji="❌")
        await sent_report.add_reaction(emoji="❔")

        globals.report_message_to_id[sent_report.id] = self.report.id
        # return endstring
        return [self.END_STRING]


    def report_complete(self):
        return self.state == State.REPORT_COMPLETE
    


    

