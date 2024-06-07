# Genaicommit: Generate AI-Powered Git Commit Messages

Genaicommit is a command-line tool that automates the generation of git commit messages using OpenAI's language models. It ensures your commit messages are concise, informative, and follow conventional commit standards.

## Features
- Generates concise git commit messages based on diff.
- Supports different commit message formats such as conventional commits.
- Integrates with git to ensure the tool is usable directly within a repository.
- Adds emojis to commit messages with devmoji (optional).

## Requirements
- Python 3.6+
- Git
- OpenAI API Key

## Installation

You can install `genaicommit` using `pip`. First, ensure you have `pip` installed, then run:

```bash
pip install genaicommit
```

## Setup

1. Generate an OpenAI API key from the [OpenAI website](https://beta.openai.com/signup/).
2. Configure `genaicommit` with your OpenAI API key:

```bash
genaicommit config set OPENAI_API_KEY=<your_api_key>
```

## Configuration

You can configure `genaicommit` using the `config set` command. Here are the available configuration keys:

- `model`: The OpenAI model to use (default: `gpt-4`).
- `devmoji`: Whether to use devmoji for commit messages (default: `false`).
- `type`: The type of commit message format (default: `conventional`).
- `max-length`: The maximum length of the commit message (default: `50`).
- `locale`: The language of the commit message (default: `en`).
- `OPENAI_API_KEY`: Your OpenAI API key for authenticating API requests.

Example:

```bash
genaicommit config set model=gpt-3.5-turbo
genaicommit config set max-length=72
```

## Usage

1. Navigate to any git repository.
2. Stage your changes:

```bash
git add <files>
```

3. Run `genaicommit` to generate and approve a commit message:

```bash
genaicommit -g 1
```

### Options

- `-g, --generate N`: Generate N commit messages (default is 1).
- `config set KEY=VALUE`: Set a configuration key to a value.
- `-h, --help`: Show the help message and exit.

## Example

```bash
cd your-git-repo
git add .
genaicommit -g 1
```

Follow the prompts to approve the commit message and commit the changes.

## License

This project is licensed under the MIT License.