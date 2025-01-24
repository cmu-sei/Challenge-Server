# **Challenge Server Readme**

This is the **Challenge Server** - designed for hands-on cybersecurity challenges.  

The idea is to have a centralized server that developers can use for startup/grading scripts and users can go to for grading and viewing results inside challenges. 

_Disclaimer: The Challenge Server was developed with under the assumption that it would be used alongside [TopoMojo](https://github.com/cmu-sei/topomojo) and VMware. Some phrasing here may use TopoMojo and VMware terminology. If using this service outside of TopoMojo and VMware, some adjustments may be required._

## Using the Challenge Server

The Challenge Server primarily consists of a web server written in Python. At startup, the server will read the config file and apply those settings. Then, the server will run startup scripts, host files for download, supply ways for users to ask for grading, and more!

Edit the [config.yml](./config.yml) file to configure the service to behave how you'd like. The config file is heavily commented to help figure out which settings you may need.

In most cases, it makes sense to run the Challenge Server code as a `systemd` service at boot. An example systemd unit is [here](./challengeserver.service). If you're using this type of configuration, you will need to restart the systemd service before changes to the config file are read by the service. Use the following command to restart the service after making configuration changes: 

```bash
sudo systemctl restart challengeserver.service
```

To ensure the service started correctly and without errors, run: 

```bash 
sudo systemctl status challengeserver.service
```

## Logs
Everything the Challenge Server does is logged to Systemd if you use a systemd service to start the server. To view the Challenge Server logs via the system journal: 

```bash
sudo journalctl -u challengeserver.service
```

The above command will put you in a `more`-style view of the systemd logs for the Challenge Server service. To jump the bottom of the logs (most recent logs) use: 

```bash
sudo journalctl -e -u challengeserver.service
```

<br></br>

# Required Guestinfo Variables

The Challenge Server relies on VMware guestinfo variables to gather some information. 

In order to operate as intended, the Challenge Server requires 2 guestinfo variables. 
1. `code` - This guestinfo variable should be a string that contains a "challenge code" or a "slug" that identified this challenge. Example: `c00`. If this guestinfo variable is not set, the Challenge Server will always assume that it is running in a workspace. 
1. `variant` - This guestinfo variable should be a string that contains which TopoMojo variant is deployed. Example: `2`. If this guestinfo variable is not set, the Challenge Server will set the variant to a default of `-1`

The Challenge Server can also read "answer tokens" from Guestinfo if configured to do so. 

<br></br>

# Monitoring Required Services

The Challenge Server can be used to monitor services that a challenge requires. Examples include: a website that needs to remain operational, a Docker container that should always have an open port, a host that should remain reachable, etc. To configure the Challenge Server to monitor required services, use the `required_services` section of the config file. 

On a periodic basis (every 30 seconds by default), the Challenge Server will determine if your required services are reachable. It does this by using the `ping` command, making a TCP socket connection, or by visiting a website. These options and their additional required settings are documented in the config file. 

Required services can also block startup scripts from executing. This is useful if your startup script requires that a host is up or a service is available. For example, if your startup script needs to use SSH to configure a host, it would be helpful to ensure that ssh is reachable on that host before running the startup script by configuring a `socket` required service on port `22` for the desired host. 

## Service Logger

The Challenge Server comes with an additional `service_logger` that can be used to collect logs service logs from other VMs in the challenge environment. Use the [service_logger config file](./monitored_services/services_config.yml) and [systemd service](./monitored_services/monitoredServices.service) to enable this additional functionality. 

<br></br>

# Startup Configuration

You can use the Challenge Server as a central location for configuring all the machines in your environment.
1. Write a startup script (or more than 1) that will remotely configure each machine in your environment to the challenge's specifications. Place all startup scripts in the [custom_scripts](custom_scripts) directory and ensure they are executable (`chmod +x <your_script>`)
1. You can use ssh, psexec, powershell remoting, or any other way to remotely manage each machine in your environment. 
1. Your startup script should log all important actions/results to standard out. 
1. You can optionally use the `required_services` section to block startup scripts from running until required services are available. This is useful in cases where you need SSH to be available on a target machine for your startup script to function as intended. 

Example startup scripts are [here](./custom_scripts/).

<br></br>

# Grading
The challenge developer (you) can write a grading script that the server executes under a few circumstances: 
- When a button on the website is pressed
- When a certain time of day is reached 
- When a certain amount of time has passed
- When the user enters text into the website

The Challenge Server will take care of reading submission tokens from guestinfo variables or a file on the Challenge Server machine (depending on the configuration) and displaying token values to the user.  

The Challenge Server can also POST values to the [Gameboard application](https://github.com/cmu-sei/gameboard) and submit answers on a user's behalf.

The challenge developer only needs to write a grading script that will perform any checks needed to ensure successful challenge completion.

<br></br>

## Types of Grading
There are several types of grading that are supported by this server. 

- User Presses a Button
    - In this style of grading, the user is expected to visit a website and press a button to initiate grading. The grading script will execute without command line arguments
- User Enters Text 
    - In this style of grading, the user is expected to visit a website and submit text which answers questions. The grading script will execute with each text submission passed as a command line argument (use argv to get these)
- Automatic/Scheduled Grading (cron job)
    - In this style of grading, the user is not expected to take any action for grading to occur. Grading happens on an interval and/or at a scheduled time
    - Additional config settings maybe be required for this style to operate to your challenge's specs. 

More information about using each grading type is provided in the comments of the [config](./config.yml) file.

<br></br>

## Grading Scripts

The challenge developer will need to write their own grading script to perform whatever checks are required as part of the challenge grading process. The grading script can be written in any language and will be executed by the grading server automatically when the user presses a button to initiate grading, at a certain time, or other conditions.

The grading script **MUST** produce output in a `key:value` format.  The `key` should be the part of the challenge you are grading (e.g., 'Part1', 'GradingCheck1', etc.).  The `value` should be any message that you want to relay to the user (e.g., 'Success - this check produced the correct output', 'Failure -- this check did not pass', etc.). 

Success messages **MUST** minimally include the word 'success'.

Your grading script should output one (1)  `key:value` pair per line. Each new line (and therefore each `key:value` pair) will be treated as different parts of a multi-part challenge.

The following is an example of valid grading script output:
```
Part1: Success
Part2: Success -- The configuration you applied mitigates the attack
GradingCheck3: Failure - Your configuration is invalid
Check4: Failure
```

Feel free to include as much or as little detail in the message as you'd like the competitor to see. The only requirement is: The word 'success' must be present in the `value` field of any part you want to display a token for. 

The Grading Server will use the `keys` output by the grading script to display output to the user. The `config.yml` file allows you to specify the text to display to the user for each part and the location to look for tokens.

The Grading Server will also display the `values` output by the grading script to the user. This can help the user figure out why they failed a particular part if useful messages are provided. **Do not include any text in the values that you do not want users to see.**

Your grading script should start with a 'shebang' line which gives the absolute path to the interpreter that should be used to run the program. 
- Bash scripts should start with `#!/bin/bash`
- Python scripts should start with `#!/usr/bin/python3`
- PowerShell scripts should start with `#!/snap/bin/pwsh`

Your grading script must have the executable bit set. Ensure you run the following command: `chmod +x <your_script>`.

Example grading scripts are [here](./custom_scripts/).

<br></br>

## Submitting Grading Results

This server supports 2 methods for grading results. 

- Display a token
    - This is the default method. In this method, a token will be displayed on the website. The user will have to visit the website, copy the token string out of the VM, then paste it to the Gameboard to submit for credit
- Grader POST
    - This method is used when the developer wants to submit answers to the grader (e.g., Gameboard) on the user's behalf. Using this submission method along with automatic grading, will result in user's being awarded points automatically -- no action is needed by the user after the grading check(s) pass.
    - Additional settings required for this are described in the config file comments.


<br></br>

# Hosting Files

This server can be used to host any files you need to share with the competitor inside the challenge environment. To host files, place the files in the `hosted_files` directory.  This will allow competitors to download the files from inside their challenge environment. 
