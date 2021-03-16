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

import io
import json
import logging
import os
import pathlib
import sys
import tempfile

from docutils.parsers.rst import Directive
from readme_renderer import markdown
from sphinx.application import Sphinx
from sphinx.util import logging as sphinx_logging
from sphinx.util.console import nocolor
from sphinx.util.docutils import docutils_namespace, patch_docutils


LOGGER = logging.getLogger(__name__)


class ZubbiDirective(Directive):
    has_content = True
    required_arguments = 0
    optional_arguments = 1
    final_argument_whitespace = True
    logger = sphinx_logging.getLogger("ZubbiDirective")

    def run(self):

        if len(self.arguments) > 0:
            values = self.arguments[0].split(",")
            for value in values:
                # Log the value with directive_name for later extraction
                self.logger.info("%s: %s", self.directive_name, value)
        # We don't want to render anything, so we return an empty list of nodes
        return []


class SupportedOS(ZubbiDirective):
    directive_name = "supported_os"


class Reusable(ZubbiDirective):
    directive_name = "reusable"


class SphinxBuildError(RuntimeError):
    pass


def render_sphinx(content):
    with tempfile.TemporaryDirectory() as tmp_dir:
        src_path = pathlib.Path(tmp_dir, "src/contents.rst")
        src_path.parent.mkdir()
        with src_path.open("w") as src:
            src.write(content)

        build_path = pathlib.Path(tmp_dir, "build/contents.fjson")

        source_dir = str(src_path.parent)
        doctree_dir = os.path.join(source_dir, ".doctrees")
        confoverrides = {"extensions": ["zuul_sphinx"], "master_doc": "contents"}
        status_log = io.StringIO()

        # NOTE (fschmidt): This part needs to be in sync with the used version
        # of Sphinx. Current version is:
        # https://github.com/sphinx-doc/sphinx/blob/v1.8.1/sphinx/cmd/build.py#L299
        with patch_docutils(source_dir), docutils_namespace():
            # Remove the color from the Sphinx' console output. Otherwise
            # the lines cannot be parsed properly as some \n are not set properly.
            nocolor()
            app = Sphinx(
                srcdir=source_dir,
                confdir=None,
                outdir=str(build_path.parent),
                doctreedir=doctree_dir,
                buildername="json",
                confoverrides=confoverrides,
                status=status_log,
                warning=sys.stderr,
            )

            # Add the mocked SupportedOS directive to get the os information
            # without rendering it into the resulting HTML page
            app.add_directive(SupportedOS.directive_name, SupportedOS)
            app.add_directive(Reusable.directive_name, Reusable)
            # Start the Sphinx build
            app.build(force_all=True, filenames=[])

            if app.statuscode:
                raise SphinxBuildError

        # Extract the platforms from the logger output
        platforms = []
        reusable = False
        status_log.seek(0)
        for line in status_log.readlines():
            prefix, _, value = line.partition(":")
            if prefix == SupportedOS.directive_name:
                platforms.append(value.strip().lower())
            elif prefix == Reusable.directive_name:
                reusable = value.strip().lower() in ["true", "yes"]
        with build_path.open() as build:
            html_parts = json.load(build)

    return {"html": html_parts["body"], "platforms": platforms, "reusable": reusable}


def render_markdown(content):
    # NOTE (fschmidt): We want to return a similar result like the parse_sphinx()
    # function.
    rendered = markdown.render(content)
    return {"html": rendered}


def render_file(file_dict):
    filepath = file_dict["path"]
    content = file_dict["content"]
    # Render the role description based on the file extension
    if filepath.lower().endswith(".rst"):
        LOGGER.debug("Rendering reStructuredText description")
        try:
            doc = render_sphinx(content)
            return doc
        except SphinxBuildError as exc:
            LOGGER.warning(
                "Content of %s could not be converted to HTML: %s", filepath, exc
            )
        except LookupError:
            LOGGER.exception(
                "Sphinx build failed. Most probably due to the usage of an invalid Sphinx directive or Zuul variable type."
            )
    elif filepath.lower().endswith(".md"):
        LOGGER.debug("Rendering markdown description")
        doc = render_markdown(content)
        return doc
    else:
        # Otherwise, we won't render the description at all.
        # In the UI we could use the missing description_html as
        # indicator to show the how-to-document link
        LOGGER.debug("Found txt or raw description. Skip rendering")
