# Copyright 2018 BMW Car IT GmbH
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from datetime import datetime, timezone

import pytest
from freezegun import freeze_time


from zubbi.utils import last_changed_from_blame_range, prettydate

BLAMES = [
    {"start": 1, "end": 4, "date": "2018-07-25T09:40:33+02:00"},
    {"start": 5, "end": 8, "date": "2018-07-25T17:41:20+02:00"},
    {"start": 9, "end": 11, "date": "2018-07-25T09:40:33+02:00"},
    {"start": 12, "end": 15, "date": "2018-07-25T17:41:20+02:00"},
    {"start": 16, "end": 18, "date": "2018-07-25T09:40:33+02:00"},
    {"start": 19, "end": 22, "date": "2018-07-25T17:41:20+02:00"},
    {"start": 23, "end": 23, "date": "2018-07-25T09:40:33+02:00"},
]


@pytest.mark.parametrize(
    "start, end, expected",
    [
        (1, 5, "2018-01-01T00:00:00"),
        (6, 18, "2018-02-02T00:00:00"),
        (20, 22, "2018-01-01T00:00:00"),
        (24, 30, "2018-01-01T00:00:00"),
    ],
)
def test_last_changed_from_blame_range(start, end, expected):
    blame_range = [
        {"start": 1, "end": 7, "date": "2018-01-01T00:00:00"},
        {"start": 8, "end": 15, "date": "2018-02-02T00:00:00"},
        {"start": 16, "end": 38, "date": "2018-01-01T00:00:00"},
    ]
    assert expected == last_changed_from_blame_range(start, end, blame_range)


@pytest.mark.parametrize(
    "start, end, expected",
    [
        (1, 5, "2018-01-01T00:00:00"),
        (6, 18, "2018-01-01T00:00:00"),
        (20, 22, "2018-01-01T00:00:00"),
    ],
)
def test_last_changed_from_blame_range_single(start, end, expected):
    blame_range = [{"start": 1, "end": 38, "date": "2018-01-01T00:00:00"}]
    assert expected == last_changed_from_blame_range(start, end, blame_range)


@pytest.mark.parametrize(
    "start, end, expected",
    [
        (1, 1, "2018-01-01T00:00:00"),
        (5, 22, "2018-08-08T00:00:00"),
        (9, 22, "2018-08-08T00:00:00"),
        (10, 21, "2018-06-06T00:00:00"),
        (10, 22, "2018-06-06T00:00:00"),
        (10, 25, "2018-06-06T00:00:00"),
    ],
)
def test_last_changed_from_blame_range_complex(start, end, expected):
    blame_range = [
        {"start": 1, "end": 5, "date": "2018-01-01T00:00:00"},
        {"start": 6, "end": 6, "date": "2018-02-02T00:00:00"},
        {"start": 7, "end": 7, "date": "2018-03-03T00:00:00"},
        {"start": 8, "end": 9, "date": "2018-08-08T00:00:00"},
        {"start": 10, "end": 20, "date": "2018-05-05T00:00:00"},
        {"start": 21, "end": 22, "date": "2018-06-06T00:00:00"},
        {"start": 23, "end": 30, "date": "2018-01-01T00:00:00"},
    ]
    assert expected == last_changed_from_blame_range(start, end, blame_range)


@pytest.mark.parametrize(
    "date, expected",
    [
        ("2018-09-17 10:14:59", "just now"),
        ("2018-09-17 10:12:02", "3 minutes ago"),
        ("2018-09-17 07:12:02", "3 hours ago"),
        ("2018-09-15 07:12:02", "2 days ago"),
        ("2018-06-06 10:25:12", "06. Jun 2018"),
        ("2015-08-14 16:31:07", "14. Aug 2015"),
    ],
)
def test_prettydate(date, expected):
    date = datetime.strptime(date, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    with freeze_time("2018-09-17 10:15:04"):
        assert expected == prettydate(date)
