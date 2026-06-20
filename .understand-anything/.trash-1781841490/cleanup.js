const fs = require('fs');
const path = require('path');

const projectRoot = 'C:\\Skripsi';
const uaDir = path.join(projectRoot, '.understand-anything');
const intermediateDir = path.join(uaDir, 'intermediate');
const tmpDir = path.join(uaDir, 'tmp');
const trashDir = path.join(uaDir, `.trash-${Math.floor(Date.now() / 1000)}`);

fs.mkdirSync(trashDir, { recursive: true });

// Move intermediate files (except scan-result.json)
if (fs.existsSync(intermediateDir)) {
  const files = fs.readdirSync(intermediateDir);
  files.forEach(file => {
    if (file !== 'scan-result.json') {
      const src = path.join(intermediateDir, file);
      const dest = path.join(trashDir, file);
      try {
        fs.renameSync(src, dest);
      } catch (err) {
        try {
          fs.copyFileSync(src, dest);
          fs.unlinkSync(src);
        } catch (e) {
          console.error(e);
        }
      }
    }
  });
}

// Move tmp files
if (fs.existsSync(tmpDir)) {
  const files = fs.readdirSync(tmpDir);
  files.forEach(file => {
    const src = path.join(tmpDir, file);
    const dest = path.join(trashDir, file);
    try {
      fs.renameSync(src, dest);
    } catch (err) {
      try {
        fs.copyFileSync(src, dest);
        fs.unlinkSync(src);
      } catch (e) {
        console.error(e);
      }
    }
  });
  try {
    fs.rmdirSync(tmpDir);
  } catch (e) {
    console.error(e);
  }
}
console.log('Cleanup completed successfully.');
