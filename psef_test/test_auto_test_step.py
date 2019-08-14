import pprint
import random
import contextlib

import regex
import pytest
from pytest import raises
from werkzeug.local import LocalProxy

import psef
import psef.models as m
from psef import helpers
from psef.exceptions import APIException
from psef.models.auto_test_step import _IoTest as IoTest
from psef.models.auto_test_step import _RunProgram as RunProgram
from psef.models.auto_test_step import _CheckPoints as CheckPoints
from psef.models.auto_test_step import _CustomOutput as CustomOutput


@contextlib.contextmanager
def raises_api(msg, full=False):
    exc = None
    proxy = LocalProxy(lambda: exc)
    with raises(APIException) as err:
        yield proxy
    exc = err.value
    pprint.pprint(exc.__to_json__())
    if full:
        assert msg == exc.message
    else:
        assert msg in exc.message


@pytest.fixture
def stub_container_class(stub_function_class):
    class Stub(stub_function_class):
        def __init__(self, code, stdout, stderr, time_spend):
            def maybe_call(a):
                return a(self) if callable(a) else a

            super().__init__(
                lambda: (
                    maybe_call(self.code), maybe_call(self.stdout),
                    maybe_call(self.stderr), maybe_call(self.time_spend)
                )
            )
            self.code = code
            self.stdout = stdout
            self.stderr = stderr
            self.time_spend = time_spend

        def run_student_command(self, *args, **kwargs):
            res = super().__call__(*args, **kwargs)
            if isinstance(self.code, Exception):
                raise self.code
            return res

    return Stub


@pytest.fixture
def stub_suite():
    yield m.AutoTestSuite(command_time_limit=5)


def test_validate_custom_output(describe, monkeypatch, stub_function_class):
    o = CustomOutput()

    with describe('Regex has to contain \\f'):
        with raises_api('You have to have at least one \\f'):
            o.validate_data({'program': '...', 'regex': '(.*)'})

    with describe('Adds warning if more than one \\f is found'):
        with monkeypatch.context() as m:
            m.setattr(psef.helpers, 'add_warning', stub_function_class())
            o.validate_data({'program': '..', 'regex': '\\f \\f'})
            assert len(psef.helpers.add_warning.all_args) == 1

    with describe('Regex has to compile'):
        with raises_api('Compiling the regex failed'):
            o.validate_data({'program': '...', 'regex': '\\f('})

    with describe('All keys are required'):
        with raises_api('The given object does not contain all required keys'):
            o.validate_data({'regex': '\\f'})

    with describe('When everything is ok it should not raise'):
        o.validate_data({'program': '...', 'regex': '\\f'})


def test_validate_data_check_points(describe):
    c = CheckPoints()
    with describe('When everything is ok it should not raise'):
        c.validate_data({'min_points': 0.5})

    with describe('Higher than 1 should not work'):
        with raises_api('has to be between 0 and 1'):
            c.validate_data({'min_points': 1.1})

    with describe('Lower than 1 should not work'):
        with raises_api('has to be between 0 and 1'):
            c.validate_data({'min_points': -0.1})

    with describe('min_points should be a number'):
        with raises_api(''):
            c.validate_data({'min_points': 'str'})

    with describe('extra data is not allowed'):
        with raises_api('Extra keys in the object'):
            c.validate_data({'min_points': 0.5, 'extra_key': 'hello!'})


def test_execute_run_program_step(
    stub_suite, describe, monkeypatch, stub_function_class,
    stub_container_class
):
    with describe('setup'):
        p = RunProgram(suite=stub_suite)
        p.update_data_from_json({'program': 'ls'})
        stub_ensure = stub_function_class()
        monkeypatch.setattr(helpers, 'ensure_on_test_server', stub_ensure)

        stub_update_result = stub_function_class()
        stub_container = stub_container_class(0, ';', 'asdf', 5)

    with describe('Non crashing program'):
        p.execute_step(
            stub_container, stub_update_result, p.get_instructions(), 1
        )
        # Make sure correct program is called
        assert stub_container.args[0][0] == 'ls'
        assert len(stub_container.args) == 1

        # Should be called exactly twice
        first_args, next_args = stub_update_result.args

        # First should be called with running and no data
        assert first_args[0].name == 'running'
        assert first_args[1] == {}

        assert next_args[0].name == 'passed'
        assert next_args[1]['stdout'] == stub_container.stdout
        assert next_args[1]['stderr'] == stub_container.stderr
        assert next_args[1]['exit_code'] == 0

    with describe('Crashing program'):
        stub_container.code = random.randint(1, 100)
        p.execute_step(
            stub_container, stub_update_result, p.get_instructions(), 1
        )
        # First should be called with running even if it crashes
        assert stub_update_result.args[0][0].name == 'running'
        assert stub_update_result.args[0][1] == {}

        next_args = stub_update_result.args[1]
        assert next_args[0].name == 'failed'
        assert next_args[1]['exit_code'] == stub_container.code


def test_validate_setting_weight(describe):
    c = m.AutoTestStepBase()
    with describe('can set weight to higher than 0'):
        c.weight = 1
        assert c.weight == 1

    with describe('can set weight to 0'):
        c.weight = 0
        assert c.weight == 0

    with describe('cannot set weight lower than 0'):
        with pytest.raises(psef.exceptions.APIException):
            c.weight = -1


def test_validate_weight_check_points(describe):
    c = CheckPoints()
    with describe('can set weight to 0'):
        c.weight = 0
        assert c.weight == 0

    with describe('cannot set weight not zero'):
        with pytest.raises(psef.exceptions.APIException):
            c.weight = -1

        with pytest.raises(psef.exceptions.APIException):
            c.weight = 1


def test_validate_data_io_step(describe):
    i = IoTest()
    i.weight = 1
    data = {'program': '', 'inputs': []}

    with describe('Program cannot be the empty string'):
        with raises_api('program may to execute may not be empty'):
            i.validate_data(data)
        data['program'] = 'ls'

    with describe(
        'At least one input is required',
    ), raises_api('You have to provide at least one input case'):
        i.validate_data(data)

    inp = {
        'args': '', 'stdin': '', 'output': '', 'options': [], 'weight': -1,
        'name': ''
    }
    data['inputs'].append(inp)

    with describe('Sum of the weight should be equal to step weight'):
        with raises_api('The sum of the weight of the steps'):
            i.validate_data(data)

    with describe('The entire input has to be valid'):
        inp['weight'] = 1
        with raises_api('Some input cases were not valid') as exc:
            i.validate_data(data)
        assert any('name may not' in c for _, c in exc.rest['invalid_cases'])

        inp['name'] = 'Valid name'
        inp['options'] = ['not valid']
        with raises_api('Some input cases were not valid') as exc:
            i.validate_data(data)
        assert any('Unknown items' in c for _, c in exc.rest['invalid_cases'])

        inp['options'] = ['substring', 'substring']
        with raises_api('Some input cases were not valid') as exc:
            i.validate_data(data)
        assert any('Duplicate' in c for _, c in exc.rest['invalid_cases'])

        inp['options'] = ['regex']
        with raises_api('Some input cases were not valid') as exc:
            i.validate_data(data)
        assert any(
            '"regex" option implies "substring"' in c
            for _, c in exc.rest['invalid_cases']
        )

        inp['options'] = ['regex', 'substring', 'all_whitespace']
        with raises_api('Some input cases were not valid') as exc:
            i.validate_data(data)
        assert any(
            '"all_whitespace" option implies "trailing_whitespace"' in c
            for _, c in exc.rest['invalid_cases']
        )
        assert any(
            '"all_whitespace" option cannot be combined with the "regex"' in c
            for _, c in exc.rest['invalid_cases']
        )

        inp['options'] = ['substring', 'regex']
        i.validate_data(data)

    with describe('Should raise when one of the inputs is invalid'):
        data['inputs'].append({
            'args': '', 'stdin': '', 'output': '', 'options': [], 'weight': 0,
            'name': ''
        })
        with raises_api('Some input cases were not valid'):
            i.validate_data(data)


@pytest.mark.parametrize(
    'output,expected,options,success',
    [
        ('hello', 'hel', [], False),
        ('hello', 'hel', ['substring'], True),
        ('hello', 'h.*', ['substring'], False),
        ('hello', 'h.*', ['substring', 'regex'], True),
        # Both trailing whitespace
        ('hello ', 'hello ', [], True),
        # One of them trailing whitespace should fail
        ('hello', 'hello ', [], False),
        ('hello ', 'hello', [], False),
        # Should work when removing that whitespace
        ('hello ', 'hello', ['trailing_whitespace'], True),
        ('hello', 'hello ', ['trailing_whitespace'], True),
        # Exact matches should still work
        ('hello', 'hello', ['trailing_whitespace'], True),
        # Leading whitespace should still fail
        (' hello', 'hello', ['trailing_whitespace'], False),
        ('hello', ' hello', ['trailing_whitespace'], False),
        # Case insensitive should work both ways
        ('hello', 'heLLO', [], False),
        ('HEllo', 'hello', [], False),
        ('hello', 'heLLO', ['case'], True),
        ('HEllo', 'hello', ['case'], True),
        # Regex can also be case insensitive
        ('Hello', 'h.*', ['substring', 'regex'], False),
        ('Hello', 'h.*', ['case', 'substring', 'regex'], True),
        ('hello', 'H.*', ['case', 'substring', 'regex'], True),
        # A timeout error should be returned
        (
            lambda: 'A' * 1000000 + 'BB', r'^(A+)*B$', ['substring', 'regex'],
            (False, -2)
        ),
        # All whitespace option should work
        (
            ' a b cd \nf', 'abc df', ['trailing_whitespace', 'all_whitespace'],
            True
        ),
        ('a\r\nb', 'ab', ['trailing_whitespace', 'all_whitespace'], True),
        ('ac', 'ab', ['trailing_whitespace', 'all_whitespace'], False),
    ]
)
def test_match_output_io_step(expected, output, options, success):
    i = IoTest()
    if callable(output):
        output = output()

    if not isinstance(success, tuple):
        success = (success, None)

    assert i.match_output(output, expected, options) == success


def test_execute_io_step(
    stub_suite, describe, monkeypatch, stub_function_class,
    stub_container_class
):
    with describe('setup'):
        i = IoTest(suite=stub_suite)
        i.weight = 2
        i.update_data_from_json({
            'program': 'ls', 'inputs': [{
                'name': 'no name',
                'args': '1',
                'weight': 1,
                'stdin': 'stdin-1',
                'output': 'WRONG STDOUT',
                'options': [],
            },
                                        {
                                            'name': 'a name',
                                            'args': '2',
                                            'weight': 1,
                                            'stdin': 'stdin-2',
                                            'output': 'CORRECT STDOUT',
                                            'options': [],
                                        }]
        })

        stub_ensure = stub_function_class()
        monkeypatch.setattr(helpers, 'ensure_on_test_server', stub_ensure)

        stub_update_result = stub_function_class()
        stub_container = stub_container_class(0, 'CORRECT STDOUT', 'asdf', 5)

    with describe('Non crashing program'):
        total_weight = i.execute_step(
            stub_container, stub_update_result, i.get_instructions(), 1
        )
        # Only one step succeeded
        assert total_weight == 1

        # Make sure correct program is called
        call1, call2 = stub_container.all_args
        last_update = stub_update_result.all_args[-1]
        last_steps = last_update[1]['steps']

        assert call1[0] == 'ls 1'
        assert call1['stdin'] == b'stdin-1'  # it should provide bytes
        assert last_steps[0]['state'] == 'failed'
        assert last_steps[0]['exit_code'] == 0

        assert call2[0] == 'ls 2'
        assert call2['stdin'] == b'stdin-2'  # Should be different
        assert last_steps[1]['state'] == 'passed'
        assert last_steps[1]['exit_code'] == 0

        # Only the two existing steps should have results
        assert len(last_steps) == 2

    with describe('Program crashing'):
        stub_container.code = random.randint(1, 100)
        res = i.execute_step(
            stub_container, stub_update_result, i.get_instructions(), 1
        )
        # No steps succeeded
        assert res == 0

        for step in stub_update_result.all_args[-1][1]['steps']:
            assert step['state'] == 'failed'
            assert step['exit_code'] == stub_container.code

        # No tests succeeded so the state should be failed
        assert stub_update_result.args[-1][0].name == 'failed'

    with describe('Call timing out'):
        stub_container.code = psef.auto_test.CommandTimeoutException(0)
        res = i.execute_step(
            stub_container, stub_update_result, i.get_instructions(), 1
        )

        # All commands timed out so no should pass
        assert res == 0

        for step in stub_update_result.all_args[-1][1]['steps']:
            assert step['state'] == 'timed_out'
            assert step['exit_code'] == -1  # -1 is used for command timeout


def test_execute_custom_output(
    describe, stub_function_class, monkeypatch, stub_container_class,
    stub_suite
):
    with describe('setup'):
        o = CustomOutput(suite=stub_suite)
        data = {'program': 'prog', 'regex': '\\f'}
        o.update_data_from_json(data)
        o.weight = random.randint(1, 100)
        stub_ensure = stub_function_class()
        monkeypatch.setattr(helpers, 'ensure_on_test_server', stub_ensure)

        stub_update_result = stub_function_class()
        stub_container = stub_container_class(0, '0.5\n', 'asdf', 5)

    def step():
        return o.execute_step(
            stub_container, stub_update_result, o.get_instructions(), 1
        )

    with describe('the outputted number should be used'):
        res = step()
        assert o.weight * 0.5 == res

        last_update = stub_update_result.all_args[-1]
        assert last_update[0].name == 'passed'
        assert last_update[1]['exit_code'] == 0
        assert last_update[1]['points'] == 0.5

    with describe('non matching regex the test should fail'
                  ), monkeypatch.context() as m:
        m.setitem(data, 'regex', '(a)')

        res = step()
        assert res == 0

        last_update = stub_update_result.all_args[-1]
        assert last_update[0].name == 'failed'
        assert last_update[1]['exit_code'] == -1  # Indicates failing regex
        assert last_update[1]['points'] == 0

    with describe('regex matching not integer should fail test'
                  ), monkeypatch.context() as m:
        m.setitem(data, 'regex', '\\f?')
        m.setattr(stub_container, 'stdout', 'NOT A FLOAT')

        res = step()
        assert res == 0

        last_update = stub_update_result.all_args[-1]
        assert last_update[0].name == 'failed'
        assert last_update[1]['exit_code'] == -2  # Indicates non int
        assert last_update[1]['points'] == 0

    with describe('number lower than 0 should be capped'
                  ), monkeypatch.context() as m:
        for val, expected in [(-1, 0), (-0.5, 0), (-0.0, 0)]:
            m.setattr(stub_container, 'stdout', str(val))

            res = step()
            assert res == expected

            last_update = stub_update_result.all_args[-1]
            assert last_update[0].name == 'passed'

    with describe('crashing command should fail'), monkeypatch.context() as m:
        m.setattr(stub_container, 'code', 1)
        res = step()
        assert res == 0

        last_update = stub_update_result.all_args[-1]
        assert last_update[0].name == 'failed'
        assert last_update[1]['points'] == 0

    with describe('slow regex should fail'), monkeypatch.context() as m:

        def raise_():
            raise TimeoutError

        m.setattr(regex, 'search', stub_function_class(raise_))
        res = step()
        assert res == 0

        last_update = stub_update_result.all_args[-1]
        assert last_update[0].name == 'failed'
        assert last_update[1]['points'] == 0
        assert last_update[1]['exit_code'] == -3
        assert 'regex took too long' in last_update[1]['stderr']


def test_execute_check_points(
    describe, stub_suite, stub_function_class, monkeypatch
):
    with describe('setup'):
        c = CheckPoints(suite=stub_suite)
        c.update_data_from_json({'min_points': 0.5})
        monkeypatch.setattr(
            helpers, 'ensure_on_test_server', stub_function_class()
        )
        stub_update_result = stub_function_class()
        cont = object()

    def step(p):
        inst = c.get_instructions()
        return c.execute_step(cont, stub_update_result, inst, p)

    with describe('achieved more than min_points should return 0'):
        r = step(0.6)
        assert r == 0
        last_update = stub_update_result.all_args[-1]
        assert last_update[0].name == 'passed'

    with describe('achieved exactly min_points should also return 0'):
        r = step(0.5)
        assert r == 0
        last_update = stub_update_result.all_args[-1]
        assert last_update[0].name == 'passed'

    with describe('achieved less than min_points should raise exception'):
        with pytest.raises(psef.exceptions.StopRunningStepsException):
            r = step(0.4)
        last_update = stub_update_result.all_args[-1]
        assert last_update[0].name == 'failed'
