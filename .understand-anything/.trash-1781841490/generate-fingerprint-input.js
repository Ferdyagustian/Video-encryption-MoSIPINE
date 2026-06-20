const fs = require('fs');
const path = require('path');

const scanResultFile = 'C:\\Skripsi\\.understand-anything\\intermediate\\scan-result.json';
const scanResult = JSON.parse(fs.readFileSync(scanResultFile, 'utf8'));

const sourceFilePaths = scanResult.files.map(f => f.path);

const fingerprintInput = {
  projectRoot: 'C:\\Skripsi',
  sourceFilePaths,
  gitCommitHash: 'b9ff58fe10e5e92c900b0a95c193521b6bf9393d'
};

const outFile = 'C:\\Skripsi\\.understand-anything\\intermediate\\fingerprint-input.json';
fs.writeFileSync(outFile, JSON.stringify(fingerprintInput, null, 2));
console.log('Successfully wrote fingerprint-input.json');
