#    Copyright 2020 Mirantis, Inc.
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

from openstack_controller import utils


def test_divide_into_groups_of():
    assert [["a", "b", "c"]] == utils.divide_into_groups_of(3, ["a", "b", "c"])
    assert [["a", "b"], ["c", "d"], ["e"]] == utils.divide_into_groups_of(
        2, ["a", "b", "c", "d", "e"]
    )
    assert [] == utils.divide_into_groups_of(2, [])
    assert [["a"]] == utils.divide_into_groups_of(5, ["a"])
