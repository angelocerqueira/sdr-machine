import type { NextConfig } from "next";

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    return {
      beforeFiles: [
        {
          source: "/api/leads/:path*",
          destination: `${BACKEND_URL}/api/leads/:path*`,
        },
        {
          source: "/api/dashboard/:path*",
          destination: `${BACKEND_URL}/api/dashboard/:path*`,
        },
        {
          source: "/api/jobs/:path*",
          destination: `${BACKEND_URL}/api/jobs/:path*`,
        },
        {
          source: "/api/pipeline/:path*",
          destination: `${BACKEND_URL}/api/pipeline/:path*`,
        },
        {
          source: "/api/settings",
          destination: `${BACKEND_URL}/api/settings`,
        },
        {
          source: "/api/health",
          destination: `${BACKEND_URL}/api/health`,
        },
      ],
      afterFiles: [],
      fallback: [],
    };
  },
};

export default nextConfig;
