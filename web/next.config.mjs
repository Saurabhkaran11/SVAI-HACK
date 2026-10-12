/** @type {import('next').NextConfig} */
const BACKEND = process.env.BACKEND_URL || "http://localhost:8000";

const nextConfig = {
  // Browser calls /api/* → FastAPI backend (no CORS, one origin for the demo)
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${BACKEND}/:path*` },
      { source: "/openapi.json", destination: `${BACKEND}/openapi.json` },
    ];
  },
};
export default nextConfig;
