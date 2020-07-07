from cg_helpers import flatten


def test_simple_case():
    res = flatten([[1, 2], [5, 6], [10, 7]])
    assert isinstance(res, list)
    assert res == [1, 2, 5, 6, 10, 7]


def test_with_iter():
    res = flatten(iter([[1, 2], [5, 6], [10, 7]]))
    assert isinstance(res, list)
    assert res == [1, 2, 5, 6, 10, 7]

def test_with_nested_list():
    res = flatten([[[1, 2], [5, 6]], [10, 7]])
    assert isinstance(res, list)
    assert res == [[1, 2], [5, 6], 10, 7]
