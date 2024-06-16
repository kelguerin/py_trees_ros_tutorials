#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# License: BSD
#   https://github.com/splintered-reality/hugr/raw/devel/LICENSE
#
##############################################################################
# Documentation
##############################################################################
"""
The mocked robot, for use with the tutorials.
"""
##############################################################################
# Imports
##############################################################################

import hugr.mock.launch

##############################################################################
# Launch Service
##############################################################################


def generate_launch_description():
    """
    A ros2 launch script for the mock robot
    """
    return hugr.mock.launch.generate_launch_description()
