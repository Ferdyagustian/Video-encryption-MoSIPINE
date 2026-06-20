const { execSync } = require('child_process');
const path = require('path');

const pluginRoot = 'C:\\Users\\LENOVO LOQ\\.claude\\plugins\\cache\\understand-anything\\understand-anything\\7f5a717694d3';
const skillDir = path.join(pluginRoot, 'skills', 'understand');

[1, 2, 3, 4].forEach(idx => {
  console.log(`Extracting batch ${idx}...`);
  try {
    execSync(
      `node "${path.join(skillDir, 'extract-structure.mjs')}" "C:\\Skripsi\\.understand-anything\\tmp\\ua-file-analyzer-input-${idx}.json" "C:\\Skripsi\\.understand-anything\\tmp\\ua-file-extract-results-${idx}.json"`,
      {
        stdio: 'inherit',
        env: {
          ...process.env,
          PLUGIN_ROOT: pluginRoot
        }
      }
    );
    console.log(`Batch ${idx} completed successfully.`);
  } catch (e) {
    console.error(`Failed on batch ${idx}:`, e.message);
  }
});
