#!/usr/bin/env python3
# -*- coding: utf-8 -*-

##############################################################################
# Imports
##############################################################################

import operator
import sys

import launch
import launch_ros
import py_trees
import py_trees_ros.trees
import py_trees.console as console
import py_trees_ros_interfaces.action as py_trees_actions  # noqa
import rclpy

from . import behaviours
from . import mock

##############################################################################
# Launcher
##############################################################################


def generate_launch_description():
    """
    Launcher for the tutorial.

    Returns:
        the launch description
    """
    return launch.LaunchDescription(
        mock.launch.generate_launch_nodes() +
        [
            launch_ros.actions.Node(
                package='hugr',
                executable="tree-action-clients",
                output='screen',
                emulate_tty=True,
            )
        ]
    )

##############################################################################
# Tutorial
##############################################################################


def tutorial_create_root() -> py_trees.behaviour.Behaviour:
    """
    Insert a task between battery emergency and idle behaviours that
    controls a rotation action controller and notifications simultaenously
    to scan a room.

    Returns:
        the root of the tree
    """
    root = py_trees.composites.Parallel(
        name="Tutorial Five",
        policy=py_trees.common.ParallelPolicy.SuccessOnAll(
            synchronise=False
        )
    )

    topics2bb = py_trees.composites.Sequence(name="Topics2BB", memory=True)
    scan2bb = py_trees_ros.subscribers.EventToBlackboard(
        name="Scan2BB",
        topic_name="/dashboard/scan",
        qos_profile=py_trees_ros.utilities.qos_profile_unlatched(),
        variable_name="event_scan_button"
    )
    battery2bb = py_trees_ros.battery.ToBlackboard(
        name="Battery2BB",
        topic_name="/battery/state",
        qos_profile=py_trees_ros.utilities.qos_profile_unlatched(),
        threshold=30.0
    )
    tasks = py_trees.composites.Selector(name="Tasks", memory=False)
    flash_red = behaviours.FlashLedStrip(
        name="Flash Red",
        colour="red"
    )

    # Emergency Tasks
    def check_battery_low_on_blackboard(blackboard: py_trees.blackboard.Blackboard) -> bool:
        return blackboard.battery_low_warning

    battery_emergency = py_trees.decorators.EternalGuard(
        name="Battery Low?",
        condition=check_battery_low_on_blackboard,
        blackboard_keys={"battery_low_warning"},
        child=flash_red
    )
    # Worker Tasks
    scan = py_trees.composites.Sequence(name="Scan", memory=True)
    is_scan_requested = py_trees.behaviours.CheckBlackboardVariableValue(
        name="Scan?",
        check=py_trees.common.ComparisonExpression(
            variable="event_scan_button",
            value=True,
            operator=operator.eq
        )
    )
    scan_preempt = py_trees.composites.Selector(name="Preempt?", memory=False)
    is_scan_requested_two = py_trees.decorators.SuccessIsRunning(
        name="SuccessIsRunning",
        child=py_trees.behaviours.CheckBlackboardVariableValue(
            name="Scan?",
            check=py_trees.common.ComparisonExpression(
                variable="event_scan_button",
                value=True,
                operator=operator.eq
            )
        )
    )
    scanning = py_trees.composites.Parallel(
        name="Scanning",
        policy=py_trees.common.ParallelPolicy.SuccessOnOne()
    )
    scan_rotate = py_trees_ros.actions.ActionClient(
        name="Rotate",
        action_type=py_trees_actions.Rotate,
        action_name="rotate",
        action_goal=py_trees_actions.Rotate.Goal(),  # noqa
        generate_feedback_message=lambda msg: "{:.2f}%%".format(msg.feedback.percentage_completed)
    )
    flash_blue = behaviours.FlashLedStrip(
        name="Flash Blue",
        colour="blue"
    )
    scan_celebrate = py_trees.composites.Parallel(
        name="Celebrate",
        policy=py_trees.common.ParallelPolicy.SuccessOnOne()
    )
    flash_green = behaviours.FlashLedStrip(name="Flash Green", colour="green")
    scan_pause = py_trees.timers.Timer("Pause", duration=3.0)
    # Fallback task
    idle = py_trees.behaviours.Running(name="Idle")

    root.add_child(topics2bb)
    topics2bb.add_children([scan2bb, battery2bb])
    root.add_child(tasks)
    tasks.add_children([battery_emergency, scan, idle])
    scan.add_children([is_scan_requested, scan_preempt, scan_celebrate])
    scan_preempt.add_children([is_scan_requested_two, scanning])
    scanning.add_children([scan_rotate, flash_blue])
    scan_celebrate.add_children([flash_green, scan_pause])
    return root


def tutorial_main():
    """
    Entry point for the demo script.
    """
    rclpy.init(args=None)
    root = tutorial_create_root()
    tree = py_trees_ros.trees.BehaviourTree(
        root=root,
        unicode_tree_debug=True
    )
    try:
        tree.setup(timeout=15)
    except py_trees_ros.exceptions.TimedOutError as e:
        console.logerror(console.red + "failed to setup the tree, aborting [{}]".format(str(e)) + console.reset)
        tree.shutdown()
        rclpy.try_shutdown()
        sys.exit(1)
    except KeyboardInterrupt:
        # not a warning, nor error, usually a user-initiated shutdown
        console.logerror("tree setup interrupted")
        tree.shutdown()
        rclpy.try_shutdown()
        sys.exit(1)

    tree.tick_tock(period_ms=1000.0)

    try:
        rclpy.spin(tree.node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        tree.shutdown()
        rclpy.try_shutdown()
