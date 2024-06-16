#!/usr/bin/env python3

import os

from distutils import log
from setuptools import find_packages, setup
from setuptools.command.develop import develop
from setuptools.command.install import install

package_name = 'hugr'


# This is somewhat dodgy as it will escape any override from, e.g. the command
# line or a setup.cfg configuration. It does however, get us around the problem
# of setup.cfg influencing requirements install on rtd installs
#
# TODO: should be a way of detecting whether scripts_dir has been influenced
# from outside
def redirect_install_dir(command_subclass):

    original_run = command_subclass.run

    def modified_run(self):
        try:
            old_script_dir = self.script_dir  # develop
        except AttributeError:
            old_script_dir = self.install_scripts  # install
        # TODO: A more intelligent way of stitching this together...
        # Warning: script_dir is typically a 'bin' path alongside the
        # lib path, if ever that is somewhere wildly different, this
        # will break.
        # Note: Consider making use of self.prefix, but in some cases
        # that is mislading, e.g. points to /usr when actually
        # everything goes to /usr/local
        new_script_dir = os.path.abspath(
            os.path.join(
                old_script_dir, os.pardir, 'lib', package_name
            )
        )
        log.info("redirecting scripts")
        log.info("  from: {}".format(old_script_dir))
        log.info("    to: {}".format(new_script_dir))
        if hasattr(self, "script_dir"):
            self.script_dir = new_script_dir  # develop
        else:
            self.install_scripts = new_script_dir  # install
        original_run(self)

    command_subclass.run = modified_run
    return command_subclass


@redirect_install_dir
class OverrideDevelop(develop):
    pass


@redirect_install_dir
class OverrideInstall(install):
    pass


def gather_launch_files():
    data_files = []
    for root, unused_subdirs, files in os.walk('launch'):
        destination = os.path.join('share', package_name, root)
        launch_files = []
        for file in files:
            pathname = os.path.join(root, file)
            launch_files.append(pathname)
        data_files.append((destination, launch_files))
    return data_files


setup(
    cmdclass={
        'develop': OverrideDevelop,
        'install': OverrideInstall
    },
    name=package_name,
    # also update package.xml (version and website url), version.py and conf.py
    version='2.1.0',
    packages=find_packages(exclude=['tests*', 'docs*', 'launch*']),
    data_files=[
        ('share/' + package_name, ['package.xml']),
        ('share/ament_index/resource_index/packages', [
            'resources/hugr']),
    ] + gather_launch_files(),
    package_data={'hugr': ['mock/gui/*']},
    install_requires=[],  # it's all lies (c.f. package.xml, but no use case for this yet)
    extras_require={},
    author='Kelleher Guerin',
    maintainer='Kelleher Guerin <kelleherguerin@gmail.com>',
    url='',
    keywords=['ROS', 'ROS2', 'behaviour-trees'],
    zip_safe=True,
    classifiers=[
        'Programming Language :: Python',
    ],
    description=(
        "Robot behavior control."
    ),
    long_description=(
        "Robot behavior control."
    ),
    license='Proprietary',
    # test_suite="tests"
    # tests_require=['nose', 'pytest', 'flake8', 'yanc', 'nose-htmloutput']
    entry_points={
        'console_scripts': [
            # Mocks
            'mock-battery = hugr.mock.battery:main',
            'mock-dashboard = hugr.mock.dashboard:main',
            'mock-docking-controller = hugr.mock.dock:main',
            'mock-led-strip = hugr.mock.led_strip:main',
            'mock-move-base = hugr.mock.move_base:main',
            'mock-rotation-controller = hugr.mock.rotate:main',
            'mock-safety-sensors = hugr.mock.safety_sensors:main',
            # Mock Tests
            'mock-dock-client = hugr.mock.actions:dock_client',
            'mock-move-base-client = hugr.mock.actions:move_base_client',
            'mock-rotate-client = hugr.mock.actions:rotate_client',
            # Tutorial Nodes
            'tree-data-gathering = hugr.one_data_gathering:tutorial_main',
            'tree-battery-check = hugr.two_battery_check:tutorial_main',
            'tree-action-clients = hugr.five_action_clients:tutorial_main',
            'tree-context-switching = hugr.six_context_switching:tutorial_main',
            'tree-docking-cancelling-failing = hugr.seven_docking_cancelling_failing:tutorial_main',
            'tree-dynamic-application-loading = hugr.eight_dynamic_application_loading:tutorial_main',
        ],
    },
)
