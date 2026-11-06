import {defineConfig} from '@playwright/test';
export default defineConfig({testDir:'./tests',use:{launchOptions:{executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium',args:['--no-sandbox','--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream']}},timeout:30000});
