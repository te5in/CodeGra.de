"""This module defines all LTI models.

SPDX-License-Identifier: AGPL-3.0-only
"""

import uuid
import typing as t

from flask import current_app

import psef

from . import UUID_LENGTH, Base, db, _MyQuery

if t.TYPE_CHECKING:  # pragma: no cover
    # pylint: disable=unused-import
    from .work import Work


class LTIProvider(Base):
    """This class defines the handshake with an LTI

    :ivar ~.LTIProvider.key: The OAuth consumer key for this LTI provider.
    """
    if t.TYPE_CHECKING:  # pragma: no cover
        query: t.ClassVar[_MyQuery['LTIProvider']] = Base.query
    __tablename__ = 'LTIProvider'
    id = db.Column('id', db.String(UUID_LENGTH), primary_key=True)
    key = db.Column('key', db.Unicode, unique=True, nullable=False)

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

    def __init__(self, key: str) -> None:
        super().__init__(key=key)
        public_id = str(uuid.uuid4())

        while db.session.query(
            LTIProvider.query.filter_by(id=public_id).exists()
        ).scalar():  # pragma: no cover
            public_id = str(uuid.uuid4())

        self.id = public_id

    @property
    def _lms_and_secret(self) -> t.Tuple[str, str]:
        """Return the OAuth consumer secret and the name of the LMS.
        """
        lms, _, sec = current_app.config['LTI_CONSUMER_KEY_SECRETS'][
            self.key].partition(':')
        assert lms and sec
        return lms, sec

    @property
    def lms_name(self) -> str:
        """The name of the LMS for this LTIProvider.

        :getter: Get the LMS name.
        :setter: Impossible as this is fixed during startup of CodeGrade.
        """
        return self._lms_and_secret[0]

    @property
    def secret(self) -> str:
        """The OAuth consumer secret for this LTIProvider.

        :getter: Get the OAuth secret.
        :setter: Impossible as all secrets are fixed during startup of
            codegra.de
        """
        return self._lms_and_secret[1]

    @property
    def lti_class(self) -> t.Type['psef.lti.LTI']:
        """The name of the LTI class to be used for this LTIProvider.

        :getter: Get the LTI class name.
        :setter: Impossible as this is fixed during startup of CodeGrade.
        """
        lms = self.lms_name
        cls = psef.lti.lti_classes.get(lms)
        if cls is None:
            raise psef.errors.APIException(
                'The requested LMS is not supported',
                f'The LMS "{lms}" is not supported',
                psef.errors.APICodes.INVALID_PARAM, 400
            )
        return cls
