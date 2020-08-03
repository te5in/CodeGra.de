import typing as t
from datetime import timedelta

from cryptography import x509
from werkzeug.utils import cached_property
from cryptography.x509.oid import NameOID
from onelogin.saml2.xml_utils import OneLogin_Saml2_XML
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from onelogin.saml2.idp_metadata_parser import OneLogin_Saml2_IdPMetadataParser
from cryptography.hazmat.primitives.asymmetric import rsa

import psef
from cg_helpers import on_not_none
from cg_dt_utils import DatetimeWithTimezone
from cg_sqlalchemy_helpers import UUIDType
from cg_sqlalchemy_helpers.mixins import UUIDMixin, TimestampMixin

from . import Base, db
from . import role as role_models
from . import user as user_models
from .. import current_app


# We are not allowed to subclass `Any`, but we do need a subclass here.
class _MetadataParser(OneLogin_Saml2_IdPMetadataParser):  # type: ignore[misc]
    @classmethod
    def parse_remote(cls, url: str, validate_cert: bool=True, entity_id: bool=None, **kwargs: t.Any) -> dict:
        idp_metadata = super().get_metadata(url, validate_cert)
        result = cls.parse(idp_metadata, entity_id=entity_id, **kwargs)
        dom = OneLogin_Saml2_XML.to_etree(idp_metadata)
        ns = {
            'mdui': psef.saml2.MDUI_NAMESPACE,
        }
        ui_info = dom.find('.//mdui:UIInfo', namespaces=ns)

        if ui_info is not None:

            def _get_if(node: t.Optional[t.Any]) -> t.Optional[str]:
                return on_not_none(node, OneLogin_Saml2_XML.element_text)

            name = ui_info.find("./mdui:DisplayName", namespaces=ns)

            description = ui_info.find('./mdui:Description', namespaces=ns)

            logo_node = ui_info.find('./mdui:Logo', namespaces=ns)

            logo = None
            if logo_node is not None:
                logo = {
                    'url': OneLogin_Saml2_XML.element_text(logo_node),
                    'height': int(logo_node.attrib['height']),
                    'width': int(logo_node.attrib['width']),
                }

            result['idp']['ui_info'] = {
                'name': _get_if(name),
                'description': _get_if(description),
                'logo': logo,
            }
        else:
            result['idp']['ui_info'] = {
                'name': None,
                'description': None,
                'logo': None,
            }

        return result


class Saml2Provider(Base, UUIDMixin, TimestampMixin):
    metadata_url = db.Column('metadata_url', db.Unicode, nullable=False)

    name = db.Column('name', db.Unicode, nullable=False)

    _cert_data = db.Column('cert_data', db.LargeBinary, nullable=False)

    _key_data = db.Column('key_data', db.LargeBinary, nullable=False)

    def __init__(self, metadata_url: str, name: str) -> None:
        super().__init__(metadata_url=metadata_url, name=name)
        self._generate_keys()

    def _generate_keys(self) -> None:
        key = rsa.generate_private_key(
            public_exponent=65537, key_size=2048, backend=default_backend()
        )
        now = DatetimeWithTimezone.utcnow()
        subject = issuer = x509.Name(
            [
                # Provide various details about who we are.
                x509.NameAttribute(
                    NameOID.ORGANIZATION_NAME,
                    'CodeGrade',
                ),
                x509.NameAttribute(
                    NameOID.COMMON_NAME,
                    current_app.config['EXTERNAL_DOMAIN'],
                ),
            ]
        )
        cert = x509.CertificateBuilder().subject_name(
            subject,
        ).issuer_name(
            issuer,
        ).public_key(
            key.public_key(),
        ).serial_number(
            x509.random_serial_number(),
        ).not_valid_before(
            DatetimeWithTimezone.as_datetime(now),
        ).not_valid_after(
            # TODO: We need to find a way to rotate these certificates. This
            # will however only become a problem in a few years. Should be
            # fixed **before** 2025.
            DatetimeWithTimezone.as_datetime(now + timedelta(days=365 * 5)),
        ).add_extension(
            x509.SubjectAlternativeName(
                [
                    # Describe what sites we want this certificate for.
                    x509.DNSName(current_app.config['EXTERNAL_DOMAIN']),
                ]
            ),
            critical=False,
            # Sign the CSR with our private key.
        ).sign(key, hashes.SHA256(), default_backend())

        self._cert_data = cert.public_bytes(serialization.Encoding.PEM)
        self._key_data = key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

    @property
    def public_x509_cert(self) -> str:
        cert = x509.load_pem_x509_certificate(
            self._cert_data, default_backend()
        )
        return cert.public_bytes(serialization.Encoding.PEM).decode('utf8')

    @property
    def private_key(self) -> str:
        assert self._key_data is not None
        key = serialization.load_pem_private_key(
            self._key_data, None, default_backend()
        )
        return key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode('utf8')

    def check_metadata_url(self) -> None:
        self._get_provider_metadata(force=True)

    def _get_provider_metadata(self, force: bool) -> dict:
        return current_app.inter_request_cache.saml2_ipds.get_or_set(
            str(self.id),
            lambda: _MetadataParser.parse_remote(
                self.metadata_url,
            )['idp'],
            force=force,
        )

    @cached_property
    def provider_metadata(self) -> dict:
        return self._get_provider_metadata(force=False)

    def __to_json__(self) -> t.Any:
        return {
            'id': self.id,
            'metadata_url': self.metadata_url,
            'ui_info':
                {
                    'name': self.name,
                    **self.provider_metadata['ui_info'],
                }
        }


class UserSamlProvider(Base, TimestampMixin):
    """This class connects a :class:`.user_models.User` to a
        :class:`.Saml2Provider`.

    This class makes sure that it is possible to have two users with the same
    name id, but from different IdPs. Each user can be linked to at most
    one IdP .
    """
    user_id = db.Column(
        'user_id', db.Integer, db.ForeignKey('User.id'), nullable=False
    )
    saml2_provider_id = db.Column(
        'saml2_provider_id',
        UUIDType,
        db.ForeignKey(Saml2Provider.id),
        nullable=False
    )
    #: The id of the user given to us by the IdP. Not globally unique!
    name_id = db.Column('name_id', db.Unicode, nullable=False, index=True)

    __table_args__ = (
        # A user can only be connected once to an LTI Provider
        db.PrimaryKeyConstraint(user_id, saml2_provider_id),
        # LTI user ids should be unique for a single LTI provider, however they
        # are NOT (!) globally unique between LMSes.
        db.UniqueConstraint(saml2_provider_id, name_id),
    )

    saml2_provider = db.relationship(
        Saml2Provider,
        lazy='joined',
        foreign_keys=saml2_provider_id,
    )

    user = db.relationship(
        lambda: user_models.User,
        lazy='joined',
        foreign_keys=user_id,
    )

    def __init__(
        self,
        user: 'user_models.User',
        saml2_provider: Saml2Provider,
        name_id: str,
    ) -> None:
        super().__init__(
            user_id=user.id,
            user=user,
            saml2_provider=saml2_provider,
            name_id=name_id,
        )

    @classmethod
    def get_or_create_user(
        cls, name_id: str, saml2_provider: Saml2Provider, username: str,
        full_name: str, email: str
    ) -> 'user_models.User':
        conn = cls.query.filter(
            cls.name_id == name_id, cls.saml2_provider == saml2_provider
        ).one_or_none()

        if conn is None:
            username = user_models.User.find_possible_username(username)
            role = role_models.Role.query.filter(
                role_models.Role.name == current_app.config['DEFAULT_SSO_ROLE']
            ).one()
            user = user_models.User(
                name=full_name,
                email=email,
                password=None,
                username=username,
                role=role,
            )
            db.session.add(user)

            conn = cls(
                user=user, saml2_provider=saml2_provider, name_id=name_id
            )
            db.session.add(conn)

            db.session.flush()
        else:
            user = conn.user
            user.email = email
            user.name = full_name

        return user
