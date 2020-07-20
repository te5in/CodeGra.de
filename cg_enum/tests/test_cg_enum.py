import flask
import pytest

from cg_enum import CGEnum
from cg_json import JSONResponse


def test_is_method():
    class Enum(CGEnum):
        b = 1
        c = 2

    assert Enum.c.is_c is True
    assert Enum.c.is_b is False

    with pytest.raises(AttributeError):
        Enum.c.is_e

    with pytest.raises(AttributeError):
        Enum.c.not_a_prop


def test_jsonify():
    class Enum(CGEnum):
        name_a = 2
        name_b = 3

    with flask.Flask(__name__).app_context():
        assert JSONResponse.dump_to_object(Enum.name_a) == 'name_a'
        assert JSONResponse.dump_to_object(Enum.name_b) == 'name_b'
