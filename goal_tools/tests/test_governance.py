# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from goal_tools.tests import base

from goal_tools import governance

import yaml


_team_data_yaml = """
Release Management:
  ptl:
    name: Doug Hellmann
    irc: dhellmann
    email: doug@doughellmann.com
  irc-channel: openstack-release
  mission: >
    Coordinating the release of OpenStack deliverables, by defining the
    overall development cycle, release models, publication processes,
    versioning rules and tools, then enabling project teams to produce
    their own releases.
  url: https://wiki.openstack.org/wiki/Release_Management
  tags:
    - team:diverse-affiliation
  deliverables:
    release-schedule-generator:
      repos:
        - openstack/release-schedule-generator
    release-test:
      repos:
        - openstack/release-test
    release-tools:
      repos:
        - openstack-infra/release-tools
    releases:
      repos:
        - openstack/releases
    reno:
      repos:
        - openstack/reno
      docs:
        contributor: https://docs.openstack.org/developer/reno/
    specs-cookiecutter:
      repos:
        - openstack-dev/specs-cookiecutter
"""

TEAM_DATA = yaml.load(_team_data_yaml)


class TestGetRepoOwner(base.TestCase):

    def test_repo_exists(self):
        owner = governance.get_repo_owner(
            TEAM_DATA,
            'openstack/releases',
        )
        self.assertEqual('Release Management', owner)

    def test_no_such_repo(self):
        self.assertRaises(
            ValueError,
            governance.get_repo_owner,
            TEAM_DATA,
            'openstack/no-such-repo',
        )


class TestGetRepositories(base.TestCase):

    def test_by_team(self):
        repos = governance.get_repositories(
            TEAM_DATA,
            team_name='Release Management',
        )
        self.assertEqual(
            sorted(['openstack/release-schedule-generator',
                    'openstack/release-test',
                    'openstack-infra/release-tools',
                    'openstack/releases',
                    'openstack/reno',
                    'openstack-dev/specs-cookiecutter']),
            sorted(r.name for r in repos),
        )

    def test_by_deliverable(self):
        repos = governance.get_repositories(
            TEAM_DATA,
            deliverable_name='release-tools',
        )
        self.assertEqual(
            ['openstack-infra/release-tools'],
            [r.name for r in repos],
        )

    def test_code_only(self):
        repos = governance.get_repositories(
            TEAM_DATA,
            code_only=True,
        )
        self.assertEqual(
            sorted(['openstack/release-schedule-generator',
                    'openstack/release-test',
                    'openstack-infra/release-tools',
                    'openstack/releases',
                    'openstack/reno']),
            sorted(r.name for r in repos),
        )

    def test_tag_negative(self):
        repos = governance.get_repositories(
            TEAM_DATA,
            tags=['team:single-vendor'],
        )
        self.assertEqual([], list(repos))

    def test_tags_positive(self):
        repos = governance.get_repositories(
            TEAM_DATA,
            tags=['team:diverse-affiliation'],
        )
        self.assertEqual(
            sorted(['openstack/release-schedule-generator',
                    'openstack/release-test',
                    'openstack-infra/release-tools',
                    'openstack/releases',
                    'openstack/reno',
                    'openstack-dev/specs-cookiecutter']),
            sorted(r.name for r in repos),
        )
