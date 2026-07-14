import vercel from "@astrojs/vercel";
import { defineConfig } from "astro/config";

export default defineConfig({
  site: "https://trialdiff.vercel.app",
  output: "server",
  adapter: vercel(),
});
