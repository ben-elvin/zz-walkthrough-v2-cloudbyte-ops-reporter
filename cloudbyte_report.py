#!/usr/bin/env python3
"""CloudByte Ops Reporter: summarise CloudByte's activity from the command line."""

import argparse
import csv
import logging
import re

LOG_LINE = r'(?P<date>\d+-\d+-\d+)T(?P<time>\d+:\d+:\d+) (?P<user>[a-z]+) (?P<action>[a-z]+) "(?P<path>[^"]+)" (?P<status>\d+)'


log = logging.getLogger("cloudbyte_report")


def get_user(record):
    return record["user"]


def get_hour(record):
    return record["time"][:2]


def get_action(record):
    return record["action"]


def get_path(record):
    return record["path"]


def by_count_then_name(pair):
    """Sort key: busiest first, ties broken A-to-Z by name."""
    count, name = pair          # "name" is whatever was ranked: a username or an hour
    return (-count, name)       # busiest first (negated count), ties A->Z by name


def count_and_rank(records, get_key):
    counts = {}
    for record in records:
        key = get_key(record)
        counts[key] = counts.get(key, 0) + 1
    pairs = [(count, key) for key, count in counts.items()]
    pairs.sort(key=by_count_then_name)
    return pairs


def main():
    parser = argparse.ArgumentParser(description="Summarise CloudByte's access log as a report.")
    parser.add_argument("log", nargs="?", default="cloudbyte_access.log", help="access log to read")
    parser.add_argument("--roster", default="users.csv", help="staff roster CSV to join")
    parser.add_argument("--user", help="user to show a per-user activity block for")
    parser.add_argument("-v", "--verbose", action="store_true", help="show INFO-level detail")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s: %(message)s",
    )

    records = []
    with open(args.log) as f:
        for lineno, line in enumerate(f, start=1):
            match = re.fullmatch(LOG_LINE, line.strip())
            if match is None:
                log.warning("skipping line %d: %r is not a log line", lineno, line.strip())
                continue
            records.append(match.groupdict())
    log.info("loaded %d records from %s", len(records), args.log)

    # Read the staff roster into a {username: department} lookup.
    with open(args.roster) as f:
        dept_of = {row["username"]: row["department"] for row in csv.DictReader(f)}

    first = records[0]
    last = records[-1]
    print("CloudByte Access Report")
    print(f"{len(records)} events from {first['date']} {first['time']} to {last['date']} {last['time']}")
    print()

    for record in records:
        print(f"{record['date']} {record['time']}  {record['user']} {record['action']}")

    print()
    user_pairs = count_and_rank(records, get_user)
    print("Most active users")
    for rank, (count, username) in enumerate(user_pairs, start=1):
        print(f"  {rank}. {username}: {count} events")

    print()
    hour_pairs = count_and_rank(records, get_hour)
    print("Busiest hours")
    for count, hour in hour_pairs:
        print(f"  {hour}:00  {count} events")

    print()
    action_pairs = count_and_rank(records, get_action)
    print("Activity by type")
    for rank, (count, action) in enumerate(action_pairs, start=1):
        print(f"  {rank}. {action}: {count} events")

    print()
    logins = [record for record in records if get_action(record) == "login"]
    login_pairs = count_and_rank(logins, get_user)
    print("Most active logins")
    for rank, (count, username) in enumerate(login_pairs, start=1):
        print(f"  {rank}. {username}: {count} events")

    if args.user:
        print()
        person = args.user
        person_records = [record for record in records if get_user(record) == person]
        person_pairs = count_and_rank(person_records, get_action)
        print(f"Activity for {person}")
        for rank, (count, action) in enumerate(person_pairs, start=1):
            print(f"  {rank}. {action}: {count} events")
    else:
        log.info("no --user given; skipping the per-user report")

    print()
    dept_totals = {}
    for count, username in user_pairs:
        dept = dept_of[username]
        dept_totals[dept] = dept_totals.get(dept, 0) + count
    dept_pairs = [(total, dept) for dept, total in dept_totals.items()]
    dept_pairs.sort(key=by_count_then_name)
    print("Activity by department")
    for rank, (total, dept) in enumerate(dept_pairs, start=1):
        print(f"  {rank}. {dept}: {total} events")

    print()
    path_pairs = count_and_rank(records, get_path)
    print("Most requested paths")
    for rank, (count, path) in enumerate(path_pairs, start=1):
        print(f"  {rank}. {path}: {count} requests")

    failures = [record for record in records if record["status"] != "200"]

    print()
    fail_totals = {}
    for count, username in count_and_rank(failures, get_user):
        dept = dept_of[username]
        fail_totals[dept] = fail_totals.get(dept, 0) + count
    fail_dept_pairs = [(total, dept) for dept, total in fail_totals.items()]
    fail_dept_pairs.sort(key=by_count_then_name)
    print("Failed requests by department")
    for rank, (total, dept) in enumerate(fail_dept_pairs, start=1):
        print(f"  {rank}. {dept}: {total} failed")

    print()
    fail_path_pairs = count_and_rank(failures, get_path)
    print("Failed requests by path")
    for rank, (count, path) in enumerate(fail_path_pairs, start=1):
        print(f"  {rank}. {path}: {count} failed")


if __name__ == "__main__":
    main()
