# Copyright (C) 2017 Jelmer Vernooij <jelmer@jelmer.uk>
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

# Modified from
# https://github.com/dulwich/dulwich/blob/master/dulwich/tests/__init__.py
# and
# https://github.com/dulwich/dulwich/blob/master/dulwich/tests/test_ignore.py
import doctest
import os
import re
import shutil
import subprocess
import sys
import tempfile
from io import BytesIO


# If Python itself provides an exception, use that
import unittest
from unittest import (  # noqa: F401
    SkipTest,
    TestCase as _TestCase,
    skipIf,
    expectedFailure,
    )


class TestCase(_TestCase):

    def setUp(self):
        super(TestCase, self).setUp()
        self._old_home = os.environ.get("HOME")
        os.environ["HOME"] = "/nonexistant"

    def tearDown(self):
        super(TestCase, self).tearDown()
        if self._old_home:
            os.environ["HOME"] = self._old_home
        else:
            del os.environ["HOME"]

from ignorelib import (
    IgnoreFilter,
    IgnoreFilterManager,
    IgnoreFilterStack,
    Pattern,
    match_pattern,
    read_ignore_patterns,
    translate,
    )


POSITIVE_MATCH_TESTS = [
    (b"foo.c", b"*.c"),
    (b".c", b"*.c"),
    (b"foo/foo.c", b"*.c"),
    (b"foo/foo.c", b"foo.c"),
    (b"foo.c", b"/*.c"),
    (b"foo.c", b"/foo.c"),
    (b"foo.c", b"foo.c"),
    (b"foo.c", b"foo.[ch]"),
    (b"foo/bar/bla.c", b"foo/**"),
    (b"foo/bar/bla/blie.c", b"foo/**/blie.c"),
    (b"foo/bar/bla.c", b"**/bla.c"),
    (b"bla.c", b"**/bla.c"),
    (b"foo/bar", b"foo/**/bar"),
    (b"foo/bla/bar", b"foo/**/bar"),
    (b"foo/bar/", b"bar/"),
    (b"foo/bar/", b"bar"),
    (b"foo/bar/something", b"foo/bar/*"),
]

NEGATIVE_MATCH_TESTS = [
    (b"foo.c", b"foo.[dh]"),
    (b"foo/foo.c", b"/foo.c"),
    (b"foo/foo.c", b"/*.c"),
    (b"foo/bar/", b"/bar/"),
    (b"foo/bar/", b"foo/bar/*"),
    (b"foo/bar", b"foo?bar")
]


TRANSLATE_TESTS = [
    (b"*.c", b'(?ms)(.*/)?[^/]*\\.c/?\\Z'),
    (b"foo.c", b'(?ms)(.*/)?foo\\.c/?\\Z'),
    (b"/*.c", b'(?ms)[^/]*\\.c/?\\Z'),
    (b"/foo.c", b'(?ms)foo\\.c/?\\Z'),
    (b"foo.c", b'(?ms)(.*/)?foo\\.c/?\\Z'),
    (b"foo.[ch]", b'(?ms)(.*/)?foo\\.[ch]/?\\Z'),
    (b"bar/", b'(?ms)(.*/)?bar\\/\\Z'),
    (b"foo/**", b'(?ms)foo(/.*)?/?\\Z'),
    (b"foo/**/blie.c", b'(?ms)foo(/.*)?\\/blie\\.c/?\\Z'),
    (b"**/bla.c", b'(?ms)(.*/)?bla\\.c/?\\Z'),
    (b"foo/**/bar", b'(?ms)foo(/.*)?\\/bar/?\\Z'),
    (b"foo/bar/*", b'(?ms)foo\\/bar\\/[^/]+/?\\Z'),
]


class TranslateTests(TestCase):

    def test_translate(self):
        for (pattern, regex) in TRANSLATE_TESTS:
            if re.escape(b'/') == b'/':
                # Slash is no longer escaped in Python3.7, so undo the escaping
                # in the expected return value..
                regex = regex.replace(b'\\/', b'/')
            self.assertEqual(
                regex, translate(pattern),
                "orig pattern: %r, regex: %r, expected: %r" %
                (pattern, translate(pattern), regex))


class ReadIgnorePatterns(TestCase):

    def test_read_file(self):
        f = BytesIO(b"""
# a comment

# and an empty line:

\\#not a comment
!negative\n""" +
b"with trailing whitespace \n" +
b"with escaped trailing whitespace\\ \n"
)  # noqa: W291
        self.assertEqual(list(read_ignore_patterns(f)), [
            b'\\#not a comment',
            b'!negative',
            b'with trailing whitespace',
            b'with escaped trailing whitespace '
        ])


class MatchPatternTests(TestCase):

    def test_matches(self):
        for (path, pattern) in POSITIVE_MATCH_TESTS:
            self.assertTrue(
                match_pattern(path, pattern),
                "path: %r, pattern: %r" % (path, pattern))

    def test_no_matches(self):
        for (path, pattern) in NEGATIVE_MATCH_TESTS:
            self.assertFalse(
                match_pattern(path, pattern),
                "path: %r, pattern: %r" % (path, pattern))


class IgnoreFilterTests(TestCase):

    def test_included(self):
        filter = IgnoreFilter([b'a.c', b'b.c'])
        self.assertTrue(filter.is_ignored(b'a.c'))
        self.assertIs(None, filter.is_ignored(b'c.c'))
        self.assertEqual(
            [Pattern(b'a.c')],
            list(filter.find_matching(b'a.c')))
        self.assertEqual(
            [],
            list(filter.find_matching(b'c.c')))

    def test_included_ignore_case(self):
        filter = IgnoreFilter([b'a.c', b'b.c'], ignore_case=False)
        self.assertTrue(filter.is_ignored(b'a.c'))
        self.assertFalse(filter.is_ignored(b'A.c'))
        filter = IgnoreFilter([b'a.c', b'b.c'], ignore_case=True)
        self.assertTrue(filter.is_ignored(b'a.c'))
        self.assertTrue(filter.is_ignored(b'A.c'))
        self.assertTrue(filter.is_ignored(b'A.C'))

    def test_excluded(self):
        filter = IgnoreFilter([b'a.c', b'b.c', b'!c.c'])
        self.assertFalse(filter.is_ignored(b'c.c'))
        self.assertIs(None, filter.is_ignored(b'd.c'))
        self.assertEqual(
            [Pattern(b'!c.c')],
            list(filter.find_matching(b'c.c')))
        self.assertEqual([], list(filter.find_matching(b'd.c')))

    def test_include_exclude_include(self):
        filter = IgnoreFilter([b'a.c', b'!a.c', b'a.c'])
        self.assertTrue(filter.is_ignored(b'a.c'))
        self.assertEqual(
            [Pattern(b'a.c'), Pattern(b'!a.c'), Pattern(b'a.c')],
            list(filter.find_matching(b'a.c')))

    def test_manpage(self):
        # A specific example from the gitignore manpage
        filter = IgnoreFilter([
            b'/*',
            b'!/foo',
            b'/foo/*',
            b'!/foo/bar'])
        self.assertTrue(filter.is_ignored(b'a.c'))
        self.assertTrue(filter.is_ignored(b'foo/blie'))
        self.assertFalse(filter.is_ignored(b'foo'))
        self.assertFalse(filter.is_ignored(b'foo/bar'))
        self.assertFalse(filter.is_ignored(b'foo/bar/'))
        self.assertFalse(filter.is_ignored(b'foo/bar/bloe'))


class IgnoreFilterStackTests(TestCase):

    def test_stack_first(self):
        filter1 = IgnoreFilter([b'[a].c', b'[b].c', b'![d].c'])
        filter2 = IgnoreFilter([b'[a].c', b'![b],c', b'[c].c', b'[d].c'])
        stack = IgnoreFilterStack([filter1, filter2])
        self.assertIs(True, stack.is_ignored(b'a.c'))
        self.assertIs(True, stack.is_ignored(b'b.c'))
        self.assertIs(True, stack.is_ignored(b'c.c'))
        self.assertIs(False, stack.is_ignored(b'd.c'))
        self.assertIs(None, stack.is_ignored(b'e.c'))


class IgnoreFilterManagerTests(TestCase):

    def test_load_ignore(self):
        tmp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp_dir)
        with open(os.path.join(tmp_dir, '.ignore'), 'wb') as f:
            f.write(b'/foo/bar\n')
            f.write(b'/dir2\n')
            f.write(b'/dir3/\n')
        os.mkdir(os.path.join(tmp_dir, 'dir'))
        with open(os.path.join(tmp_dir, 'dir', '.ignore'), 'wb') as f:
            f.write(b'/blie\n')
        with open(os.path.join(tmp_dir, 'dir', 'blie'), 'wb') as f:
            f.write(b'IGNORED')
        os.mkdir(os.path.join(tmp_dir, '.config'))
        exclude_file_rel_path = os.path.join('.config', 'exclude')
        exclude_file_abs_path = os.path.join(tmp_dir, exclude_file_rel_path)
        with open(exclude_file_abs_path, 'wb') as f:
            f.write(b'/excluded\n')
        m = IgnoreFilterManager.build(tmp_dir,
            global_patterns=['.config'],
            global_ignore_file_paths=[exclude_file_rel_path],
            ignore_file_name='.ignore')
        self.assertTrue(m.is_ignored('dir/blie'))
        self.assertIs(None,
                      m.is_ignored(os.path.join('dir', 'bloe')))
        self.assertIs(None, m.is_ignored('dir'))
        self.assertTrue(m.is_ignored(os.path.join('foo', 'bar')))
        self.assertTrue(m.is_ignored(os.path.join('excluded')))
        self.assertTrue(m.is_ignored(os.path.join(
            'dir2', 'fileinignoreddir')))
        self.assertFalse(m.is_ignored('dir3'))
        self.assertTrue(m.is_ignored('dir3/'))
        self.assertTrue(m.is_ignored('dir3/bla'))

    def test_load_ignore_ignore_case(self):
        tmp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp_dir)
        with open(os.path.join(tmp_dir, '.ignore'), 'wb') as f:
            f.write(b'/foo/bar\n')
            f.write(b'/dir\n')
        m = IgnoreFilterManager.build(tmp_dir, ignore_file_name='.ignore', ignore_case=True)
        self.assertTrue(m.is_ignored(os.path.join('dir', 'blie')))
        self.assertTrue(m.is_ignored(os.path.join('DIR', 'blie')))

    def test_ignored_contents(self):
        tmp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp_dir)
        with open(os.path.join(tmp_dir, '.ignore'), 'wb') as f:
            f.write(b'a/*\n')
            f.write(b'!a/*.txt\n')
        m = IgnoreFilterManager.build(tmp_dir, ignore_file_name='.ignore')
        os.mkdir(os.path.join(tmp_dir, 'a'))
        self.assertIs(None, m.is_ignored('a'))
        self.assertIs(None, m.is_ignored('a/'))
        self.assertFalse(m.is_ignored('a/b.txt'))
        self.assertTrue(m.is_ignored('a/c.dat'))

    def test_walk(self):
        tmp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp_dir)
        with open(os.path.join(tmp_dir, '.ignore'), 'wb') as f:
            f.write(b'/foo/bar\n')
            f.write(b'/dir2\n')
            f.write(b'/dir3/\n')
            f.write(b'/dir4/\n')
        os.mkdir(os.path.join(tmp_dir, 'foo'))
        with open(os.path.join(tmp_dir, 'foo', 'bar'), 'wb') as f:
            f.write(b'IGNORED')
        with open(os.path.join(tmp_dir, 'foo', 'baz'), 'wb') as f:
            f.write(b'NOT_IGNORED')

        os.mkdir(os.path.join(tmp_dir, 'dir2'))
        with open(os.path.join(tmp_dir, 'dir2', 'fileinignoreddir'), 'wb') as f:
            f.write(b'IGNORED')

        os.mkdir(os.path.join(tmp_dir, 'dir3'))
        with open(os.path.join(tmp_dir, 'dir3', 'bla'), 'wb') as f:
            f.write(b'IGNORED')

        with open(os.path.join(tmp_dir, 'dir4'), 'wb') as f:
            f.write(b'NOT_IGNORED')

        os.mkdir(os.path.join(tmp_dir, 'dir'))
        with open(os.path.join(tmp_dir, 'dir', '.ignore'), 'wb') as f:
            f.write(b'/blie\n')
        with open(os.path.join(tmp_dir, 'dir', 'blie'), 'wb') as f:
            f.write(b'IGNORED')
        with open(os.path.join(tmp_dir, 'dir', 'bloe'), 'wb') as f:
            f.write(b'NOT_IGNORED')

        os.mkdir(os.path.join(tmp_dir, 'all_ignored'))
        with open(os.path.join(tmp_dir, 'all_ignored', '.ignore'), 'wb') as f:
            f.write(b'.ignore\n')
            f.write(b'one\n')
            f.write(b'two\n')
        with open(os.path.join(tmp_dir, 'all_ignored', 'one'), 'wb') as f:
            f.write(b'IGNORED')
        with open(os.path.join(tmp_dir, 'all_ignored', 'two'), 'wb') as f:
            f.write(b'IGNORED')

        os.mkdir(os.path.join(tmp_dir, '.config'))
        exclude_file_rel_path = os.path.join('.config', 'exclude')
        exclude_file_abs_path = os.path.join(tmp_dir, exclude_file_rel_path)
        with open(exclude_file_abs_path, 'wb') as f:
            f.write(b'/excluded\n')
        with open(os.path.join(tmp_dir, 'excluded'), 'wb') as f:
            f.write(b'IGNORED')

        m = IgnoreFilterManager.build(tmp_dir,
            global_patterns=['.config'],
            global_ignore_file_paths=[exclude_file_rel_path],
            ignore_file_name='.ignore')

        results = {}
        for dirpath, dirnames, filenames in m.walk():
            rel_dirpath = os.path.relpath(dirpath, tmp_dir)
            results[rel_dirpath] = set(filenames)

        m.to_dict()

        self.assertEqual(set(results.keys()), {'.', 'foo', 'dir'})

        self.assertEqual(results['.'], {'.ignore', 'dir4'})

        self.assertEqual(results['foo'], {'baz'})

        self.assertEqual(results['dir'], {'.ignore', 'bloe'})
