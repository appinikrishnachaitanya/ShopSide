import {defineConfig} from '@playwright/test';
export default defineConfig({testDir:'./tests',use:{launchOptions:{executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium',args:['--no-sandbox']}},timeout:30000});
