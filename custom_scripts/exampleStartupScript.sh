#!/bin/bash
#
# Challenge Sever
# Copyright 2024 Carnegie Mellon University.
# NO WARRANTY. THIS CARNEGIE MELLON UNIVERSITY AND SOFTWARE ENGINEERING INSTITUTE MATERIAL IS FURNISHED ON AN "AS-IS" BASIS. CARNEGIE MELLON UNIVERSITY MAKES NO WARRANTIES OF ANY KIND, EITHER EXPRESSED OR IMPLIED, AS TO ANY MATTER INCLUDING, BUT NOT LIMITED TO, WARRANTY OF FITNESS FOR PURPOSE OR MERCHANTABILITY, EXCLUSIVITY, OR RESULTS OBTAINED FROM USE OF THE MATERIAL. CARNEGIE MELLON UNIVERSITY DOES NOT MAKE ANY WARRANTY OF ANY KIND WITH RESPECT TO FREEDOM FROM PATENT, TRADEMARK, OR COPYRIGHT INFRINGEMENT.
# Licensed under a MIT (SEI)-style license, please see license.txt or contact permission@sei.cmu.edu for full terms.
# [DISTRIBUTION STATEMENT A] This material has been approved for public release and unlimited distribution.  Please see Copyright notice for non-US Government use and distribution.
# DM24-0645
#


# pulls value of token1 out of guestinfo and puts it into a local filed called token1
token1=$(vmtoolsd --cmd "info-get guestinfo.token1")
echo $token1 > token1

# scp the token1 file over to a different VM on the network. Echo the result as a log
scp -i /home/user/.ssh/id_rsa -o "StrictHostKeyChecking=no" ./token1 user@ubuntu:/home/user/test_file
echo "Done ssh command. Return value was $?"

# edit a local file and echo the result as a log
echo "Example" > /home/user/challengeServer/hosted_files/example
echo "Done echo command. Return value was $?"

# log that the startup script is done and was successful
echo "Done startup configuration. All was successful."