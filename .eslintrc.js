// http://eslint.org/docs/user-guide/configuring

module.exports = {
    root: true,
    parser: 'babel-eslint',
    parserOptions: {
        sourceType: 'module'
    },
    env: {
        browser: true,
    },
    extends: 'airbnb-base',
    // required to lint *.vue files
    plugins: [
        'html'
    ],
    // check if imports actually resolve
    'settings': {
        'import/resolver': {
            'webpack': {
                'config': 'build/webpack.base.conf.js'
            }
        }
    },
    // add your custom rules here
    'rules': {
        // don't require .vue extension when importing
        'import/extensions': ['error', 'always', {
            'js': 'never',
            'vue': 'never'
        }],
        // allow optionalDependencies
        'import/no-extraneous-dependencies': ['error', {
            'optionalDependencies': ['test/unit/index.js']
        }],
        // allow debugger during development
        'no-debugger': process.env.NODE_ENV === 'production' ? 2 : 0,
        'indent': ["error", 4, { 'SwitchCase': 1 }],
        'no-else-return': 'off',
        'no-plusplus': 'off',
        'function-paren-newline': 'off',
        'no-bitwise': 'off',
        'no-mixed-operators': 'off',
        'arrow-parens': ['error', 'as-needed'],
        'prefer-destructuring': 'off',
        'import/prefer-default-export': 'off',

        // allow vuex
        'no-param-reassign': ["error", { 'props': false }],

        'no-underscore-dangle': ['error', { 'allowAfterThis': true, 'allowAfterSuper': true }],
    },
    globals: {
        'UserConfig': true,
        'AutoTestBaseSystems': true,
    },
}
