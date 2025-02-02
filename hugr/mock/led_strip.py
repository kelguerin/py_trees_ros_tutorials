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
Mock a hardware LED strip.
"""


##############################################################################
# Imports
##############################################################################

import argparse
import functools
import math
import py_trees.console as console
import py_trees_ros
import rclpy
import std_msgs.msg as std_msgs
import sys
import threading
import uuid

##############################################################################
# Class
##############################################################################


class LEDStrip(object):
    """
    Emulates command/display of an led strip so that it flashes various colours.

    Node Name:
        * **led_strip**

    Publishers:
        * **~display** (:class:`std_msgs.msg.String`)

          * colourised string display of the current led strip state

    Subscribers:
        * **~command** (:class:`std_msgs.msg.String`)

          * send it a colour to express, it will flash this for the next 3 seconds
    """
    _pattern = '*'
    _pattern_width = 60  # total width of the pattern to be output
    _pattern_name_spacing = 4  # space between pattern and the name of the pattern

    def __init__(self):
        self.node = rclpy.create_node("led_strip")
        self.command_subscriber = self.node.create_subscription(
            msg_type=std_msgs.String,
            topic='~/command',
            callback=self.command_callback,
            qos_profile=py_trees_ros.utilities.qos_profile_unlatched()
        )
        self.display_publisher = self.node.create_publisher(
            msg_type=std_msgs.String,
            topic="~/display",
            qos_profile=py_trees_ros.utilities.qos_profile_latched()
        )
        self.duration_sec = 3.0
        self.last_text = ''
        self.last_uuid = None
        self.lock = threading.Lock()
        self.flashing_timer = None

    def _get_display_string(self, width: int, label: str="Foo") -> str:
        """
        Display the current state of the led strip as a formatted
        string.

        Args:
            width: the width of the pattern
            label: display this in the centre of the pattern rather
                than the pattern name
        """
        # top and bottom of print repeats the pattern as many times as possible
        # in the space specified
        top_bottom = LEDStrip._pattern * int(width / len(LEDStrip._pattern))
        # space for two halves of the pattern on either side of the pattern name
        mid_pattern_space = (width - len(label) - self._pattern_name_spacing * 2) / 2

        # pattern for the mid line
        mid = LEDStrip._pattern * int(mid_pattern_space / len(LEDStrip._pattern))

        # total length of the middle line with pattern, spacing and name
        mid_len = len(mid) * 2 + self._pattern_name_spacing * 2 + len(label)

        # patterns won't necessarily match up with the width, so need to deal
        # with extra space. Odd numbers of extra space handled by putting more
        # spaces on the right side
        extra_space = width - mid_len
        extra_left_space = int(math.floor(extra_space / 2.0))
        extra_right_space = int(math.ceil(extra_space / 2.0))

        # left and right parts of the mid line to go around the name
        left = mid + ' ' * (self._pattern_name_spacing + extra_left_space)
        right = ' ' * (self._pattern_name_spacing + extra_right_space) + mid

        return '\n' + top_bottom + '\n' + left + label.replace('_', ' ') + right + '\n' + top_bottom

    def generate_led_text(self, colour: bool) -> str:
        """
        Generate a formatted string representation of the  the current state of the led strip.

        Args:
            colour: use shell escape sequences for colour, matching the specified text colour label
        """
        if not colour:
            return ""
        else:
            text = self._get_display_string(self._pattern_width, label=colour)

            # map colour names in message to console colour escape sequences
            console_colour_map = {
                'grey': console.dim + console.white,
                'red': console.red,
                'green': console.green,
                'yellow': console.yellow,
                'blue': console.blue,
                'purple': console.magenta,
                'white': console.white
            }

            coloured_text = console_colour_map[colour] + console.blink + text + console.reset
            return coloured_text

    def command_callback(self, msg: std_msgs.String):
        """
        If the requested state is different from the existing state, update and
        restart a periodic timer to affect the flashing effect.

        Args:
            msg (:class:`std_msgs.msg.String`): incoming command message
        """
        with self.lock:
            text = self.generate_led_text(msg.data)
            # don't bother publishing if nothing changed.
            if self.last_text != text:
                self.node.get_logger().info("{}".format(text))
                self.last_text = text
                self.last_uuid = uuid.uuid4()
                self.display_publisher.publish(std_msgs.String(data=msg.data))
            if self.flashing_timer is not None:
                self.flashing_timer.cancel()
                self.node.destroy_timer(self.flashing_timer)
            # TODO: convert this to a one-shot once rclpy has the capability
            # Without oneshot, it will keep triggering, but do nothing while
            # it has the uuid check
            self.flashing_timer = self.node.create_timer(
                timer_period_sec=self.duration_sec,
                callback=functools.partial(
                    self.cancel_flashing,
                    this_uuid=self.last_uuid
                )
            )

    def cancel_flashing(self, this_uuid: uuid.UUID):
        """
        If the notification identified by the given uuid is still relevant (i.e.
        new command requests haven't come in) then publish an update with an
        empty display message.

        Args:
            this_uuid: the uuid of the notification to cancel
        """
        with self.lock:
            if self.last_uuid == this_uuid:
                # We're still relevant, publish and make us irrelevant
                self.display_publisher.publish(std_msgs.String(data=""))
                self.last_text = ""
                self.last_uuid = uuid.uuid4()

    def shutdown(self):
        """
        Cleanup ROS components.
        """
        self.node.destroy_node()


def main():
    """
    Entry point for the mock led strip.
    """
    parser = argparse.ArgumentParser(description='Mock an led strip')
    command_line_args = rclpy.utilities.remove_ros_args(args=sys.argv)[1:]
    parser.parse_args(command_line_args)
    rclpy.init(args=sys.argv)
    led_strip = LEDStrip()
    try:
        rclpy.spin(led_strip.node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        rclpy.try_shutdown()
