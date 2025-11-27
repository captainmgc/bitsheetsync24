import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Enable standalone output for Docker deployment
  output: 'standalone',
  
  // Environment variables available at build time
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
  },
  
  // Disable x-powered-by header for security
  poweredByHeader: false,
  
  // Configure allowed image domains if needed
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'etablo.japonkonutlari.com',
      },
    ],
  },
};

export default nextConfig;
