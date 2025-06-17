import sys
import time

import colorama
import humanize, os, threading
import emoji
import asyncio

import utils.audio
import utils.hotkeys
import utils.transcriber_translate
import utils.voice
import utils.vtube_studio
import utils.alarm
import utils.volume_listener
import utils.minecraft
import utils.log_conversion
import utils.cane_lib

import API.gemini_controller
import API.character_card
import API.task_profiles

import utils.lorebook
import utils.camera

import utils.z_waif_discord
import utils.web_ui

import utils.settings
import utils.retrospect
import utils.based_rag
import utils.tag_task_controller
import utils.gaming_control
import utils.hangout

import utils.uni_pipes
import utils.zw_logging

from dotenv import load_dotenv
load_dotenv()

TT_CHOICE = os.environ.get("WHISPER_CHOICE")
char_name = os.environ.get("CHAR_NAME", "Aria")

stored_transcript = "Issue with message cycling!"

undo_allowed = False
is_live_pipe = False

# Not for sure live pipe... atleast how it is counted now. Unipipes in a few updates will clear this up
# Livepipe is only for the hotkeys actions, that is why... but these are for non-hotkey stuff!
live_pipe_no_speak = False
live_pipe_force_speak_on_response = False
live_pipe_use_streamed_interrupt_watchdog = False


# noinspection PyBroadException
def main():
    """Main loop for the Z-Waif AI VTuber system"""
    print(f"{colorama.Fore.CYAN}Z-Waif AI VTuber Starting up...{colorama.Fore.RESET}")
    
    # Initialize all systems
    initialize_systems()
    
    print(f"{colorama.Fore.GREEN}System ready! Starting main loop...{colorama.Fore.RESET}")

    while True:
        print("You" + colorama.Fore.GREEN + colorama.Style.BRIGHT + " (mic) " + colorama.Fore.RESET + ">", end="", flush=True)

        # Stative control depending on what mode we are (gaming, streaming, normal, ect.)
        if utils.settings.is_gaming_loop:
            command = utils.gaming_control.gaming_step()
        else:
            command = utils.hotkeys.chat_input_await()

        # Flag us as running a command now
        global is_live_pipe
        is_live_pipe = True

        if command == "CHAT":
            utils.uni_pipes.start_new_pipe(desired_process="Main-Chat", is_main_pipe=True)

        elif command == "NEXT":
            utils.uni_pipes.start_new_pipe(desired_process="Main-Next", is_main_pipe=True)

        elif command == "REDO":
            utils.uni_pipes.start_new_pipe(desired_process="Main-Redo", is_main_pipe=True)

        elif command == "SOFT_RESET":
            utils.uni_pipes.start_new_pipe(desired_process="Main-Soft-Reset", is_main_pipe=True)

        elif command == "ALARM":
            utils.uni_pipes.start_new_pipe(desired_process="Main-Alarm", is_main_pipe=True)

        elif command == "VIEW":
            utils.uni_pipes.start_new_pipe(desired_process="Main-View-Image", is_main_pipe=True)

        elif command == "BLANK":
            utils.uni_pipes.start_new_pipe(desired_process="Main-Blank", is_main_pipe=True)

        elif command == "Hangout":
            utils.uni_pipes.start_new_pipe(desired_process="Hangout-Loop", is_main_pipe=True)

        # Wait until the main pipe we have sent is finished
        while utils.uni_pipes.main_pipe_running:
            # Sleep the loop while our main pipe still running
            time.sleep(0.001)

        # Stack wipe any current inputs, to avoid doing multiple in a row
        utils.hotkeys.stack_wipe_inputs()

        # For semi-autochat, press the button
        if utils.settings.semi_auto_chat:
            utils.hotkeys.speak_input_toggle_from_ui()

        # Flag us as no longer running a command
        is_live_pipe = False


def initialize_systems():
    """Initialize all Z-Waif systems"""
    print(f"{colorama.Fore.YELLOW}Initializing Gemini API...{colorama.Fore.RESET}")
    API.gemini_controller.initialize()
    
    print(f"{colorama.Fore.YELLOW}Loading character card...{colorama.Fore.RESET}")
    API.character_card.load_character_card()
    
    print(f"{colorama.Fore.YELLOW}Initializing audio systems...{colorama.Fore.RESET}")
    utils.audio.initialize()
    
    print(f"{colorama.Fore.YELLOW}Setting up hotkeys...{colorama.Fore.RESET}")
    utils.hotkeys.initialize()
    
    print(f"{colorama.Fore.YELLOW}Initializing voice synthesis...{colorama.Fore.RESET}")
    utils.voice.initialize()
    
    if utils.settings.vtube_enabled:
        print(f"{colorama.Fore.YELLOW}Connecting to VTube Studio...{colorama.Fore.RESET}")
        utils.vtube_studio.initialize()
    
    if utils.settings.web_ui_enabled:
        print(f"{colorama.Fore.YELLOW}Starting Web UI...{colorama.Fore.RESET}")
        utils.web_ui.start_ui()
    
    print(f"{colorama.Fore.YELLOW}Initializing RAG memory...{colorama.Fore.RESET}")
    utils.based_rag.initialize()


def main_converse():
    """Main conversation function for voice input"""
    print(
        "\rYou" + colorama.Fore.GREEN + colorama.Style.BRIGHT + " (mic " + colorama.Fore.YELLOW + "[Recording]" + colorama.Fore.GREEN + ") " + colorama.Fore.RESET + ">",
        end="", flush=True)

    # Actual recording and waiting bit
    audio_buffer = utils.audio.record()

    size_string = ""
    try:
        size_string = humanize.naturalsize(os.path.getsize(audio_buffer))
    except:
        size_string = str(1 + len(utils.transcriber_translate.transcription_chunks)) + " Chunks"

    try:
        transcribing_log = "\rYou" + colorama.Fore.GREEN + colorama.Style.BRIGHT + " (mic " + colorama.Fore.BLUE + "[Transcribing (" + size_string + ")]" + colorama.Fore.GREEN + ") " + colorama.Fore.RESET + "> "

        print(transcribing_log, end="", flush=True)

        while utils.transcriber_translate.chunky_request != None:  # rest to wait for transcription to complete
            time.sleep(0.01)

        # My own edit- To remove possible transcribing errors
        transcript = "Whoops! The code is having some issues, chill for a second."

        # Check for if we are in autochat and the audio is not big enough, then just return and forget about this
        if utils.audio.latest_chat_frame_count < utils.settings.autochat_mininum_chat_frames and utils.hotkeys.get_autochat_toggle():
            print("Audio length too small for autochat - cancelling...")
            utils.zw_logging.update_debug_log("Autochat too small in length. Assuming anomaly and not actual speech...")
            utils.transcriber_translate.clear_transcription_chunks()
            return

        transcript = utils.transcriber_translate.transcribe_voice_to_text(audio_buffer)

        if len(transcript) < 2:
            print("Transcribed chat is blank - cancelling...")
            utils.zw_logging.update_debug_log("Transcribed chat is blank. Assuming anomaly and not actual speech...")
            return

    except Exception as e:
        print(colorama.Fore.RED + colorama.Style.BRIGHT + "Error: " + str(e))
        return

    # Print the transcript
    print('\r' + ' ' * len(transcribing_log), end="")
    print('\r' + colorama.Fore.RED + colorama.Style.BRIGHT + "--" + colorama.Fore.RESET
          + "----Me----"
          + colorama.Fore.RED + colorama.Style.BRIGHT + "--\n" + colorama.Fore.RESET)
    print(f"{transcript.strip()}")
    print("\n")

    # Store the message, for cycling purposes
    global stored_transcript
    stored_transcript = transcript

    # Actual sending of the message, waits for reply automatically
    API.gemini_controller.send_message(transcript)

    # Run our message checks
    reply_message = API.gemini_controller.get_last_response()
    message_checks(reply_message)

    # Pipe us to the reply function
    main_message_speak()

    # After use, delete the recording.
    try:
        os.remove(audio_buffer)
    except:
        pass


def main_message_speak():
    """Handle speaking the AI's response"""
    global live_pipe_force_speak_on_response

    # Message is received Here
    message = API.gemini_controller.get_last_response()

    # Stop this if the message was streamed- we have already read it!
    if API.gemini_controller.last_message_streamed and not live_pipe_force_speak_on_response:
        live_pipe_force_speak_on_response = False
        return

    # Speak the message now!
    s_message = emoji.replace_emoji(message, replace='')

    utils.voice.set_speaking(True)

    voice_speaker = threading.Thread(target=utils.voice.speak_line, args=(s_message, False))
    voice_speaker.daemon = True
    voice_speaker.start()

    # Minirest for frame-piercing (race condition as most people call it) for the speaking
    time.sleep(0.01)

    while utils.voice.check_if_speaking():
        time.sleep(0.01)


def message_checks(message):
    """Runs message checks for plugins, such as VTube Studio and Minecraft"""

    # Log our message (ONLY if the last chat was NOT streaming)
    if not API.gemini_controller.last_message_streamed:
        print(colorama.Fore.MAGENTA + colorama.Style.BRIGHT + "--" + colorama.Fore.RESET
              + "----" + char_name + "----"
              + colorama.Fore.MAGENTA + colorama.Style.BRIGHT + "--\n" + colorama.Fore.RESET)
        print(f"{message}")
        print("\n")

    # Vtube Studio Emoting
    if utils.settings.vtube_enabled and not API.gemini_controller.last_message_streamed:
        # Feeds the message to our VTube Studio script
        utils.vtube_studio.set_emote_string(message)

        # Check for any emotes on it's end
        vtube_studio_thread = threading.Thread(target=utils.vtube_studio.check_emote_string)
        vtube_studio_thread.daemon = True
        vtube_studio_thread.start()

    # Minecraft API
    if utils.settings.minecraft_enabled:
        utils.minecraft.check_for_command(message)

    # Gaming
    if utils.settings.gaming_enabled:
        utils.gaming_control.message_inputs(message)

    # Check if we need to close the program (botside killword)
    if message.lower().__contains__("/ripout/"):
        print("\n\nBot is knowingly closing the program! This is typically done as a last resort! Please re-evaluate your actions! :(\n\n")
        sys.exit("Closing...")
        exit()

    # We can now undo the previous message
    global undo_allowed
    undo_allowed = True


def main_next():
    """Generate next message variation"""
    API.gemini_controller.regenerate_last_response()

    # Run our message checks
    reply_message = API.gemini_controller.get_last_response()
    message_checks(reply_message)

    # Pipe us to the reply function
    main_message_speak()


def main_minecraft_chat(message):
    """Handle Minecraft chat integration"""
    # This is a shadow chat
    global live_pipe_no_speak
    if (not utils.settings.speak_shadowchats) and utils.settings.stream_chats:
        live_pipe_no_speak = True

    # Limit the amount of tokens allowed to send (minecraft chat limits)
    API.gemini_controller.set_max_tokens(47)

    # Actual sending of the message, waits for reply automatically
    API.gemini_controller.send_message(message)

    # Reply in the craft
    utils.minecraft.minecraft_chat()

    # Run our message checks
    reply_message = API.gemini_controller.get_last_response()
    message_checks(reply_message)

    # Pipe us to the reply function, if we are set to speak them (will be spoken otherwise)
    live_pipe_no_speak = False
    if utils.settings.speak_shadowchats and not utils.settings.stream_chats:
        main_message_speak()


def main_discord_chat(message):
    """Handle Discord chat integration"""
    # This is a shadow chat
    global live_pipe_no_speak
    if (not utils.settings.speak_shadowchats) and utils.settings.stream_chats:
        live_pipe_no_speak = True

    # Actual sending of the message, waits for reply automatically
    API.gemini_controller.send_message(message)

    # Run our message checks
    reply_message = API.gemini_controller.get_last_response()
    message_checks(reply_message)

    # Pipe us to the reply function, if we are set to speak them (will be spoken otherwise)
    live_pipe_no_speak = False
    if utils.settings.speak_shadowchats and not utils.settings.stream_chats:
        main_message_speak()


def main_web_ui_chat(message):
    """Handle Web UI chat interface"""
    # This is a shadow chat
    global live_pipe_no_speak
    if (not utils.settings.speak_shadowchats) and utils.settings.stream_chats:
        live_pipe_no_speak = True

    # Actual sending of the message, waits for reply automatically
    API.gemini_controller.send_message(message)

    # Cut voice if needed
    utils.voice.force_cut_voice()

    # Run our message checks
    reply_message = API.gemini_controller.get_last_response()
    message_checks(reply_message)

    # Pipe us to the reply function, if we are set to speak them (will be spoken otherwise)
    live_pipe_no_speak = False
    if utils.settings.speak_shadowchats and not utils.settings.stream_chats:
        main_message_speak()


def main_web_ui_next():
    """Handle Web UI next/regenerate functionality"""
    # This is a shadow chat
    global live_pipe_no_speak
    if (not utils.settings.speak_shadowchats) and utils.settings.stream_chats:
        live_pipe_no_speak = True

    # Cut voice if needed
    utils.voice.force_cut_voice()

    # Force end the existing stream (if there is one)
    if API.gemini_controller.is_generating:
        API.gemini_controller.stop_generation()
        live_pipe_no_speak = False
        return

    API.gemini_controller.regenerate_last_response()

    # Run our message checks
    reply_message = API.gemini_controller.get_last_response()
    message_checks(reply_message)

    # Pipe us to the reply function, if we are set to speak them (will be spoken otherwise)
    live_pipe_no_speak = False
    if utils.settings.speak_shadowchats and not utils.settings.stream_chats:
        main_message_speak()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{colorama.Fore.YELLOW}Shutting down Z-Waif...{colorama.Fore.RESET}")
        sys.exit(0)
    except Exception as e:
        print(f"{colorama.Fore.RED}Fatal error: {e}{colorama.Fore.RESET}")
        utils.zw_logging.update_debug_log(f"Fatal error in main: {e}")
        sys.exit(1)
