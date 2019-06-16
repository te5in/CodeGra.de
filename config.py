import os
import json
import typing as t
import datetime
import tempfile
import warnings
import subprocess
from configparser import ConfigParser

from mypy_extensions import TypedDict

config_file = os.getenv('CODEGRADE_CONFIG_FILE', 'config.ini')

CONFIG: t.Dict[str, t.Any] = dict()
CONFIG['BASE_DIR'] = os.path.dirname(os.path.abspath(__file__))

os.environ['BASE_DIR'] = str(CONFIG['BASE_DIR'])

parser = ConfigParser(os.environ)
parser.read(config_file)

if 'Back-end' not in parser:
    parser['Back-end'] = {}
if 'Features' not in parser:
    parser['Features'] = {}
if 'AutoTest' not in parser:
    parser['AutoTest'] = {}

backend_ops = parser['Back-end']
feature_ops = parser['Features']
auto_test_ops = parser['AutoTest']


class CeleryConfig(TypedDict, total=True):
    pass


if t.TYPE_CHECKING and getattr(
    t, 'SPHINX', False
) is not True:  # pragma: no cover
    import psef.features
    import psef.auto_test

AutoTestConfig = TypedDict(
    'AutoTestConfig', {
        'password': str,
        'container_url': t.Optional[str],
    }
)
AutoTestHosts = t.Mapping[str, AutoTestConfig]

FlaskConfig = TypedDict(
    'FlaskConfig', {
        'FEATURES': t.Mapping['psef.features.Feature', bool],
        '__S_FEATURES': t.Mapping[str, bool],
        'IS_AUTO_TEST_RUNNER': bool,
        'AUTO_TEST_HOSTS': AutoTestHosts,
        'AUTO_TEST_PASSWORD': str,
        'AUTO_TEST_DISABLE_ORIGIN_CHECK': bool,
        'AUTO_TEST_MAX_TIME_COMMAND': int,
        'AUTO_TEST_MAX_TIME_TOTAL_RUN': int,
        'AUTO_TEST_POLL_TIME': int,
        'AUTO_TEST_OUTPUT_LIMIT': int,
        'AUTO_TEST_MEMORY_LIMIT': str,
        'AUTO_TEST_BDEVTYPE': str,
        'AUTO_TEST_HEARTBEAT_INTERVAL': int,
        'AUTO_TEST_HEARTBEAT_MAX_MISSED': int,
        'AUTO_TEST_TEMPLATE_CONTAINER': str,
        'AUTO_TEST_BROKER_URL': str,
        'AUTO_TEST_BROKER_PASSWORD': str,
        '__S_AUTO_TEST_HOSTS': t.Mapping[str, t.Any],
        'Celery': CeleryConfig,
        'LTI Consumer keys': t.Mapping[str, str],
        'DEBUG': bool,
        'SQLALCHEMY_DATABASE_URI': str,
        'SECRET_KEY': str,
        'LTI_SECRET_KEY': str,
        'HEALTH_KEY': None,
        'JWT_ACCESS_TOKEN_EXPIRES': int,
        'UPLOAD_DIR': str,
        'MIRROR_UPLOAD_DIR': str,
        'SHARED_TEMP_DIR': str,
        'MAX_NUMBER_OF_FILES': int,
        'MAX_FILE_SIZE': int,
        'MAX_NORMAL_UPLOAD_SIZE': int,
        'MAX_LARGE_UPLOAD_SIZE': int,
        'DEFAULT_ROLE': str,
        'EXTERNAL_URL': str,
        'JAVA_PATH': str,
        'JPLAG_JAR': str,
        'MAIL_SERVER': str,
        'MAIL_PORT': int,
        'MAIL_USE_TLS': bool,
        'MAIL_USE_SSL': bool,
        'MAIL_USERNAME': str,
        'MAIL_PASSWORD': str,
        'MAIL_DEFAULT_SENDER': str,
        'MAIL_MAX_EMAILS': int,
        'RESET_TOKEN_TIME': int,
        'EMAIL_TEMPLATE': str,
        'REMINDER_TEMPLATE': str,
        'GRADER_STATUS_TEMPLATE': str,
        'DONE_TEMPLATE': str,
        'MIN_PASSWORD_SCORE': int,
        'CHECKSTYLE_PROGRAM': t.List[str],
        'PMD_PROGRAM': t.List[str],
        'PYLINT_PROGRAM': t.List[str],
        'FLAKE8_PROGRAM': t.List[str],
        '_USING_SQLITE': str,
        '_TRANSIP_PRIVATE_KEY_FILE': str,
        '_TRANSIP_USERNAME': str,
    },
    total=True
)


def ensure_between(
    option: str,
    val: t.Union[int, float],
    min: t.Union[int, float, None],
    max: t.Union[int, float, None],
) -> None:
    if (min is not None and val < min) or (max is not None and val > max):
        raise ValueError(
            f'Value of setting {option} must be between {min} and {max} (inclusive)',
        )


def set_bool(
    out: t.MutableMapping[str, t.Any],
    parser: t.Any,
    item: str,
    default: bool,
) -> None:
    val = parser.getboolean(item)
    out[item] = bool(default if val is None else val)


def set_float(
    out: t.MutableMapping[str, t.Any],
    parser: t.Any,
    item: str,
    default: float,
    min: float = None,
    max: float = None,
) -> None:
    val = parser.getfloat(item)
    val = float(default if val is None else val)
    ensure_between(item, val, min, max)
    out[item] = val


def set_int(
    out: t.MutableMapping[str, t.Any],
    parser: t.Any,
    item: str,
    default: int,
    min: int = None,
    max: int = None,
) -> None:
    val = parser.getint(item)
    val = int(default if val is None else val)
    ensure_between(item, val, min, max)
    out[item] = val


def set_str(
    out: t.MutableMapping[str, t.Any],
    parser: t.Any,
    item: str,
    default: object,
) -> None:
    val = parser.get(item)
    out[item] = default if val is None else str(val)


def set_list(
    out: t.MutableMapping[str, t.Any],
    parser: t.Any,
    item: str,
    default: object,
) -> None:
    val = parser.get(item)
    if val is None:
        out[item] = default
    else:
        parsed_val = json.loads(val)
        assert isinstance(parsed_val, list), f'Value "{item}" should be a list'
        assert all(isinstance(v, str) for v in parsed_val)
        out[item] = parsed_val


def set_dict(
    out: t.MutableMapping[str, t.Any],
    parser: t.Any,
    item: str,
    default: object,
) -> None:
    val = parser.get(item)
    if val is None:
        out[item] = default
    else:
        parsed_val = json.loads(val)
        assert isinstance(parsed_val, dict), f'Value "{item}" should be a list'
        out[item] = parsed_val


set_bool(CONFIG, backend_ops, 'DEBUG', False)

# Define the database. If `CODEGRADE_DATABASE_URL` is found in the enviroment
# variables it is used. The string should be in this format for postgresql:
# `postgresql://dbusername:dbpassword@dbhost/dbname`
set_str(
    CONFIG, backend_ops, 'SQLALCHEMY_DATABASE_URI',
    os.getenv('SQLALCHEMY_DATABASE_URI', 'postgresql:///codegrade_dev')
)
CONFIG['_USING_SQLITE'] = CONFIG['SQLALCHEMY_DATABASE_URI'].startswith(
    'sqlite'
)
CONFIG['DATABASE_CONNECT_OPTIONS'] = {}

# Secret key for signing JWT tokens.
set_str(
    CONFIG,
    backend_ops,
    'SECRET_KEY',
    (
        'secret'
        if CONFIG['DEBUG'] else os.environ.get('CODEGRADE_JWT_SECRET_KEY')
    ),
)

# This should be a strong random key that is not public.
set_str(
    CONFIG,
    backend_ops,
    'LTI_SECRET_KEY',
    (
        'hunter123'
        if CONFIG['DEBUG'] else os.environ.get('CODEGRADE_LTI_SECRET_KEY')
    ),
)

set_str(CONFIG, backend_ops, 'HEALTH_KEY', None)
if CONFIG['HEALTH_KEY'] is None:
    warnings.warn('No "health_key" provided, disabling health route.')

CONFIG['JWT_ALGORITHM'] = 'HS512'

set_float(CONFIG, backend_ops, 'JWT_ACCESS_TOKEN_EXPIRES', 30)
CONFIG['JWT_ACCESS_TOKEN_EXPIRES'] = datetime.timedelta(
    days=CONFIG['JWT_ACCESS_TOKEN_EXPIRES']
)

# Path for storage of uploaded files.
# WARNING: Make sure these directories exist.
set_str(
    CONFIG, backend_ops, 'UPLOAD_DIR',
    os.path.join(CONFIG['BASE_DIR'], 'uploads')
)
if not os.path.isdir(CONFIG['UPLOAD_DIR']):
    warnings.warn(
        f'The given uploads directory "{CONFIG["UPLOAD_DIR"]}" does not exist',
    )

set_str(
    CONFIG, backend_ops, 'MIRROR_UPLOAD_DIR',
    os.path.join(CONFIG['BASE_DIR'], 'mirror_uploads')
)
if not os.path.isdir(CONFIG['MIRROR_UPLOAD_DIR']):
    warnings.warn(
        f'The given uploads directory "{CONFIG["MIRROR_UPLOAD_DIR"]}"'
        ' does not exist',
    )

set_str(CONFIG, backend_ops, 'SHARED_TEMP_DIR', tempfile.gettempdir())
if not os.path.isdir(CONFIG['SHARED_TEMP_DIR']):
    warnings.warn(
        f'The given shared temp dir "{CONFIG["SHARED_TEMP_DIR"]}"'
        ' does not exist'
    )

# Maximum size in bytes for single upload request
set_int(CONFIG, backend_ops, 'MAX_FILE_SIZE', 50 * 2 ** 20)  # default: 50MB
set_int(
    CONFIG, backend_ops, 'MAX_NORMAL_UPLOAD_SIZE', 64 * 2 ** 20
)  # default: 64MB
set_int(
    CONFIG, backend_ops, 'MAX_LARGE_UPLOAD_SIZE', 128 * 2 ** 20
)  # default: 128MB
set_int(CONFIG, backend_ops, 'MAX_NUMBER_OF_FILES', 1 << 16)

with open(
    os.path.join(CONFIG['BASE_DIR'], 'seed_data', 'course_roles.json'), 'r'
) as f:
    CONFIG['_DEFAULT_COURSE_ROLES'] = json.load(f)

# The default site role a user should get. The name of this role should be
# present as a key in `seed_data/roles.json`.
set_str(CONFIG, backend_ops, 'DEFAULT_ROLE', 'Student')

# The external URL the server runs on.
set_str(CONFIG, backend_ops, 'EXTERNAL_URL', 'http://localhost:8080')

set_str(CONFIG, backend_ops, 'JAVA_PATH', 'java')

set_str(CONFIG, backend_ops, 'JPLAG_JAR', 'jplag.jar')


def _set_version() -> None:
    CONFIG['_VERSION'] = subprocess.check_output(
        ['git', 'describe', '--abbrev=0', '--tags']
    ).decode('utf-8').strip()


try:
    _set_version()
except subprocess.CalledProcessError as e:
    print(
        'An error occurred trying to get the version, this is probably caused'
        ' by not deep cloning the repository. We will try that now.'
    )
    subprocess.check_call(['git', 'fetch', '--unshallow'])
    _set_version()
del _set_version

# Set email settings
set_str(CONFIG, backend_ops, 'MAIL_SERVER', 'localhost')
set_int(CONFIG, backend_ops, 'MAIL_PORT', 25)
set_bool(CONFIG, backend_ops, 'MAIL_USE_TLS', False)
set_bool(CONFIG, backend_ops, 'MAIL_USE_SSL', False)
set_str(CONFIG, backend_ops, 'MAIL_USERNAME', 'noreply')
set_str(CONFIG, backend_ops, 'MAIL_PASSWORD', 'nopasswd')
set_str(CONFIG, backend_ops, 'MAIL_DEFAULT_SENDER', 'noreply')
set_int(CONFIG, backend_ops, 'MAIL_MAX_EMAILS', 100)
set_int(CONFIG, backend_ops, 'RESET_TOKEN_TIME', 86400)
set_str(
    CONFIG,
    backend_ops,
    'EMAIL_TEMPLATE',
    """
<p>Dear {user_name},

This email lets you reset your password on <a
href="{site_url}">{site_url}</a>. If you go to <a href="{url}">this page</a>
you can reset your password there. Please do not reply to this email.

If you have not triggered this action please ignore this email.</p>
    """.strip(),
)
set_str(
    CONFIG,
    backend_ops,
    'REMINDER_TEMPLATE',
    """
<p>Dear {user_name},

This email is a reminder that you have work left to grade on the assignment
"{assig_name}" on <a href="{site_url}">{site_url}</a>. If you go to <a
href="{site_url}/courses/{course_id}/assignments/{assig_id}/submissions">this
page</a> you can directly continue grading, which of course is joyful business
on CodeGrade! Good luck with grading.

This email was automatically sent because of reminder that was set for this
assignment and you have not yet indicated you were done grading. You can
indicate this <a href="{site_url}/courses/{course_id}">here</a>.</p>
    """.strip(),
)
set_str(
    CONFIG,
    backend_ops,
    'GRADER_STATUS_TEMPLATE',
    """
<p>Dear {user_name},

This email is a reminder that your grade status has been reset to 'not done'
for "{assig_name}" on <a href="{site_url}">{site_url}</a>. If you go to <a
href="{site_url}/courses/{course_id}/assignments/{assig_id}/submissions">this
page</a> you can directly continue grading, which of course is joyful business
on CodeGrade! Good luck with grading.

This email was automatically sent. The reason for this can be that a course
admin has reset your status or that you have been assigned new
submission(s).</p>
    """.strip(),
)
set_str(
    CONFIG, backend_ops, 'DONE_TEMPLATE', """
<p>Dear,

This email has been sent to let you know that all work has been graded on the
assignment "{assig_name}" on <a href="{site_url}">{site_url}</a>. If you go to
<a href="{site_url}/courses/{course_id}">this page</a> you can set the state of
the assignment to 'done' so that the students can see their grade!

This email was automatically sent because of reminder that was set for this
assignment. You can change these settings <a
href="{site_url}/courses/{course_id}">here</a>.</p>
        """.strip()
)

set_float(CONFIG, backend_ops, 'MIN_PASSWORD_SCORE', 3, min=0, max=4)

set_list(
    CONFIG, backend_ops, 'CHECKSTYLE_PROGRAM', [
        'java',
        '-Dbasedir={files}',
        '-jar',
        'checkstyle.jar',
        '-f',
        'xml',
        '-c',
        '{config}',
        '{files}',
    ]
)
set_list(
    CONFIG, backend_ops, 'PMD_PROGRAM', [
        './pmd/bin/run.sh',
        'pmd',
        '-dir',
        '{files}',
        '-failOnViolation',
        'false',
        '-format',
        'csv',
        '-shortnames',
        '-rulesets',
        '{config}',
    ]
)
set_list(
    CONFIG, backend_ops, 'PYLINT_PROGRAM', [
        'pylint',
        '--rcfile',
        '{config}',
        '--output-format',
        'json',
        '{files}',
    ]
)
set_list(
    CONFIG, backend_ops, 'FLAKE8_PROGRAM', [
        'flake8',
        '--disable-noqa',
        '--config={config}',
        '--format',
        '{line_fmt}',
        '--exit-zero',
        '{files}',
    ]
)

set_str(CONFIG, backend_ops, '_TRANSIP_PRIVATE_KEY_FILE', '')
set_str(CONFIG, backend_ops, '_TRANSIP_USERNAME', '')

############
# FEATURES #
############
CONFIG['__S_FEATURES'] = {}
# This section contains all features, please do not add, remove or edit any
# keys, the values however can and should be edited. A truth value enables the
# given feature. Please do not add or remove any keys.

# Should any user be able to upload blackboard zips. If this is enabled
# sometimes the username can collide with another user, meaning work is
# uploaded for the wrong user. This option is UNSAFE to enable when working
# on a multiple school instance.
set_bool(CONFIG['__S_FEATURES'], feature_ops, 'BLACKBOARD_ZIP_UPLOAD', True)

# Should rubrics be enabled. This means rubrics can be created by teachers
# and used for grading purposes.
set_bool(CONFIG['__S_FEATURES'], feature_ops, 'RUBRICS', True)

# Should we automatically create a default role for LTI launches with roles
# that are not known.
set_bool(CONFIG['__S_FEATURES'], feature_ops, 'AUTOMATIC_LTI_ROLE', True)

# Should LTI be enabled.
set_bool(CONFIG['__S_FEATURES'], feature_ops, 'LTI', True)

# Should linters be enabled.
set_bool(CONFIG['__S_FEATURES'], feature_ops, 'LINTERS', True)

# Should incremental rubric submission be enabled.
set_bool(
    CONFIG['__S_FEATURES'], feature_ops, 'INCREMENTAL_RUBRIC_SUBMISSION', True
)

# Should it be possible to register
set_bool(CONFIG['__S_FEATURES'], feature_ops, 'REGISTER', False)

set_bool(CONFIG['__S_FEATURES'], feature_ops, 'GROUPS', False)

set_bool(CONFIG['__S_FEATURES'], feature_ops, 'AUTO_TEST', False)

############
# LTI keys #
############
# All LTI consumer keys mapped to secret keys. Please add your own.
lti_parser = ConfigParser()
lti_parser.optionxform = str  # type: ignore
if lti_parser.read(config_file) and 'LTI Consumer keys' in lti_parser:
    CONFIG['LTI_CONSUMER_KEY_SECRETS'] = dict(lti_parser['LTI Consumer keys'])
else:
    CONFIG['LTI_CONSUMER_KEY_SECRETS'] = {}

##########
# CELERY #
##########
celery_parser = ConfigParser()
celery_parser.optionxform = str  # type: ignore
if celery_parser.read(config_file) and 'Celery' in celery_parser:
    CONFIG['CELERY_CONFIG'] = dict(celery_parser['Celery'])
else:
    CONFIG['CELERY_CONFIG'] = {}

val = json.loads(auto_test_ops.get('auto_test_hosts', '{}'))
assert isinstance(val, dict)
CONFIG['__S_AUTO_TEST_HOSTS'] = val

set_bool(CONFIG, auto_test_ops, 'IS_AUTO_TEST_RUNNER', False)

set_int(CONFIG, auto_test_ops, 'AUTO_TEST_MAX_TIME_COMMAND', 5 * 60)
set_int(CONFIG, auto_test_ops, 'AUTO_TEST_MAX_TIME_TOTAL_RUN', 1440)
set_int(CONFIG, auto_test_ops, 'AUTO_TEST_POLL_TIME', 30)
set_int(CONFIG, auto_test_ops, 'AUTO_TEST_OUTPUT_LIMIT', 32768)
set_str(CONFIG, auto_test_ops, 'AUTO_TEST_MEMORY_LIMIT', '512M')
set_str(CONFIG, auto_test_ops, 'AUTO_TEST_BDEVTYPE', 'best')
set_int(CONFIG, auto_test_ops, 'AUTO_TEST_HEARTBEAT_INTERVAL', 10)
set_int(CONFIG, auto_test_ops, 'AUTO_TEST_HEARTBEAT_MAX_MISSED', 6)
set_str(CONFIG, auto_test_ops, 'AUTO_TEST_TEMPLATE_CONTAINER', None)
set_str(CONFIG, auto_test_ops, 'AUTO_TEST_BROKER_URL', '')
set_str(CONFIG, auto_test_ops, 'AUTO_TEST_BROKER_PASSWORD', None)
set_str(CONFIG, auto_test_ops, 'AUTO_TEST_PASSWORD', None)
set_bool(CONFIG, auto_test_ops, 'AUTO_TEST_DISABLE_ORIGIN_CHECK', False)

if CONFIG['IS_AUTO_TEST_RUNNER']:
    assert CONFIG['SQLALCHEMY_DATABASE_URI'] == 'postgresql:///codegrade_dev'
    assert CONFIG['CELERY_CONFIG'] == {}
    assert CONFIG['LTI_CONSUMER_KEY_SECRETS'] == {}
    assert CONFIG['LTI_SECRET_KEY'] == ''
    assert CONFIG['SECRET_KEY'] == ''
    assert CONFIG['HEALTH_KEY'] == ''
    assert CONFIG['AUTO_TEST_BROKER_PASSWORD'] is None
