#!/usr/bin/env python3
#
# Challenge Sever
# Copyright 2024 Carnegie Mellon University.
# NO WARRANTY. THIS CARNEGIE MELLON UNIVERSITY AND SOFTWARE ENGINEERING INSTITUTE MATERIAL IS FURNISHED ON AN "AS-IS" BASIS. CARNEGIE MELLON UNIVERSITY MAKES NO WARRANTIES OF ANY KIND, EITHER EXPRESSED OR IMPLIED, AS TO ANY MATTER INCLUDING, BUT NOT LIMITED TO, WARRANTY OF FITNESS FOR PURPOSE OR MERCHANTABILITY, EXCLUSIVITY, OR RESULTS OBTAINED FROM USE OF THE MATERIAL. CARNEGIE MELLON UNIVERSITY DOES NOT MAKE ANY WARRANTY OF ANY KIND WITH RESPECT TO FREEDOM FROM PATENT, TRADEMARK, OR COPYRIGHT INFRINGEMENT.
# Licensed under a MIT (SEI)-style license, please see license.txt or contact permission@sei.cmu.edu for full terms.
# [DISTRIBUTION STATEMENT A] This material has been approved for public release and unlimited distribution.  Please see Copyright notice for non-US Government use and distribution.
# DM24-0645
#

# This script cleans up files to ensure a clean boot after saving a VM running this service

import subprocess, json, datetime, os

def runShutdown():
    ## Use challenge code to check if server running in workspace or gamespace
    challenge_code = subprocess.run(f"vmtoolsd --cmd 'info-get guestinfo.code'", shell=True, capture_output=True).stdout.decode('utf-8').strip()
    challenge_code = "workspace" if not challenge_code or "##" in challenge_code else challenge_code
    in_workspace = True if "workspace" in challenge_code else False
    if in_workspace == True:
        print("Running in workspace...prepping host for commit.")
        # 1. Shutdown challengeServer and dnsmasq service
        cmd1 = subprocess.run(f"sudo systemctl stop challengeServer.service dnsmasq.service", shell=True, capture_output=True)
        # 2. Delete dnsmasq lease file to ensure correct Static IP assignment at boot. Delete challengeServer SQL DB file to ensure it doesn't get committed in bad state.
        cmd2 = subprocess.run(f"sudo rm /var/lib/misc/dnsmasq.leases /home/user/challengeServer/challenge.db", shell=True, capture_output=True)
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
        print("Script must be run as root\n")
        exit()
    runShutdown()
