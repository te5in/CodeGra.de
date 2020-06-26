import types

from cg_helpers import remove_duplicates


def test_without_duplicates():
    res = remove_duplicates(range(10), lambda x: x)
    assert isinstance(res, types.GeneratorType)
    assert list(res) == list(range(10))


def test_with_duplicates():
    assert list(
        remove_duplicates(list(range(10)) + list(range(10)), lambda x: x)
    ) == list(range(10))


def test_with_constant_key_function():
    assert list(remove_duplicates(range(10), lambda x: 1)) == [0]
