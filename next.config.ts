import type { NextConfig } from 'next';
const nextConfig: NextConfig = {
  allowedDevOrigins: ['127.0.0.1'],
  turbopack: { root: process.cwd() },
  outputFileTracingIncludes: { '/api/engine': ['./server/**/*.py','./server/reference_data/*.json'] },
};
export default nextConfig;
