const { override } = require('customize-cra');

module.exports = override(
  (config) => {
    config.resolve.fallback = {
      ...config.resolve.fallback,
      crypto: require.resolve('crypto-browserify'),
stream:require.resolve('stream-browserify'),
vm:require.resolve('vm-browserify'),
process:require.resolve('process/browser'),
    };
    return config;
  }
);
