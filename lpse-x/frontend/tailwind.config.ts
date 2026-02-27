import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        aman: '#22c55e',
        pantauan: '#f59e0b',
        tinggi: '#ef4444',
        kritis: '#7c2d12',
      }
    },
  },
  plugins: [],
}

export default config
