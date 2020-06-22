import enum

import pytest

from cg_helpers import assert_never


def test_assert_never_raises_assertion_error():
    class MyEnum(enum.Enum):
        pass

    with pytest.raises(AssertionError) as err:
        assert_never(None, MyEnum)

    assert '"MyEnum"' in err.value.args[0]
    assert '"None"' in err.value.args[0]
