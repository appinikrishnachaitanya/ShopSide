import {defineConfig} from '@playwright/test';
import base from './playwright.config';
export default defineConfig({...base,testMatch:['**/mobile-workspace.spec.ts','**/merchant-portal.spec.ts','**/order-summary.spec.ts'],use:{...base.use,viewport:{width:390,height:844},isMobile:true,hasTouch:true}});
