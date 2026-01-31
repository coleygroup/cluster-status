# Cluster Dash Mole

_A script that continually polls the compute resources on the host machine sending them to various logging/dashboard
services._

# 1. Installation

Use uv to install the dependencies, e.g.:

```bash
uv sync
```

If you don't have uv, you can install it via:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Set the `PYTHONPATH`, e.g. (in this directory run):

```bash
$ export PYTHONPATH=${PYTHONPATH}:$(pwd)
```

# 2. Configuration

Configure the settings in `config_molgpu0X.toml` as needed. Since now molgpus are on NAS, need to create a seperate config file for each server.

## Poll_Settings

- `poll_interval_in_secs`: the time interval (in seconds) for polling the host's resources. Note this does not necessary
  mean that we send the results to all external sources at this interval -- the other loggers will only
  send if their `min_interval_in_secs` is also met.

## Json_Sender_Logger

This controls the settings for the logger that sends the information to a remote server.

- `use`: whether to use this logger.
- `min_interval_in_secs`: min interval for sending logs in seconds. Therefore, if we have just polled but
  this time has not been met then we will wait till next poll.
- `address_in`: address to make the post request to.
- `auth_code`: auth code to add into the JSON that we post. Note this will not be encrypted but acts as a very rudimentary
  safeguard in case someone else wants to send requests to our server.

## Google_Sheets_Logger

This controls the settings for the logger that adds information to Google Sheets.

- `use`: whether to use this logger.
- `min_interval_in_secs`: min interval for sending logs in seconds. Therefore, if we have just polled but
  this time has not been met then we will wait till next poll.
- `service_account_file_path`: path to the credentials file.
- `spreadsheets_id`: Google sheets spreadsheet id. (usually you can get this from its url.)
- `worksheet_name`: worksheet to append to. `!hostname` means we will use the actual machine's hostname.

**Google Sheets Credentials:** see the instructions [here](https://developers.google.com/workspace/guides/create-credentials)
for creating credentials. Note a service account is fine. Once you've created a service account's credentials, remember to
share edit permissions with the service account's email address on the sheet you want to use (in the same way you would
add an ordinary collaborator).

## StdOut_Logger

This controls the settings for the logger that pretty prints the information to standard out.

- `use`: whether to use this logger.
- `min_interval_in_secs`: min interval for sending logs in seconds. Therefore, if we have just polled but
  this time has not been met then we will wait till next poll.

# 3. Starting

Start the reporting by:

```bash
python smart_startup.py
```

# Add service file

An example service file is as follows:

```ini
[Unit]
Description=Cluster Dashboard Mole Client
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/workdir
Environment=VIRTUAL_ENV=/path/to/env/
Environment=PYTHONPATH=/path/to/workdir
ExecStart=/path/to/env/bin/python smart_startup.py
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
```

Then run the following commands to enable and start the service so that it will start automatically on reboot:

```bash
sudo systemctl daemon-reload
sudo systemctl enable cluster-dash-mole
sudo systemctl start cluster-dash-mole
sudo systemctl status cluster-dash-mole
```

## Troubleshooting

```bash
# View live logs
sudo journalctl -u cluster-dash-mole -f

# Check recent logs
sudo journalctl -u cluster-dash-mole --since "10 minutes ago"

# Restart the service
sudo systemctl restart cluster-dash-mole
```
