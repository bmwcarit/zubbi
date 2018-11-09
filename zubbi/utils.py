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

import arrow
import pkg_resources


def urljoin(base, *parts):
    clean_parts = (p.strip("/") for p in parts)
    return "/".join((base.rstrip("/"), *clean_parts))


def last_changed_from_blame_range(start, end, blames):
    if not blames:
        return
    # Sort the blames by date (newest first)
    blames = sorted(blames, key=lambda b: b["date"], reverse=True)
    # Build a range including each line (+1 to ensure the last line is also
    # part of the range)
    line_range = set(range(start, end + 1))
    # Try to find the first blame (newest one) that is matching the line range
    for blame in blames:
        blame_range = range(blame["start"], blame["end"] + 1)
        # Find intersections between both ranges
        # If we found one, we return the date (as the first match is also the
        # newest one)
        if line_range.intersection(blame_range):
            return blame["date"]


def prettydate(date):
    now = datetime.now(timezone.utc)
    """
    Return the relative timeframe between the given date and now.

    e.g. 'Just now', 'x days ago', 'x hours ago', ...

    When the difference is greater than 7 days, the timestamp will be returned
    instead.
    """
    diff = now - date
    # Show the timestamp rather than the relative timeframe when the difference
    # is greater than 7 days
    if diff.days > 7:
        return date.strftime("%d. %b %Y")
    return arrow.get(date).humanize()


def get_version():
    try:
        version = pkg_resources.get_distribution("zubbi").version
    except pkg_resources.DistributionNotFound:
        version = "unknown"
    return version
