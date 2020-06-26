"""This module provides utilities for parsing JUnit XML files.

SPDX-License-Identifier: AGPL-3.0-only
"""
import typing as t
import dataclasses
import xml.etree.ElementTree

from typing_extensions import Literal, TypedDict
from defusedxml.ElementTree import parse as defused_xml_parse

ET = xml.etree.ElementTree
ParseError = ET.ParseError


class MalformedXmlData(ParseError):
    """Error raised when the given data could be parsed as XML, but does not
    follow the JUnit specification.
    """

    @classmethod
    @t.overload
    def ensure(
        cls, flag: Literal[False], msg: str, *formatters: object
    ) -> t.NoReturn:
        ...

    @classmethod
    @t.overload
    def ensure(
        cls, flag: t.Union[Literal[True], bool], msg: str, *formatters: object
    ) -> None:
        ...

    @classmethod
    def ensure(  # pylint: disable=useless-return
        cls,
        flag: bool,
        msg: str,
        *formatters: object,
    ) -> None:
        """Assert the validity of a proposition, and raise a
        :class:`MalformedXmlData` if it is not valid.

        :param flag: Proposition to validate.
        :param msg: Message format string, may contain % format specifiers.
        :param formatters: Arguments to the string formatting function, i.e.
            the values to be substituted for the % format specifiers.
        :returns: Nothing.
        :raises MalformedXmlData: When the proposition is not valid.
        """
        if not flag:
            raise cls(msg % formatters)

        return None


@dataclasses.dataclass(frozen=True)
class _CGJunitCaseAttribs:
    """Attributes of a test case.

    :ivar name: Name of the test case.
    :ivar time: Time it took for the test case to run.
    """
    __slots__ = ('name', 'time')

    name: str
    time: float


class _CGJunitCase:
    """Test case data.

    :ivar failure: XML <failure> node containing the failure message, if this
        case failed.
    :ivar error: XML <error> node containing the error message, if an error
        occurred while executing this test case.
    :ivar skipped: XML <skipped> node containing the skipped message, if this
        case was skipped.
    :ivar attribs: Attributes of this test case.
    """
    __slots__ = ('failure', 'error', 'skipped', 'attribs')

    def __init__(
        self,
        failure: t.Optional[ET.Element],
        error: t.Optional[ET.Element],
        skipped: t.Optional[ET.Element],
        attribs: _CGJunitCaseAttribs,
    ) -> None:
        self.failure = failure
        self.error = error
        self.skipped = skipped
        self.attribs = attribs

    @property
    def is_error(self) -> bool:
        """Is this an error case.

        :returns: Boolean indicating whether this is an error case.
        """
        return self.error is not None

    @property
    def is_failure(self) -> bool:
        """Is this a failure case.

        :returns: Boolean indicating whether this is a failure case.
        """
        return self.failure is not None

    @property
    def is_skipped(self) -> bool:
        """Is this a skipped case.

        :returns: Boolean indicating whether this is a skipped case.
        """
        return self.skipped is not None

    @classmethod
    def from_xml(cls, xml_el: ET.Element) -> '_CGJunitCase':
        """Parse a :class:`_CGJunitCase` from an XML tree.

        :param xml_el: The XML node to parse a test case from.
        :returns: The parsed test case.
        :raises MalformedXmlData: When the XML could not be parsed as JUnit
            compatible XML.
        """
        MalformedXmlData.ensure(
            xml_el.tag == 'testcase',
            'Unknown tag encountered, got %s, expected "testcase"', xml_el.tag
        )
        MalformedXmlData.ensure(
            all(attr in xml_el.attrib for attr in ['name']),
            'Not all required attributes were found found for this testcase'
        )
        return cls(
            failure=xml_el.find('failure'),
            error=xml_el.find('error'),
            skipped=xml_el.find('skipped'),
            attribs=_CGJunitCaseAttribs(
                name=xml_el.attrib['name'],
                time=float(xml_el.attrib['time']),
            ),
        )


@dataclasses.dataclass(frozen=True)
class _CGJunitSuiteAttribs:
    """Attributes of a test suite.

    :ivar name: Name of the test suite.
    :ivar errors: The number of error test cases.
    :ivar failures: The number of failure test cases.
    :ivar tests: The total number of test cases.
    :ivar skipped: The number of skipped test cases.
    """
    __slots__ = ('name', 'errors', 'failures', 'tests', 'skipped')

    name: str
    errors: int
    failures: int
    tests: int
    skipped: int


class _CGJunitSuite:
    """Test suite data.

    :ivar cases: The test cases contained in this suite.
    :ivar attribs: Attributes of this test suite.
    """
    __slots__ = ('attribs', 'cases')

    def __init__(
        self, cases: t.Sequence[_CGJunitCase], attribs: _CGJunitSuiteAttribs
    ) -> None:
        self.attribs = attribs
        self.cases = cases
        MalformedXmlData.ensure(
            sum(c.is_failure for c in cases) == attribs.failures, (
                'Got a different amount of failed cases compared to the found'
                ' attribute'
            )
        )
        MalformedXmlData.ensure(
            sum(c.is_error for c in cases) == attribs.errors, (
                'Got a different amount of error cases compared to the found'
                ' attribute'
            )
        )

    @classmethod
    def from_xml(cls, xml_el: ET.Element) -> '_CGJunitSuite':
        """Parse a :class:`_CGJunitSuite` from an XML tree.

        :param xml_el: The XML node to parse a test suite from.
        :returns: The parsed test suite.
        :raises MalformedXmlData: When the XML could not be parsed as JUnit
            compatible XML.
        """
        MalformedXmlData.ensure(
            xml_el.tag == 'testsuite',
            'Unknown tag encountered, got %s, expected "testsuite"', xml_el.tag
        )
        MalformedXmlData.ensure(
            all(
                attr in xml_el.attrib
                for attr in ['name', 'errors', 'failures', 'tests']
            ),
            (
                'Did not find all required attributes for this testsuite,'
                ' found: %s'
            ),
            list(xml_el.attrib.keys()),
        )
        return cls(
            [_CGJunitCase.from_xml(child) for child in xml_el],
            _CGJunitSuiteAttribs(
                name=xml_el.attrib['name'],
                errors=int(xml_el.attrib['errors']),
                failures=int(xml_el.attrib['failures']),
                tests=int(xml_el.attrib['tests']),
                skipped=int(xml_el.attrib.get('skipped', '0')),
            ),
        )


class CGJunit:
    """Class containing the information of a test run available in a JUnit
    compatible XML file.

    :ivar suites: The test suites in this test run.
    :ivar total_failures: The total number of failed test cases in this test
        run.
    :ivar total_errors: The total number of error cases in this test run.
    :ivar total_skipped: The total number of skipped cases in this test run.
    :ivar total_tests: The total number of test cases in this test run.
    """

    def __init__(self, suites: t.Sequence[_CGJunitSuite]) -> None:
        self.suites = suites
        self.total_failures = sum(s.attribs.failures for s in suites)
        self.total_errors = sum(s.attribs.errors for s in suites)
        self.total_skipped = sum(s.attribs.skipped for s in suites)
        self.total_tests = sum(
            s.attribs.tests for s in suites
        ) - self.total_skipped

    @property
    def total_success(self) -> int:
        """The total number of successful test cases in this test run.
        """
        return self.total_tests - (self.total_failures + self.total_errors)

    @classmethod
    def parse_file(cls, xml_file: t.IO[bytes]) -> 'CGJunit':
        """Parse a :class:`CGJunit` from an XML bytestream.

        :param xml_file: The XML data to parse a test run from.
        :returns: The parsed test run data.
        :raises ParseError: When the XML could not be parsed, or does not
            follow the JUnit specification.
        """
        xml_data: ET.ElementTree = defused_xml_parse(xml_file)

        root_node = xml_data.getroot()
        if root_node.tag == 'testsuites':
            return cls([_CGJunitSuite.from_xml(node) for node in root_node])
        elif root_node.tag == 'testsuite':
            return cls([_CGJunitSuite.from_xml(root_node)])

        MalformedXmlData.ensure(
            False, 'Unknown root tag encountered, found: %s', root_node.tag
        )
