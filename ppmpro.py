#!/usr/bin/env python3

"""This tool allows a user to interact programmatically with their
PPM Pro timesheet.  It is designed to be called from cron on a
regular basis to keep hours updated."""

__author__ = "Greg Veldman <gv@purdue.edu>"

import sys
import urllib.request
import json
import codecs
import argparse
from datetime import date, datetime, timedelta
from pathlib import Path

# The organization name of your PPM Pro instance
org_name = "mycompany"


def make_req(url, cookie, data=None, method='GET', proxy=None):
    req = urllib.request.Request(url, data, method=method)
    req.add_header('Cookie', cookie)
    if (method == 'PUT'):
        req.add_header('Content-Type', 'application/json')
    if (proxy):
        req.set_proxy(proxy, 'http')

    try:
        resp = urllib.request.urlopen(req)
    except urllib.error.HTTPError as e:
        print("Unable to make request. Code {} returned: {}.".format(
            e.status, e.reason))
        sys.exit(1)

    return resp


def report(data, today):
    # Date header and totals list setup
    dates = [e.get('entryDate') for e in data.get('timesheet').get(
        'activities')[0].get('entries')]
    totals = [0.0 for i in range(len(dates))]
    print("{:<25}DATES:\t".format(
        '[' + data.get('timesheet').get('stateName', 'UNKNOWN') + ']'), end='')
    for d in dates:
        print("{:<6}".format(d.lstrip("{}-".format(str(today.year)))), end='')

    print()

    # Daily values for each activity
    for a in data.get('timesheet').get('activities'):
        print("{:<32}".format(a.get('projectName')), end='')
        for e in a.get('entries'):
            for d in dates:
                if (e.get('entryDate') == d):
                    hours = e.get('entryHours')
                    totals[dates.index(d)] += hours
                    print("{:<4.1f}  ".format(hours), end='')

        print()

    # Totals for each day
    print("\t\t\tTOTALS:\t", end='')
    for t in totals:
        print("{:<4.1f}  ".format(t), end='')

    print()


def get_hours(data):
    """This function is provided only as an example where one could
    hook into an external source to get one's hours for the day.
    The default implementation simply divides the target hours for
    each day evenly between all activities, which is probably not
    correct.  Implementation is left as an exercise to the reader..."""

    activities = len(data.get('timesheet').get('activities'))
    target = 8
    return [round(target / activities, 1) for a in range(activities)]


def build_upload(data, today, hours=None):
    # Build upload data and set hours for entries
    activities = data.get('timesheet').get('activities')
    external_hours = get_hours(data)
    current = 0
    upload = []
    for a in activities:
        ud = {}
        ud['entries'] = []
        ud['id'] = a.get('id')
        ud['projectId'] = a.get('projectId')
        ud['taskId'] = a.get('taskId')
        ud['role'] = a.get('role')
        ud['taskScheduleId'] = 0
        ud['remainingHours'] = 0
        ud['dynamicFields'] = {}
        ud['type'] = a.get('type')
        ud['isPinned'] = a.get('isPinned')
        ud['isBillable'] = a.get('isBillable')
        ud['isCapitalized'] = a.get('isCapitalized')
        ud['isEditable'] = a.get('isEditable')
        ud['state'] = a.get('state')
        for e in a.get('entries'):
            # Only update the hours for today
            if (e.get('entryDate') == today.isoformat()):
                e['entryHours'] = hours.split(',')[current] \
                    if hours and len(hours.split(',')) == len(activities) \
                    else external_hours[current]

            ud['entries'].append(e)

        upload.append(ud)
        current += 1

    return upload


def main():
    desc = "Programmatically interact with PPM Pro timesheets."
    base_url = "https://{}.ppmpro.com/api".format(org_name)
    reader = codecs.getreader('utf-8')
    today = date.today()
    timesheet = None

    # Setup cmdline arguments
    parser = argparse.ArgumentParser(
        description=desc, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument(
        '-f', '--file', default=str(Path.home()/'.ppmpro.session'),
        type=argparse.FileType('r'),
        help=("File to read in session cookie from."))
    parser.add_argument(
        '-r', '--report', default=False, action='store_true',
        help=("Generate a report of the current week's timesheet."))
    parser.add_argument(
        '-u', '--update', default=False, action='store_true',
        help=("Update timesheet values for today."))
    parser.add_argument(
        '-s', '--submit', default=False, action='store_true',
        help=("Submit current timesheet for approval."))
    parser.add_argument(
        '-a', '--approve', default=False, action='store_true',
        help=("Approve all pending timesheets."))
    parser.add_argument(
        '-p', '--proxy', default=None,
        help=("Use specified proxy server to make API requests.  Format "
              "is \"host:port\"."))
    parser.add_argument(
        '-D', '--date', default=None,
        help=("Override timesheet date we're operating on.  Format is "
              "\"YYYY-MM-DD\"."))
    parser.add_argument(
        '-H', '--hours', default=None,
        help=("Override externally generated hours with data.  Format is "
              "a comma-seperated list of hours for each project."))
    args = parser.parse_args()

    # Load the authentication cookie value.  File access handled by argparse.
    cookie = args.file.readline().strip()
    args.file.close()

    # See if we should operate on a different day
    if (args.date):
        try:
            today = datetime.strptime(args.date, '%Y-%m-%d').date()
        except ValueError:
            pass

    # GET request to find the id for this week's sheet
    resp = make_req('{}/timesheet/recent'.format(base_url), cookie,
                    proxy=args.proxy)
    data = json.load(reader(resp))
    # Look for the date of the most recent Monday, that's when sheets start
    start = (today - timedelta(days=today.weekday())).isoformat()
    for i in data.get('items'):
        if (i.get('startDate') == start):
            timesheet = i.get('id')

    if not (timesheet):
        print("Could not get id of current timesheet.")
        sys.exit(1)

    if (args.report) or (args.update):
        # GET request to find ids for activities and entries in current sheet
        resp = make_req('{}/timesheet/{}'.format(base_url, timesheet), cookie,
                        proxy=args.proxy)
        data = json.load(reader(resp))

    if (args.report):
        report(data, today)

    if (args.update):
        # PUT request to set hours for specific activities/entries
        make_req('{}/timesheet/{}/activities'.format(
                base_url, timesheet),
            cookie, method='PUT', proxy=args.proxy,
            data=json.dumps(build_upload(
                data, today, args.hours)).encode('utf-8'))

    if (args.submit):
        # PUT request to submit the timesheet for approval
        make_req('{}/timesheet/{}?submit=true'.format(
                base_url, timesheet),
            cookie, method='PUT', proxy=args.proxy,
            data=json.dumps({'note': ''}).encode('utf-8'))

    if (args.approve):
        # PUT request to approve all pending timesheets
        make_req('{}/timesheet/approveAllTimesheets?filterApproval=AsApprover'
                 .format(base_url),
                 cookie, method='PUT', proxy=args.proxy,
                 data=json.dumps({'note': ''}).encode('utf-8'))


if __name__ == '__main__':
    main()
