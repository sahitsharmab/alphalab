import path from "path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Pin the tracing root to this app so stray lockfiles elsewhere on the
  // machine don't change build behavior.
  outputFileTracingRoot: path.join(__dirname),
};

export default nextConfig;
