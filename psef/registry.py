import typing as t

from .helpers import register

if t.TYPE_CHECKING and not getattr(t, 'SPHINX', False):  # pragma: no cover
    from .models import AutoTestStepBase

Register = register.Register

auto_test_handlers: Register[str, t.Type['AutoTestStepBase']] = Register()
