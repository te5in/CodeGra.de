"""This module is a central place to define registers to prevent circular
imports.

SPDX-License-Identifier: AGPL-3.0-only
"""
import typing as t

from .helpers import register

if t.TYPE_CHECKING and not getattr(t, 'SPHINX', False):  # pragma: no cover
    # pylint: disable=unused-import
    from .models import AutoTestStepBase, RubricItem, WebhookBase
    from .models.rubric import RubricRowBase
    from .models.auto_test import GradeCalculator

Register = register.Register

auto_test_handlers: Register[str, t.Type['AutoTestStepBase']] = Register()

auto_test_grade_calculators: Register[str, 'GradeCalculator'] = Register()

webhook_handlers: Register[str, t.Type['WebhookBase']] = Register()

rubric_row_types: Register[str, t.Type['RubricRowBase']] = Register()
