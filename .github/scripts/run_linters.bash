#!/bin/bash
set -o xtrace

cat >config.ini <<EOF
[Back-end]
external_url = http://localhost:1234
proxy_base_domain = test.com
redis_cache_url = redis://localhost:6379/cg_cache
EOF

npm run build &
NPM_PID="$!"

make pylint &
PYLINT_PID="$!"

make privacy_statement
npm run lint
res2="$?"

make mypy
res3="$?"

out="$(make isort_check)"
res4=$?
if [[ "$res4" -ne 0 ]]; then
    echo "$out"
fi

make yapf_check
res5=$?

( cd docs && make html )
res6="$?"

wait "$NPM_PID"
res7="$?"

wait "$PYLINT_PID"
res1="$?"

[[ $(( res1 + res2 + res3 + res4 + res5 + res6 + res7 )) = 0 ]]
exit_code="$?"

exit "$exit_code"
