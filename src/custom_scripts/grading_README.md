# Skills Hub Server Grading README
> This document will explain how grading works in the Skills Hub Server.<br>

## Grading

It was referenced in the `config_README.md` file but the Skills Hub Server has been updated to allow for two grading scripts to be entered into its configuration. 
- One grading script to be used for all questions that are defined with the `cron` grading type 
- One grading script then to be used for all questions that are a `manual` grading type (text, button).

This is due to the fact that the grading mode is now configured on a per-question basis, and if the developer wants to be able to grade both types then this allows for it. They were separated as well due to the nature of each grading type as we don't want to run the same grading script every time grading occurs whether it be cron or a user submission. So this allows for separation of them.

Like its predecessor, the Challenge Server, the grading script should only print out a string for each task/token that follows the format: `task : status -- optional msg`, where the status is either `Failure` or `Success`, followed by an optional message starting with two hyphens (`--`) if the developer wants to provide feedback to the user.
<br><br>

### runSSHCommand function

I've added the function `runSSHCommand` at the top of the `manualGradingExample.py` script. This function can be used to execute SSH commands to a remote host.

It requires the following arguments to be passed to it:
- The `username` you want to log into on remote host.
- The `password` for that user.
- The `hostname` of remote host you want to connect to (IP address or DNS name work).
- A **list** variable that contains all the commands you want to execute on the remote host.

This function will always return a **dictionary** data type, regardless if the connection/commands pass or fail. So make sure to check the output after calling the function. 

If `error` is present as a key in the functions output, that means one of the following has occurred:
1. One of the required arguments was missing in the function call. 
2. The command(s) were not passed in as a list data type.
3. The SSH connection failed and couldn't be completed.

If the connection succeeds, the function will then loop through running all of the passed commands and storing their output into a dictionary. Once all commands have been ran, it will close the connection and return the results. 

The results dictionary will follow this structure:

```json
{
    "cmd1": {
            "command":"Command executed",
            "stdout": "**output returned from running command**",
            "stderr": "**errors/exceptions messages returned from running the command**"
        }
}
```

Some bash commands are weird with how they return data, some commands return it through `stdout` while others return some information from `stderr`, so both are saved.


### Manual type (text, button)

If your lab doesn't utilize question sets and/or `phases` and have `phases` disabled in `config.yml`, then the grading script can be created like normal without any special formatting.

If you do have question sets and/or `phases` in your lab and have `phases` enabled, you will need to format the grading script in a specific way.

for this explanation, we will assume that the Skills Hub `config.yml` is configured with the following settings (which is also the default phase configuration). For reference, here is what it looks like in the `config.yml` file:

```yml
phases: true
phase_info:
    phase1: ["GradingCheck1", "GradingCheck2"]
    phase2: ["GradingCheck3"]
    phase3: ["GradingCheck4"]
```
<br><br>

#### Understanding Skills Hub Functionality 

In this example, the server is configured with three phases, where questions 1 and 2 are in phase 1, question 3 is in phase 2, and question 4 is in phase 3. 

When phases are configured, the web server will only present the questions on the `tasks` page that are associated with the phase the user is currently on. For example: If the user is on phase 1, only questions 1 and 2 will be presented. Once these questions are solved, it will present the questions for the next phase the next time you visit the `tasks` page.

**IMPORTANT**: In order to specify what phase is currently being graded, the server will pass the name of the current phase being graded to the grading script as an argument. This argument will always be the **FINAL** argument in the argument list. It is created this way because other data may be passed to the grading script based on the question type being graded (`text` questions will pass submitted strings to the grading script), and so appending the phase as the last argument is efficient and allows for easier consistency. 
<br><br>

#### Grading Script Requirements

Due to the server passing the current phase to the grading script, the grading script must have a method of reading in the current phase passed by the server and then grading the corresponding questions based on that data.

Additionally, as the lab progresses there may be different question types that are being graded and so there also needs to be a method of checking the arguments being passed to the grading script and having it react accordingly.

To support this, the Skills Hub Server will always pass any/all submission data that was inputted from the user as a `JSON string`. This string will always be the first argument passed to the grading script (Which is also the 2nd argument when using `sys.argv` in Python)

To help with creating the grading script, I have detailed the method I used to read in the data and have the grading script act correctly based on the data. Please view the data below to view how I accomplished this:

- I created a function for each phase in the grading script, where the name of the function needs to match the phase currently being graded.
- There is no limit to the number of phases you can implement, you just need to ensure that each phase configured in `config.yml` corresponds to a function in your grading script.
- Remember that if data is passed to your grading script, it will be in `JSON` format.
- The code snippet below is the `main` function pulled from `manualGradingExample.py` and so the information below is based off that entire file.
    - The code below contains code that covers all possible configurations that a lab could have when grading (Phases enabled & grade user submission, phases enabled but no user submission, phases disabled but grade user submission, and phases disabled and no user submissions)
    - The `manualGradingExample.py` grading script has a function labeled `phase1` and within it is code that will grade the questions that make up `phase1`(which should be configured in `config.yml`) -- In this scenario is the questions associated with `GradingCheck1` and `GradingCheck2`.
    - Next, it should have another function labeled as `phase2` containing the code to grade the questions that make up `phase2`
    - and lastly the function `phase3` containing the code to grade the question associated with the label `GradingCheck4`.
    - I create a `phases` list object that contains the names of all the phases that need to be graded (Which needs to match what is configured in `config.yml`)
    - I check the passed arguments to see if a phase has been passed by comparing the phase passed to the list of phases.
    - If valid phase has been passed, run its associated function and pass any arguments to it if they are present.
    - If no phase is passed, then the grading script will execute all the functions in the script effectively grading everything in the lab.


```python
if __name__ == '__main__':
    phases = ['phase1','phase2','phase3']
    args = sys.argv[1:]
    if len(args) > 0:
        passed_phase = args[-1].strip().lower()
        if passed_phase in phases:
            ## This section will grade if phases are enabled & phase is read in correctly.
            res = dict()
            if len(args) > 2:
                ques_sub = args
                ques_sub.pop(-1)
                res = globals()[passed_phase](ques_sub)
            else:
                res = globals()[passed_phase]()
            for key,val in res.items():
                print(key, ' : ', val)
        else:
            # This section is intended to be used if 'phases' are not enabled in server & all grading occurs at once
            # This section is used if some data is supposed to be passed to grading script from SH
            res = dict()
            ques_sub = args
            ques_sub.pop(-1)
            for phase_func in ['phase1','phase2','phase3']:
                output = globals()[phase_func](ques_sub)
                res.update(output)
            [print(key, " : ",val) for key,val in res.items()]
    else:
        # This section is intended to be used if 'phases' are not enabled in server & all grading occurs at once
        res = dict()
        for phase in phases:
            output = globals()[phase]()
            res.update(output)
        [print(key, " : ",val) for key,val in res.items()]
```
<br><br>

## **NOTE**

This server is still being edited, tested, and updated so there may be bugs that appear. 