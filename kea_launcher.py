import argparse
import unittest

def _set_driver_parser(subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]"):
    parser = subparsers.add_parser("driver", help="Driver Settings")
    parser.add_argument(
        "-s",
        "--serial",
        dest="serial",
        type=str,
        help="The serial of your device. Can be found with `adb devices`",
    )

    parser.add_argument(
        "-p",
        "--packages",
        dest="package_names",
        nargs="+",
        type=str,
        required=True,
        help="The target package names com.example.app",
    )

    parser.add_argument(
        "--agent",
        dest="agent",
        type=str,
        default="u2",
        choices=["native", "u2"],
        help="Running native fastbot or u2-fastbot. (Only u2-fastbot support PBT)",
    )

    parser.add_argument(
        "--running-minutes",
        dest="running_minutes",
        type=int,
        required=False,
        help="Time to run fastbot",
    )

    parser.add_argument(
        "--max-step",
        dest="max_step",
        type=int,
        required=False,
        help="maxium monkey events count to send",
    )

    parser.add_argument(
        "--throttle",
        dest="throttle_ms",
        type=int,
        required=False,
        help="The pause between two monkey event.",
    )
    
    parser.add_argument(
        "--driver-name",
        dest="driver_name",
        type=str,
        required=False,
        help="The name of driver in script.",
    )

    parser.add_argument(
        "extra",
        nargs=argparse.REMAINDER,
        help="Extra args for unittest <args>",
    )


def unittest_info_logger(args):
    if args.agent == "native":
        print("[Warning] Property not availble in native agent.", flush=True)
    if args.extra and args.extra[0] == "unittest":
        print("Captured unittest args:", args.extra, flush=True)


def driver_info_logger(args):
    print("[INFO] Driver Settings:", flush=True)
    if args.serial:
        print("  serial:", args.serial, flush=True)
    if args.package_names:
        print("  package_names:", args.package_names, flush=True)
    if args.agent:
        print("  agent:", args.agent, flush=True)
    if args.running_minutes:
        print("  running_minutes:", args.running_minutes, flush=True)
    if args.throttle_ms:
        print("  throttle_ms:", args.throttle_ms, flush=True)


def parse_args():
    parser = argparse.ArgumentParser(description="Kea4Fastbot")
    subparsers = parser.add_subparsers(dest="command", required=True)

    _set_driver_parser(subparsers)

    args = parser.parse_args()
    driver_info_logger(args)
    unittest_info_logger(args)
    return args


if __name__ == "__main__":
    args = parse_args()

    import sys
    argv = sys.argv

    from kea2 import KeaTestRunner, Options
    from kea2.u2Driver import U2Driver
    options = Options(
        agent=args.agent,
        driverName=args.driver_name,
        Driver=U2Driver,
        packageNames=args.package_names,
        serial=args.serial,
        running_mins=args.running_minutes if args.running_minutes else 10,
        maxStep=args.max_step if args.max_step else 500,
        throttle=args.throttle_ms if args.throttle_ms else 200
    )

    KeaTestRunner.setOptions(options)
    unittest_args = []
    if args.extra and args.extra[0] == "unittest":
        unittest_args = args.extra[1:]
    sys.argv = ["python3 -m unittest"] + unittest_args

    unittest.main(module=None, testRunner=KeaTestRunner)
