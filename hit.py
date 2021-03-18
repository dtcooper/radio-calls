#!/usr/bin/env python3

import argparse
from datetime import datetime, timedelta
import html
import json
import pprint
import sys
import traceback
from urllib.parse import urlencode

import boto3
from botocore.exceptions import ClientError
from dotenv import dotenv_values

env = dotenv_values()
AWS_ACCESS_KEY_ID = env["AWS_ACCESS_KEY_ID"]
AWS_SECRET_ACCESS_KEY = env["AWS_SECRET_ACCESS_KEY"]
EXTERNAL_QUESTION_URL = env["MTURK_QUESTION_URL"]

EXTERNAL_QUESTION_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<ExternalQuestion
        xmlns="http://mechanicalturk.amazonaws.com/AWSMechanicalTurkDataSchemas/2006-07-14/ExternalQuestion.xsd">
    <ExternalURL>{}</ExternalURL>
    <FrameHeight>0</FrameHeight>
</ExternalQuestion>
"""
HIT_TITLE = "Call a Live Radio Show"
## TODO change for --no-topic
HIT_DESCRIPTION = "Call a live radio show in your browser and have a funny conversation with the hosts."
HIT_KEYWORDS = "telephone, call, talking, radio show, radio, funny, joke, swimming, poop, inappropriate"
SHOW_CHOICES = ("poolabs", "tigwit")
TOPICS = ("pool", "poop")

# Qualification IDs from mturk Api docs
MASTERS_QUAL_ID_SANDBOX = "2ARFPLSP75KLA8M8DH1HTEQVJT3SY6"
MASTERS_QUAL_ID_PROD = "2F1QJWKUDD8XADTFD2Q0G6UTO95ALH"
PERCENT_APPROVED_QUAL_ID = "000000000000000000L0"
NUM_APPROVED_QUAL_ID = "00000000000000000040"
COUNTRY_QUAL_ID = "00000000000000000071"


def get_client(sandbox=True):
    return boto3.client(
        "mturk",
        region_name="us-east-1",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        **({"endpoint_url": "https://mturk-requester-sandbox.us-east-1.amazonaws.com"} if sandbox else {}),
    )


class FullHelpParser(argparse.ArgumentParser):
    def error(self, message):
        self.print_help()
        sys.stderr.write(f"\nerror: {message}\n")
        sys.exit(2)


def parse_args(argv=None):
    parser = FullHelpParser("Submit HIT to Amazon's MTurk API")
    parser.add_argument('-v', '--verbose', action='store_true', help="Print verbose output from Amazon's API")
    environment_group = parser.add_mutually_exclusive_group(required=True)
    environment_group.add_argument("-p", "--prod", action="store_true", help="Submit to production environment")
    environment_group.add_argument("-t", "-S", "--sandbox", action="store_true", help="Submit to sandbox environment")
    parser.add_argument("--dry-run", action="store_true", help="Dry run. Don't actually submit assignment.")
    parser.add_argument(
        "-r", "--reward", metavar="int", help="Reward in dollars (default: 0.75)", type=float, required=True
    )
    duration_group = parser.add_mutually_exclusive_group(required=True)
    duration_group.add_argument(
        "-H", "--hours", metavar="int", help="Duration of assignment (hours)", type=float, default=0
    )
    duration_group.add_argument(
        "-M", "--minutes", metavar="int", help="Duration of assignment (minutes)", type=float, default=0
    )
    parser.add_argument(
        "--buffer-minutes", metavar="int", type=int, default=15, help="Extra lifetime mins (default: 15)"
    )
    parser.add_argument("-n", "--num", metavar="int", help="The number of assignments", type=int, required=True)
    parser.add_argument("-s", "--show", choices=SHOW_CHOICES, help="Show to choose", required=True)
    topic = parser.add_mutually_exclusive_group()
    topic.add_argument("-T", "--topic", choices=TOPICS, help="Force a topic")
    topic.add_argument("--no-topic", action="store_true", help="Hide topic choosing UI")
    parser.add_argument(
        "-A",
        "--annotation",
        metavar="str",
        help="Prepend text to requester annotation (for organization purposes)",
    )
    parser.add_argument("--ignore-balance-check", action="store_true", help="Ignore account balance check")
    parser.add_argument("-y", "--yes", action="store_true", help="Don't prompt for confirmation")
    parser.add_argument("--debug", action="store_true", help="Set debug flag to on in hit HTML")

    qualifications = parser.add_argument_group("worker qualifications")
    qualifications.add_argument("-m", "--masters", action="store_true", help="Masters")
    qualifications.add_argument("-a", "--approval", metavar="int", type=int, help="Greater than N approval percentage")
    qualifications.add_argument(
        "-N", "--num-prev", metavar="int", type=int, help="Greather than N assignments previously approved"
    )
    qualifications.add_argument(
        "-c",
        "--country",
        dest="countries",
        metavar="XX",
        action="append",
        help="Limit to country code, can used more than once (ENG for all english speaking)",
    )

    return parser.parse_args(args=argv)


def main(argv=None):
    args = parse_args(argv=argv)

    duration = round(args.hours * 60 * 60) + round(args.minutes * 60)

    fees = [(0.2, "base")]
    if args.num >= 10:
        fees.append((0.2, "10+ assignments"))
    if args.masters:
        fees.append((0.05, "masters"))

    fee_total = sum(fee for fee, desc in fees)
    unit_fees = fee_total * args.reward
    unit_cost = args.reward * (fee_total + 1)
    total_cost = unit_cost * args.num

    client = get_client(sandbox=args.sandbox)
    balance = float(client.get_account_balance()["AvailableBalance"])

    print(f" Environment: {('sandbox' if args.sandbox else 'production')}")
    print(f"Acct Balance: ${balance:.02f} (${balance - total_cost:.02f} after assignment posted)")
    print(f"    Duration: {timedelta(seconds=duration)} (+{timedelta(minutes=args.buffer_minutes)} buffer)")
    print(
        f"   Unit Cost: ${args.reward:.02f} reward + ${unit_fees:.02f} fees = ${unit_cost:.02f} each"
        f" ({int(fee_total * 100)}% fee = {', '.join(f'{int(fee * 100)}% {desc}' for fee, desc in fees)})"
    )
    print(f"  Total Cost: {args.num} assignments @ ${unit_cost:.02f} each = ${total_cost:.02f} total")

    if total_cost > balance and not args.ignore_balance_check:
        print(
            f"\nInsufficient funds! ${balance:.02f} balance, ${total_cost:.02f} required. Add"
            f" ${total_cost - balance:.02f} to your account. Exiting."
        )
        sys.exit(1)

    qualifications = []
    qualifications_pretty = []
    if args.masters:
        qualifications_pretty.append("Masters")
        qualifications.append(
            {
                "QualificationTypeId": MASTERS_QUAL_ID_PROD if args.prod else MASTERS_QUAL_ID_SANDBOX,
                "Comparator": "Exists",
            }
        )
    if args.approval:
        qualifications_pretty.append(f"{args.approval}% Approval Rate")
        qualifications.append(
            {
                "QualificationTypeId": PERCENT_APPROVED_QUAL_ID,
                "Comparator": "GreaterThanOrEqualTo",
                "IntegerValues": [args.approval],
            }
        )
    if args.num_prev:
        qualifications_pretty.append(f"{args.num_prev} or More Assignments Previously Approved")
        qualifications.append(
            {
                "QualificationTypeId": NUM_APPROVED_QUAL_ID,
                "Comparator": "GreaterThanOrEqualTo",
                "IntegerValues": [args.num_prev],
            }
        )
    if args.countries:
        if len(args.countries) == 1 and args.countries[0].upper() == 'ENG':
            countries = ['US', 'CA', 'GB', 'AU', 'IE', 'NZ']
        else:
            countries = [country.upper() for country in args.countries]
        qualifications_pretty.append(f"Limited to Countries: {', '.join(countries)}")
        qualifications.append(
            {
                "QualificationTypeId": COUNTRY_QUAL_ID,
                "Comparator": "In",
                "LocaleValues": [{"Country": country} for country in countries],
            }
        )

    if qualifications_pretty:
        print("Worker Qualifications...")
        for qualification_pretty in qualifications_pretty:
            print(f" + {qualification_pretty}")

    if args.prod and not args.yes:
        yesno = input(
            f"{'[Dry run] ' if args.dry_run else ''}Are you SURE you want to use prod @ ${total_cost:.02f} total cost"
            " (y/N)? "
        )
        if not yesno.strip().lower().startswith("y"):
            print("Exiting.")
            sys.exit(0)

    external_question_url_kwargs = {"show": args.show}
    if args.debug:
        external_question_url_kwargs["debug"] = "1"
    if args.topic:
        external_question_url_kwargs["force_topic"] = args.topic
    elif args.no_topic:
        external_question_url_kwargs["force_topic"] = "none"

    external_question_url = f"{EXTERNAL_QUESTION_URL}?{urlencode(external_question_url_kwargs)}"
    question = EXTERNAL_QUESTION_XML.format(html.escape(external_question_url))

    requester_annotation = f"Radio Calls ({args.show}) @ {datetime.now().replace(microsecond=0)}"
    if args.annotation:
        requester_annotation = f"{args.annotation} - {requester_annotation}"

    print()

    create_hit_kwargs = {
        "AssignmentDurationInSeconds": duration,
        "AutoApprovalDelayInSeconds": 3 * 24 * 60 * 60,  # 3 days
        "LifetimeInSeconds": duration + args.buffer_minutes * 60,
        "MaxAssignments": args.num,
        "Question": question,
        "Reward": f"{args.reward:.02f}",
        "Title": HIT_TITLE,
        "Description": HIT_DESCRIPTION,
        "Keywords": HIT_KEYWORDS,
        "RequesterAnnotation": requester_annotation,
        **({"QualificationRequirements": qualifications} if qualifications else {}),
    }

    if args.dry_run:
        print(f"Would create HIT in {'sandbox' if args.sandbox else 'prod'}: ", end="")
        print(json.dumps(create_hit_kwargs, indent=2, sort_keys=True))
    else:
        try:
            response = client.create_hit(**create_hit_kwargs)
        except ClientError:
            print("Error creating HIT!")
            traceback.print_exc()
        else:
            if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
                if args.verbose:
                    pprint.pprint(response)
                else:
                    print("HIT successfully created.")
            else:
                print("Response code not 200!")
                pprint.pprint(response)


if __name__ == "__main__":
    main()
