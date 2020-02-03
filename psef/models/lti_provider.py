"""This module defines all LTI models.

SPDX-License-Identifier: AGPL-3.0-only
"""

import abc
import uuid
import typing as t

import flask_jwt_extended as flask_jwt
from flask import current_app

import psef
from cg_sqlalchemy_helpers.mixins import TimestampMixin

from . import UUID_LENGTH, Base, db
from . import user as user_models
from . import _MyQuery
from .. import auth
from ..registry import lti_provider_handlers

if t.TYPE_CHECKING:  # pragma: no cover
    # pylint: disable=unused-import
    from .work import Work

_ALL_LTI_PROVIDERS = sorted(['lti1.1', 'lti1.3'])
lti_provider_handlers.set_possible_options(_ALL_LTI_PROVIDERS)


class LTIProviderBase(Base):
    """This class defines the handshake with an LTI

    :ivar ~.LTIProvider.key: The OAuth consumer key for this LTI provider.
    """
    __tablename__ = 'LTIProvider'
    id: str = db.Column('id', db.String(UUID_LENGTH), primary_key=True)
    _lti_provider_version: str = db.Column(
        'lti_provider_version',
        db.Enum(*_ALL_LTI_PROVIDERS, name='ltiproviderversion'),
        nullable=False,
        server_default='lti1.1'
    )

    __mapper_args__ = {
        'polymorphic_on': _lti_provider_version,
        'polymorphic_identity': 'non_existing',
    }

    def __init__(self) -> None:
        super().__init__(id=str(uuid.uuid4()))

    def find_user(self, lti_user_id: str) -> t.Optional['user_models.User']:
        user_link = db.session.query(UserLTIProvider).filter(
            UserLTIProvider.lti_user_id == lti_user_id,
            UserLTIProvider.lti_provider_id == self.id,
        ).first()
        if user_link is None:
            return None

        return user_link.user

    @property
    @abc.abstractmethod
    def lms_name(self) -> str:
        """The name of the LMS for this LTIProvider.

        :getter: Get the LMS name.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def delete_grade_for_submission(self, sub: 'Work') -> None:
        """Delete the grade for the given submission.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def passback_grade(self, sub: 'Work', initial: bool) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def supports_deadline(self) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    def supports_max_points(self) -> bool:
        raise NotImplementedError


@lti_provider_handlers.register_table
class LTI1p1Provider(LTIProviderBase):
    __mapper_args__ = {'polymorphic_identity': 'lti1.1'}
    key: str = db.Column('key', db.Unicode, unique=True, nullable=True)

    def __init__(self, key: str) -> None:
        super().__init__()
        self.key = key

    @property
    def lms_name(self) -> str:
        return self._lms_and_secret[0]

    def delete_grade_for_submission(self, sub: 'Work') -> None:
        """Delete the grade for the given submission.
        """
        if sub.assignment.lti_outcome_service_url is None:  # pragma: no cover
            return

        for user in sub.get_all_authors():
            sourcedid = sub.assignment.assignment_results[user.id].sourcedid
            if sourcedid is None:  # pragma: no cover
                continue

            self.lti_class.passback_grade(
                key=self.key,
                secret=self.secret,
                grade=None,
                initial=False,
                service_url=sub.assignment.lti_outcome_service_url,
                sourcedid=sourcedid,
                lti_points_possible=sub.assignment.lti_points_possible,
                submission=sub,
                host=current_app.config['EXTERNAL_URL'],
            )

    def passback_grade(self, sub: 'Work', initial: bool) -> None:
        """Passback the grade for a given submission to this lti provider.

        :param sub: The submission to passback.
        :param initial: If true no grade will be send, this is to make sure the
            ``created_at`` date is correct in the LMS. Not all providers
            actually do a passback when this is set to ``True``.
        :returns: Nothing.
        """
        if sub.assignment.lti_outcome_service_url is None:  # pragma: no cover
            return

        for user in sub.get_all_authors():
            sourcedid = sub.assignment.assignment_results[user.id].sourcedid
            if sourcedid is None:  # pragma: no cover
                continue

            self.lti_class.passback_grade(
                key=self.key,
                secret=self.secret,
                grade=sub.grade,
                initial=initial,
                service_url=sub.assignment.lti_outcome_service_url,
                sourcedid=sourcedid,
                lti_points_possible=sub.assignment.lti_points_possible,
                submission=sub,
                host=current_app.config['EXTERNAL_URL'],
            )

    @property
    def _lms_and_secret(self) -> t.Tuple[str, str]:
        """Return the OAuth consumer secret and the name of the LMS.
        """
        lms, _, sec = current_app.config['LTI_CONSUMER_KEY_SECRETS'][
            self.key].partition(':')
        assert lms and sec
        return lms, sec

    @property
    def secret(self) -> str:
        """The OAuth consumer secret for this LTIProvider.

        :getter: Get the OAuth secret.
        :setter: Impossible as all secrets are fixed during startup of
            codegra.de
        """
        return self._lms_and_secret[1]

    @property
    def lti_class(self) -> t.Type['psef.lti.v1_1.LTI']:
        """The name of the LTI class to be used for this LTIProvider.

        :getter: Get the LTI class name.
        :setter: Impossible as this is fixed during startup of CodeGrade.
        """
        lms = self.lms_name
        cls = psef.lti.v1_1.lti_classes.get(lms)
        if cls is None:
            raise psef.errors.APIException(
                'The requested LMS is not supported',
                f'The LMS "{lms}" is not supported',
                psef.errors.APICodes.INVALID_PARAM, 400
            )
        return cls

    def supports_deadline(self) -> bool:
        return self.lti_class.supports_deadline()

    def supports_max_points(self) -> bool:
        return self.lti_class.supports_max_points()


@lti_provider_handlers.register_table
class LTI1p3Provider(LTIProviderBase):
    __mapper_args__ = {'polymorphic_identity': 'lti1.3'}


lti_provider_handlers.freeze()


class UserLTIProvider(Base, TimestampMixin):
    __tablename__ = 'user_lti-provider'

    user_id = db.Column(
        'user_id', db.Integer, db.ForeignKey('User.id'), nullable=False
    )
    lti_provider_id = db.Column(
        'lti_provider_id',
        db.String(UUID_LENGTH),
        db.ForeignKey(LTIProviderBase.id),
        nullable=False
    )
    lti_user_id = db.Column(
        'lti_user_id', db.Unicode, nullable=False, index=True
    )

    __table_args__ = (
        # A user can only be connected once to an LTI Provider
        db.PrimaryKeyConstraint(user_id, lti_provider_id),
        # LTI user ids should be unique for a single LTI provider
        db.UniqueConstraint(lti_provider_id, lti_user_id),
    )

    lti_provider: 'LTIProviderBase' = db.relationship(
        LTIProviderBase,
        lazy='joined',
        foreign_keys=lti_provider_id,
    )

    user: 'user_models.User' = db.relationship(
        'User',
        lazy='joined',
        foreign_keys=user_id,
    )

    def __init__(
        self, user: 'user_models.User', lti_provider: LTIProviderBase,
        lti_user_id: str
    ) -> None:
        super().__init__()
        self.user = user
        self.lti_provider = lti_provider
        self.lti_user_id = lti_user_id

    @classmethod
    def user_is_linked(cls, user: 'user_models.User') -> bool:
        """Is the given user known in any LTIProvider
        """
        return psef.helpers.handle_none(
            db.session.query(
                db.session.query(cls).filter(
                    cls.user_id == user.id,
                ).exists()
            ).scalar(),
            False,
        )

    @classmethod
    def get_or_create_user(
        cls,
        lti_user_id: str,
        lti_provider: LTIProviderBase,
        wanted_username: str,
        full_name: str,
        email: str,
    ) -> t.Tuple['user_models.User', t.Optional[str]]:
        current_user = psef.current_user
        is_logged_in = auth.user_active(current_user)
        token = None
        user = None

        lti_user = lti_provider.find_user(lti_user_id=lti_user_id)

        if is_logged_in and lti_user is not None and current_user == lti_user:
            # The currently logged in user is now using LTI
            user = current_user
        elif lti_user is not None:
            # LTI users are used before the current logged user.
            token = flask_jwt.create_access_token(
                identity=lti_user.id,
                fresh=True,
            )
            user = lti_user
        elif is_logged_in and not cls.user_is_linked(current_user):
            # TODO show some sort of screen if this linking is wanted
            db.session.add(
                cls(
                    user=current_user,
                    lti_provider=lti_provider,
                    lti_user_id=lti_user_id,
                )
            )
            user = current_user
        else:
            # New LTI user id is found and no user is logged in or the current
            # user has a different LTI user id. A new user is created and
            # logged in.
            i = 0

            def _get_username() -> str:
                return wanted_username + (f' ({i})' if i > 0 else '')

            while db.session.query(
                user_models.User.query.filter_by(username=_get_username()
                                                 ).exists()
            ).scalar():  # pragma: no cover
                i += 1

            user = user_models.User(
                name=full_name,
                email=email,
                active=True,
                password=None,
                username=_get_username(),
            )
            db.session.add(user)
            db.session.add(
                cls(
                    user=user,
                    lti_provider=lti_provider,
                    lti_user_id=lti_user_id,
                )
            )
            db.session.flush()

            token = flask_jwt.create_access_token(
                identity=user.id,
                fresh=True,
            )

        return user, token
