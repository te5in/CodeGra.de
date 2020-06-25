import typing as t
import dataclasses
import xml.etree.ElementTree

from typing_extensions import Literal, TypedDict
from defusedxml.ElementTree import parse as defused_xml_parse

ET = xml.etree.ElementTree
ParseError = ET.ParseError


class MalformedXmlData(ParseError):
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
    def ensure(cls, flag: bool, msg: str, *formatters: object) -> None:
        if not flag:
            raise cls(msg % formatters)

        return None


@dataclasses.dataclass(frozen=True)
class _CGJunitCaseAttribs:
    __slots__ = ('name', 'time')

    name: str
    time: float


class _CGJunitCase:
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
        return self.error is not None

    @property
    def is_failure(self) -> bool:
        return self.failure is not None

    @property
    def is_skipped(self) -> bool:
        return self.skipped is not None

    @classmethod
    def from_xml(cls, xml_el: ET.Element) -> '_CGJunitCase':
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
    __slots__ = ('name', 'errors', 'failures', 'tests', 'skipped')

    name: str
    errors: int
    failures: int
    tests: int
    skipped: int


class _CGJunitSuite:
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
        return self.total_tests - (self.total_failures + self.total_errors)

    @classmethod
    def parse_file(cls, xml_file: t.IO[bytes]) -> 'CGJunit':
        xml_data: ET.ElementTree = defused_xml_parse(xml_file)

        root_node = xml_data.getroot()
        if root_node.tag == 'testsuites':
            return cls([_CGJunitSuite.from_xml(node) for node in root_node])
        elif root_node.tag == 'testsuite':
            return cls([_CGJunitSuite.from_xml(root_node)])

        MalformedXmlData.ensure(
            False, 'Unknown root tag encountered, found: %s', root_node.tag
        )
