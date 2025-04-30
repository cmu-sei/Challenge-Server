# Challenge Server Configuration

This document explains each setting in the [config.yml](./config.yml).

## app

- `host` - IP address to host the site on (defaults to `0.0.0.0`)
- `port` - Port to host the site on (defaults to `8888`)
- `tls_cert` - Certificate to use for HTTPS (defaults to None)
- `tls_key` - Private key for the HTTPS cert above (defaults to None)S

## port_checker

- When set to true, this enables a feature that will use the `ss` command to log all open ports on the system every 30 seconds.
- Defaults to false.

## challenge_name

- Name of the challenge
- This is utilized by the `Event Tracker`. All events that are recorded contain this challenge name.

## startup

- `runInWorkspace`
  - `true` if the developer wants to run startup scripts in a workspace.
  - `false` if the developer only wants to run startup scripts in a gamespace.

- `scripts`
  - List of startup scripts to execute before the server becomes available.
  - All scripts must be in the [custom_scripts](./custom_scripts/) directory and have execute permissions (`chmod +x`).

## required_services

This section contains optional configurations to regularly check the status remote services. These are services that are required for the challenge to operate as intended.

All required services will have periodic connectivity checks logged.

Services can optionally prevent startup scripts from executing until they are available. **When using this option, all startup scripts will be blocked until all blocking services are available.**

- `host` - required - hostname/IP address of the remote service
- `type` - required - type of connectivity check (options listed below) to perform
  - `ping` (default)
    - Attempt to ping the host.
    - If a ping reply is received, log success. Else, log failure.
  - `socket`
    - Attempt to initiate a socket connection to the host on the specified port.
    - If the connection is successful, log success. Else, log failure.
    - Requires the parameter `port` to be defined in service to work.
  - `web`
    - Send a web request to the defined host/port/path
    - If the web request returns a 200, log success. Else, log failure.
    - Port will default to `80` if it is not defined
    - Path will default to `/` if it is not defined.
- `port` - optional - port to use for connectivity checks (socket and web)
  - Required for service type: `socket`
  - Defaults to `80` for service type: web
- `path` - optional - the URI path to be used in the web request (e.g., `/`, `/test`)
  - Defaults to `/` for service type: web
- `block_startup_scripts` - optional - block startup scripts until this service is available
  - Can be set to `true` or `false` (default)

Examples can be found in the `required_services` section of the `config.yml` file.

## hosted_files

- `enabled` - true/false if hosted files should be enabled (allow users to download artifacts). `false` by default.

## info_and_services

- `info_home_enabled` - Provides an "Information" home page that provides challenge insight. Disabled by default.
- `services_home_enabled` - Provides a "Services" page to show the current status of required services. Useful for troubleshooting the environment. Disabled by default.

## services_to_log

Remote services can be polled for status and their logs sent to a logging service.

List any **SYSTEMD** services that are required for the challenge to operate. All services will be polled periodically.

**This service required SSH enabled on the remote host.**

- `host` - Hostname/IP address that is hosting a required service
- `user` - Username to use with SSH connections. Deafults to `user`
- `password` - Password to use with SSH connections
- `service` - name of the systemd service (including the `.service` extension)

Examples can be found in the `services_to_log` section of the `config.yml` file.

## grading

- `enabled`
  - Set this to `true` if you need any grading.
  - `false` will disable all grading regardless of additional config.
- `grader_post`
  - Set this to `true` if you want the grading results to be automatically posted to Gameboard.
- `manual_grading`
  - Set this to `true` if you have *any* questions that are configured with a manual-type mode. (I.e: text, button)
  - Otherwise, set `false`
- `manual_grading_script`
  - This setting is required if `manual_grading` is set to `true`. (I.e: there are manual type questions.)
  - The script is required to be in the `custom_scripts` directory and requires execution permission.
- `cron_grading`
  - Set this to `true` if you have *any* questions that are configured with the mode cron.
  - Otherwise, set `false`
- `cron_grading_script`
  - This setting is required if `cron_grading` is set to `true`. (I.e: there are cron type questions.)
  - The script is required to be in the `custom_scripts` directory and requires execution permission.
- `cron_interval`
  - Set how many seconds are between each run of your cron-type grading
  - Setting can be overwritten with an environment variable named `CS_CRON_INTERVAL`.
- `cron_at`
  - Start executing the cron job at a certain time - uses 24-hour time format
  - Format:   "%H:%M"  where %H is a zero padded hour (24 hour format)  and %M is a zero padded minute
  - Time must be inside double quotes " "
  - the value `null` will ignore this setting
  - If the setting `cron_delay` is set below, the grading will occur **AFTER** this time condition is met
  - Setting can be overwritten with an environment variable named `CS_CRON_AT`.
- `cron_delay`
  - Set how long to wait before the first cron-type grading fires off
  - Any delays will take place AFTER the cron_at time is reached
  - Setting can be overwritten with an environment variable named `CS_CRON_DELAY`.
  - EXAMPLE:
    - If you set `cron_at = 00:00` and `cron_delay = 3600`, the first grading will run at `01:00`
- `cron_limit`
  - Set a limit on the number of times the cron job should run. Needs to be whole integer.
  - Setting can be overwritten with an environment variable named `CS_CRON_LIMIT`.
- `rate_limit`
  - This setting applies to manual grading tasks as it can limit the frequency of grading done by the user.
  - set this to the number of seconds you want the user to be required to wait in between grading attempts
  - The value `0` means there is no limit
  - Setting can be overwritten with an environment variable named `CS_GRADING_RATE_LIMIT`.
- `token_location`
  - set to `env` if tokens are located in environment variables. **This is the default.**
  - set to `guestinfo` if tokens are located in VMware guestinfo variables.
  - set to `file` if tokens are located in a file on disk.
  - Setting can be overwritten with an environment variable named `CS_TOKEN_LOCATION`.

### submission

- `method`
  - `display` - Display the token to the user on the Challenge Server website
  - `grader_post` - Submit the answer to a grading service (e.g., Gameboard) on the user's behalf
    - `grader_url`- URL to be used to send POST request in order to upload results to Gameboard.
    - `grader_key`- API Key that is required and needs to be included in POST request to Gameboard.

### parts

- `part name` - The `key` that defines the question.
  - All entries should typically follow the same syntax of: `GradingCheck` followed by a number (e.g., the first entry is `GradingCheck1`, the second entry is `GradingCheck2`, etc.).
- `token_name` - The name of the token variable (environment variable, guestinfo variable, etc.).
  - Best practice is to follow the same naming format as the `part_names`, where the first is named `token1`, the second is `token2`, and so on.
  - **If you are using the `file` token_location, this value should be the full path to the file.**
- `text` - Question text to display to the user on the task page.
- `mode` - Grading mode for this question.
  - `text` - Provide the user with a text box to submit an answer.
  - `button` - Provides a button to trigger the grading script.
  - `cron` - Grade automatically on the configured schedule (see `cron_grading` settings).
  - `upload` - Allow users to upload files that are processed by the grading script.
    - `upload_key` - Define a set of files that an uploaded file should belong to. This is useful if multiple grading checks are looking at the same file or if multiple uploaded files are associated with one grading check. This value will be used to generate the name of the saved artifact.
  - `mc` - Multiple Choice question.
    - `opts` -- Multiple choice options. Only applies when question mode is `mc`.
      - Keys start at `a` and continue in alphabetical order.
      - Values are the text for each option.

### phases (question sets)

Phases group tasks that should be graded together. Phases are intended to split grading based on a set of currently available tasks - old tasks are no longer graded and future tasks are not yet available.

A phase cannot be viewed until the previous phase has been completed. This is to force users to step through a solution rather than skip to the end.

- `phases` - Set to `true` if you want to enable phases. (defaults to false)
- `phase_info` - A list of phases
  - Each entry under `phase_info` consists of a single `key:value pair`, where the key is the name of the phase and the value is a list of the parts (see parts above) in that phase.
  - Best practice is to name phases with `phase` followed by a number (e.g., `phase1`, `phase2`, etc.).

Examples can be found in the `config.yml` file.
