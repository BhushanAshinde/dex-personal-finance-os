const repository = 'dex-personal-finance-os';
const isGitHubPages = process.env.GITHUB_PAGES === 'true';

/** @type {import('next').NextConfig} */
const nextConfig = {
  images: { unoptimized: true },
  ...(isGitHubPages ? { output: 'export', trailingSlash: true } : {}),
  ...(isGitHubPages ? { basePath: `/${repository}`, assetPrefix: `/${repository}/` } : {}),
};

export default nextConfig;
