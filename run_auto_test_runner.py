#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only

import typing as t

import psef
import cg_logger
# TODO: Fix the complete shit we have done with imports. This requires us to
# first import models to prevent circular imports...
import psef.models
import psef.auto_test

if __name__ == '__main__':
    import config

    cg_logger.configure_logging(
        config.CONFIG['DEBUG'],
        False,
        config.CONFIG.get('SENTRY_DSN'),
        config.CONFIG.get('CUR_COMMIT'),
    )
    cg_logger.logger_callback(cg_logger.report_error_to_sentry)
    psef.enable_testing()
    psef.auto_test.start_polling(t.cast(t.Any, config.CONFIG))
