import cg_cache.intra_request as c


def test_cache_default_key(app):
    lst = []

    @c.cache_within_request
    def fun(a, b, c):
        lst.append((a, b, c))
        return sum([a, b, c])

    with app.app_context():
        assert fun(1, 2, 3) == 6
        # This should be cached.
        assert fun(1, 2, 3) == 6
        assert fun(1, 2, 4) == 7
        assert lst == [(1, 2, 3), (1, 2, 4)]


def test_make_key(app):
    lst = []
    key = 1
    res = 2
    orig_res = res

    @c.cache_within_request_make_key(lambda _: key)
    def fun(a):
        lst.append(a)
        return res

    with app.app_context():
        assert fun('anything') == res
        assert len(lst) == 1

        # This should be cached
        res = 4
        assert fun('anything') == orig_res
        assert len(lst) == 1

        # This should not be cached
        key = object()
        assert fun('anything') == res
        assert len(lst) == 2


def test_outside_app():
    res = []
    fun = c.cache_within_request(lambda: res.append('Hello'))

    fun()
    assert res == ['Hello']

    fun()
    assert res == ['Hello', 'Hello']


def test_cache_in_cls(app):
    lst = []
    lst2 = []

    class A:
        def __init__(self, a):
            self.a = a

        @c.cache_within_request_make_key(lambda self: self.a)
        def calc(self):
            lst.append(self)
            return self

        @c.cache_within_request
        def calc2(self):
            lst2.append(self)
            return self

    with app.app_context():
        a1 = A('same')
        a2 = A('same')
        a3 = A('other')
        assert a1 is not a2

        assert a1.calc() is a1
        assert a1.calc2() is a1
        assert len(lst) == 1
        assert len(lst2) == 1

        # The return value is a1 as this is cached
        assert a2.calc() is a1
        # This should be cached based on `self`
        assert a2.calc2() is a2
        assert len(lst) == 1
        assert len(lst2) == 2

        # Second call should be cached
        assert a2.calc2() is a2
        assert len(lst2) == 2

        # This should not be cached
        assert a3.calc() is a3
        assert len(lst) == 2


def test_with_object_id(app):
    amount_called = 0

    class ObjectWithId:
        def __init__(self, id, number):
            self.id = id
            self.number = number

        def __hash__(self):
            return self.number

        @c.cache_for_object_id
        def get_self(self):
            nonlocal amount_called
            amount_called += 1
            return self

    obj1 = ObjectWithId(1, 5)
    obj2 = ObjectWithId(2, 5)
    obj3 = ObjectWithId(1, 10)

    with app.app_context():
        assert obj1.get_self() is obj1
        assert amount_called == 1
        assert obj2.get_self() is obj2
        assert amount_called == 2
        assert obj3.get_self() is obj1
        assert amount_called == 2

        obj3.get_self.clear_cache()

        assert obj3.get_self() is obj3
        assert obj2.get_self() is obj2
        assert obj1.get_self() is obj3
        assert amount_called == 4
