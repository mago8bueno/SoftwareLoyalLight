// next.config.js
const path = require('path')

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
    NEXT_PUBLIC_OPENAI_KEY: process.env.NEXT_PUBLIC_OPENAI_KEY,
  },
  images: {
    domains: ['eqntartkrscrvqevezkz.supabase.co'],
  },
  eslint: {
    ignoreDuringBuilds: true, // ⬅️ ignora ESLint en Vercel (temporal)
  },
  typescript: {
    ignoreBuildErrors: true,   // ⬅️ ignora errores TS en Vercel (temporal)
  },
  webpack(config) {
    config.resolve.alias['@components'] = path.resolve(__dirname, 'components')
    config.resolve.alias['@hooks'] = path.resolve(__dirname, 'hooks')
    config.resolve.alias['@layouts'] = path.resolve(__dirname, 'layouts')
    config.resolve.alias['@services'] = path.resolve(__dirname, 'services')
    config.resolve.alias['@contexts'] = path.resolve(__dirname, 'contexts')
    config.resolve.alias['@styles'] = path.resolve(__dirname, 'styles')
    return config
  },
}

module.exports = nextConfig

