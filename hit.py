#!/usr/bin/env python3

import argparse
from datetime import datetime, timedelta
import html
import pprint
import sys
from urllib.parse import urlencode

import boto3
from dotenv import dotenv_values

env = dotenv_values()
AWS_ACCESS_KEY_ID = env["AWS_ACCESS_KEY_ID"]
AWS_SECRET_ACCESS_KEY = env["AWS_SECRET_ACCESS_KEY"]
MTURK_QUESTION_URL = env["MTURK_QUESTION_URL"]

EXTERNAL_QUESTION_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<ExternalQuestion
        xmlns="http://mechanicalturk.amazonaws.com/AWSMechanicalTurkDataSchemas/2006-07-14/ExternalQuestion.xsd">
    <ExternalURL>{}</ExternalURL>
    <FrameHeight>0</FrameHeight>
</ExternalQuestion>
"""
HIT_TITLE = "Call a Live Radio Show & Talk About Your Poop or Swimming"
HIT_DESCRIPTION = (
    "Call a live radio show in your browser and have a funny conversation with the hosts. You will talk about either"
    " your most recent poop or your favourite way to swim - the topic is assigned randomly at the start of the"
    " assignment."
)
HIT_KEYWORDS = "telephone, call, talking, radio show, radio, funny, joke, swimming, poop, inappropriate"
SHOW_CHOICES = ("poolabs", "tigwit")
TOPICS = ("pool", "poop")


class FullHelpParser(argparse.ArgumentParser):
    def error(self, message):
        self.print_help()
        sys.stderr.write(f"\nerror: {message}\n")
        sys.exit(2)


def main():
    parser = FullHelpParser("Submit HIT to Amazon's MTurk API")
    environment_group = parser.add_mutually_exclusive_group(required=True)
    environment_group.add_argument("-p", "--prod", action="store_true", help="Submit to production environment")
    environment_group.add_argument("-t", "-S", "--sandbox", action="store_true", help="Submit to sandbox environment")
    parser.add_argument("-r", "--reward", help="Reward in dollars (default: 0.75)", type=float, required=True)
    duration_group = parser.add_mutually_exclusive_group(required=True)
    duration_group.add_argument("-H", "--hours", help="Duration of assignment (hours)", type=float, default=0)
    duration_group.add_argument("-m", "--minutes", help="Duration of assignment (minutes)", type=float, default=0)
    parser.add_argument("--buffer-minutes", type=int, default=15, help="Additional lifetime mins (default: 15)")
    parser.add_argument("-n", "--num", help="The number of assignments", type=int, required=True)
    parser.add_argument("-d", "--debug", action="store_true", help="Set debug flag to on in hit HTML")
    parser.add_argument("-s", "--show", choices=SHOW_CHOICES, help="Show to choose", required=True)
    parser.add_argument("-T", "--topic", choices=TOPICS, help="Force a topic")

    args = parser.parse_args()

    duration = round(args.hours * 60 * 60) + round(args.minutes * 60)

    fee = 0.2 if args.num < 10 else 0.4
    print(f"Environment: {('sandbox' if args.sandbox else 'production')}")

    if args.prod:
        print(f"   Duration: {timedelta(seconds=duration)} (+{timedelta(minutes=args.buffer_minutes)} buffer)")
        print(
            f"  Unit Cost: ${args.reward:.02f} reward + ${args.reward * fee:.02f} w/ {int(fee * 100)}% fee ="
            f" ${args.reward * (fee + 1):.02f} each{' (incl. num +10 penalty of 20%)' if args.num >= 10 else ''}",
        )
        print(
            f" Total Cost: {args.num} assignments @ ${args.reward * (fee + 1):.02f} each ="
            f" ${args.num * args.reward * (fee + 1):.02f} total"
        )
        if not input("\nAre you sure you want to use production (y/N)? ").strip().lower().startswith("y"):
            print("Exiting.")
            sys.exit(0)

    url_kwargs = {"show": args.show}
    if args.debug:
        url_kwargs["debug"] = "1"
    if args.topic:
        url_kwargs["force_topic"] = args.topic

    url = f"{MTURK_QUESTION_URL}?{urlencode(url_kwargs)}"
    question = EXTERNAL_QUESTION_XML.format(html.escape(url))

    client = boto3.client(
        "mturk",
        region_name="us-east-1",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        **({"endpoint_url": "https://mturk-requester-sandbox.us-east-1.amazonaws.com"} if args.sandbox else {}),
    )

    response = client.create_hit(
        AssignmentDurationInSeconds=duration,
        AutoApprovalDelayInSeconds=3 * 24 * 60 * 60,  # 3 days
        LifetimeInSeconds=duration + args.buffer_minutes * 60,
        MaxAssignments=args.num,
        Question=question,
        Reward=f"{args.reward:.02f}",
        Title=HIT_TITLE,
        Description=HIT_DESCRIPTION,
        Keywords=HIT_KEYWORDS,
        RequesterAnnotation=f"Radio Calls ({args.show}) @ {datetime.now().replace(microsecond=0)}",
    )

    pprint.pprint(response)


if __name__ == "__main__":
    main()
