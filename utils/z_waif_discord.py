"""
Discord Integration - Connects Z-Waif to Discord for chat interaction
Allows the AI to participate in Discord conversations
"""

import discord
import asyncio
import threading
import os
import time
from typing import Optional, List
import utils.zw_logging
import utils.settings
import main

# Discord variables
discord_client = None
discord_enabled = True
target_channels = []
bot_token = "MTM4NDczNDg1OTA0OTgzMjQ5OA.G5WoFV.1r8o6kHreM5CDNazh7iAAt9s_uAmGM_T2a0De8"
command_prefix = "!"
last_message_time = 0
message_cooldown = 2.0

class ZWaifDiscordClient(discord.Client):
    """Custom Discord client for Z-Waif"""
    
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
    
    async def on_ready(self):
        """Called when bot is ready"""
        utils.zw_logging.update_debug_log(f"Discord bot connected as {self.user}")
        print(f"Discord bot ready: {self.user}")
    
    async def on_message(self, message):
        """Handle incoming Discord messages"""
        global last_message_time
        
        # Ignore messages from the bot itself
        if message.author == self.user:
            return
        
        # Check if message is in target channels
        if target_channels and message.channel.id not in target_channels:
            return
        
        # Check cooldown
        current_time = time.time()
        if current_time - last_message_time < message_cooldown:
            return
        
        try:
            # Process message
            await self.process_discord_message(message)
            last_message_time = current_time
            
        except Exception as e:
            utils.zw_logging.update_debug_log(f"Discord message processing error: {e}")
    
    async def process_discord_message(self, message):
        """Process Discord message and generate response"""
        try:
            # Check if bot is mentioned or message starts with prefix
            bot_mentioned = self.user in message.mentions
            starts_with_prefix = message.content.startswith(command_prefix)
            
            # Only respond if mentioned or prefixed (or in DM)
            if not (bot_mentioned or starts_with_prefix or isinstance(message.channel, discord.DMChannel)):
                return
            
            # Clean message content
            content = message.content
            if starts_with_prefix:
                content = content[len(command_prefix):].strip()
            
            # Remove mentions
            content = content.replace(f'<@{self.user.id}>', '').strip()
            
            if not content:
                return
            
            # Format message for AI
            discord_context = f"Discord message from {message.author.display_name}: {content}"
            
            # Send to main chat handler
            main.main_discord_chat(discord_context)
            
            # Get AI response
            import API.gemini_controller
            response = API.gemini_controller.get_last_response()
            
            if response:
                # Clean response for Discord
                discord_response = self.clean_response_for_discord(response)
                
                # Send response
                if len(discord_response) <= 2000:  # Discord character limit
                    await message.channel.send(discord_response)
                else:
                    # Split long messages
                    chunks = self.split_message(discord_response, 2000)
                    for chunk in chunks[:3]:  # Max 3 chunks
                        await message.channel.send(chunk)
                        await asyncio.sleep(0.5)
            
        except Exception as e:
            utils.zw_logging.update_debug_log(f"Discord message processing error: {e}")
            await message.channel.send("Sorry, I had trouble processing that message!")
    
    def clean_response_for_discord(self, response: str) -> str:
        """Clean AI response for Discord"""
        # Remove excessive newlines
        response = '\n'.join(line for line in response.split('\n') if line.strip())
        
        # Escape Discord markdown if needed
        # response = discord.utils.escape_markdown(response)
        
        return response.strip()
    
    def split_message(self, message: str, max_length: int) -> List[str]:
        """Split long message into chunks"""
        if len(message) <= max_length:
            return [message]
        
        chunks = []
        current_chunk = ""
        
        for line in message.split('\n'):
            if len(current_chunk) + len(line) + 1 <= max_length:
                current_chunk += line + '\n'
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = line + '\n'
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks


def initialize():
    """Initialize Discord integration"""
    global discord_enabled, bot_token, target_channels, command_prefix
    
    discord_enabled = utils.settings.discord_enabled
    
    if not discord_enabled:
        utils.zw_logging.update_debug_log("Discord integration disabled")
        return
    
    # Load Discord configuration
    bot_token = os.getenv("DISCORD_BOT_TOKEN", "")
    command_prefix = os.getenv("DISCORD_COMMAND_PREFIX", "!")
    
    # Parse target channels
    channels_str = os.getenv("DISCORD_TARGET_CHANNELS", "")
    if channels_str:
        try:
            target_channels = [int(ch.strip()) for ch in channels_str.split(',') if ch.strip()]
        except ValueError:
            utils.zw_logging.update_debug_log("Invalid Discord channel IDs in config")
    
    if not bot_token:
        utils.zw_logging.update_debug_log("Discord bot token not provided")
        return
    
    # Start Discord client
    start_discord_client()


def start_discord_client():
    """Start Discord client in background thread"""
    global discord_client
    
    def run_discord():
        try:
            discord_client = ZWaifDiscordClient()
            
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Run the Discord client
            loop.run_until_complete(discord_client.start(bot_token))
            
        except Exception as e:
            utils.zw_logging.update_debug_log(f"Discord client error: {e}")
    
    discord_thread = threading.Thread(target=run_discord)
    discord_thread.daemon = True
    discord_thread.start()
    
    utils.zw_logging.update_debug_log("Discord client started")


def send_discord_message(channel_id: int, message: str):
    """Send message to specific Discord channel"""
    if not discord_client or not discord_client.is_ready():
        utils.zw_logging.update_debug_log("Discord client not ready")
        return False
    
    async def send_message():
        try:
            channel = discord_client.get_channel(channel_id)
            if channel:
                await channel.send(message)
                return True
            else:
                utils.zw_logging.update_debug_log(f"Discord channel {channel_id} not found")
                return False
        except Exception as e:
            utils.zw_logging.update_debug_log(f"Discord send error: {e}")
            return False
    
    # Schedule the coroutine
    if discord_client.loop and discord_client.loop.is_running():
        asyncio.create_task(send_message())
        return True
    
    return False


def get_discord_status():
    """Get Discord integration status"""
    status = {
        "enabled": discord_enabled,
        "connected": False,
        "user": None,
        "target_channels": target_channels,
        "command_prefix": command_prefix
    }
    
    if discord_client:
        status["connected"] = discord_client.is_ready()
        if discord_client.user:
            status["user"] = str(discord_client.user)
    
    return status


def set_discord_status(status_text: str, activity_type: str = "playing"):
    """Set Discord bot status"""
    if not discord_client or not discord_client.is_ready():
        return False
    
    async def update_status():
        try:
            activity_types = {
                "playing": discord.ActivityType.playing,
                "listening": discord.ActivityType.listening,
                "watching": discord.ActivityType.watching,
                "streaming": discord.ActivityType.streaming
            }
            
            activity = discord.Activity(
                type=activity_types.get(activity_type, discord.ActivityType.playing),
                name=status_text
            )
            
            await discord_client.change_presence(activity=activity)
            utils.zw_logging.update_debug_log(f"Discord status updated: {status_text}")
            
        except Exception as e:
            utils.zw_logging.update_debug_log(f"Discord status update error: {e}")
    
    if discord_client.loop and discord_client.loop.is_running():
        asyncio.create_task(update_status())
        return True
    
    return False


def add_target_channel(channel_id: int):
    """Add channel to target list"""
    global target_channels
    
    if channel_id not in target_channels:
        target_channels.append(channel_id)
        utils.zw_logging.update_debug_log(f"Added Discord target channel: {channel_id}")


def remove_target_channel(channel_id: int):
    """Remove channel from target list"""
    global target_channels
    
    if channel_id in target_channels:
        target_channels.remove(channel_id)
        utils.zw_logging.update_debug_log(f"Removed Discord target channel: {channel_id}")


def disconnect_discord():
    """Disconnect from Discord"""
    global discord_client, discord_enabled
    
    if discord_client:
        async def disconnect():
            await discord_client.close()
        
        if discord_client.loop and discord_client.loop.is_running():
            asyncio.create_task(disconnect())
    
    discord_enabled = False
    utils.zw_logging.update_debug_log("Discord disconnected")


# Initialize if enabled
if utils.settings.discord_enabled:
    initialize()
