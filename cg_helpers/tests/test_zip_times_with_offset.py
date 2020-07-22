import types
import pprint
import random

import pytest

from cg_helpers import zip_times_with_offset


def test_zip_times_with_offset():
    res = zip_times_with_offset(list(range(8)), 4, lambda x: x)
    assert isinstance(res, types.GeneratorType)
    assert list(res) == [
        (0, 1, 2, 3),
        (1, 2, 3, 4),
        (2, 3, 4, 5),
        (3, 4, 5, 6),
        (4, 5, 6, 7),
        (5, 6, 7, 0),
        (6, 7, 0, 1),
        (7, 0, 1, 2),
    ]


def test_with_offset_per_item():
    res = zip_times_with_offset(list(range(10)), 4, lambda x: 4 * x)
    assert isinstance(res, types.GeneratorType)
    assert list(res) == [
        (0, 4, 8, 2),
        (1, 5, 9, 3),
        (2, 6, 0, 4),
        (3, 7, 1, 5),
        (4, 8, 2, 6),
        (5, 9, 3, 7),
        (6, 0, 4, 8),
        (7, 1, 5, 9),
        (8, 2, 6, 0),
        (9, 3, 7, 1),
    ]


@pytest.mark.parametrize('range_len', list(range(10, 100)))
def test_with_increasing_offset_per_item(range_len):
    amount = 4

    res = zip_times_with_offset(
        list(range(range_len)), amount, lambda x: x ** 2
    )
    assert isinstance(res, types.GeneratorType)
    res_list = list(res)

    for items in res_list:
        assert len(items) == len(set(items)), f'{items} contains duplicates'

    for row in zip(*res_list):
        assert len(row) == len(set(row)) == range_len


def test_zip_times_with_offset_small_list():
    res = zip_times_with_offset(list(range(2)), 4, lambda x: x * 3)
    assert isinstance(res, types.GeneratorType)
    assert list(res) == [
        (0, 1, 0, 1),
        (1, 0, 1, 0),
    ]


def test_with_amount_smaller_than_or_eq_0():
    with pytest.raises(TypeError):
        list(zip_times_with_offset([1, 2], 0, lambda _: 1))

    with pytest.raises(TypeError):
        list(zip_times_with_offset([1, 2], -1, lambda _: 1))
