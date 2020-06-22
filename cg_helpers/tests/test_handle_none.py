from cg_helpers import handle_none


def test_with_none():
    assert handle_none(None, 5) == 5
    obj = object()
    assert handle_none(None, obj) is obj


def test_with_not_none():
    assert handle_none(5, 6) == 5
    obj1 = object()
    obj2 = object()
    assert handle_none(obj1, obj2) is obj1


def test_with_both_none():
    assert handle_none(None, None) is None
