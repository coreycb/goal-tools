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

from goal_tools import utils
from goal_tools.tests import base


class TestUnique(base.TestCase):

    def test_no_dupes(self):
        input = 'abc'
        expected = 'abc'
        actual = ''.join(utils.unique(input))
        self.assertEqual(expected, actual)

    def test_dupes(self):
        input = 'abcabc'
        expected = 'abc'
        actual = ''.join(utils.unique(input))
        self.assertEqual(expected, actual)
