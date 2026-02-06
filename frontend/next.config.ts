import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  allowedDevOrigins: ["192.168.111.42"],
  output: "standalone", // Required for Docker deployment
};

export default nextConfig;
