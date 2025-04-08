#!/usr/bin/env python3
#
# Challenge Sever
# Copyright 2024 Carnegie Mellon University.
# NO WARRANTY. THIS CARNEGIE MELLON UNIVERSITY AND SOFTWARE ENGINEERING INSTITUTE MATERIAL IS FURNISHED ON AN "AS-IS" BASIS. CARNEGIE MELLON UNIVERSITY MAKES NO WARRANTIES OF ANY KIND, EITHER EXPRESSED OR IMPLIED, AS TO ANY MATTER INCLUDING, BUT NOT LIMITED TO, WARRANTY OF FITNESS FOR PURPOSE OR MERCHANTABILITY, EXCLUSIVITY, OR RESULTS OBTAINED FROM USE OF THE MATERIAL. CARNEGIE MELLON UNIVERSITY DOES NOT MAKE ANY WARRANTY OF ANY KIND WITH RESPECT TO FREEDOM FROM PATENT, TRADEMARK, OR COPYRIGHT INFRINGEMENT.
# Licensed under a MIT (SEI)-style license, please see license.txt or contact permission@sei.cmu.edu for full terms.
# [DISTRIBUTION STATEMENT A] This material has been approved for public release and unlimited distribution.  Please see Copyright notice for non-US Government use and distribution.
# DM24-0645
#


import logging
from flask_sqlalchemy import SQLAlchemy
from app.globals import Globals


#######
## This file contains all of the persistent objects to be used throughout the sites execution
#######

# Create database object, currently unused
db = SQLAlchemy()

# Instantiate globals object
globals = Globals()

# configure logging obj (default log level of INFO)
logging.basicConfig(format=f'CHALLENGE-SERVER | %(threadName)s | %(levelname)s | {globals.support_code} | {globals.challenge_code} | Variant {globals.variant_index} | %(message)s', level=logging.INFO)
logger = logging.getLogger("challengeServer")
