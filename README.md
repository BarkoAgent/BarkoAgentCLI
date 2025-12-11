# BarkoAgentCLI

BarkoAgentCLI is a CLI tool for triggering BarkoAgent functionalities and retrieve information

## Installation

To install download the tool and run installation via `pip3 install -r requirements.txt`

## Usage

### Prerequisites
Before any usage of the CLI you need to configure the BarkoAgent environment URL and authentication token.

The URL/endpoint for which BarkoAgent environment you want to run commands in is specified in `URL` value, 
and the authentication token in `TOKEN` value.

You can configure these by running:
```bash
python3 runner.py config --set-url=<your-barkoagent-url> --set-token=<your-auth-token>
```

This will create/update the `.env` file with your credentials.

### Running Commands
To run commands you can run the help command:
```bash
python3 runner.py --help
```

To run a command use, for example:
```bash
python3 runner.py run-single-script --project-id=foo --chat-id=bar
```

### Example Flags

- `--junit` - Generate JUnit report with live test execution dashboard
- `--html` - Generate HTML test report

Example usage:
```bash
python3 runner.py run-all-scripts --project-id=foo --junit --html
python3 runner.py run-single-script --project-id=foo --chat-id=bar --junit --html
```

If anything you can run help argument to get the necessary arguments to add 
```bash
python3 runner.py run-single-script --help
```

## Contributing

Pull requests are welcome. For major changes, please open an issue first
to discuss what you would like to change.
