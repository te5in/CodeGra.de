import pytest

from cg_signals import Signal


def fun1():
    pass


def connect_fun1(sig):
    was_connected = sig.is_connected(fun1)
    sig.connect_immediate(fun1)
    return was_connected


def test_immediate():
    signal = Signal('MY_NAME')
    assert 'MY_NAME' in repr(signal)

    # Can send without listeners
    signal.send('5')

    found = []

    def handler(obj):
        found.append(obj)

    signal.connect_immediate(handler)

    to_send = object()
    signal.send(to_send)

    # Should be called once and with the exact same argument
    assert len(found) == 1
    assert found[0] is to_send

    # New send should use the new object
    to_send_2 = object()
    signal.send(to_send_2)
    assert len(found) == 2
    assert found[1] is to_send_2


def test_connecting_multiple_times():
    signal = Signal('MY_NAME')

    def fun1(_):
        pass

    def fun2(_):
        pass

    not signal.is_connected(fun1)
    signal.connect_immediate(fun1)
    # Can connect multiple
    signal.connect_immediate(fun2)

    assert len(list(signal.get_listners())) == 2
    assert any(name.endswith('.fun1') for name in signal.get_listners())
    assert any(name.endswith('.fun2') for name in signal.get_listners())

    with pytest.raises(AssertionError):
        # Cannot connect functions twice
        signal.connect_immediate(fun1)

    assert len(list(signal.get_listners())) == 2

    def fun1(_):
        pass

    with pytest.raises(AssertionError):
        # Cannot connect redefinition of function
        signal.connect_immediate(fun1)

    signal.is_connected(fun1)

    # Can connect function with same name defined in another scope
    was_connected = connect_fun1(signal)
    assert not was_connected


def test_disconnect():
    signal = Signal('MY_NAME')

    found = []

    def handler(obj):
        found.append(obj)

    signal.connect_immediate(handler)
    assert signal.is_connected(handler)

    to_send = object()
    signal.send(to_send)

    # Should be called once and with the exact same argument
    assert len(found) == 1
    assert found[0] is to_send

    signal.disconnect(handler)

    signal.send('6')
    assert len(found) == 1
    assert '6' not in found
