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
import datetime
import fileinput
import logging
import urllib.parse

from goal_tools import apis

LOG = logging.getLogger(__name__)

# The base URL to Gerrit REST API
GERRIT_API_URL = 'https://review.openstack.org/'

QUERY_OPTIONS = [
    'ALL_REVISIONS',
    'REVIEWER_UPDATES',
    'DETAILED_ACCOUNTS',
    'CURRENT_COMMIT',
    'LABELS',
    'DETAILED_LABELS',
]


def parse_review_id(line):
    parsed = urllib.parse.urlparse(line)
    if parsed.fragment:
        # https://review.openstack.org/#/c/561507/
        return parsed.fragment.lstrip('/c').partition('/')[0]
    else:
        # https://review.openstack.org/555353/
        return parsed.path.lstrip('/').partition('/')[0]


def parse_review_lists(filenames):
    """Generator that produces review IDs as strings.

    Read the files expecting to find one review URL or ID per
    line. Ignore lines that start with # as comments. Ignore blank
    lines.

    :param filenames: Iterable of filenames to read.
    :return: Generator of str

    """
    for line in fileinput.input(filenames):
        line = line.strip()
        if not line:
            continue
        if line.startswith('#'):
            continue
        LOG.debug('parsing %r', line)
        yield parse_review_id(line)


def query_gerrit(method, params={}):
    """Query the Gerrit REST API"""
    url = GERRIT_API_URL + method
    LOG.debug('fetching %s', url)
    raw = apis.requester(
        url, params=params,
        headers={'Accept': 'application/json'})
    return apis.decode_json(raw)


def _to_datetime(s):
    "Convert a string to a datetime.datetime instance"
    # Ignore the trailing decimal seconds.
    if s is None:
        return None
    s = s.rpartition('.')[0]
    return datetime.datetime.strptime(s, '%Y-%m-%d %H:%M:%S')


Participant = collections.namedtuple(
    'Participant', ['role', 'name', 'email', 'date'])


class Review:
    "The history of one code review"

    def __init__(self, id, data):
        self._id = id
        self._data = data

    @property
    def id(self):
        return self._id

    @property
    def raw_change(self):
        return self._data

    @property
    def url(self):
        return GERRIT_API_URL + str(self._id) + '/'

    @property
    def created(self):
        return _to_datetime(self._data.get('created'))

    @property
    def is_merged(self):
        return self._data.get('status') == 'MERGED'

    @property
    def project(self):
        return self._data.get('project')

    @property
    def participants(self):
        yield self.owner
        yield from self.reviewers
        yield from self.uploaders

    @property
    def branch(self):
        return self._data.get('branch', '*unknown')

    @property
    def owner(self):
        owner = self._data.get('owner')
        if 'email' not in owner:
            owner['email'] = owner.get('email', 'no-reply@openstack.org')
        return Participant(
            'owner',
            owner.get('name'),
            owner.get('email'),
            self.created,
        )

    @property
    def uploaders(self):
        known_uploaders = set()

        # Record the owner of the patch as a known uploader so we do
        # not emit their information again. This means someone with
        # the "uploader" role can be counted as someone taking over a
        # patch created by someone else to fix it in some way.
        owner_email = self._data.get('owner', {}).get('email')
        known_uploaders.add(owner_email)

        # The revision data is stored in a mapping keyed by the SHA,
        # so in order to be consistent with how we return the
        # uploaders we sort the revisions based on the number before
        # we process them.
        revisions = sorted(
            self._data.get('revisions', {}).values(),
            key=lambda x: x.get('_number', 0),
        )

        for revision in revisions:
            uploader = revision.get('uploader', {})
            if 'email' not in uploader:
                uploader['email'] = 'no-reply@openstack.org'
            if uploader['email'] in known_uploaders:
                # Ignore duplicates
                continue
            known_uploaders.add(uploader['email'])
            yield Participant(
                'uploader',
                uploader.get('name'),
                uploader['email'],
                _to_datetime(revision.get('created')),
            )

    @property
    def reviewers(self):
        labels = self._data.get('labels', {})

        code_review_labels = labels.get('Code-Review', {}).get('all', [])
        for label in code_review_labels:
            if label.get('value') not in (2, -1):
                # Only report reviewers with negative reviews or
                # approvals to avoid counting anyone who is just
                # leaving lots of +1 votes without actually providing
                # feedback.
                continue
            yield Participant(
                'reviewer',
                label.get('name', 'Unknown Person'),
                label.get('email', 'unknown@example.com'),
                _to_datetime(label.get('date')),
            )

        workflow_labels = labels.get('Workflow', {}).get('all', [])
        for label in workflow_labels:
            if label.get('value', 0) != 1:
                continue
            yield Participant(
                'approver',
                label.get('name', 'Unknown Person'),
                label.get('email', 'unknown@example.com'),
                _to_datetime(label.get('date')),
            )

    @property
    def plus_ones(self):
        labels = self._data.get('labels', {})

        code_review_labels = labels.get('Code-Review', {}).get('all', [])
        for label in code_review_labels:
            if label.get('value') != 1:
                # Other types of reviews are counted elsewhere.
                continue
            yield Participant(
                'plus_one',
                label.get('name', 'Unknown Person'),
                label.get('email', 'unknown@example.com'),
                _to_datetime(label.get('date')),
            )


def cache_review(review_id, data, cache):
    """Add a review to the cache.

    Review data is only cached if the review is MERGED because
    otherwise it is more likely to change.

    :param review_id: Review ID of the review to look for.
    :type review_id: str
    :param data: Data structure returned by query_gerrit
    :type data: dict
    :param cache: Storage for repeated lookups.
    :type cache: goal_tools.cache.Cache

    """
    if data.get('status') == 'MERGED':
        cache[('review', str(review_id))] = data


class ReviewFactory:

    def __init__(self, cache):
        self._cache = cache

    def fetch(self, review_id):
        """Find the review in the cache or look it up in the API.

        Review data is only cached if the review is MERGED because
        otherwise it is more likely to change.

        :param review_id: Review ID of the review to look for.
        :type review_id: str
        :param cache: Storage for repeated lookups.
        :type cache: goal_tools.cache.Cache

        """
        key = ('review', str(review_id))
        if key in self._cache:
            LOG.debug('found %s cached', review_id)
            return Review(review_id, self._cache[key])
        data = query_gerrit(
            'changes/' + review_id + '/detail',
            params={
                'o': QUERY_OPTIONS,
            },
        )
        response = Review(review_id, data)
        cache_review(review_id, data, self._cache)
        return response

    def query(self, query_string):
        "Generator for changes matching the query criteria."
        batch_size = 200
        offset = 0
        while True:
            changes = query_gerrit(
                'changes/',
                params={
                    'n': str(batch_size),
                    'start': offset,
                    'q': query_string,
                    'o': QUERY_OPTIONS,
                },
            )
            LOG.debug('%d changes', len(changes))

            for change in changes:
                review = Review(
                    change['_number'],
                    change,
                )
                cache_review(
                    review.id,
                    review.raw_change,
                    self._cache,
                )
                yield review

            if changes and changes[-1].get('_more_changes', False):
                offset += batch_size
            else:
                break
