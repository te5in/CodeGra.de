"""This module contains constants for the claims used in LTI 1.3 messages.

SPDX-License-Identifier: AGPL-3.0-only
"""
from typing_extensions import Final

CONTEXT: Final = 'https://purl.imsglobal.org/spec/lti/claim/context'
CUSTOM: Final = 'https://purl.imsglobal.org/spec/lti/claim/custom'
ROLES: Final = 'https://purl.imsglobal.org/spec/lti/claim/roles'
RESOURCE: Final = 'https://purl.imsglobal.org/spec/lti/claim/resource_link'
NAMESROLES: Final = (
    'https://purl.imsglobal.org/spec/lti-nrps/claim/namesroleservice'
)
GRADES: Final = 'https://purl.imsglobal.org/spec/lti-ags/claim/endpoint'
DEEP_LINK: Final = (
    'https://purl.imsglobal.org/spec/lti-dl/claim/deep_linking_settings'
)
