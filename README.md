# BarkoAgentCLI

BarkoAgentCLI is a CLI tool for triggering BarkoAgent functionalities and retrieve information

## Installation

To install download the tool and run installation via `pip3 install -r requirements.txt`

## Usage
Before any usage of the CLI you need to generate an authentication token for valid execution of commands.
The token should be inserted into `.env` file - example template in `.env.example` file

The URL/endpoint for which BarkoAgent environment you want to run commands in is specified in `URL` value, 
authentication token in `TOKEN` value

To run commands you can run the help command:
```bash
python3 runner.py --help
```

To run a command use, for example:
```bash
python3 runner.py run-single-script --project-id=foo --chat-id=bar
```

If anything you can run help argument to get the necessary arguments to add 
```bash
python3 runner.py run-single-script --help
```

## Contributing

Pull requests are welcome. For major changes, please open an issue first
to discuss what you would like to change.
