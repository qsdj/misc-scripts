#!/usr/bin/env python
"""
pagerduty_list_incidents
========================

Python script using the PagerDuty v2 API to list and filter incidents.

If you have ideas for improvements, or want the latest version, it's at:
<https://github.com/jantman/misc-scripts/blob/master/pagerduty_list_incidents.py>

Requirements
------------

``pip install git+https://github.com/PagerDuty/pagerduty-api-python-client.git@99e3f7e665f5e43bdd4088cdf478b2cc4faaef5f``

License
-------

Copyright 2016 Jason Antman <jason@jasonantman.com> <http://www.jasonantman.com>
Free for any use provided that patches are submitted back to me.

CHANGELOG
---------

2016-10-18 Jason Antman <jason@jasonantman.com>:
  - initial version of script
"""

import sys
import argparse
import logging
import pypd
import re
import os
import json

FORMAT = "[%(asctime)s %(levelname)s] %(message)s"
logging.basicConfig(level=logging.WARNING, format=FORMAT)
logger = logging.getLogger()

# suppress logging from pypd
pypd_log = logging.getLogger("pypd")
pypd_log.setLevel(logging.WARNING)
pypd_log.propagate = True

# suppress logging from requests, used internally by pypd
requests_log = logging.getLogger("requests")
requests_log.setLevel(logging.WARNING)
requests_log.propagate = True


class PagerDutyListIncidents(object):
    """main class"""

    def __init__(self, api_key, substring=None, detail_re=None, output_type='list'):
        """ init method, run at class creation """
        self.api_key = api_key
        pypd.api_key = api_key
        self.substring = substring
        self.detail_re = detail_re
        self.output_type = output_type

    def run(self, since=None, until=None, service_ids=[]):
        """ do stuff here """
        kwargs = {'fetch_all': True}
        if since is not None:
            kwargs['since'] = since
        if until is not None:
            kwargs['until'] = until
        if len(service_ids) > 0:
            kwargs['service_ids'] = service_ids
        logger.debug('Calling pypd.Incident.find(%s)', kwargs)
        incidents = pypd.Incident.find(**kwargs)
        logger.debug('Found %d incidents', len(incidents))
        filtered = self.filter_incidents(incidents)
        logger.debug('Filtered down to %d incidents', len(filtered))
        self.output(filtered)

    def filter_incidents(self, incidents):
        """filter the incidents"""
        final = []
        if self.detail_re is not None and self.substring is not None:
            logger.debug('filtering on RE and substring')
            m_re = re.compile(self.detail_re)
            for i in incidents:
                if m_re.match(i['summary']) and self.substring in i['summary']:
                    final.append(i)
            return final
        if self.detail_re is not None:
            logger.debug('filtering on RE')
            m_re = re.compile(self.detail_re)
            for i in incidents:
                if m_re.match(i['summary']):
                    final.append(i)
            return final
        if self.substring is not None:
            logger.debug('filtering on substring')
            for i in incidents:
                if self.substring in i['summary']:
                    final.append(i)
            return final
        logger.debug('No filters in use.')
        return incidents

    def output(self, incidents):
        """output the incidents"""
        if self.output_type == 'json':
            self.output_json(incidents)
        else:
            self.output_csv(incidents)

    def output_csv(self, incidents):
        print('"Created At","ID","Incident Number","Description","Urgency","Status","HTML URL","Service ID","Service Summary","Escalation Policy ID","Escalation Policy Summary"')
        for i in incidents:
            print('"%s","%s","%d","%s","%s","%s","%s","%s","%s","%s","%s"' % (
                i['created_at'],
                i['id'],
                i['incident_number'],
                i['description'],
                i['urgency'],
                i['status'],
                i['html_url'],
                i['service']['id'],
                i['service']['summary'],
                i['escalation_policy']['id'],
                i['escalation_policy']['summary']
            ))

    def output_json(self, incidents):
        res = []
        for i in incidents:
            res.append(vars(i))
        print(json.dumps(res))


def parse_args(argv):
    """
    parse arguments/options
    """
    p = argparse.ArgumentParser(description='List and filter PagerDuty Incidents.')
    p.add_argument('-a', '--api-key', dest='api_key', action='store', type=str,
                   help='PagerDuty API key; if not specified, will be read '
                   'from PAGERDUTY_API_KEY environment variable', default=None)
    p.add_argument('-s', '--since', dest='since', action='store', type=str,
                   default=None, help='filter incidents since this time; '
                   'string in the form YYYY-MM-DDTHH:MM:SSZ')
    p.add_argument('-u', '--until', dest='until', action='store', type=str,
                   default=None, help='filter incidents until this time; '
                   'string in the form YYYY-MM-DDTHH:MM:SSZ')
    p.add_argument('-S', '--service-id', dest='service_ids', action='append',
                   default=[], help='one or more PagerDuty Service IDs to '
                   'limit search to')
    p.add_argument('--substring', dest='substring', action='store', type=str,
                   default=None, help='limit results to incident details '
                   'containing this string')
    p.add_argument('-r', '--re', dest='detail_re', action='store', type=str,
                   default=None, help='limit results to incident details '
                   'matching this regex')
    p.add_argument('-v', '--verbose', dest='verbose', action='count', default=0,
                   help='verbose output. specify twice for debug-level output.')
    out_types = ['csv', 'json']
    p.add_argument('-o', '--output-type', dest='output_type', action='store',
                   type=str, default='csv', choices=out_types,
                   help='output type - one of: %s' % out_types)
    args = p.parse_args(argv)
    if args.api_key is None:
        if 'PAGERDUTY_API_KEY' not in os.environ:
            raise Exception("Please either set PAGERDUTY_API_KEY environment "
                            "variable or specify -a/--api-key option.")
        args.api_key = os.environ['PAGERDUTY_API_KEY']
    return args

def set_log_info():
    """set logger level to INFO"""
    set_log_level_format(logging.INFO,
                         '%(asctime)s %(levelname)s:%(name)s:%(message)s')


def set_log_debug():
    """set logger level to DEBUG, and debug-level output format"""
    set_log_level_format(
        logging.DEBUG,
        "%(asctime)s [%(levelname)s %(filename)s:%(lineno)s - "
        "%(name)s.%(funcName)s() ] %(message)s"
    )


def set_log_level_format(level, format):
    """
    Set logger level and format.

    :param level: logging level; see the :py:mod:`logging` constants.
    :type level: int
    :param format: logging formatter format string
    :type format: str
    """
    formatter = logging.Formatter(fmt=format)
    logger.handlers[0].setFormatter(formatter)
    logger.setLevel(level)

if __name__ == "__main__":
    args = parse_args(sys.argv[1:])

    # set logging level
    if args.verbose > 1:
        set_log_debug()
    elif args.verbose == 1:
        set_log_info()

    script = PagerDutyListIncidents(
        api_key=args.api_key,
        substring=args.substring,
        detail_re=args.detail_re,
        output_type=args.output_type
    )
    script.run(
        since=args.since,
        until=args.until,
        service_ids=args.service_ids
    )
