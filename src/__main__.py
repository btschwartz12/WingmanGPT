"""Main module for the WingmanGPT program."""

# pylint: disable=invalid-name,broad-exception-raised,broad-exception-caught


import os
import subprocess
import shlex
import argparse
from contextlib import redirect_stdout
from io import StringIO

from revChatGPT.V1 import Chatbot

from src.prompts import prompt_data, PromptData


class WingmanGPT:
    """Command-line tool that generates and sends text messages."""

    def __init__(self,
                 number: str,
                 noconfirm: bool,
                 token: str,
                 message: str,
                 mode: str):
        """Take a message, give it to chatGPT, send response to number."""
        # Command line arguments
        self.__phone_number = self.__get_phone_number(number)
        self.__token = self.__get_token(token)
        self.__message = self.__get_message(message)
        self.__wants_to_confirm = not noconfirm
        # Prompt data
        self.__prompt_data: PromptData = prompt_data
        # Mode
        self.__mode_modification = self.__get_mode_modification(mode)

    def __get_token(self, token):
        """Get the token to be used for the ChatGPT API.

        It will first check to see if the token is passed as an argument.
        If not, it will check to see if there is a token file.
        If not, it will throw an error.
        """
        # First see if it is passed as an argument
        if isinstance(token, str) and token != "":
            return token
        # Now check to see if there is a token file
        if os.path.exists("token"):
            with open("token", "r", encoding='utf-8') as f:
                tok = f.read()
                if tok != "":
                    return tok
        # Now throw an error
        raise Exception("No token provided or found in token file")

    def __get_phone_number(self, number):
        """Get the phone number to send the message to.

        If the phone nuber is not a string or is not 10 characters long,
        it will throw an error.
        """
        if not isinstance(number, str) or len(number) != 10:
            raise Exception("Invalid phone number")
        # Make sure all of the characters are digits
        for char in number:
            if not char.isdigit():
                raise Exception("Invalid phone number")
        return number

    def __get_message(self, message):
        """Get the message to be used for the prompt for ChatGPT.

        First check to see if the message is passed as an argument.
        If not, check to see if there is a message.txt file.
        If not, throw an error.
        """
        # First see if it is passed as an argument
        if isinstance(message, str) and message != "":
            return message
        # Now check to see if there is a message.txt file
        if os.path.exists("message.txt"):
            with open("message.txt", "r", encoding='utf-8') as f:
                msg = f.read()
                if msg != "":
                    return msg
        # Now throw an error
        raise Exception("No message provided or found in message.txt")

    def __get_mode_modification(self, mode_str) -> str:
        """Get response mode to be used for the prompt for ChatGPT.

        If no mode is provided, it will default to ROMANTIC.
        If an invalid mode is provided, it will throw an error.
        """
        available_modes = {response_mode.NAME:
                           response_mode.PROMPT_MODIFICATION
                           for response_mode in self.__prompt_data.MODES}

        if mode_str is None or mode_str == "":
            # Default
            return available_modes[self.__prompt_data.DEFAULT_MODE]
        if mode_str not in available_modes:
            raise Exception(f"Invalid mode: {mode_str}\n Available modes: \
                            {', '.join(available_modes.keys())}")
        return available_modes[mode_str]

    def __get_prompt(self):
        """Get the prompt to be used for the ChatGPT API."""
        PROMPT = ""

        PROMPT += " ".join(self.__prompt_data.PREFIX)
        PROMPT += f" Here is the message: \"{self.__message}\"."
        PROMPT += " Here is how I want you to modify the message: "
        PROMPT += f"\"{self.__mode_modification}\"."
        PROMPT += " ".join(self.__prompt_data.SUFFIX)

        return PROMPT

    def __get_response(self):
        """Get the ChatGPT Response."""
        # Get the prompt to be used
        PROMPT = self.__get_prompt()
        # Configure the ChatGPT API
        token = self.__token
        # strip any newlines from the token
        token = token.replace("\n", "")
        chatbot = Chatbot(config={
            # Change to bens bc hes rich boi
            "access_token": token
        })
        # Prepare to capture output for errors
        output = StringIO()
        response = ""
        with redirect_stdout(output):
            # Ask ChatGPT for a response
            for data in chatbot.ask(PROMPT):
                response = data["message"]
        # If anything printed from ask(), it is an error
        captured_output = output.getvalue()
        if 'invalid_request_error' in captured_output:
            raise Exception("Invalid API token")
        # Strip the quotes from the response
        response = response[1:-1]
        return response

    def __send_message(self, response):
        """Send message to phone number."""
        # Properly escape special characters for a bash command
        prepared_response = "\"" + shlex.quote(response)[1:-1] + "\""
        # Send the message
        command = "osascript -e 'tell application \"Messages\" to send "
        command += f"{prepared_response} to buddy \"{self.__phone_number}\"'"
        try:
            subprocess.run(command, shell=True, check=True)
        except Exception as e:
            raise Exception(f"Failed to send message: \n\n{e}") from e

    def execute(self):
        """Execute the program.

        This will first get the response from ChatGPT,
        then it will ask the user if they want to send the message,
        and then it will send the message.
        """
        try:
            print('Fetching response from ChatGPT...')
            response = self.__get_response()
        except Exception as e:
            print(e)
            print('Failed to get response from ChatGPT API')
            return
        
        try:
            print("Sending message...")
            if self.__wants_to_confirm:
                print(f"********\nMessage: {response}\n********")
                confirm = input("Send message? (y/n): ")
                if confirm.lower() != "y":
                    print("Message not sent.")
                    return
            self.__send_message(response)
            print('Message Sent.')
        except Exception as e:
            print(f'Failed to send message. \n\n{e}')

def make_token(token):
    """Make a file named token with the token in it."""
    with open("token", "w+", encoding='utf-8') as f:
        f.write(token)

def make_message(message):
    """Make a file named message.txt with the message in it."""
    with open("message.txt", "w+", encoding='utf-8') as f:
        f.write(message)




def main():
    parser = argparse.ArgumentParser(description='Tool for sending messages to a phone number.')
    subparsers = parser.add_subparsers(dest='command')

    # Create parser for normal usage
    send_parser = subparsers.add_parser('send')
    send_parser.add_argument('-n', '--number', required=True, help='Phone number to send the message to.')
    send_parser.add_argument('-t', '--token', help='ChatGPT API token.')
    send_parser.add_argument('--mode', help='Mode to use for sending the message.')
    send_parser.add_argument('--noconfirm', action='store_true', help='Do not confirm before sending the message.')
    send_parser.add_argument('-m', '--message', help='Message to send.')

    # Create parser for make-token command
    make_token_parser = subparsers.add_parser('make-token')
    make_token_parser.add_argument('token', help='ChatGPT API token.')

    # Create parser for make-message command
    make_message_parser = subparsers.add_parser('make-message')
    make_message_parser.add_argument('message', help='Message to send.')

    # Create parser for show_modes
    subparsers.add_parser('show-modes')

    args = parser.parse_args()

    if args.command == 'send':
        # Handle send command
        try:
            tgpt = WingmanGPT(number=args.number, noconfirm=args.noconfirm, token=args.token,
                            message=args.message, mode=args.mode)
            tgpt.execute()
        except Exception as e:
            print(f"Error occurred: {str(e)}")
    elif args.command == 'make-token':
        # Handle make-token command
        make_token(args.token)
        print('Token file created.')
    elif args.command == 'make-message':
        # Handle make-message command
        make_message(args.message)
        print('Message file created.')
    elif args.command == 'show-modes':
        # Handle show-modes command
        prompt_data.show_modes()
    else:
        parser.print_help()

if __name__ == '__main__':
    main()