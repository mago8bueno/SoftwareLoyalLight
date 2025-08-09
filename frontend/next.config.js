const path = require('path');

const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
    NEXT_PUBLIC_OPENAI_KEY: process.env.NEXT_PUBLIC_OPENAI_KEY,
  },
  eslint: {
    ignoreDuringBuilds: true, // <--- Ignora errores ESLint en el build
  },
  typescript: {
    ignoreBuildErrors: true, // <--- Ignora errores TS en el build
  },
  images: {
    domains: ['eqntartkrscrvqevezkz.supabase.co'],
  },
  webpack(config) {
    config.resolve.alias['@components'] = path.resolve(__dirname, 'components');
    config.resolve.alias['@hooks'] = path.resolve(__dirname, 'hooks');
    config.resolve.alias['@layouts'] = path.resolve(__dirname, 'layouts');
    config.resolve.alias['@services'] = path.resolve(__dirname, 'services');
    config.resolve.alias['@contexts'] = path.resolve(__dirname, 'contexts');
    config.resolve.alias['@styles'] = path.resolve(__dirname, 'styles');
    return config;
  },
};

module.exports = nextConfig;
