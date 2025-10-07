const path = require('path');

const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  // 🔧 FORZAR NUEVO BUILD - Cambiar hash de bundles
  generateBuildId: async () => {
    return `build-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  },
  
  // 🔧 CACHE BUSTER - Forzar recarga de assets
  assetPrefix: process.env.NODE_ENV === 'production' ? `https://software-loyal-light.vercel.app` : '',
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
