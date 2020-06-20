import typing as t
import xml.etree.ElementTree

from typing_extensions import Literal, TypedDict
from defusedxml.ElementTree import parse as defused_xml_parse

ET = xml.etree.ElementTree
ParseError = ET.ParseError

class MalformedXmlData(ParseError):
    @classmethod
    @t.overload
    def ensure(cls, flag: Literal[False]) -> t.NoReturn:
        ...

    @classmethod
    @t.overload
    def ensure(cls, flag: t.Union[Literal[True], bool]) -> None:
        ...

    @classmethod
    def ensure(cls, flag: bool) -> t.Union[None, t.NoReturn]:
        if not flag:
            raise cls()

        return None


class _CGJunitCaseAttribs(TypedDict, total=True):
    name: str
    time: float


class _CGJunitCase:
    def __init__(
        self, failure: t.Optional[ET.Element], error: t.Optional[ET.Element],
        skipped: t.Optional[ET.Element], attribs: _CGJunitCaseAttribs
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
        MalformedXmlData.ensure(xml_el.tag == 'testcase')
        MalformedXmlData.ensure(
            all(attr in xml_el.attrib for attr in ['name'])
        )
        return cls(
            failure=xml_el.find('failure'),
            error=xml_el.find('error'),
            skipped=xml_el.find('skipped'),
            attribs={
                'name': xml_el.attrib['name'],
                'time': float(xml_el.attrib['time']),
            },
        )


class _CGJunitSuiteAttribs(TypedDict, total=True):
    name: str
    errors: int
    failures: int
    tests: int
    skipped: int


class _CGJunitSuite:
    def __init__(
        self, cases: t.Sequence[_CGJunitCase], attribs: _CGJunitSuiteAttribs
    ) -> None:
        self.attribs = attribs
        self.cases = cases
        MalformedXmlData.ensure(
            sum(c.is_failure for c in cases) == attribs['failures']
        )
        MalformedXmlData.ensure(
            sum(c.is_error for c in cases) == attribs['errors']
        )

    @classmethod
    def from_xml(cls, xml_el: ET.Element) -> '_CGJunitSuite':
        MalformedXmlData.ensure(xml_el.tag == 'testsuite')
        MalformedXmlData.ensure(
            all(
                attr in xml_el.attrib
                for attr in ['name', 'errors', 'failures', 'tests']
            )
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
        self.total_failures = sum(s.attribs['failures'] for s in suites)
        self.total_errors = sum(s.attribs['errors'] for s in suites)
        self.total_skipped = sum(s.attribs['skipped'] for s in suites)
        self.total_tests = sum(s.attribs['tests'] for s in suites) - self.total_skipped

    @property
    def total_success(self) -> int:
        return self.total_tests - (self.total_failures + self.total_errors)

    @classmethod
    def parse_file(cls, xml_file: t.BinaryIO) -> 'CGJunit':
        xml_data: ET.ElementTree = defused_xml_parse(xml_file)

        root_node = xml_data.getroot()
        if root_node.tag == 'testsuites':
            return cls([_CGJunitSuite.from_xml(node) for node in root_node])
        elif root_node.tag == 'testsuite':
            return cls([_CGJunitSuite.from_xml(root_node)])
        MalformedXmlData.ensure(False)
