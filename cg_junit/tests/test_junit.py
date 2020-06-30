import os

import pytest

from cg_junit import CGJunit, ParseError, MalformedXmlData


def fixture(name):
    return f'{os.path.dirname(__file__)}/../../test_data/{name}'


def parse_fixture(name):
    return CGJunit.parse_file(fixture(name))


@pytest.mark.parametrize(
    'junit_xml', [
        'test_junit_xml/valid.xml',
        'test_junit_xml/valid_many_errors.xml',
    ],
)
def test_parse_valid_xml(junit_xml):
    parse_fixture(junit_xml)


def test_valid_xml_unknown_state():
    res = parse_fixture('test_junit_xml/valid_unknown_state.xml')

    assert res.total_errors == 0
    assert res.total_failures == 0
    assert res.total_skipped == 0
    assert res.total_success == 0


def test_valid_xml_without_skipped_attr():
    res = parse_fixture('test_junit_xml/valid_no_skipped.xml')

    assert res.total_skipped == 0
    assert all(suite.attribs.skipped == 0 for suite in res.suites)
    assert all(not case.is_skipped for suite in res.suites for case in suite.cases)


def test_valid_xml_no_toplevel_testsuites():
    res = parse_fixture('test_junit_xml/valid_no_testsuites_tag.xml')

    assert len(res.suites) == 1


def test_invalid_xml_missing_attrs():
    with pytest.raises(MalformedXmlData) as err:
        parse_fixture('test_junit_xml/invalid_missing_attrs.xml')

    assert 'Did not find all required attributes' in str(err.value)

def test_invalid_xml_invalid_toplevel_tag():
    with pytest.raises(MalformedXmlData) as err:
        parse_fixture('test_junit_xml/invalid_top_level_tag.xml')

    assert 'Unknown root tag' in str(err.value)


def test_invalid_xml_mismatch_number_of_failures():
    with pytest.raises(MalformedXmlData) as err:
        parse_fixture('test_junit_xml/invalid_mismatch_failures.xml')

    assert 'Got a different amount of failed cases' in str(err.value)


def test_invalid_xml_mismatch_number_of_errors():
    with pytest.raises(MalformedXmlData) as err:
        parse_fixture('test_junit_xml/invalid_mismatch_errors.xml')

    assert 'Got a different amount of error cases' in str(err.value)

@pytest.mark.parametrize(
    'junit_xml', [
        'test_submissions/hello.py',
        'test_junit_xml/invalid_xml.xml',
    ],
)
def test_parse_not_xml(junit_xml):
    with pytest.raises(ParseError):
        parse_fixture(junit_xml)


def test_parse_nonexisting_file():
    with pytest.raises(FileNotFoundError):
        parse_fixture('NONEXISTING_FILE')
