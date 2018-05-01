# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import collections
import csv
import logging

from cliff import lister

from goal_tools.who_helped import contributions

LOG = logging.getLogger(__name__)


def _summarize_by(by_names, data_source):
    counts = collections.Counter()
    counts.update(
        tuple(row[by] for by in by_names)
        for row in data_source
    )
    return counts


class SummarizeContributions(lister.Lister):
    "Summarize a contribution report."

    def get_parser(self, prog_name):
        parser = super().get_parser(prog_name)
        parser.add_argument(
            '--by', '-b',
            action='append',
            default=[],
            choices=contributions._COLUMNS,
            help=('column(s) to summarize by (may be repeated), '
                  'defaults to "Organization"'),
        )
        parser.add_argument(
            '--role',
            default=[],
            action='append',
            help='filter to only include specific roles (may be repeated)',
        )
        parser.add_argument(
            'contribution_list',
            nargs='+',
            help='name(s) of files containing contribution details',
        )
        return parser

    def take_action(self, parsed_args):
        group_by = parsed_args.by[:]
        if not group_by:
            group_by.append('Organization')

        def rows():
            for filename in parsed_args.contribution_list:
                LOG.debug('reading %s', filename)
                with open(filename, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    yield from reader

        data = rows()

        roles = parsed_args.role
        if roles:
            data = (d for d in data if d['Role'] in roles)

        counts = _summarize_by(group_by, data)
        items = reversed(sorted(counts.items(), key=lambda x: x[1]))
        columns = tuple(group_by) + ('Count',)
        return (columns, (cols + (count,) for cols, count in items))
