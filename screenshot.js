const puppeteer = require('puppeteer-core');
const path = require('path');

const SCREENSHOT_DIR = path.join(__dirname, 'screenshots');

async function run() {
    const fs = require('fs');
    if (!fs.existsSync(SCREENSHOT_DIR)) fs.mkdirSync(SCREENSHOT_DIR);

    const browser = await puppeteer.launch({
        headless: 'new',
        executablePath: 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
        args: ['--no-sandbox']
    });
    const page = await browser.newPage();
    await page.setViewport({ width: 1920, height: 1080 });

    // Login
    await page.goto('http://localhost:5000/login', { waitUntil: 'networkidle0' });
    await page.type('input[name="username"]', 'admin');
    await page.type('input[name="password"]', 'admin123');
    await page.click('button[type="submit"]');
    await page.waitForNavigation({ waitUntil: 'networkidle0' });

    // Portal
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '1-portal.png'), fullPage: false });
    console.log('1. Portal page captured');

    // Enter decision platform
    await page.goto('http://localhost:5000/dashboard', { waitUntil: 'networkidle0' });
    await new Promise(r => setTimeout(r, 1500));
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '2-dashboard.png'), fullPage: false });
    console.log('2. Dashboard captured');

    // Open outpatient registration report
    await page.goto('http://localhost:5000/report/opd_reg', { waitUntil: 'networkidle0' });
    await new Promise(r => setTimeout(r, 2000));
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '3-report-outpatient.png'), fullPage: false });
    console.log('3. Outpatient registration report captured');

    // Open surgery report
    await page.goto('http://localhost:5000/report/surg_record', { waitUntil: 'networkidle0' });
    await new Promise(r => setTimeout(r, 2000));
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '4-report-surgery.png'), fullPage: false });
    console.log('4. Surgery report captured');

    // Open finance daily report
    await page.goto('http://localhost:5000/report/fin_daily', { waitUntil: 'networkidle0' });
    await new Promise(r => setTimeout(r, 2000));
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '5-report-finance.png'), fullPage: false });
    console.log('5. Finance report captured');

    // Go back to portal
    await page.goto('http://localhost:5000/portal', { waitUntil: 'networkidle0' });
    await new Promise(r => setTimeout(r, 1000));
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '6-portal-admin.png'), fullPage: false });
    console.log('6. Portal admin captured');

    // Enter system management
    await page.goto('http://localhost:5000/admin', { waitUntil: 'networkidle0' });
    await new Promise(r => setTimeout(r, 1000));
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '7-admin.png'), fullPage: false });
    console.log('7. System management captured');

    await browser.close();
    console.log('\nAll screenshots saved to screenshots/');
}

run().catch(console.error);
