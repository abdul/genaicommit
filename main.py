import configparser
import json
import os
import subprocess
import sys
import ssl
import urllib.request
from urllib.error import URLError, HTTPError
from pathlib import Path

import inquirer
from cryptography.fernet import Fernet
from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)

# Constants for configuration paths
CONFIG_DIR = Path.home() / ".config" / "genaicommit"
CONFIG_FILE = CONFIG_DIR / "settings.ini"
KEY_FILE = CONFIG_DIR / "key.key"

# Create configuration directory if it doesn't exist
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

# Load or create encryption key
if KEY_FILE.exists():
    with open(KEY_FILE, 'rb') as f:
        encryption_key = f.read()
else:
    encryption_key = Fernet.generate_key()
    with open(KEY_FILE, 'wb') as f:
        f.write(encryption_key)

cipher = Fernet(encryption_key)

config = configparser.ConfigParser()

# Load configuration or create default
if CONFIG_FILE.exists():
    config.read(CONFIG_FILE)
else:
    config['SETTINGS'] = {
        'model': 'gpt-4',
        'devmoji': 'false',
        'type': 'conventional',
        'max-length': '50',
        'locale': 'en',
        'OPENAI_API_KEY': ''
    }
    with open(CONFIG_FILE, 'w') as configfile:
        config.write(configfile)

def save_config():
    with open(CONFIG_FILE, 'w') as configfile:
        config.write(configfile)

def encrypt_api_key(api_key):
    return cipher.encrypt(api_key.encode()).decode()

def decrypt_api_key(encrypted_api_key):
    return cipher.decrypt(encrypted_api_key.encode()).decode()

class KnownError(Exception):
    pass

def https_post(host, path, headers, data, timeout, proxy=None):
    post_data = json.dumps(data).encode('utf-8')
    url = f"https://{host}{path}"
    req = urllib.request.Request(url, data=post_data, headers=headers, method='POST')

    if proxy:
        req.set_proxy(proxy, 'https')

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        with urllib.request.urlopen(req, context=ctx, timeout=timeout) as response:
            response_data = response.read().decode('utf-8')
            return response, response_data
    except HTTPError as e:
        raise KnownError(f"HTTPError: {e.code} {e.reason}")
    except URLError as e:
        raise KnownError(f"URLError: {e.reason}")
    except Exception as e:
        raise KnownError(f"Unknown Error: {e}")

def create_chat_completion(api_key, json_data, timeout, proxy=None):
    headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
    path = '/v1/chat/completions'
    response, data = https_post('api.openai.com', path, headers, json_data, timeout, proxy)

    if not (200 <= response.status < 300):
        error_message = f"OpenAI API Error: {response.status} - {response.reason}"
        if data:
            error_message += f"\n\n{data}"
        if response.status == 500:
            error_message += '\n\nCheck the API status: https://status.openai.com'
        raise KnownError(error_message)

    return json.loads(data)

def sanitize_message(message):
    # Ensure message follows the "<type>(<optional scope>): <commit message>" format
    if message.startswith(":"):
        return message[1:].strip()
    return message.strip().replace('\n', '').replace('\r', '')

def deduplicate_messages(messages):
    return list(set(messages))

def generate_prompt(locale, max_length, commit_type, commit_types, commit_type_formats):
    return "\n".join([
        'Generate a concise git commit message written in present tense for the following code diff with the given specifications below:',
        f'Message language: {locale}',
        f'Commit message must be a maximum of {max_length} characters.',
        'Exclude anything unnecessary such as translation. Your entire response will be passed directly into git commit.',
        commit_types[commit_type],
        "The output response must be in format:",
        commit_type_formats[commit_type]
    ])

def generate_commit_message(api_key, model, locale, diff, completions, max_length, commit_type, commit_types, commit_type_formats, timeout, proxy=None):
    try:
        model_prompt = generate_prompt(locale, max_length, commit_type, commit_types, commit_type_formats)
        json_data = {
            "model": model,
            "messages": [
                {"role": "system", "content": model_prompt},
                {"role": "user", "content": diff}
            ],
            "temperature": 0.7,
            "top_p": 1,
            "frequency_penalty": 0,
            "presence_penalty": 0,
            "max_tokens": 200,
            "stream": False,
            "n": completions,
        }
        completion = create_chat_completion(api_key, json_data, timeout, proxy)
        return deduplicate_messages([
            sanitize_message(choice["message"]["content"])
            for choice in completion["choices"]
            if "message" in choice and "content" in choice["message"]
        ])
    except KnownError as e:
        raise KnownError(f"Failed to generate commit message: {e}")

def is_git_repo():
    try:
        subprocess.run(['git', 'rev-parse', '--is-inside-work-tree'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError:
        return False

def get_git_diff():
    try:
        result = subprocess.run(['git', 'diff', '--cached'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        diff = result.stdout.strip()
        if not diff:
            raise KnownError("No staged changes found. Please stage your changes using `git add <files>`.")
        return diff
    except subprocess.CalledProcessError as e:
        raise KnownError(f"Error getting git diff: {e.stderr}")

def print_help():
    print(f"{Fore.CYAN}Usage: main.py [options]{Style.RESET_ALL}")
    print("Options:")
    print("  -g, --generate N       Generate N commit messages (default is 1).")
    print("  config set KEY=VALUE   Set a configuration key to a value.")
    print("  -h, --help             Show this help message and exit.")

def main():
    if '-h' in sys.argv or '--help' in sys.argv:
        print_help()
        sys.exit(0)

    print(f"{Fore.GREEN}Starting generation...{Style.RESET_ALL}")
    if not is_git_repo():
        print(f"{Fore.RED}Error: This script must be run inside a git repository.{Style.RESET_ALL}")
        sys.exit(1)

    if len(sys.argv) > 1 and sys.argv[1] == 'config' and sys.argv[2] == 'set':
        key, value = sys.argv[3].split('=')
        if key == 'OPENAI_API_KEY':
            config['SETTINGS'][key] = encrypt_api_key(value)
        else:
            config['SETTINGS'][key] = value
        save_config()
        print(f"{Fore.GREEN}Configuration set: {Fore.YELLOW}{key}={value}{Style.RESET_ALL}")
        sys.exit(0)

    completions = 1
    if '-g' in sys.argv or '--generate' in sys.argv:
        try:
            if '-g' in sys.argv:
                index = sys.argv.index('-g') + 1
            else:
                index = sys.argv.index('--generate') + 1
            completions = int(sys.argv[index])
        except (ValueError, IndexError):
            print(f"{Fore.RED}Error: Please provide a valid number of generations with the -g or --generate flag.{Style.RESET_ALL}")
            sys.exit(1)

    settings = config['SETTINGS']

    max_length = int(settings['max-length'])
    locale = settings['locale']

    api_key = decrypt_api_key(settings['OPENAI_API_KEY']) if settings['OPENAI_API_KEY'] else os.environ.get('OPENAI_API_KEY')

    if not api_key:
        print(f"{Fore.RED}Error: No API key set. Use `genaicommit.py config set OPENAI_API_KEY=<key>` to set it.{Style.RESET_ALL}")
        sys.exit(1)

    # Define commit types and formats
    commit_types = {
        '': '',
        'conventional': 'Choose a type from the type-to-description JSON below that best describes the git diff:\n' + json.dumps({
            'docs': 'Documentation only changes',
            'style': 'Changes that do not affect the meaning of the code (white-space, formatting, missing semi-colons, etc)',
            'refactor': 'A code change that neither fixes a bug nor adds a feature',
            'perf': 'A code change that improves performance',
            'test': 'Adding missing tests or correcting existing tests',
            'build': 'Changes that affect the build system or external dependencies',
            'ci': 'Changes to our CI configuration files and scripts',
            'chore': "Other changes that don't modify src or test files",
            'revert': 'Reverts a previous commit',
            'feat': 'A new feature',
            'fix': 'A bug fix'
        }, indent=2),
    }

    commit_type_formats = {
        '': '<commit message>',
        'conventional': '<type>(<optional scope>): <commit message>',
    }

    # Get the git diff to send to OpenAI
    print(f"{Fore.BLUE}Fetching git diff...{Style.RESET_ALL}")
    try:
        diff = get_git_diff()
    except KnownError as e:
        print(f"{Fore.RED}{e}{Style.RESET_ALL}")
        sys.exit(1)

    # Generate commit messages using the OpenAI model specified in config
    print(f"{Fore.BLUE}Generating commit messages...{Style.RESET_ALL}")
    try:
        commit_messages = generate_commit_message(
            api_key=api_key,
            model=settings['model'],
            locale=locale,
            diff=diff,
            completions=completions,
            max_length=max_length,
            commit_type='conventional',
            commit_types=commit_types,
            commit_type_formats=commit_type_formats,
            timeout=30  # Timeout in seconds, adjust as necessary
        )

        if len(commit_messages) < completions:
            print(f"{Fore.YELLOW}Warning: Only received {len(commit_messages)} messages out of the requested {completions}.{Style.RESET_ALL}")

        if len(commit_messages) > 1:
            questions = [
                inquirer.List(
                    'selected_message',
                    message="Select a commit message:",
                    choices=commit_messages,
                ),
            ]
            answers = inquirer.prompt(questions)
            commit_message = answers['selected_message']
        else:
            commit_message = commit_messages[0]
    except KnownError as e:
        print(f"{Fore.RED}Error generating commit message: {e}{Style.RESET_ALL}")
        sys.exit(1)

    # Optionally use devmoji to add emojis to the commit message
    if settings['devmoji'] == 'true':
        devmoji_command = f'echo "{commit_message}" | devmoji --commit'
        result = subprocess.run(devmoji_command, shell=True, capture_output=True, text=True)
        commit_message = result.stdout.strip()

    # Show the selected commit message and ask for approval
    print(f"\n{Fore.CYAN}Selected commit message:{Style.RESET_ALL}\n{commit_message}\n")

    approval_question = [
        inquirer.Confirm('approved', message=f"{Fore.GREEN}Do you approve this commit message?{Style.RESET_ALL}", default=True),
    ]

    approval_answer = inquirer.prompt(approval_question)

    if approval_answer['approved']:
        # Commit the changes
        try:
            subprocess.run(['git', 'commit', '-m', commit_message], check=True)
            print(f"{Fore.GREEN}Commit successful!{Style.RESET_ALL}")
        except subprocess.CalledProcessError as e:
            print(f"{Fore.RED}Error committing changes: {e}{Style.RESET_ALL}")
    else:
        print(f"{Fore.YELLOW}Commit message not approved. Commit aborted.{Style.RESET_ALL}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Fore.RED}Operation cancelled by user.{Style.RESET_ALL}")
        sys.exit(1)