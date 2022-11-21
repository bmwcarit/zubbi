# Copyright 2022 BMW Car IT GmbH
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

from zubbi.models import ZuulJob


def test_zuul_job_description():
    job = ZuulJob()
    job.job_name = "foo"
    job.description_html = "<p>Some nice html</p>"

    # Validate that the description is rendered correctly and doesn't
    # result in an AttributeError.
    assert "<p>Some nice html</p>" == job.description_rendered
