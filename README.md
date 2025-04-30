# **Challenge Server**

This is the **Challenge Server** - designed for hands-on cybersecurity challenges.

The idea is to have a centralized server that developers can use for startup/grading scripts and users can go to for grading and viewing results inside challenges.

## Using the Challenge Server

At startup, the Challenge Server will read the config file and apply settings. Then, the server will run startup scripts, host files for download, supply ways for users to ask for grading, and more!

Edit the [config.yml](./src/config.yml) file to configure the service to behave how you'd like. Check the [supplemental README.md](./src/README.md) for details on configuration options.

### Using HTTPS

To run the Challenge Server with HTTPS, provide the path to a TLS certificate and private key via the [config.yml](./src/config.yml) or the `CS_APP_CERT` and `CS_APP_KEY` environment variables.

### Running the Challenge Server

In some cases, it makes sense to run the Challenge Server code as a `systemd` service at boot. An example systemd unit is [here](./challengeserver.service). If you're using this type of configuration, you will need to restart the systemd service before changes to the config file are read by the service. Use the following command to restart the service after making configuration changes:

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

## Required Environment Variables

In order to operate as intended, the Challenge Server requires 2 environment variables.

1. `CS_CODE` - This environment variable should be a string that contains a "challenge code" or a "slug" that identified this challenge. Example: `c00`. If this environment variable is not set, the Challenge Server will always assume that it is running in a workspace.
1. `CS_VARIANT` - This environment variable should be a string that contains which TopoMojo variant is deployed. Example: `2`. If this environment variable is not set, the Challenge Server will set the variant to a default of `-1`

## Monitoring Required Services

The Challenge Server can be used to monitor services that a challenge requires. Examples include: a website that needs to remain operational, a Docker container that should always have an open port, a host that should remain reachable, etc. To configure the Challenge Server to monitor required services, use the `required_services` section of the config file.

On a periodic basis (every 30 seconds by default), the Challenge Server will determine if your required services are reachable. It does this by using the `ping` command, making a TCP socket connection, or by visiting a website. These options and their additional required settings are documented in the config file.

Required services can also block startup scripts from executing. This is useful if your startup script requires that a host is up or a service is available. For example, if your startup script needs to use SSH to configure a host, it would be helpful to ensure that ssh is reachable on that host before running the startup script by configuring a `socket` required service on port `22` for the desired host.

## Service Logger

The Challenge Server comes with an additional `service_logger` that can be used to collect logs service logs from other VMs in the challenge environment. This additional feature is detailed more [here](./src/README.md)

## Startup Configuration

You can use the Challenge Server as a central location for configuring all the machines in your environment.

1. Write a startup script (or more than 1) that will remotely configure each machine in your environment to the challenge's specifications. Place all startup scripts in the [custom_scripts](./src/custom_scripts) directory and ensure they are executable (`chmod +x <your_script>`)
1. You can use ssh, psexec, powershell remoting, or any other way to remotely manage each machine in your environment.
1. Your startup script should log all important actions/results to standard out.
1. You can optionally use the `required_services` section to block startup scripts from running until required services are available. This is useful in cases where you need SSH to be available on a target machine for your startup script to function as intended.

Example startup scripts are [here](./src/custom_scripts/).

## Grading

The challenge developer (you) can write a grading script that the server executes under a few circumstances:

- When a button on the website is pressed
- When a certain time of day is reached
- When a certain amount of time has passed
- When the user enters text into the website

The Challenge Server will read tokens from environment variables, VMware guestinfo variables or a file and displaying/submitting the tokens depending on submission configuration.

### Submission

The Challenge Server can display tokens to users for copy/paste submissions on their own.

The Challenge Server can also POST values to the [Gameboard application](https://github.com/cmu-sei/gameboard) and submit answers on a user's behalf.

The challenge developer only needs to write a grading script that will perform any checks needed to ensure successful challenge completion.

### Types of Grading

There are several types of grading that are supported by this server.

- User Presses a Button
  - In this style of grading, the user is expected to visit a website and press a button to initiate grading. The grading script will execute without command line arguments
- User Enters Text
  - In this style of grading, the user is expected to visit a website and submit text which answers questions. The grading script will execute with each text submission passed as a command line argument (use argv to get these)
- Automatic/Scheduled Grading (cron job)
  - In this style of grading, the user is not expected to take any action for grading to occur. Grading happens on an interval and/or at a scheduled time
  - Additional config settings maybe be required for this style to operate to your challenge's specs.

More information about using each grading type is provided in the [supplemental readme](./src/README.md).

#### Uploading Files

The Challenge Server allows users to upload files for grading. This type of grading is useful for:

1. Programming exercises where running the user-supplied code can determine if they have met the success conditions
2. Exercises where parsing a file can determine if the user has met the success conditions

When files are uploaded, the Challenge Server first zips files that are part of the same file set. This allows users to select multiple files to upload, and results in a single zip file being stored on the Challenge Server after upload.

When using the file upload grading type, multiple grading checks can be associated with the same file and multiple files can be associated with one grading check. When uploaded files are associated with a grading check, the Challenge Server will include the path to the file sets as part of the JSON passed to the grading script as an argument.

##### Example

A challenge requires a user to write a Python program that produces an expected output. The user uploads their Python program, consisting of multiple `.py` files in a format that follows the challenge instructions. The grading script will run the Python program in the way that the challenge developer described in the instructions to determine if the uploaded program meets the requirements.

_Caution: Running user-uploaded code can be dangerous. The challenge developer should take necessary security precautions to ensure user-uploaded code/files do not have unintended consequences._

### Grading Scripts

The challenge developer will need to write their own grading script to perform whatever checks are required as part of the challenge grading process. The grading script can be written in any language and will be executed by the grading server automatically when the user presses a button to initiate grading, at a certain time, or other conditions.

The grading script **MUST** produce output in a `key:value` format.  The `key` should be the part of the challenge you are grading (e.g., 'Part1', 'GradingCheck1', etc.).  The `value` should be any message that you want to relay to the user (e.g., 'Success - this check produced the correct output', 'Failure -- this check did not pass', etc.).

Success messages **MUST** minimally include the word 'success'.

Your grading script should output one (1)  `key:value` pair per line. Each new line (and therefore each `key:value` pair) will be treated as different parts of a multi-part challenge.

The following is an example of valid grading script output:

```text
Part1: Success
Part2: Success -- The configuration you applied mitigates the attack
GradingCheck3: Failure - Your configuration is invalid
Check4: Failure
```

Feel free to include as much or as little detail in the message as you'd like the competitor to see. The only requirement is: The word 'success' must be present in the `value` field of any part you want to display a token for.

The Grading Server will use the `keys` output by the grading script to display output to the user. The [config.yml](./src/config.yml) file allows you to specify the text to display to the user for each part and the location to look for tokens.

The Grading Server will also display the `values` output by the grading script to the user. This can help the user figure out why they failed a particular part if useful messages are provided. **Do not include any text in the values that you do not want users to see.**

Your grading script should start with a 'shebang' line which gives the absolute path to the interpreter that should be used to run the program.

- Bash scripts should start with `#!/bin/bash`
- Python scripts should start with `#!/usr/bin/python3`
- PowerShell scripts should start with `#!/snap/bin/pwsh`

Your grading script must have the executable bit set. Ensure you run the following command: `chmod +x <your_script>`.

Example grading scripts are [here](./src/custom_scripts/).

### Submitting Grading Results

This server supports 2 methods for grading results.

- Display a token
  - This is the default method. In this method, a token will be displayed on the website. The user will have to visit the website, copy the token string out of the VM, then paste it to the Gameboard to submit for credit
- Grader POST
  - This method is used when the developer wants to submit answers to the grader (e.g., Gameboard) on the user's behalf. Using this submission method along with automatic grading, will result in user's being awarded points automatically -- no action is needed by the user after the grading check(s) pass.
  - Additional settings required for this are described in the config file comments.

## Hosting Files

This server can be used to host any files you need to share with the competitor inside the challenge environment. To host files, place the files in the [hosted_files](./src/hosted_files/) directory.  This will allow competitors to download the files from inside their challenge environment.

## xAPI/CMI5

The Challenge Server can send [xAPI](https://xapi.com/)/[CMI5](https://xapi.com/cmi5/) compliant statements to a configured [Learning Record Store (LRS)](https://xapi.com/get-lrs/). Using this feature requires configuring variables that are used to communicate with the LRS (see the [supplemental readme](./src/README.md) for configuration details).

1. When a user submits for grading, the Challenge Server will send a [CMI5 Allowed Statement](https://github.com/AICC/cmi-5_Spec_Current/blob/quartz/cmi5_spec.md#713-types-of-statements) with these details:
  a. Verb: `answered`
  b. Question and answer details, including question, question mode (text, multiple choice, etc.), answers, etc.
  c. [Interaction type](https://github.com/adlnet/xAPI-Spec/blob/master/xAPI-Data.md#interaction-types) is set according to the configured question mode
    i. `text` mode maps to the `fill-in` xAPI interaction type
    ii. `mc` mode maps to the `choice` xAPI interaction type
    iii. All other grading modes map to the `performance` xAPI interaction type
2. When a user correctly answers all questions, the Challenge Server will send a [CMI5 Defined Statement](https://github.com/AICC/cmi-5_Spec_Current/blob/quartz/cmi5_spec.md#713-types-of-statements) with these details:
  a. Verb: [completed](https://github.com/AICC/cmi-5_Spec_Current/blob/quartz/cmi5_spec.md#verbs_completed)
  b. The `challenge_name` is used as the statement Object Name.
3. When a user correctly answers all questions, the Challenge Server will send a [CMI5 Defined Statement](https://github.com/AICC/cmi-5_Spec_Current/blob/quartz/cmi5_spec.md#713-types-of-statements) with these details:
  a. Verb: [terminated](https://github.com/AICC/cmi-5_Spec_Current/blob/quartz/cmi5_spec.md#verbs_terminated)
  b. The `challenge_name` is used as the statement Object Name.
