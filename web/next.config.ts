import type { NextConfig } from "next";

/** Server-side proxy target (not exposed to the browser). Local dev: API on host. Docker web: service name `api`. */
const apiProxyTarget =
  process.env.API_PROXY_TARGET?.replace(/\/$/, "") || "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    return [{ source: "/api-backend/:path*", destination: `${apiProxyTarget}/:path*` }];
  },
};

export default nextConfig;
