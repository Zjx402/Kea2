# coding: utf-8
# cli.py

from __future__ import absolute_import, print_function

from .kea_launcher import run
import argparse
import json
import logging
import sys

import os
from pathlib import Path


logger = logging.getLogger(__name__)

def enable_pretty_logging(level=logging.DEBUG):
    if not logger.handlers:
        # Configure handler
        handler = logging.StreamHandler()
        formatter = logging.Formatter('[%(levelname)1s][%(asctime)s %(module)s:%(lineno)d pid:%(process)d] %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    logger.setLevel(level)

enable_pretty_logging()

def cmd_init(args):
    cwd = Path(os.getcwd())
    if os.path.isdir(cwd / "configs"):
        logger.warning("Kea2 project already initialized")
        return

    import shutil
    def copy_configs():
        src = Path(__file__).parent / "assets" / "fastbot_configs"
        dst = cwd / "config"
        shutil.copytree(src, dst)

    def copy_samples():
        root = Path(__file__).parent.parent
        files = {
            root / "quickstart.py": "quickstart.py",
            root / "quickstart2.py": "quickstart2.py",
            root / "omninotes.apk": "omninotes.apk"
        }

        for src, dst in files.items():
            shutil.copyfile(src, cwd / dst)

    copy_configs()
    copy_samples()
    logger.info("Kea2 project initialized.")


def cmd_load_configs(args):
    pass


def cmd_run(args):
    argv = [__file__]
    argv.extend(args.args)
    run(argv)


def cmd_install(args):
    pass


def cmd_uninstall(args):
    pass


def cmd_start(args):
    pass


def cmd_stop(args):
    pass


def cmd_current(args):
    pass


def cmd_doctor(args):
    pass


# def cmd_version(args):
#     print(__version__)


_commands = [
    # dict(action=cmd_version, command="version", help="show version"),
    dict(
        action=cmd_init,
        command="init",
        help="init the Kea2 project in current directory",
    ),
    dict(
        action=cmd_run,
        command="run",
        help="run kea2",
        flags=[
            dict(args=["args"], nargs=argparse.REMAINDER, help="args for kea2 run"),
        ],
    ),
    # dict(
    #     action=cmd_install,
    #     command="",
    #     help="install packages",
    #     flags=[
    #         dict(args=["url"], help="package url"),
    #     ],
    # ),
    # dict(
    #     action=cmd_uninstall,
    #     command="uninstall",
    #     help="uninstall packages",
    #     flags=[
    #         dict(args=["--all"], action="store_true", help="uninstall all packages"),
    #         dict(args=["package_name"], nargs="*", help="package name"),
    #     ],
    # ),
    # dict(
    #     action=cmd_start,
    #     command="start",
    #     help="start application",
    #     flags=[dict(args=["package_name"], type=str, nargs=None, help="package name")],
    # ),
    # dict(
    #     action=cmd_stop,
    #     command="stop",
    #     help="stop application",
    #     flags=[
    #         dict(args=["--all"], action="store_true", help="stop all"),
    #         dict(args=["package_name"], nargs="*", help="package name"),
    #     ],
    # ),
    # dict(action=cmd_current, command="current", help="show current application"),
    # dict(action=cmd_doctor, command="doctor", help="detect connect problem"),
]


def main():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("-d", "--debug", action="store_true",
                        help="show log")
    parser.add_argument('-s', '--serial', type=str,
                        help='device serial number')

    subparser = parser.add_subparsers(dest='subparser')

    actions = {}
    for c in _commands:
        cmd_name = c['command']
        actions[cmd_name] = c['action']
        sp = subparser.add_parser(
            cmd_name,
            help=c.get('help'),
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
        for f in c.get('flags', []):
            args = f.get('args')
            if not args:
                args = ['-'*min(2, len(n)) + n for n in f['name']]
            kwargs = f.copy()
            kwargs.pop('name', None)
            kwargs.pop('args', None)
            sp.add_argument(*args, **kwargs)

    args = parser.parse_args()
    enable_pretty_logging()

    if args.debug:
        logger.debug("args: %s", args)

    if args.subparser:
        actions[args.subparser](args)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
