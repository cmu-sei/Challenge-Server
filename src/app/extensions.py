#!/usr/bin/env python3

import logging
from flask_sqlalchemy import SQLAlchemy
# local imports
from app.globals import Globals


#######
## This file contains all of the persistent objects to be used throughout the sites execution
#######

# Create database object, currently unused
db = SQLAlchemy()

# Instantiate globals object
globals = Globals()

# configure logging obj (default log level of INFO)
logging.basicConfig(format=f'SKILLS-HUB | %(threadName)s | %(levelname)s | {globals.support_code} | {globals.challenge_code} | Variant {globals.variant_index} | %(message)s', level=logging.INFO)
logger = logging.getLogger("skillsHub")