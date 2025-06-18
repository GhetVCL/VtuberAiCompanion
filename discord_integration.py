"""
Discord Integration for Z-Waif AI VTuber
Handles Discord bot functionality with memory integration
"""

import discord
from discord.ext import commands
import asyncio
import json
import os
from typing import Dict, Any, Optional
from datetime import datetime
from memory_rag_system import memory_rag_system
import google.generativeai as genai

class ZWaifDiscordBot(commands.Bot):
    """Discord bot for Z-Waif AI VTuber"""
    
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True
        
        super().__init__(
            command_prefix='!aria ',
            intents=intents,
            description='Z-Waif AI VTuber Discord Bot'
        )
        
        self.ai_model = None
        self.initialize_ai()
        
        # Bot configuration
        self.response_channels = set()  # Channels where bot should respond
        self.user_sessions = {}  # Track user conversation sessions
        
    def initialize_ai(self):
        """Initialize Gemini AI model"""
        try:
            api_key = os.getenv('GEMINI_API_KEY')
            if api_key:
                genai.configure(api_key=api_key)
                self.ai_model = genai.GenerativeModel("gemini-2.0-flash-exp")
                print("Discord bot AI initialized")
            else:
                print("Warning: No Gemini API key found for Discord bot")
        except Exception as e:
            print(f"Error initializing Discord bot AI: {e}")
    
    async def on_ready(self):
        """Called when bot is ready"""
        print(f'{self.user.name} has connected to Discord!')
        print(f'Bot is in {len(self.guilds)} guilds')
        
        # Set bot presence
        activity = discord.Activity(
            type=discord.ActivityType.streaming,
            name="AI VTuber Stream"
        )
        await self.change_presence(activity=activity)
    
    async def on_message(self, message):
        """Handle incoming messages"""
        # Ignore bot's own messages
        if message.author == self.user:
            return
        
        # Process commands first
        await self.process_commands(message)
        
        # Check if bot should respond in this channel
        if (message.channel.id in self.response_channels or 
            isinstance(message.channel, discord.DMChannel) or
            self.user.mentioned_in(message)):
            
            await self.handle_ai_response(message)
    
    async def handle_ai_response(self, message):
        """Generate and send AI response"""
        try:
            user_id = f"discord_{message.author.id}"
            user_message = message.content
            
            # Remove bot mention from message
            if self.user.mentioned_in(message):
                user_message = user_message.replace(f'<@{self.user.id}>', '').strip()
            
            if not user_message:
                return
            
            # Show typing indicator
            async with message.channel.typing():
                # Get enhanced context from memory system
                context = memory_rag_system.build_context_for_response(user_message, user_id)
                
                # Build Discord-specific prompt
                enhanced_prompt = f"""
{context}

Current Discord message from {message.author.display_name}: {user_message}

Respond as Aria, the AI VTuber, in Discord chat style. Keep responses:
- Conversational and engaging
- Appropriate for Discord (use some Discord formatting if helpful)
- Reference relevant memories when appropriate
- Not too long (Discord has message limits)

Use the context above to provide a personalized response.
"""
                
                # Generate response
                if self.ai_model:
                    response = self.ai_model.generate_content(enhanced_prompt)
                    ai_response = response.text
                else:
                    ai_response = "I'm having trouble connecting to my AI brain right now."
                
                # Split long messages if needed
                if len(ai_response) > 2000:
                    chunks = [ai_response[i:i+1900] for i in range(0, len(ai_response), 1900)]
                    for chunk in chunks:
                        await message.channel.send(chunk)
                else:
                    await message.channel.send(ai_response)
                
                # Store conversation in memory system
                memory_rag_system.store_conversation(
                    user_id=user_id,
                    user_message=user_message,
                    ai_response=ai_response,
                    platform='discord',
                    session_id=f"discord_channel_{message.channel.id}"
                )
                
                # Update user profile
                context_data = memory_rag_system._extract_context(user_message, ai_response)
                context_data['discord_user'] = {
                    'username': message.author.name,
                    'display_name': message.author.display_name,
                    'guild': message.guild.name if message.guild else 'DM'
                }
                memory_rag_system.update_user_profile(user_id, context_data)
        
        except Exception as e:
            print(f"Error handling Discord message: {e}")
            await message.channel.send("Sorry, I encountered an error processing your message.")
    
    @commands.command(name='hello')
    async def hello_command(self, ctx):
        """Say hello to the bot"""
        await ctx.send(f"Hello {ctx.author.mention}! I'm Aria, your AI VTuber assistant!")
    
    @commands.command(name='enable')
    @commands.has_permissions(manage_channels=True)
    async def enable_channel(self, ctx):
        """Enable bot responses in current channel"""
        self.response_channels.add(ctx.channel.id)
        await ctx.send("I'll now respond to messages in this channel!")
    
    @commands.command(name='disable')
    @commands.has_permissions(manage_channels=True)
    async def disable_channel(self, ctx):
        """Disable bot responses in current channel"""
        self.response_channels.discard(ctx.channel.id)
        await ctx.send("I'll stop responding to messages in this channel.")
    
    @commands.command(name='memory')
    async def memory_stats(self, ctx):
        """Show memory statistics for the user"""
        user_id = f"discord_{ctx.author.id}"
        stats = memory_rag_system.get_conversation_stats(user_id)
        
        embed = discord.Embed(
            title="Memory Statistics",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="Conversations",
            value=f"{stats.get('total_conversations', 0)} total\n{stats.get('recent_conversations', 0)} this week",
            inline=True
        )
        embed.add_field(
            name="Memories",
            value=f"{stats.get('total_memories', 0)} stored",
            inline=True
        )
        embed.add_field(
            name="Status",
            value=stats.get('system_status', 'unknown'),
            inline=True
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(name='forget')
    async def forget_user(self, ctx):
        """Allow user to request forgetting their data"""
        user_id = f"discord_{ctx.author.id}"
        
        embed = discord.Embed(
            title="Data Deletion Request",
            description="To delete your conversation data, please contact the bot administrator.",
            color=discord.Color.orange()
        )
        embed.add_field(
            name="Your User ID",
            value=user_id,
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(name='personality')
    async def set_personality(self, ctx, *, personality_trait: str = None):
        """Set or view personality preferences"""
        user_id = f"discord_{ctx.author.id}"
        
        if not personality_trait:
            # Show current preferences
            embed = discord.Embed(
                title="Personality Preferences",
                description="Use `!aria personality <trait>` to set preferences",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
        else:
            # Store personality preference
            context_data = {
                'personality_preference': personality_trait,
                'set_at': datetime.utcnow().isoformat()
            }
            memory_rag_system.update_user_profile(user_id, context_data)
            await ctx.send(f"Personality preference set: {personality_trait}")
    
    @commands.command(name='status')
    async def bot_status(self, ctx):
        """Show bot status and statistics"""
        embed = discord.Embed(
            title="Aria Bot Status",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="Servers",
            value=len(self.guilds),
            inline=True
        )
        embed.add_field(
            name="Active Channels",
            value=len(self.response_channels),
            inline=True
        )
        embed.add_field(
            name="AI Model",
            value="Gemini 2.5 Flash" if self.ai_model else "Offline",
            inline=True
        )
        
        # Get overall stats
        total_stats = memory_rag_system.get_conversation_stats()
        embed.add_field(
            name="Total Conversations",
            value=total_stats.get('total_conversations', 0),
            inline=True
        )
        embed.add_field(
            name="Total Memories",
            value=total_stats.get('total_memories', 0),
            inline=True
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(name='stream')
    async def stream_info(self, ctx):
        """Show streaming information"""
        embed = discord.Embed(
            title="Z-Waif AI VTuber Stream",
            description="Real-time AI VTuber with advanced memory and personality",
            color=discord.Color.purple()
        )
        
        embed.add_field(
            name="Features",
            value="• Persistent memory\n• Personalized responses\n• Real-time streaming\n• Multi-platform support",
            inline=False
        )
        
        embed.add_field(
            name="Platforms",
            value="• Discord\n• Web Interface\n• Streaming Services",
            inline=True
        )
        
        await ctx.send(embed=embed)

class DiscordManager:
    """Manages Discord bot integration"""
    
    def __init__(self):
        self.bot = None
        self.is_running = False
        self.token = os.getenv('DISCORD_BOT_TOKEN')
    
    def start_bot(self):
        """Start Discord bot"""
        if not self.token:
            print("Warning: No Discord bot token found. Discord integration disabled.")
            return False
        
        try:
            self.bot = ZWaifDiscordBot()
            
            # Run bot in background
            import threading
            
            def run_bot():
                asyncio.set_event_loop(asyncio.new_event_loop())
                loop = asyncio.get_event_loop()
                loop.run_until_complete(self.bot.start(self.token))
            
            bot_thread = threading.Thread(target=run_bot, daemon=True)
            bot_thread.start()
            
            self.is_running = True
            print("Discord bot started in background")
            return True
            
        except Exception as e:
            print(f"Error starting Discord bot: {e}")
            return False
    
    def stop_bot(self):
        """Stop Discord bot"""
        if self.bot:
            asyncio.create_task(self.bot.close())
            self.is_running = False
            print("Discord bot stopped")
    
    def get_bot_status(self) -> Dict[str, Any]:
        """Get bot status information"""
        if not self.bot:
            return {'status': 'not_initialized'}
        
        return {
            'status': 'running' if self.is_running else 'stopped',
            'guilds': len(self.bot.guilds) if self.bot.guilds else 0,
            'user': str(self.bot.user) if self.bot.user else None,
            'response_channels': len(self.bot.response_channels)
        }

# Global Discord manager instance
discord_manager = DiscordManager()