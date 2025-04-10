# Additional Configuration Details

1. If any script being executed relies on a host in the network to have the same IP, it is recommended to assign a static IP address to host using the `dnsmasq` configuration file.
2. The script `runBeforeCommit.py` is intended to help clean up some files/configurations to ensure teh VM is committed in the desired state. This script will do the following:
    1. Turn off `dnsmasq` and `challengeServer` services. This is to make sure they don't re-create any files that will be removed as part of cleanup.
    2. Delete the `dnsmasq.leases` file. This is required if you assigned static IPs.
    3. Delete the `challenge.db` file to ensure a fresh database instance is created upon every deployment.

## **PLEASE NOTE**

This document will explain each aspect of the new `config.yml` used in the Challenge Server. Each configuration in this document can be found in the [config.yml](../src/config.yml) file in the matching section.

### challenge_name

- This is a standalone configuration available that allows the developer to assign the current challenge
- This is utilized by the `Event Tracker` and all events that are recorded contain this challenge name in it.

## Section 1: startup

This section contains configurations relating to the startup sequence of the server.

- `runInWorkspace`
  - This option tells the server if we want it to execute a startup script in a workspace. It requires a value of either true or false.
  - false -- This will make it so startup scripts do not run in workspace.
  - true -- This will allow for the startup script to run in workspace.
- `scripts`
  - This is the section where you specify a startup script if you are using one. If you are not using one, leave this section commented.
  - If you have a startup script, uncomment `script:` and add an entry with your script starting with a dash (`-`).
  - All scripts must be located within the `custom_scripts` directory and have execute permission. (`chmod 755` or `chmod +x`)
  - It should support having multiple startup scripts and will execute them in the order they are declared. But this feature can be touchy and so it is recommended to have everything needed in one startup script.
  - Currently it does support:
    - passing arguments to the startup script.

## Section 2: required_services

This section contains optional configurations to check specific remote services and have them be required for the challenge to operate.

> All of the listed services will have periodic connectivity checks logged.
> Listed services have the option of preventing startup scripts from executing until they are available (all startup scripts will be blocked until all blocking services are available)

There are five parameters that can utilized when configuring the required services. Some are required while others are optional and can be used depending on the type of check being performed.

### **Required Services**

1. host
   - This is required for each service
   - Consists of the hostname or IP address that is hosting a required service.
2. type
   - This is required for each service
   - The type of connectivity check you want to perform (valid types are listed below)
   - ping (default)
     - Will attempt to ping the defined host.
     - If a ping reply is received, log success.
     - If anything besides a successful ping reply, log failure.
   - socket
     - Will attempt to initiate a socket connection to the defined port.
     - If the connection is successful, log success. If the socket connection is not successful, log failure.
     - Requires the parameter `port` to be defined in service to work.
   - web
     - Will send a web request to the defined host/port/path
     - If the web request returns a 200, log success. If the web request returns anything besides 200, log failure.
     - Port will default to `80` if it is not defined
     - Path will default to `/` if it is not defined.
3. port
   - Defines the port to be used for connectivity checks.
   - Required for service type: socket
   - Defaults to `80` for service type: web
4. path
   - Include only the URI path to be used in the web request (e.g., /)
   - Defaults to `/` for service type: web
5. block_startup_scripts
   - This will determine if the service being checked is required to be up/reachable before the server can run the startup scripts.
   - Can be set to either `true` or `false`
   - Defaults to `false` if it is not defined.

Examples can be found in the `required_services` section of the `config.yml` file.

## Section 3: hosted_files

This section contains option to enable or disable the hosting of files.

- `enabled`
  - Tells website whether or not you want to host files.
  - The value assigned must either be `true` or `false`.

## Section 4: info_and_services

By default these are disabled, but they can be enabled in the config.

- An "Information" home page that provides insight into the challenge, the topology, and any other important data that might be useful during the challenge.
- A "Services" page that tracked and presented the current status of services configured in the `config.yml` file so that users can view them at any time to know if something is broken/incorrect.

## Section 5: services_to_log

This section contains optional configurations where remote services can be polled and have their logs be sent to a logging service.

> List all of the **SYSTEMD** services that logging is required for your challenge to operate.
> All of the listed services will have periodic checks sending their logs to graylog.
> This section is intended to be used as a way to log the status of services throughout the challenge in order to support troubleshooting. It is disabled by default.

There are four required parameters for each service to be logged.

### **Logged Services**

1. host
   - This is the hostname or IP address that is hosting a required service
2. user
   - The user (or username) that will be connected too via SSH.
   - Defaults to 'user', only needs applying if need to connect using a different user.
3. password
   - The password to be used to log in to the account of the user specified.
4. service
   1. the name of the service (including the `.service` extension) that is running on the specified host.

Examples can be found in the `services_to_log` section of the `config.yml` file.

## Section 6: grading

This section contains a variety of options that can be set to affect how grading of questions/tasks occur on the server.

### **Background**

- This server allows for granular control of questions where each question is configured with its own `mode`, which defines how it is graded.
- The modes available are: `text`, `button`, and `cron`.
  - text    -- this option will configure its associated question to prompt the user a text box to be solved.
  - button  -- This option will configure its associated question to be graded by the grading script when pressed.
  - cron    -- this option will configure its associated question to be graded automatically every so often based on the settings below.
- The term `manual` is used to describe a grading mode other than `cron`.
  - This generally refers to the question types `button` and `text` since they require an interaction in order to be graded.
- Due to the nature of how manual grading occurs Vs cron grading, each mode requires its own grading script.

### Configuration

This section contains options that relate to grading of both manual and cron type questions.

- `enabled`
  - Set this to `true` if you need any grading.
  - `false` will disable all grading regardless of additional config.
- `grader_post`
  - Set this to `true` if you want the grading results to be automatically posted to Gameboard. (Currently requires testing)
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
  - Setting value can be overwritten by using guestinfo variables and passing `test_cron_interval` as the variable name.
- `cron_at`
  - Start executing the cron job at a certain time - uses 24-hour time format
  - Format:   "%H:%M"  where %H is a zero padded hour (24 hour format)  and %M is a zero padded minute
  - Time must be inside double quotes " "
  - the value `null` will ignore this setting
  - If the setting `cron_delay` is set below, the grading will occur **AFTER** this time condition is met
  - Setting value can be overwritten by using guestinfo variables and passing `test_cron_at` as the variable name.
- `cron_delay`
  - Set how long to wait before the first cron-type grading fires off
  - Any delays will take place AFTER the cron_at time is reached
  - Setting value can be overwritten by using guestinfo variables and passing `test_cron_delay` as the variable name.
  - EXAMPLE:
    - If you set cron_at to be 00:00  and delay to be 3600, then the first grading will run at 01:00
- `cron_limit`
  - Set a limit on the number of times the cron job should run. Needs to be whole integer.
  - Setting value can be overwritten by using guestinfo variables and passing `test_cron_limit` as the variable name.
- `rate_limit`
  - This setting applies to manual grading tasks as it can limit the frequency of grading done by the user.
  - set this to the number of seconds you want the user to be required to wait in between grading attempts
  - The value `0` means there is no limit
- `token_location`
  - set to `[guestinfo]` if tokens are located in guestinfo variables. This is usually what is used.
  - set to `[file]` if tokens are located in a file on disk.

### grading subsection: submission

This section contains settings that are required in order to POST results to source outside gamespace.

- `method`  -- **needs testing -- may not be needed**
  - Should not be changed from value `display`
  - these grader variables can be set with guestinfo variables too - use the same variable name in guestinfo
- `grader_url`
  - URL to be used to send POST request in order to upload results to Gameboard. Should not be changed unless developer understands what they need to change it to
- `grader_key`
  - KEY that is required and needs to be included in POST request to Gameboard.

### grading subsection: parts

This section contains parameters for the questions that are asked as part of the challenge.

The format of each entry in this section consists of the `part_name` which defines the key to be used. Within that key is the sections `token_name`, `text`, and `mode.`

- `part name`
  - This is the `key` to be used to define what question is being asked.
  - All entries must follow the same syntax of: `GradingCheck` followed by a number which indicates what number question it is.
  - For example, the first entry should be defined as `GradingCheck1`, the second entry should be labeled as `GradingCheck2`, and so on.
  - This name **is case sensitive**, so ensure you follow the syntax
- `token_name`
  - The string entered here should match the same name you used for the associated value in the guest variables.
  - The value pulled from the associated guest variable will be assigned to this question.
  - It is suggested to follow the same naming format as the `part_names`, where the first questions guest variable would be `Q1`, the second is `Q2`, and so on. Although this is not required. They just need to match.
  - **IF** you are referencing a file for the tokens, this value should be the full path pointing to the file.
- `text`
  - This is the string that will be presented on the servers task page.
  - This should be the question you are asking the user or the task that needs to be completed.
- `mode`
  - This is the type of grading that needs to occur for this question.
  - options are: `text`, `button`, or `cron`.

### phases (question sets)

This section contains settings to configure phase grading in order to support question sets.

#### Background

Phases were implemented to correlate to specific tasks that should be graded together in a challenge. They aren't required to  map 1:1 to question sets, but can be. It Depends on the structure of challenge.

Phases are intended to be used to split up the grading to only grade on the tasks they're currently on.

This will cut down on grading time as questions that have been completed shouldn't need to be graded again and tasks they're not on yet don't need to be graded.

Additionally, phases cannot be completed unless the previous phase has been completed. This is to force users to have to step through solution rather than just skip ahead.

If the requirement is to have this training end with a sort of `test` or `mini-challenge`, this is where it will be defined

- `phases`
  - Set this to `true` if you want to enable phases and have the questions be prompted to the user in order, only allowing new questions to be shown once all the previous ones have been solved.
- `phase_info`
  - This is where you define the phases you want in your challenge.
  - Each entry under `phase_info` consists of a single `key:value pair`, where the key is the name of the phase and the value is a list type object consisting of all the questions you want asked in that phase.
  - The naming convention for the key must generally use the format `"phase"+ #`, where the `#` correlates to which number phase it is.
    - For example: the first phase needs to be set as `phase1`, the second is `phase2`, etc.
  - The only caveat to the naming convention is that the final entry in this section can be created with the key `mini_challenge` to indicate the final part of the challenge.
  - As stated, the value for any of these entries is required to be a list.
  - The list should contain strings, where each string is the `key` of a specific question that was defined in the `parts` section above.

The default configuration will present an example of how to declare your questions and then how phases can be configured with specific questions to be asked.

Also Note: The entry `mini_challenge` is commented out in the phase section, but can be uncommented and used if the developer wishes.
