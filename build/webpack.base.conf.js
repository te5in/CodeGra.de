var path = require('path')
var utils = require('./utils')
var webpack = require('webpack')
var config = require('../config')
var vueLoaderConfig = require('./vue-loader.conf')
var userConfig = require('./userConfig')
var permissions = require('../seed_data/permissions.json')
const { VueLoaderPlugin } = require('vue-loader')
const ForkTsCheckerWebpackPlugin = require('fork-ts-checker-webpack-plugin');
const keysTransformer = require('ts-transformer-keys/transformer').default;

function resolve (dir) {
  return path.join(__dirname, '..', dir)
}

module.exports = {
  mode: process.env.NODE_ENV,
  entry: {
    app: './src/main.js'
  },
  output: {
    path: config.build.assetsRoot,
    filename: '[name].js',
    publicPath: process.env.NODE_ENV === 'production'
      ? config.build.assetsPublicPath
      : config.dev.assetsPublicPath
  },
  resolve: {
    extensions: ['.js', '.vue', '.json', '.ts'],
    alias: {
      'vue$': 'vue/dist/vue.esm.js',
      '@': resolve('src'),
      'mixins': path.resolve(__dirname, '../src/mixins.less'),
      'mixins.less': path.resolve(__dirname, '../src/mixins.less')
    }
  },
  module: {
    rules: [
      {
        test: /\.(js|vue|ts)$/,
        loader: 'eslint-loader',
        enforce: 'pre',
          include: [
              resolve('src'),
              resolve('test')
          ],
        options: {
          formatter: require('eslint-friendly-formatter')
        }
      },
      {
        test: /\.vue$/,
        loader: 'vue-loader',
        options: vueLoaderConfig
      },
      {
        test: /\.tsx?$/,
        exclude: /node_modules/,
        use: [
          {
            loader: "ts-loader",
            options: {
              appendTsSuffixTo: [/\.vue$/],
              transpileOnly: false,
              experimentalWatchApi: false,
              getCustomTransformers: program => ({
                before: [
                    keysTransformer(program),
                ],
              }),
            },
          },
        ]
      },
      {
        test: /\.js$/,
        loader: 'babel-loader',
          include: [resolve('src'), resolve('test'),
                    resolve('node_modules/bootstrap-vue')
                   ]
      },
      {
        test: /\.(png|jpe?g|gif|svg)(\?.*)?$/,
        loader: 'url-loader',
        options: {
          limit: 10000,
          name: utils.assetsPath('img/[name].[hash:7].[ext]')
        }
      },
      {
        test: /\.(woff2?|eot|ttf|otf)(\?.*)?$/,
        loader: 'url-loader',
        options: {
          limit: 10000,
          name: utils.assetsPath('fonts/[name].[hash:7].[ext]')
        }
      }
    ]
  },
  node: {
    fs: 'empty',
    buffer: false,
  },
  plugins: [
    new VueLoaderPlugin(),
    new webpack.DefinePlugin({
        'UserConfig': JSON.stringify(userConfig),
        'Permissions': JSON.stringify(permissions),
    }),
  ],
}
