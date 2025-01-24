#!/usr/bin/python3
#
# Challenge Sever
# Copyright 2024 Carnegie Mellon University.
# NO WARRANTY. THIS CARNEGIE MELLON UNIVERSITY AND SOFTWARE ENGINEERING INSTITUTE MATERIAL IS FURNISHED ON AN "AS-IS" BASIS. CARNEGIE MELLON UNIVERSITY MAKES NO WARRANTIES OF ANY KIND, EITHER EXPRESSED OR IMPLIED, AS TO ANY MATTER INCLUDING, BUT NOT LIMITED TO, WARRANTY OF FITNESS FOR PURPOSE OR MERCHANTABILITY, EXCLUSIVITY, OR RESULTS OBTAINED FROM USE OF THE MATERIAL. CARNEGIE MELLON UNIVERSITY DOES NOT MAKE ANY WARRANTY OF ANY KIND WITH RESPECT TO FREEDOM FROM PATENT, TRADEMARK, OR COPYRIGHT INFRINGEMENT.
# Licensed under a MIT (SEI)-style license, please see license.txt or contact permission@sei.cmu.edu for full terms.
# [DISTRIBUTION STATEMENT A] This material has been approved for public release and unlimited distribution.  Please see Copyright notice for non-US Government use and distribution.
# DM24-0645
#



print("test script 1")


## This script can do anything you need it to do. 

## It can ssh to other machines and run commands
# import paramiko
# ssh = paramiko.SSHClient()
# ssh.connect(server, username=username, password=password)
# ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(cmd_to_execute)



## It can use psexec to remote into windows machines and run commands
# from pypsexec.client import Client
# client = Client(ip, username=user, password=pw, encrypt=False)
# try:
#     # connect to client
#     client.connect()
#     client.create_service()
#     # start remote process
#     stout, sterr, pid = client.run_executable("cmd.exe",
#                                         arguments=f"/c type_your_cmd_here",
#                                         asynchronous=False)

# except Exception as e:
#     print(f"Exception {e}")
