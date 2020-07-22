from cg_helpers import maybe_wrap_in_list


def test_not_a_list():
    assert maybe_wrap_in_list(5) == [5]

    # Items are not mutated or copied
    item = object()
    assert maybe_wrap_in_list(item)[0] is item

    # Dicts and tuples are not lists
    assert maybe_wrap_in_list({5: 5}) == [{5: 5}]
    assert maybe_wrap_in_list((1, 2)) == [(1, 2)]


def test_a_list():
    assert maybe_wrap_in_list([5]) == [5]

    # Lists are not mutated or copied
    lst_item = [object()]
    assert maybe_wrap_in_list(lst_item) is lst_item
    assert len(lst_item) == 1


def test_list_subclass():
    class my_list(list):
        pass

    obj = my_list(['5'])
    assert maybe_wrap_in_list(obj) is obj
