#!/usr/bin/env python3

import json
import typing as t

from psef import app


class CustomJSONEncoder(json.JSONEncoder):
    """This JSON encoder is used to enable the JSON serialization of custom
    classes.

    Classes can define their serialization by implementing a `__to_json__`
    method.
    """

    def default(self, obj: t.Any) -> t.Any:
        """A way to serialize arbitrary methods to JSON.

        Classes can use this method by implementing a `__to_json__` method that
        should return a JSON serializable object.

        :param object obj: The object that should be converted to JSON.
        """
        try:
            return obj.__to_json__()
        except AttributeError:  # pragma: no cover
            return super().default(obj)


class CustomExtendedJSONEncoder(json.JSONEncoder):
    """This JSON encoder is used to enable the JSON serialization of custom
    classes.

    Classes can define their serialization by implementing a
    `__extended_to_json__` or a `__to_json__` method. This class first tries
    the extended method and if it does not exist it tries to normal one.
    """

    def default(self, obj: t.Any) -> t.Any:
        """A way to serialize arbitrary methods to JSON.

        Classes can use this method by implementing a `__to_json__` method that
        should return a JSON serializable object.

        :param object obj: The object that should be converted to JSON.
        """
        try:
            return obj.__extended_to_json__()
        except AttributeError:  # pragma: no cover
            try:
                return obj.__to_json__()
            except AttributeError:  # pragma: no cover
                return super().default(obj)


app.json_encoder = CustomJSONEncoder
