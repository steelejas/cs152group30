from enum import Enum, auto
import discord
import re
from datetime import datetime
import json

class reported_message:
    def __init__(self, reporter, message):
        self.reporter = reporter 
        self.message = message
        self.time = datetime.now()
    
    def set_type(self, abuse_type):
        self.abuse_type = abuse_type

    def set_harassment_target(self, harassment_target):
        self.harassment_target = harassment_target

    def set_harassment_type(self, harassment_type):
        self.harassment_type = harassment_type

    def set_imminent_danger(self, imminent_danger):
        self.imminent_danger = imminent_danger

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    REPORT_COMPLETE = auto()
    HARASSMENT_TYPE = auto()
    IMMINENT_DANGER = auto()
    HARASSMENT_TARGET = auto()


class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"
    END_STRING = "Thank you for reporting. Our content moderation team will review the message and decide on the appripriate action. This may include post and/or account removal."
    
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
                    "Please select the reason for reporting the message.", \
                    "- Harassment", \
                    "- Spam", \
                    "- Fraud", \
                    "- Graphic/Violent Content, Gore", \
                    "- Imminent Danger"
                    ]
        
        if self.state == State.MESSAGE_IDENTIFIED:
            if message.content == "Harassment":
                self.report.set_type(message.content)
                self.state = State.HARASSMENT_TARGET
                return ["Please select who is being or will be harrassed.", \
                        "- Against Myself", \
                        "- Against Someone Else", \
                        "- Against a group of people"
                        ]
            elif message.content == "Imminent Danger":
                self.report.set_type(message.content)
                self.state = State.IMMINENT_DANGER
                return ["Please select the type of imminent danger.", \
                        "- Credible threat of violence", \
                        "- Self-harm or suicidal intent", \
                        "- Doxxing"
                        ]
            elif message.content in ["Spam", "Fraud", "Graphic/Violent Content, Gore"]:
                self.report.set_type(message.content)
                self.state = State.REPORT_COMPLETE
                await self.send_report_to_mod()
                return [self.END_STRING]         
            else:
                self.report.set_type(message.content)
                self.state = State.REPORT_COMPLETE
                await self.send_report_to_mod()
                return [self.END_STRING]

        if self.state == State.HARASSMENT_TARGET:
            if message.content in ["Against Myself", "Against Someone Else", "Against a group of people"]:
                self.report.set_harassment_target(message.content)
                self.state = State.HARASSMENT_TYPE
                return ["Please select the type of harassment.", \
                        "- Organizing of Harassment", \
                        "- Impersonation", \
                        "- Hate Speech", \
                        "- Offensive content", \
                        "- Sexual Harassment", \
                        "- Doxxing", \
                        "- Spam", \
                        ]
            else:
                return ["Please select one of the three options", \
                        "- Against Myself", \
                        "- Against Someone Else", \
                        "- Against a group of people", \
                        "or say `cancel` to cancel."]

        if self.state == State.HARASSMENT_TYPE:
            if message.content in ["Organizing of Harassment", "Impersonation", "Hate Speech", "Offensive content", "Sexual Harassment", "Doxxing", "Spam"]:
                self.report.set_harassment_type(message.content)
                self.state = State.REPORT_COMPLETE
                await self.send_report_to_mod()
                return [self.END_STRING]
            else:
                return ["Please select one of the harassment types or say `cancel` to cancel."]
            
        if self.state == State.IMMINENT_DANGER:
            if message.content in ["Credible threat of violence", "Self-harm or suicidal intent", "Doxxing"]:
                self.report.set_imminent_danger(message.content)
                self.state = State.REPORT_COMPLETE
                await self.send_report_to_mod()
                return [self.END_STRING]
            else:
                return ["Please select one of the imminent danger types or say `cancel` to cancel."]
            
    async def send_report_to_mod(self):
        # Forward the report to the mod channel
        reporter = self.report.reporter
        message = self.report.message
        mod_channel = self.client.mod_channels[message.guild.id]
        await mod_channel.send(f'Reported message:\n'
                               f'{message.author.name}: "{message.content}"\n'
                               f'Reporter: {reporter.name}\n'
                               f'Abuse Type: {self.report.abuse_type}\n'
                               )
        if self.report.abuse_type == "Harassment":
            await mod_channel.send(f'Harassment Target: {self.report.harassment_target}\n'
                                f'Harassment Type: {self.report.harassment_type}\n'
                                )
        elif self.report.abuse_type == "Imminent Danger":
            await mod_channel.send(f'Imminent Danger Type: {self.report.imminent_danger}\n')


    def report_complete(self):
        return self.state == State.REPORT_COMPLETE
    


    

