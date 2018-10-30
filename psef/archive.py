"""This modules handles archives and extracting them in a safe way.

This original version of this module from `here
<https://github.com/gdub/python-archive>`_ and licensed under MIT. It has been
extensively modified.

SPDX-License-Identifier: MIT
"""

# Copyright (c) Gary Wilson Jr. <gary@thegarywilson.com> and contributors.
# All rights reserved.

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import os
import abc
import typing as t
import tarfile
import zipfile

import structlog
import dataclasses

from .helpers import add_warning
from .exceptions import APIWarnings

T = t.TypeVar('T', bound='_BaseArchive')

logger = structlog.get_logger()


@dataclasses.dataclass(order=True, repr=True)
class ArchiveMemberInfo:
    """Information for member of an archive.

    :ivar name: The complete name of the member including previous directories.
    :ivar is_dir: Is the member a directory
    """
    name: str
    is_dir: bool


def _safe_join(*args: str) -> str:
    return os.path.normpath(os.path.realpath(os.path.join(*args)))


class ArchiveException(Exception):
    """Base exception class for all archive errors."""


class UnrecognizedArchiveFormat(ArchiveException):
    """Error raised when passed file is not a recognized archive format."""


class UnsafeArchive(ArchiveException):
    """
    Error raised when passed file contains paths that would be extracted
    outside of the target directory.
    """

    def __init__(self, msg: str, member: ArchiveMemberInfo) -> None:
        super().__init__(msg)
        self.member = member


extensions_map: t.Dict[str, t.Type['_BaseArchive']] = {}


def _register_archive(
    extensions: t.List[str],
) -> t.Callable[[t.Type[T]], t.Type[T]]:
    def __decorator(cls: t.Type[T]) -> t.Type[T]:
        for ext in extensions:
            assert ext not in extensions_map
            extensions_map[ext] = cls
        return cls

    return __decorator


class Archive:
    """
    Base Archive class.  Implementations should inherit this class.
    """

    def __init__(self, archive: '_BaseArchive') -> None:
        self.__archive = archive

    @classmethod
    def is_archive(cls: t.Type['Archive'], filename: str) -> bool:
        """Is the filename an archive we can extract.

        :param filename: The filename to check.
        :returns: A boolean indicating if :meth:`.Archive.create_from_file` for
            this filename would work.
        """
        return cls.__get_base_archive_class(filename) is not None

    @staticmethod
    def __get_base_archive_class(filename: str
                                 ) -> t.Optional[t.Type['_BaseArchive']]:
        base, tail_ext = os.path.splitext(filename.lower())
        cls = extensions_map.get(tail_ext)
        if cls is None:
            base, ext = os.path.splitext(base)
            cls = extensions_map.get(ext)

        return cls

    @classmethod
    def create_from_file(cls: t.Type['Archive'], filename: str) -> 'Archive':
        """Create a instance of this class from the given filename.

        >>> Archive.create_from_file('test_data/test_blackboard/correct.tar.gz')
        <psef.archive.Archive object at 0x...>
        >>> Archive.create_from_file('non_existing.tar.gz')
        Traceback (most recent call last):
        ...
        FileNotFoundError: [Errno 2] No such file or directory: 'non_existing.tar.gz'
        >>> Archive.create_from_file('not_an_archive')
        Traceback (most recent call last):
        ...
        psef.archive.UnrecognizedArchiveFormat: Path is not a recognized archive format

        :param filename: The path to the file as source for this archive.
        :returns: An instance of :class:`Archive` when the filename was a
            recognized archive format.
        """
        base_archive_cls = cls.__get_base_archive_class(filename)

        if base_archive_cls is None:
            raise UnrecognizedArchiveFormat(
                'Path is not a recognized archive format'
            )
        return cls(base_archive_cls(filename))

    def extract(self, to_path: str) -> None:
        """Safely extract the current archive.

        :param to_path: The path were the archive should be extracted to.
        :returns: Nothing
        """
        # Make sure we are passing a proper path as to_path
        assert os.path.isabs(to_path)
        assert os.path.isdir(to_path)

        self.check_files(to_path)
        self.__archive.extract(to_path)
        self._replace_symlinks(to_path)

    def _replace_symlinks(self, to_path: str) -> None:
        """Replace symlinks in the given directory with regular files
        containing a notice that the symlink was replaced.

        :param to_path: Directory to scan for symlinks.
        :returns: Nothing
        """
        symlinks = []

        for parent, _, files in os.walk(to_path):
            for f in files:
                file_path = os.path.join(parent, f)

                if not os.path.islink(file_path):
                    continue

                rel_path = os.path.relpath(file_path, to_path)
                link_target = os.readlink(file_path)

                symlinks.append(rel_path)
                os.remove(file_path)
                with open(file_path, 'w') as new_file:
                    new_file.write(
                        (
                            'This file was a symbolic link to "{}" when it '
                            'was submitted, but CodeGrade does not support '
                            'symbolic links.'
                        ).format(link_target),
                    )

                logger.warning(
                    'Symlink detected in archive',
                    archive=self.__archive.filename,
                    filename=rel_path,
                    link_target=link_target,
                )

        if symlinks:
            add_warning(
                (
                    'The archive contained symbolic links which are not '
                    'supported by CodeGrade: {}. The links have been replaced '
                    'with a regular file explaining that these files were '
                    'symbolic links, and the path they pointed to. Note: '
                    'This may break your submission when viewed by the '
                    'teacher.'
                ).format(', '.join(symlinks)),
                APIWarnings.SYMLINK_IN_ARCHIVE,
            )

    def get_members(self) -> t.Iterable[ArchiveMemberInfo]:
        return self.__archive.get_members()

    def check_files(self, to_path: str) -> None:
        """
        Check that all of the files contained in the archive are within the
        target directory.


        >>> from pprint import pprint
        >>> arch = Archive.create_from_file( \
          'test_data/test_submissions/multiple_dir_archive.tar.gz' \
        )
        >>> print(arch.check_files('/tmp/out'))
        None
        >>> arch = Archive.create_from_file('test_data/test_submissions/unsafe.tar.gz')
        >>> arch.check_files('/tmp/out')
        Traceback (most recent call last):
        ...
        psef.archive.UnsafeArchive: Archive member destination is outside the target directory

        :param to_path: The path were the archive should be extracted to.
        :returns: Nothing
        """
        target_path = _safe_join(to_path)

        for member in self.get_members():
            extract_path = _safe_join(target_path, member.name)

            if not extract_path.startswith(target_path):
                raise UnsafeArchive(
                    'Archive member destination is outside the target'
                    ' directory', member
                )


class _BaseArchive(abc.ABC):
    def __init__(self, filename: str) -> None:
        self.filename = filename

    @abc.abstractmethod
    def extract(self, to_path: str) -> None:
        """Extract the given filename to the given path.

        :param to_path: The desired location of the contents of the archive.
        :returns: Nothing
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_members(self) -> t.Iterable[ArchiveMemberInfo]:
        """Get information of all the members of the archive.

        :returns: An iterable containing an :class:`.ArchiveMemberInfo` for
            each member of the archive, including directories.
        """
        raise NotImplementedError


@_register_archive(
    [
        '.tar', '.tar.bz2', '.tar.gz', '.tgz', '.tz2', '.tar.xz', '.tbz',
        '.tb2', '.tbz2', '.txz'
    ]
)
class _TarArchive(_BaseArchive):
    def __del__(self) -> None:
        self._archive.close()

    def __init__(self, filename: str) -> None:
        super().__init__(filename)
        self._archive = tarfile.open(name=self.filename)

    def extract(self, to_path: str) -> None:
        # Make sure archives can be deleted later by fixing permissions
        for tarinfo in self._archive.getmembers():
            if tarinfo.isdir():
                tarinfo.mode = 0o700
            else:
                tarinfo.mode = 0o600

        self._archive.extractall(to_path)

    def get_members(self) -> t.Iterable[ArchiveMemberInfo]:
        """Get all members from this tar archive.

        >>> from pprint import pprint
        >>> zp = _TarArchive('test_data/test_submissions/multiple_dir_archive.tar.gz')
        >>> pprint([dataclasses.astuple(i) for i in sorted(zp.get_members())])
        [('dir/', True),
         ('dir/single_file_work', False),
         ('dir/single_file_work_copy', False),
         ('dir2/', True),
         ('dir2/single_file_work', False),
         ('dir2/single_file_work_copy', False)]
        >>> zp = _TarArchive('test_data/test_submissions/deheading_dir_archive.tar.gz')
        >>> pprint([dataclasses.astuple(i) for i in sorted(zp.get_members())])
        [('dir/', True),
         ('dir/dir2/', True),
         ('dir/dir2/single_file_work', False),
         ('dir/dir2/single_file_work_copy', False)]
        """
        for member in self._archive.getmembers():
            name = member.name
            if member.isdir():
                name += '/'
            yield ArchiveMemberInfo(name=name, is_dir=member.isdir())


@_register_archive(['.zip'])
class _ZipArchive(_BaseArchive):
    def __del__(self) -> None:
        self._archive.close()

    def __init__(self, filename: str) -> None:
        super().__init__(filename)
        self._archive = zipfile.ZipFile(self.filename)

    def extract(self, to_path: str) -> None:
        self._archive.extractall(to_path)

    def get_members(self) -> t.Iterable[ArchiveMemberInfo]:
        """Get all members from this zip archive.

        >>> from pprint import pprint
        >>> zp = _ZipArchive('test_data/test_submissions/multiple_dir_archive.zip')
        >>> pprint([dataclasses.astuple(i) for i in sorted(zp.get_members())])
        [('dir/', True),
         ('dir/single_file_work', False),
         ('dir/single_file_work_copy', False),
         ('dir2/', True),
         ('dir2/single_file_work', False),
         ('dir2/single_file_work_copy', False)]
        >>> zp = _ZipArchive('test_data/test_submissions/deheading_dir_archive.zip')
        >>> pprint([dataclasses.astuple(i) for i in sorted(zp.get_members())])
        [('dir/', True),
         ('dir/dir2/', True),
         ('dir/dir2/single_file_work', False),
         ('dir/dir2/single_file_work_copy', False)]
        """
        seen_dirs: t.Set[str] = set()
        for name in self._archive.namelist():
            cur_is_dir = name[-1] == '/'
            name = name[:-1] if cur_is_dir else name

            while name and name not in seen_dirs:
                name, tail = os.path.split(name)
                if name:
                    cur_path = '{}/{}'.format(name, tail)
                else:
                    cur_path = tail

                seen_dirs.add(cur_path)

                if cur_is_dir:
                    cur_path += '/'
                yield ArchiveMemberInfo(name=cur_path, is_dir=cur_is_dir)
                cur_is_dir = True
