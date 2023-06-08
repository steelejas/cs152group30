# bot.py
import discord
from discord.ext import commands
import os
import json
import logging
import re
import requests
from report import Report, send_autoreport, reported_message
import pdb
import globals
#import badwordlist
from blocklist import BlocklistInteraction, blocklist, blockregex
from unidecode import unidecode
from gpt_pii import check_post_for_pii
from datetime import datetime, timezone
from perspective_api import checkpost_perspective
from openai_harassment import checkpost_openai
import uuid

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

perspective_attributes = {"TOXICITY":0.5,"SPAM":0.7,"IDENTITY_ATTACK":0.5,"INSULT":0.5,"THREAT":0.8}

class ModBot(discord.Client):
    def __init__(self): 
        intents = discord.Intents.default()
        try: 
            intents.message_content = True
        except: 
            intents.messages = True
        super().__init__(command_prefix='.', intents=intents)
        self.group_num = None
        self.mod_channels = {} # Map from guild to the mod channel id for that guild
        self.auto_mod_channels = {} # Map from guild to the automatic forwarding mod channel id for that guild
        self.reports = {} # Map from user IDs to the state of their report
        self.blocklist_interaction = {} # Map from user ID to current interaction with blocklist

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
            reply += "Use the `list` command to see past reports filed.\n"
            reply += "Use the `search {report_id}` command to see status of report with corresponding id.\n"
            reply += "Use the `strike` command to see your content strikes and false report strikes.\n"
            reply += "Use the `blocklist` command to see blocklist, blocked regex, and add or remove words or regex from the blocklist.\n"
            await message.channel.send(reply)
            return

        author_id = message.author.id
        responses = []

        if author_id in self.reports:
            # Let the report class handle this message; forward all the messages it returns to uss
            responses = await self.reports[author_id].handle_message(message)
            if responses is None:
                self.reports[author_id] = Report(self)
                responses = await self.reports[author_id].handle_message(message)
            for r in responses:
                await message.channel.send(r)

            # If the report is complete or cancelled, remove it from our map
            if self.reports[author_id].report_complete():
                self.reports.pop(author_id)
        
        elif author_id in self.blocklist_interaction:
            # Let the report class handle this message; forward all the messages it returns to uss
            responses = await self.blocklist_interaction[author_id].handle_message(message)
            if responses is None:
                self.blocklist_interaction[author_id] = BlocklistInteraction(self)
                responses = await self.blocklist_interaction[author_id].handle_message(message)
            for r in responses:
                await message.channel.send(r)

            # If the report is complete or cancelled, remove it from our map
            if self.blocklist_interaction[author_id].blocklist_complete():
                self.blocklist_interaction.pop(author_id)

        elif message.content.startswith(Report.START_KEYWORD):
            self.reports[author_id] = Report(self)
            # Let the report class handle this message; forward all the messages it returns to uss
            responses = await self.reports[author_id].handle_message(message)
            for r in responses:
                await message.channel.send(r)

            # If the report is complete or cancelled, remove it from our map
            if self.reports[author_id].report_complete():
                self.reports.pop(author_id)
        
        elif message.content.startswith(BlocklistInteraction.START_KEYWORD):
            self.blocklist_interaction[author_id] = BlocklistInteraction(self)
            # Let the report class handle this message; forward all the messages it returns to uss
            responses = await self.blocklist_interaction[author_id].handle_message(message)
            for r in responses:
                await message.channel.send(r)

            # If the report is complete or cancelled, remove it from our map
            if self.blocklist_interaction[author_id].blocklist_complete():
                self.blocklist_interaction.pop(author_id)

        elif message.content.startswith("list"):
            retString = 'Reports filed:\n'
            for id, report in globals.reports.items():
                if report.reporter == message.author:
                    retString += f'{id}\n'
            retString += '\n'
            await message.channel.send(retString)

        elif message.content.startswith("strike"):
            retString = f'{message.author}\'s strikes:\n'
            time = datetime.now(timezone.utc)
            user = message.author 
            if user not in globals.user_strikes:
                strike_number = 0
            else:
                while True:
                    if len(globals.user_strikes[user]) == 0:
                        break
                    strike = globals.user_strikes[user][0]
                    timediff = time - strike.report_created_time
                    if timediff.days >= 365:
                        globals.user_strikes[user].pop(0) 
                    else:
                        break
                strike_number = len(globals.user_strikes[user])
            retString += f'strikes: {strike_number}\n'

            if user not in globals.user_false_report_strikes:
                false_report_strike_number = 0
            else:
                while True:
                    if len(globals.user_false_report_strikes[user]) == 0:
                        break
                    strike = globals.user_false_report_strikes[user][0]
                    timediff = time - strike.report_created_time
                    if timediff.days >= 30:
                        globals.user_false_report_strikes[user].pop(0) 
                    else:
                        break
                false_report_strike_number = len(globals.user_false_report_strikes[user])
            retString += f'false report strikes: {false_report_strike_number}\n\n'
            await message.channel.send(retString)

        elif message.content.startswith("search"):
            if len(message.content.strip().split(' ')) != 2:
                await message.channel.send("Please search for report with command `search \{report_id\}`")
                return
            try:
                id = uuid.UUID(message.content.strip().split(' ')[1])
            except:
                return
            if id not in globals.reports or globals.reports[id].reporter != message.author:
                await message.channel.send("Invalid ID. Please search for a report id that you have filed.")
                return
            report = globals.reports[id]
            report_string = f'''Report {report.id} at time {report.report_created_time.astimezone()}:
\tReported message:
\t{report.message.author.name}: "{report.message.content}"
\tLink:{report.message.jump_url}
\tReporter: {report.reporter.name}
\tAbuse Type: {report.abuse_type}\n'''
            if report.abuse_type == "Other":
                report_string += f'''\t\tAbuse Type Details: {report.other_details}\n'''  
            elif report.abuse_type == "Harassment":
                report_string += f'''\t\tHarassment Type: {report.harassment_type}\n'''
                report_string += f'''\t\tMultiple Harassers: {report.multiple_harasser}\n'''
            elif report.abuse_type == "Imminent Danger":
                report_string += f'\t\tImminent Danger Type: {report.imminent_danger}\n'
            report_string += f'\tHas reporter turned on safety mode: {report.safety_mode}\n'
            report_string += f'\tIs this a false report: {report.false_report_strike}\n'
            report_string += f'\tHas the sender been placed on slow mode: {report.slow_mode}\n'
            report_string += f'\tHas the sender been blocked: {report.message.author.name in report.block_user}\n'
            report_string += f'\tHas the message been deleted: {report.deleted}\n'
            report_string += f'\tHas the message sender been given a strike: {report.strike}\n'
            report_string += f'\tHas the message been escalated: {report.escalation}\n'
            await message.channel.send(report_string)

        else:
            return


    async def handle_channel_message(self, message):
        # Only handle messages sent in the "group-#" channel
        if not message.channel.name == f'group-{self.group_num}':
            return

        # Forward the message to the mod channel
        mod_channel = self.auto_mod_channels[message.guild.id]
        await mod_channel.send(f'Forwarded message:\n{message.author.name}: "{message.content}"')
        score, reason = await self.eval_text(message)
        await mod_channel.send(self.code_format(message.content, score, reason))
        if score == 1:
            await message.delete()
            abuser = message.author
            abuser_dm = abuser.dm_channel if abuser.dm_channel else await abuser.create_dm()
            await abuser_dm.send(f'''Your message {message.jump_url} with text {message.content} has been deleted for reason: {reason}.''')

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
        if reporter != 'auto report': 
            reporter_dm = reporter.dm_channel if reporter.dm_channel else await reporter.create_dm()
        if payload.emoji.name == "⏱️":
            report.set_slow_mode()
            await abuser_dm.send(f'''Your message {report.message.jump_url} with text {report.message.content} has been reported for {report.abuse_type}. 
As such, your account would be placed under slow mode for the next 72 hours.''')
            if reporter != 'auto report': await reporter_dm.send(f'Your report {report.id} has been resolved. The abuser has been placed under slow mode.') 
        elif payload.emoji.name == "🛑":
            report.set_block_user(abuser.name)
            if reporter != 'auto report': await reporter_dm.send(f'Your report {report.id} has been resolved. All messages from the abuser will now be blocked.')
        elif payload.emoji.name == "🗑️":
            await report.message.delete()
            report.set_deleted()
            await abuser_dm.send(f'''Your message {report.message.jump_url} with text {report.message.content} has been reported for {report.abuse_type}. 
As such, your message has been deleted.''')
            if reporter != 'auto report': await reporter_dm.send(f'Your report {report.id} has been resolved. The message has been deleted.')
        elif payload.emoji.name == "❌":
            report.set_banned()
            await abuser_dm.send(f'''Your message {report.message.jump_url} with text {report.message.content} has been reported for {report.abuse_type}.
Your account has been banned for abuse. If you wish to appeal your ban, please go to our appeal website.''')
            if reporter != 'auto report': await reporter_dm.send(f'Your report {report.id} has been resolved. The abuser has been banned.')
        elif payload.emoji.name == "⬆️":
            report.set_escalation()
            if reporter != 'auto report': await reporter_dm.send(f'Your report {report.id} has been escalated to a specialized team.')
        elif payload.emoji.name == "❔":
            if reporter == 'auto report': 
                return
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
                report.set_false_report_strike()
                await reporter_dm.send(f'''Your report {report.id} has been resolved and classified as a malicious false report.
You have been given a strike and is currently at {len(globals.user_false_report_strikes[reporter])} strikes.
You would be restricted from filing reports if you reach 3 strikes. Please refrain from filing malicious false reports.''')
            else:
                await reporter_dm.send(f'''Your report {report.id} has been resolved and classified as a malicious false report.
You have reached three strikes for false reports. 
Your account has been restricted from filing further malicious reports. If you wish to appeal the restriction, please go to our appeal website.''')
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
            report.set_strike()
            if len(globals.user_strikes[abuser]) == 2 and payload.emoji.name == "‼️":
                await abuser_dm.send(f'''Your message {report.message.jump_url} with text {report.message.content} has been reported for {report.abuse_type}. 
Your account has been given a strike for abuse and is currently at {len(globals.user_strikes[abuser])} strikes.
Since you have a large account, your account has been slowed down for 2 strikes. 
You would be banned if you reach 3 strikes.
As a large account, please demonstrate caution before sharing or posting and refrain from posting any abuse''')
                if reporter != 'auto report': await reporter_dm.send(f'Your report {report.id} has been resolved. The abuser has been placed on slow mode.')
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
                if reporter != 'auto report': await reporter_dm.send(f'Your report {report.id} has been resolved. The abuser has been given a strike.')
            else:
                report.set_banned()
                await abuser_dm.send(f'''Your message {report.message.jump_url} with text {report.message.content} has been reported for {report.abuse_type}.
You have reached three strikes for abuses.
Your account has been banned. If you wish to appeal your ban, please go to our appeal website.''')
                if reporter != 'auto report': await reporter_dm.send(f'Your report {report.id} has been resolved. The abuser has been banned.')
            


    async def eval_text(self, message):
        score = 0
        reason = "N/A"
        stripped_message = message.content.strip()
        unidecode_message = unidecode(stripped_message, errors='preserve')
        lowercase_message = unidecode_message.lower()
        for word in blocklist:
            if word in lowercase_message:
                score = 1
                start_pos = lowercase_message.find(word)
                end_pos = start_pos + len(word)
                reason = f"contains blocked word or expression: `{word}` at " + \
                f"\"{stripped_message[0: start_pos]}`{stripped_message[start_pos: end_pos]}`{stripped_message[end_pos: len(stripped_message)]}\""
                return score, reason
        for regex in blockregex:
            if re.search(regex, unidecode_message):
                start_pos = re.search(regex, unidecode_message).span()[0]
                end_pos = re.search(regex, unidecode_message).span()[1]
                score = 1
                reason = f"contains blocked regex `{regex}` at " + \
                f"\"{stripped_message[0: start_pos]}`{stripped_message[start_pos: end_pos]}`{stripped_message[end_pos: len(stripped_message)]}\""
                return score, reason
        if check_post_for_pii(unidecode_message):
            score = 1
            reason = "contains pii: home street"
            return score, reason
        
        perspective_result = checkpost_perspective(unidecode_message, perspective_attributes)
        openai_result = checkpost_openai(unidecode_message)

        if perspective_result[0] and openai_result:
            score=1
            reason= "post has been flagged by openai and perspective for potential harassment\n"
            return score,reason 
        elif perspective_result[0] or openai_result:
            report = reported_message('auto report', message)
            report.set_type('Other')
            if openai_result:
                other_details = 'Flagged by open ai'
            else:
                other_details = f'Flagged by perspective for high {perspective_result[1]} value'
            report.set_other(other_details)
            globals.reports[report.id] = report
            await send_autoreport(self.mod_channels[message.guild.id], report)
            score = 0.5
            if openai_result:
                reason = "post has been flagged by openai and a report was sent\n"
            else:
                reason = "post has been flagged by perspective and a report was sent\n"
            return score,reason
        return score,reason 


    
    def code_format(self, text, score, reason):
        ''''
        TODO: Once you know how you want to show that a message has been 
        evaluated, insert your code here for formatting the string to be 
        shown in the mod channel. 
        '''
        return "Evaluated: '" + text+ "': " + str(score) + ", reason: " + str(reason)


client = ModBot()
client.run(discord_token)