#!/bin/bash
set -o xtrace

printf '[Back-end]\nproxy_base_domain = test.com' > config.ini
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

out="$(npm run check-format)"
res6=$?
if [[ "$res6" -ne 0 ]]; then
    echo "$out"
fi

( cd docs && make html )
res7="$?"

wait "$NPM_PID"
res8="$?"

wait "$PYLINT_PID"
res1="$?"

[[ $(( res1 + res2 + res3 + res4 + res5 + res6 + res7 + res8 )) = 0 ]]
exit_code="$?"

exit "$exit_code"
