from enum import Enum, auto
import discord
import re
from datetime import datetime, timezone
import pytz
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
        self.message_created_time = message.created_at
        self.report_created_time = datetime.now(timezone.utc)
        self.safety_mode = False
        self.block_user = set()
    
    def set_type(self, abuse_type):
        self.abuse_type = abuse_type

    def set_harassment_type(self, harassment_type):
        self.harassment_type = harassment_type

    def set_multiple_harasser(self, multiple_harasser):
        self.multiple_harasser = multiple_harasser

    def set_imminent_danger(self, imminent_danger):
        self.imminent_danger = imminent_danger

    def set_other(self, other_details):
        self.other_details = other_details

    def add_other_messages(self, other_messages):
        self.other_messages = other_messages

    def set_safety(self):
        self.safety_mode = True
    
    def set_block_user(self, blocked_user):
        self.block_user.add(blocked_user)

    
class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    REPORT_COMPLETE = auto()
    HARASSMENT_TYPE = auto()
    IMMINENT_DANGER = auto()
    OTHER_DETAILS = auto()
    BLOCK_AWAITED = auto()
    SAFETY_MODE = auto()
    MULTIPLE_HARASSER = auto()
    ADD_MESSAGES = auto()


class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"
    
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
            return [f'''I found this message:```{message.author.name}: {message.content}```
Please select the reason for reporting the message by entering its number.
1. Harassment
2. Spam
3. Fraud
4. Graphic/Violent Content, Gore
5. Imminent Danger
6. Other'''
]
        
        if self.state == State.MESSAGE_IDENTIFIED:
            if not message.content.strip().isdigit() or int(message.content) < 1 or int(message.content) > 6: 
                return ['''Please enter a number from 1 to 6 corresponding to the category of abuse.
or say `cancel` to cancel.''']
            self.report.set_type(report_category[int(message.content)])
            if int(message.content) == 1:
                self.state = State.HARASSMENT_TYPE
                return ['''Please select the type of harassment by entering its number.
1. Organizing of Harassment
2. Impersonation
3. Hate Speech
4. Offensive content
5. Sexual Harassment
6. Doxxing
7. Spam'''
                        ]
            elif int(message.content) == 5:
                self.state = State.IMMINENT_DANGER
                return ['''Please select the type of imminent danger by entering its number.
1. Credible threat of violence
2. Self-harm or suicidal intent
3. Doxxing'''
                        ]
            elif int(message.content) == 6:
                self.state = State.OTHER_DETAILS
                return ["Please describe details of the type of abuse or say \"skip\" to skip."]
            else:
                return await self.add_multiple_messages()
            
        
        if self.state == State.OTHER_DETAILS:
            self.report.set_other(message.content)
            return await self.add_multiple_messages()

        if self.state == State.HARASSMENT_TYPE:
            if not message.content.strip().isdigit() or int(message.content) < 1 or int(message.content) > 7: 
                return ["Please select one of the harassment types or say `cancel` to cancel."]
            self.report.set_harassment_type(harassment_category[int(message.content)])
            self.state = State.MULTIPLE_HARASSER
            return ['''Are there multiple users involved in the harassment?
1. Yes
2. No'''
                    ]
        
        if self.state == State.MULTIPLE_HARASSER:
            if not message.content.strip().isdigit() or int(message.content) < 1 or int(message.content) > 7: 
                return ["Please select yes or no or say `cancel` to cancel."]
            if int(message.content) == 1:
                self.report.set_multiple_harasser(True)
            else: 
                self.report.set_multiple_harasser(False)
            return await self.add_multiple_messages()

        if self.state == State.IMMINENT_DANGER:
            if not message.content.strip().isdigit() or int(message.content) < 1 or int(message.content) > 3: 
                return ["Please select one of the imminent danger types or say `cancel` to cancel."]
            else:
                self.report.set_imminent_danger(imminent_danger_category[int(message.content)])
                return await self.add_multiple_messages()

        if self.state == State.ADD_MESSAGES: 
            reported_message_list = message.content.split()
            valid_message_list = list()
            for message in reported_message_list:
                m = re.search('/(\d+)/(\d+)/(\d+)', message)
                if not m:
                    continue
                guild = self.client.get_guild(int(m.group(1)))
                if not guild:
                    continue
                channel = guild.get_channel(int(m.group(2)))
                if not channel:
                    continue
                try:
                    message = await channel.fetch_message(int(m.group(3)))
                    valid_message_list.append(message)
                except discord.errors.NotFound:
                    continue
            self.report.add_other_messages(valid_message_list)
            self.state = State.SAFETY_MODE
            return ['''Do you want to turn on safety mode for your account?
This limits the people who can DM you or leave a message on your profile
This also slows down the number of message that can be left on your profile or sent to you
1. Yes
2. No'''
                ]

        if self.state == State.SAFETY_MODE:
            if not message.content.strip().isdigit() or int(message.content) < 1 or int(message.content) > 2: 
                return ["Please select either 1 (Yes) or 2 (No)."]
            channel = message.channel
            if int(message.content) == 1:
                await channel.send('We have activated safety mode on your account.')
                self.report.set_safety()
            self.state = State.BLOCK_AWAITED
            return ['''Do you wish to block the person you are reporting?
1. Yes
2. No'''
                    ]

        if self.state == State.BLOCK_AWAITED:
            if not message.content.strip().isdigit() or int(message.content) < 1 or int(message.content) > 2: 
                return ["Please select either 1 (Yes) or 2 (No)."]
            channel = message.channel
            if int(message.content) == 1:
                blocklist = set()
                blocklist.add(self.report.message.author.name)
                if len(self.report.other_messages) > 0:
                    for message in self.report.other_messages:
                        blocklist.add(message.author.name)
                for user in blocklist:
                    await channel.send(f'We have blocked {user} for you.')
                    self.report.set_block_user(user)
            return await self.complete_report()

    async def add_multiple_messages(self):
        self.state = State.ADD_MESSAGES
        return ['''Are there any other similar messages that you would like to report?
They will be filed under separate reports
Please copy and paste all the links to the messages you want to report separated by spaces or shift-enter
You can obtain this link by right-clicking the message and clicking `Copy Message Link`.
or type skip to skip.'''
                ]

    async def complete_report(self):
        # Set state to end
        self.state = State.REPORT_COMPLETE
        return_string = list()
        # Store report in list
        globals.reports[self.report.id] = self.report
        return_string.append(await self.send_reports(self.report))
        # Generate new reports if multiple messages were added
        if len(self.report.other_messages) > 0:
            for message in self.report.other_messages:
                new_report = reported_message(self.report.reporter, message)
                new_report.set_type(self.report.abuse_type)
                if new_report.abuse_type == "Other":
                    new_report.set_other(self.report.other_details)
                elif new_report.abuse_type == "Harassment":
                    new_report.set_harassment_type(self.report.harassment_type)
                    new_report.set_multiple_harasser(self.report.multiple_harasser)
                elif new_report.abuse_type == "Imminent Danger":
                    new_report.set_imminent_danger(self.report.imminent_danger)
                if self.report.safety_mode == True:
                    new_report.set_safety()
                if len(self.report.block_user) > 0:
                    new_report.set_block_user(message.author.name)
                globals.reports[new_report.id] = new_report
                return_string.append(await self.send_reports(new_report))
        return return_string
    
    async def send_reports(self, report):
        # Forward the report to the mod channel
        reporter = report.reporter
        message = report.message
        mod_channel = self.client.mod_channels[message.guild.id]
        report_string = f'''Report {report.id} at time {report.report_created_time.astimezone()}:
\tReported message:
\t{message.author.name}: "{message.content}"
\tLink:{message.jump_url}
\tReporter: {reporter.name}
\tAbuse Type: {self.report.abuse_type}\n'''
        if report.abuse_type == "Other":
            report_string += f'''\t\tAbuse Type Details: {report.other_details}\n'''  
        elif report.abuse_type == "Harassment":
            report_string += f'''\t\tHarassment Type: {report.harassment_type}\n'''
            report_string += f'''\t\tMultiple Harassers: {report.multiple_harasser}\n'''
        elif report.abuse_type == "Imminent Danger":
            report_string += f'\t\tImminent Danger Type: {report.imminent_danger}\n'
        report_string += f'\tHas reporter turned on safety mode: {report.safety_mode}\n'
        report_string += f'\tHas reporter blocked message sender: {report.message.author.name in report.block_user}\n'
        report_string += '''Press ⏱️ to place abuser under slow mode.
Press 🛑 to block abuser for reporter.
Press 🗑️ to delete the message.\n'''
        if globals.user_followers[message.author.name] > 5000:
            report_string += 'Press ‼️ to send strike and warning to abuser.\n'
        else: 
            report_string += 'Press ❗ to send strike and warning to abuser.\n'
        report_string += '''Press ❌ to ban abuser.
Press ❔ to strike reporter for false report. (Only strike if false report is intentional and malicious)
Press ⬆️ to escalate to a specialized team that handles organized harassment'''
        sent_report = await mod_channel.send(report_string)
        await sent_report.add_reaction(emoji="⏱️")
        await sent_report.add_reaction(emoji="🛑")
        await sent_report.add_reaction(emoji="🗑️")
        if globals.user_followers[message.author.name] > 5000:
            await sent_report.add_reaction(emoji="‼️")
        else: 
            await sent_report.add_reaction(emoji="❗")
        await sent_report.add_reaction(emoji="❌")
        await sent_report.add_reaction(emoji="❔")
        await sent_report.add_reaction(emoji="⬆️")

        globals.report_message_to_id[sent_report.id] = report.id

        # send endstring
        if report.abuse_type == "Harassment":
            endstring = f'''Thank you for reporting {report.abuse_type}. Your report has been filed as report {report.id}.
We will notify you when your report has been reviewed and appropriate actions has been taken.
This may include a warning or banning the user and removing the content.'''
        elif report.abuse_type == "Imminent Danger":
            endstring = f'''Thank you for reporting {report.abuse_type}. Your report has been filed as report {report.id}.
We will notify you when your report has been reviewed and appropriate actions has been taken.
This may include notification of authorities if necessary.'''
        else:
            endstring = f'''Thank you for reporting {report.abuse_type}. Your report has been filed as report {report.id}.
We will notify you when your report has been reviewed and appropriate actions has been taken.
This may include removing the content.'''
        return endstring 

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE
    


    

