import type { NextConfig } from 'next';
const nextConfig: NextConfig = {
  turbopack: { root: process.cwd() },
  outputFileTracingIncludes: { '/api/engine': ['./server/bridge.py'] },
};
export default nextConfig;
