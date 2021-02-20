#!/usr/bin/env python3

import argparse
import datetime

import boto3

AWS_ACCESS_KEY_ID = "***REMOVED***"
AWS_SECRET_ACCESS_KEY = "***REMOVED***"
QUESTION_URL = "***REMOVED***"
EXTERNAL_QUESTION_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<ExternalQuestion xmlns="http://mechanicalturk.amazonaws.com/AWSMechanicalTurkDataSchemas/2006-07-14/ExternalQuestion.xsd">
    <ExternalURL>{}</ExternalURL>
    <FrameHeight>0</FrameHeight>
</ExternalQuestion>
"""


def main():
    parser = argparse.ArgumentParser("Submit HIT to Amazon's MTurk API")
    parser.add_argument("-p", "--prod", action="store_true", help="Submit to production instead of sandbox")
    parser.add_argument("-r", "--reward", help="Reward in dollars (default: 0.75)", type=float, required=True)
    parser.add_argument("-H", "--hours", help="Lifetime of assignment", type=float, required=True)
    parser.add_argument("-n", "--num", help="The number of assignments", required=True, type=int)
    parser.add_argument("-d", "--debug", action="store_true", help="Set debug flag to on in hit HTML")

    args = parser.parse_args()

    url = QUESTION_URL
    if args.debug:
        url += "?debug=1"

    question = EXTERNAL_QUESTION_XML.format(url)

    client = boto3.client(
        "mturk",
        region_name="us-east-1",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        **({} if args.prod else {"endpoint_url": "https://mturk-requester-sandbox.us-east-1.amazonaws.com"}),
    )

    lifetime = round(args.hours * 60 * 60)

    response = client.create_hit(
        MaxAssignments=args.num,
        AutoApprovalDelayInSeconds=3 * 24 * 60 * 60,  # 3 days
        LifetimeInSeconds=lifetime + 15 * 60,  # Add 15 minutes afterwards
        AssignmentDurationInSeconds=lifetime,
        Reward=f"{args.reward:.02f}",
        Title=f"Test Title @ {datetime.datetime.now().replace(microsecond=0)}",
        Keywords="keyword1, keyword2, keyword3",
        Description="test description",
        Question=question,
    )

    # import ipdb

    # ipdb.set_trace()


if __name__ == "__main__":
    main()
