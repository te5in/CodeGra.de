"""This file implements parsing LTI 1.3 roles.

For LTI 1.3 there are two types of roles:

    1. *Context Roles*: These are the roles a user has within a specific
       context. The context for CodeGrade is always a course. So these roles
       map to CodeGrade course roles.

    2. *System Roles*: These are the roles a user has within the system. These
       roles map to CodeGrade user roles (i.e. global roles).

SPDX-License-Identifier: AGPL-3.0-only
"""
import abc
import typing as t
import itertools

from typing_extensions import Final

from ... import current_app
from ...helpers import contains_duplicate

T_ROLE = t.TypeVar('T_ROLE', bound='AbstractRole[str]')  # pylint: disable=invalid-name
IMS_LIS: Final = 'http://purl.imsglobal.org/vocab/lis/v2'

T = t.TypeVar('T')


class AbstractRole(abc.ABC, t.Generic[T]):
    """This class defines the base for an parsed LTI 1.3 role.

    To implement a new role you simply need to override the ``_LOOKUP``
    variable. This variable should contain a mapping between the role inside
    CodeGrade and a collection of LTI roles. An LTI role ``X`` is parsed to the
    CodeGrade role ``Y`` if and only if ``Y in _LOOKUP[X]``.

    So you might be wondering why this class is generic. This is to allow
    parsing of unmapped context roles. See
    :meth:`.ContextRole.get_unmapped_roles` for more info.
    """
    _LOOKUP: t.Mapping[str, t.Set[str]]

    def __init__(self, *, name: str, codegrade_role_name: T) -> None:
        self._name = name
        self.codegrade_role_name = codegrade_role_name
        if current_app.do_sanity_checks:
            assert self._LOOKUP
            assert not contains_duplicate(
                itertools.chain(*self._LOOKUP.values()),
            ), (
                'Found duplicate LTI roles, each role may only be associated'
                ' with one CodeGrade role'
            )

    @property
    def full_name(self) -> str:
        """Get the full LTI name of this role.
        """
        return self._name

    @classmethod
    def parse(cls: t.Type[T_ROLE], role_str: str) -> t.Optional[T_ROLE]:
        """Parse the given LTI role string.

        :param role_str: The role string to parse.

        :returns: A parse role, with the generic parameter always bound to
                  ``str``.
        """
        for key, values in cls._LOOKUP.items():
            if role_str in values:
                return cls(name=role_str, codegrade_role_name=key)
        return None

    @classmethod
    def parse_roles(cls: t.Type[T_ROLE], roles: t.List[str]) -> t.List[T_ROLE]:
        """Parse a list of roles (also known as the LTI 1.3 roles claim).

        :param roles: The roles to parse.

        :returns: A list of roles that could be parsed. So if some roles in the
                  given ``roles`` list could not be parsed they are simply
                  dropped.
        """
        return [role for role in map(cls.parse, roles) if role is not None]

    @classmethod
    def codegrade_role_name_used(cls, name: str) -> bool:
        """Is the given name used for any known LTI role as CodeGrade role
        name.

        This is true if there is any role ``l`` for which
        ``l.codegrade_role_name == name``.

        :param name: The CodeGrade role name to check.
        """
        return name in cls._LOOKUP

    def __repr__(self) -> str:
        return '{0}.{1}(name={2!r}, codegrade_role_name={3!r})'.format(
            self.__class__.__module__,
            self.__class__.__name__,
            self.full_name,
            self.codegrade_role_name,
        )


# Pylint bug: https://github.com/PyCQA/pylint/issues/2822
class ContextRole(AbstractRole[T], t.Generic[T]):  # pylint: disable=unsubscriptable-object
    """This class represents a parsed context (i.e. course) role.
    """
    _BASE = f'{IMS_LIS}/membership'

    _LOOKUP = {
        # Not many LMSes use this role at the moment unfortunately
        'TA': {f'{_BASE}/Instructor#TeachingAssistant'},
        'Teacher':
            {
                # So some LMSes don't use the IMS prefix, so we allow roles
                # with and without prefix.
                'Instructor',
                'Administrator',
                f'{_BASE}#Instructor',
                f'{_BASE}#Administrator',
            },
        'Student':
            {
                'Learner',
                'Member',
                f'{_BASE}#Learner',
                f'{_BASE}#Member',
            },
        # It isn't really clear at the moment inside CodeGrade what a
        # 'Designer' should be allowed to do.
        # TODO: Figure out what a designer is inside LMSes.
        'Designer': {
            'ContentDeveloper',
            f'{_BASE}#ContentDeveloper',
        },
        # With LTI 1.3 we can also get the subject of a mentor, so if we were
        # ever to really do something with this role we should investigate
        # that.
        'Observer': {
            f'{_BASE}#Mentor',
            'Mentor',
        },
    }

    @classmethod
    def get_unmapped_roles(
        cls: t.Type['ContextRole[None]'], roles: t.Sequence[str]
    ) -> t.Sequence['ContextRole[None]']:
        """Get all the context roles which we cannot map to CodeGrade roles.

        :param roles: The roles to get the unmapped roles from.

        :returns: A list of parsed CodeGrade roles were the
                  ``codegrade_role_name`` is always ``None``. This filters out
                  any role in ``roles`` which we *can* parse successfully, and
                  more importantly: it removes any role that is not a context
                  roles according to the LTI 1.3 spec.
        """
        res = []
        for role in roles:
            if ContextRole[str].parse(role) is not None:
                continue
            elif role.startswith(cls._BASE):
                res.append(cls(
                    name=role,
                    codegrade_role_name=None,
                ))
            elif not role.startswith(IMS_LIS):
                # Bare roles should also be recognized as course roles
                # according to the LTI 1.3 spec.
                # https://www.imsglobal.org/spec/lti/v1p3/#lis-vocabulary-for-context-roles
                res.append(cls(name=role, codegrade_role_name=None))

        return res

    @property
    def stripped_name(self) -> str:
        """Get the LTI name of this role, without the IMS prefix.

        This is equal to ``full_name`` for bare roles.
        """
        fname = self.full_name
        if fname.startswith(self._BASE):
            # We add one to the length of the base to strip out the pound sign
            # or the slash that follows the base.
            return fname[len(self._BASE) + 1:]
        return fname


# Pylint bug: https://github.com/PyCQA/pylint/issues/2822
class SystemRole(AbstractRole[str]):  # pylint: disable=unsubscriptable-object
    """This class represents a system role.

    There is a difference in the LTI 1.3 spec between ``system`` and
    ``institution`` roles, however for CodeGrade this distinction is not really
    important.
    """
    _LOOKUP = {
        'Staff':
            {
                f'{IMS_LIS}/system/person#Administrator',
                f'{IMS_LIS}/system/person#SysAdmin',
                f'{IMS_LIS}/institution/person#SysAdmin',
                f'{IMS_LIS}/institution/person#Faculty',
                f'{IMS_LIS}/institution/person#Staff',
                f'{IMS_LIS}/institution/person#Instructor',
            },
        'Student':
            {
                f'{IMS_LIS}/system/person#User',
                f'{IMS_LIS}/institution/person#Student',
                f'{IMS_LIS}/institution/person#Learner',
                f'{IMS_LIS}/institution/person#Member',
                f'{IMS_LIS}/institution/person#ProspectiveStudent',
            },
        'Nobody':
            {
                f'{IMS_LIS}/system/person#None',
                f'{IMS_LIS}/institution/person#None',
                f'{IMS_LIS}/institution/person#Other',
            },
    }
