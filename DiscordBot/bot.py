# bot.py
import discord
from discord.ext import commands
import os
import json
import logging
import re
import requests
from report import Report
import pdb
import globals

# Set up logging to the console
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

# There should be a file called 'tokens.json' inside the same folder as this file
token_path = 'tokens.json'
if not os.path.isfile(token_path):
    raise Exception(f"{token_path} not found!")
with open(token_path) as f:
    # If you get an error here, it means your token is formatted incorrectly. Did you put it in quotes?
    tokens = json.load(f)
    discord_token = tokens['discord']


class ModBot(discord.Client):
    def __init__(self): 
        intents = discord.Intents.default()
        intents.messages = True
        super().__init__(command_prefix='.', intents=intents)
        self.group_num = None
        self.mod_channels = {} # Map from guild to the mod channel id for that guild
        self.auto_mod_channels = {} # Map from guild to the automatic forwarding mod channel id for that guild
        self.reports = {} # Map from user IDs to the state of their report

    async def on_ready(self):
        print(f'{self.user.name} has connected to Discord! It is these guilds:')
        for guild in self.guilds:
            print(f' - {guild.name}')
        print('Press Ctrl-C to quit.')

        # Parse the group number out of the bot's name
        match = re.search('[gG]roup (\d+) [bB]ot', self.user.name)
        if match:
            self.group_num = match.group(1)
        else:
            raise Exception("Group number not found in bot's name. Name format should be \"Group # Bot\".")

        # Find the mod channel in each guild that this bot should report to
        for guild in self.guilds:
            for channel in guild.text_channels:
                if channel.name == f'group-{self.group_num}-human-mod':
                    self.mod_channels[guild.id] = channel
                elif channel.name == f'group-{self.group_num}-mod':
                    self.auto_mod_channels[guild.id] = channel

    async def on_message(self, message):
        '''
        This function is called whenever a message is sent in a channel that the bot can see (including DMs). 
        Currently the bot is configured to only handle messages that are sent over DMs or in your group's "group-#" channel. 
        '''
        # Ignore messages from the bot 
        if message.author.id == self.user.id:
            return

        # Check if this message was sent in a server ("guild") or if it's a DM
        if message.guild:
            await self.handle_channel_message(message)
        else:
            await self.handle_dm(message)

    async def handle_dm(self, message):
        # Handle a help message
        if message.content == Report.HELP_KEYWORD:
            reply =  "Use the `report` command to begin the reporting process.\n"
            reply += "Use the `cancel` command to cancel the report process.\n"
            await message.channel.send(reply)
            return

        author_id = message.author.id
        responses = []

        # Only respond to messages if they're part of a reporting flow
        if author_id not in self.reports and not message.content.startswith(Report.START_KEYWORD):
            return

        # If we don't currently have an active report for this user, add one
        if author_id not in self.reports:
            self.reports[author_id] = Report(self)

        # Let the report class handle this message; forward all the messages it returns to uss
        responses = await self.reports[author_id].handle_message(message)
        for r in responses:
            await message.channel.send(r)

        # If the report is complete or cancelled, remove it from our map
        if self.reports[author_id].report_complete():
            self.reports.pop(author_id)

    async def handle_channel_message(self, message):
        # Only handle messages sent in the "group-#" channel
        if not message.channel.name == f'group-{self.group_num}':
            return

        # Forward the message to the mod channel
        mod_channel = self.auto_mod_channels[message.guild.id]
        await mod_channel.send(f'Forwarded message:\n{message.author.name}: "{message.content}"')
        scores = self.eval_text(message.content)
        await mod_channel.send(self.code_format(scores))

    async def on_raw_reaction_add(self, payload):
        if not payload.channel_id == self.mod_channels[payload.guild_id].id:
            return  
        if not payload.message_id in globals.report_message_to_id.keys():
            return
        if not payload.emoji.name in ["⏱️", "🛑", "🗑️", "❗", "‼️", "❌", "❔", "⬆️"]:
            return
        if payload.member.id == self.user.id:
            return
        report_id = globals.report_message_to_id[payload.message_id]
        report = globals.reports[report_id]
        reporter = report.reporter
        abuser = report.message.author
        abuser_dm = abuser.dm_channel if abuser.dm_channel else await abuser.create_dm()
        reporter_dm = reporter.dm_channel if reporter.dm_channel else await reporter.create_dm()
        if payload.emoji.name == "⏱️":
            await abuser_dm.send(f'''Your message {report.message.jump_url} with text {report.message.content} has been reported for {report.abuse_type}. 
As such, your account would be placed under slow mode for the next 72 hours.''')
            await reporter_dm.send(f'Your report {report.id} has been resolved. The abuser has been placed under slow mode.')
        elif payload.emoji.name == "🛑":
            await reporter_dm.send(f'Your report {report.id} has been resolved. All messages from the abuser will now be blocked.')
        elif payload.emoji.name == "🗑️":
            await report.message.delete()
            await abuser_dm.send(f'''Your message {report.message.jump_url} with text {report.message.content} has been reported for {report.abuse_type}. 
As such, your message has been deleted.''')
            await reporter_dm.send(f'Your report {report.id} has been resolved. The message has been deleted.')
        elif payload.emoji.name == "❌":
            await abuser_dm.send(f'''Your message {report.message.jump_url} with text {report.message.content} has been reported for {report.abuse_type}.
Your account has been banned for abuse.''')
            await reporter_dm.send(f'Your report {report.id} has been resolved. The abuser has been banned.')
        elif payload.emoji.name == "⬆️":
            await reporter_dm.send(f'Your report {report.id} has been escalated to a specialized team.')
        elif payload.emoji.name == "❔":
            if reporter not in globals.user_false_report_strikes:
                globals.user_false_report_strikes[reporter] = list()
            while True:
                if len(globals.user_false_report_strikes[reporter]) == 0:
                    break
                strike = globals.user_false_report_strikes[reporter][0]
                timediff = report.report_created_time - strike.report_created_time
                if timediff.days >= 30:
                    globals.user_false_report_strikes[reporter].pop(0) 
                else:
                    break
            globals.user_false_report_strikes[reporter].append(report)
            if len(globals.user_false_report_strikes[reporter]) < 3:
                await reporter_dm.send(f'''Your report {report.id} has been resolved and classified as a malicious false report.
You have been given a strike and is currently at {len(globals.user_false_report_strikes[reporter])} strikes.
You would be banned if you reach 3 strikes. Please refrain from filing malicious false reports.''')
            else:
                await reporter_dm.send(f'''Your report {report.id} has been resolved and classified as a malicious false report.
You have reached three strikes for false reports. 
Your account has been banned for filing malicious false reports.''')
        elif payload.emoji.name == "❗" or payload.emoji.name == "‼️":
            if abuser not in globals.user_strikes:
                globals.user_strikes[abuser] = list()
            while True:
                if len(globals.user_strikes[abuser]) == 0:
                    break
                strike = globals.user_strikes[abuser][0]
                timediff = report.report_created_time - strike.report_created_time
                if timediff.days >= 365:
                    globals.user_strikes[abuser].pop(0) 
                else:
                    break
            globals.user_strikes[abuser].append(report)
            if len(globals.user_strikes[abuser]) == 2 and payload.emoji.name == "‼️":
                await abuser_dm.send(f'''Your message {report.message.jump_url} with text {report.message.content} has been reported for {report.abuse_type}. 
Your account has been given a strike for abuse and is currently at {len(globals.user_strikes[abuser])} strikes.
Since you have a large account, your account has been slowed down for 2 strikes. 
You would be banned if you reach 3 strikes.
As a large account, please demonstrate caution before sharing or posting and refrain from posting any abuse''')
                await reporter_dm.send(f'Your report {report.id} has been resolved. The abuser has been placed on slow mode.')
            elif len(globals.user_strikes[abuser]) < 3:
                if payload.emoji.name == "❗":
                    await abuser_dm.send(f'''Your message {report.message.jump_url} with text {report.message.content} has been reported for {report.abuse_type}. 
Your account has been given a strike for abuse and is currently at {len(globals.user_strikes[abuser])} strikes.
You would be banned if you reach 3 strikes.
Please refrain from posting abuse.''')
                else:
                    await abuser_dm.send(f'''Your message {report.message.jump_url} with text {report.message.content} has been reported for {report.abuse_type}. 
Your account has been given a strike for abuse and is currently at {len(globals.user_strikes[abuser])} strikes.
Since you have a large account, your account would be slowed down if you reach 2 strikes. 
You would be banned if you reach 3 strikes.
As a large account, please demonstrate caution before sharing or posting and refrain from posting any abuse''')
                await reporter_dm.send(f'Your report {report.id} has been resolved. The abuser has been given a strike.')
            else:
                await abuser_dm.send(f'''Your message {report.message.jump_url} with text {report.message.content} has been reported for {report.abuse_type}.
You have reached three strikes for abuses.
Your account has been banned.''')
                await reporter_dm.send(f'Your report {report.id} has been resolved. The abuser has been banned.')
            


    def eval_text(self, message):
        ''''
        TODO: Once you know how you want to evaluate messages in your channel, 
        insert your code here! This will primarily be used in Milestone 3. 
        '''
        return message

    
    def code_format(self, text):
        ''''
        TODO: Once you know how you want to show that a message has been 
        evaluated, insert your code here for formatting the string to be 
        shown in the mod channel. 
        '''
        return "Evaluated: '" + text+ "'"


client = ModBot()
client.run(discord_token)