from cg_helpers import on_not_none


def test_with_none():
    obj1 = object()
    assert on_not_none(None, lambda x: x[0]) is None


def test_with_not_none():
    obj1 = object()
    assert on_not_none([obj1], lambda x: x[0]) is obj1
