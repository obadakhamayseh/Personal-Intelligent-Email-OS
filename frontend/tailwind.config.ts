import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        gmail: {
          bg: "#F6F8FC",
          search: "#EAF1FB",
          active: "#D3E3FD",
          compose: "#C2E7FF",
          composeHover: "#B3D7EF",
          rowUnread: "#FFFFFF",
          rowRead: "#F2F6FC",
          border: "#E1E5EA",
          textPrimary: "#1F1F1F",
          textSecondary: "#444746",
          blue: "#0B57D0",
        },
      },
    },
  },
  plugins: [],
};
export default config;
