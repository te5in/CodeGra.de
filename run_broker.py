#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only

# Run a test server.
import cg_broker

if __name__ == '__main__':
    app = cg_broker.create_app()
    app.run(host='0.0.0.0', port=2020, debug=True, threaded=True)
