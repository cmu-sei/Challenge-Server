#!/usr/bin/env python3

import subprocess, json, datetime, os

## This script will handle configuring services and editing/removing files during shutdown to ensure it is in correct state for committing when off.
## This script will only run in the workspace, these files should not be edited if the server is rebooted during deployment.

def runShutdown():
    ## Use Skills Hub code to check if server running in workspace or gamespace
    challenge_code = subprocess.run(f"vmtoolsd --cmd 'info-get guestinfo.code'", shell=True, capture_output=True).stdout.decode('utf-8').strip()
    challenge_code = "workspace" if not challenge_code or "##" in challenge_code else challenge_code
    in_workspace = True if "workspace" in challenge_code else False
    if in_workspace == True:
        print("Running in workspace...prepping host for commit.")
        # 1. Shutdown skillsHub and dnsmasq service
        cmd1 = subprocess.run(f"sudo systemctl stop skillsHub.service dnsmasq.service", shell=True, capture_output=True)
        # 2. Delete dnsmasq lease file to ensure correct Static IP assignment at boot. Delete Skills Hub SQL DB file to ensure it doesnt get committed in bad state.
        cmd2 = subprocess.run(f"sudo rm /var/lib/misc/dnsmasq.leases /home/user/skillsHub/hub.db", shell=True, capture_output=True)
        logOutput = {
            "services": {
                "stdout": cmd1.stdout.decode('utf-8'),
                "stderr": cmd1.stderr.decode('utf-8')
            },
            "rm_files": {
                "stdout": cmd2.stdout.decode('utf-8'),
                "stderr": cmd2.stderr.decode('utf-8')
            }
        }
        with open('/usr/temp/shutdown_log.txt','a+') as f:
            f.write(f"Workspace shutdown occurred at: {datetime.datetime.now().strftime('%m/%d/%Y %H:%M:%S')}\n")
            f.write(json.dumps(logOutput,indent=2))
        print("Configuration edits completed. VM is ready to be stopped & committed.")

if __name__ == "__main__":
    if os.geteuid() != 0:
        print("Script must be ran as root\n")
        exit()
    runShutdown()
