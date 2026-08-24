import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  eslint: { ignoreDuringBuilds: true },
  async rewrites() {
    // Server-side proxy to the FastAPI backend; the browser only talks to this app.
    const api = process.env.API_URL ?? "http://127.0.0.1:8000";
    return [{ source: "/api/:path*", destination: `${api}/api/:path*` }];
  },
};

export default nextConfig;
