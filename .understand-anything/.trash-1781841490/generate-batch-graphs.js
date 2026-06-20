const fs = require('fs');
const path = require('path');

const projectRoot = 'C:\\Skripsi';
const batchesFile = path.join(projectRoot, '.understand-anything', 'intermediate', 'batches.json');
const batchesData = JSON.parse(fs.readFileSync(batchesFile, 'utf8'));

// Hardcoded Indonesian summaries for files
const fileSummaries = {
  'sipine.py': 'Inti algoritma chaotic map Modulo Sine-PWLCM, dioptimasi dengan Numba JIT untuk membangkitkan keystream pseudo-random secara cepat.',
  'ai_optimizer.py': 'Modul untuk mencari parameter atau kunci optimal peta chaos menggunakan pencarian acak (Random Search) dan optimasi Lyapunov exponent.',
  'video_core.py': 'Modul utama backend untuk memproses enkripsi dan dekripsi video serta audio terpadu menggunakan keystream dari peta chaos.',
  'audio_core.py': 'Modul backend untuk enkripsi dan dekripsi audio WAV secara standalone.',
  'gui_video_main.py': 'Entry point utama aplikasi desktop berbasis GUI Tkinter.',
  'gui_video.py': 'Modul implementasi GUI Tkinter lengkap untuk enkripsi, dekripsi, pemutar video, dan visualisasi uji kualitas.',
  'generator_nist.py': 'Modul pembangun bitstream (1 Megabit) dari peta chaos untuk pengujian statistik standar NIST SP 800-22.',
  'bifurkasi.py': 'Utilitas untuk mensimulasikan dan membuat visualisasi diagram bifurkasi dari peta chaos.',
  'lyapunov.py': 'Utilitas untuk menghitung dan memvisualisasikan nilai eksponen Lyapunov dari peta chaos.',
  'fix_avi.py': 'Skrip utilitas migrasi format video dari format .avi ke kontainer .mp4.',
  'DOKUMENTASI_SISTEM_MO_SIPINE.txt': 'Dokumentasi komprehensif sistem kriptografi MO-SiPINE, arsitektur file, rumus, dan panduan penggunaan.',
  'Hasil_Uji_NIST_SubSampling.bin': 'Berkas biner output hasil uji NIST (bitstream).',
  'Hasil_Uji_NIST_SubSampling.txt': 'Berkas teks hasil simulasi uji NIST.',
  'hasil nist 100.txt': 'Catatan log hasil uji NIST dengan 100 iterasi.',
  'hasiluji.txt': 'Catatan log hasil evaluasi performa dan kualitas enkripsi sistem.',
  'Laporan_Hasil_Uji_NIST.txt': 'Laporan statistik hasil pengujian acak menggunakan paket uji NIST SP 800-22.',
  '.understand-anything/.understandignore': 'Konfigurasi pola berkas dan direktori yang diabaikan dalam analisis kode.',
  '.understand-anything/config.json': 'Konfigurasi internal plugin untuk bahasa output dan pembaruan otomatis.',
  'pyrightconfig.json': 'Konfigurasi statis untuk analisis tipe Python menggunakan Pyright.',
  'nist_data/sipine_threshold_x0123456789_10000_info.txt': 'Informasi metadata uji NIST.',
  'nist_data/sipine_threshold_x0123456789_10000.bin': 'Berkas biner bitstream uji NIST.',
  'nist_data/sipine_threshold_x0123456789_10000.txt': 'Berkas teks bitstream uji NIST.',
  'Tempat_gambar/AI_Key_Report.txt': 'Laporan hasil pencarian kunci optimal AI.',
  'Tempat_gambar/audio_asli.wav': 'Berkas contoh audio asli dalam format WAV.',
  'Tempat_gambar/audio_noise.wav': 'Berkas audio terenkripsi dalam format WAV yang terdengar seperti noise.',
  'Tempat_gambar/audio_terdekripsi.wav': 'Berkas audio hasil dekripsi dalam format WAV.',
  'Tempat_gambar/audio_terenkripsi.bin': 'Berkas biner hasil enkripsi audio.',
  'Tempat_gambar/output_terenkripsi.mkv': 'Berkas video hasil enkripsi dalam wadah MKV.',
  'Tempat_gambar/video_terdekripsi.avi': 'Berkas video hasil dekripsi dalam format AVI.',
  'Tempat_gambar/video_terenkripsi.bin': 'Berkas biner hasil enkripsi video.',
  'Tempat_gambar/video_terenkripsi.ven2': 'Berkas video terenkripsi menggunakan format biner kustom .ven2.'
};

// Function to determine complexity
function getComplexity(lines) {
  if (lines < 50) return 'simple';
  if (lines <= 200) return 'moderate';
  return 'complex';
}

// Function to map category to node type
function getNodeType(filePath, category) {
  if (category === 'code') return 'file';
  if (category === 'config') return 'config';
  if (category === 'docs') return 'document';
  if (category === 'infra') {
    const base = path.basename(filePath);
    if (base.toLowerCase().includes('docker')) return 'service';
    if (base.toLowerCase().includes('workflow') || base.toLowerCase().includes('ci')) return 'pipeline';
    return 'resource';
  }
  if (category === 'data') {
    const ext = path.extname(filePath).toLowerCase();
    if (ext === '.sql') return 'table';
    if (ext === '.graphql' || ext === '.proto' || ext === '.prisma') return 'schema';
    return 'endpoint';
  }
  return 'file';
}

// Loop through each batch
batchesData.batches.forEach(b => {
  const batchIdx = b.batchIndex;
  const extractFile = path.join(projectRoot, '.understand-anything', 'tmp', `ua-file-extract-results-${batchIdx}.json`);
  const extractData = JSON.parse(fs.readFileSync(extractFile, 'utf8'));

  const nodes = [];
  const edges = [];

  // Map of file path to node ID
  const fileNodeIds = {};

  // First pass: Create file nodes
  extractData.results.forEach(res => {
    const filePath = res.path;
    const type = getNodeType(filePath, res.fileCategory);
    const idPrefix = type === 'document' ? 'document:' : type === 'config' ? 'config:' : 'file:';
    const id = `${idPrefix}${filePath}`;
    fileNodeIds[filePath] = id;

    const summary = fileSummaries[filePath] || `Berkas ${res.fileCategory} untuk ${path.basename(filePath)}.`;
    const complexity = getComplexity(res.totalLines);

    // Tags generator
    const tags = ['kriptografi-chaos'];
    if (res.fileCategory === 'code') {
      if (filePath.endsWith('.py')) {
        tags.push('python');
        if (filePath.includes('gui')) tags.push('gui-tkinter');
        else if (filePath.includes('core')) tags.push('backend-kripto');
        else if (filePath.includes('optimizer')) tags.push('optimasi-ai');
        else tags.push('utilitas');
      } else {
        tags.push('multimedia');
      }
    } else if (res.fileCategory === 'docs') {
      tags.push('dokumentasi');
    } else {
      tags.push(res.fileCategory);
    }

    nodes.push({
      id,
      type,
      name: path.basename(filePath),
      filePath,
      summary,
      tags: tags.slice(0, 4),
      complexity
    });
  });

  // Second pass: Create function and class nodes for code files
  extractData.results.forEach(res => {
    const filePath = res.path;
    const fileId = fileNodeIds[filePath];

    if (res.fileCategory === 'code') {
      // Classes
      if (res.classes) {
        res.classes.forEach(cls => {
          // Check significance filter: exported or methods >= 2 or lines >= 20
          const lines = cls.endLine - cls.startLine + 1;
          const isSignificant = (cls.methods && cls.methods.length >= 2) || lines >= 20;

          if (isSignificant) {
            const classId = `class:${filePath}:${cls.name}`;
            nodes.push({
              id: classId,
              type: 'class',
              name: cls.name,
              filePath,
              lineRange: [cls.startLine, cls.endLine],
              summary: `Kelas ${cls.name} yang berisi properti dan metode terkait.`,
              tags: ['kriptografi-chaos', 'kelas-python'],
              complexity: getComplexity(lines)
            });

            // Contains and Exports edges
            edges.push({
              source: fileId,
              target: classId,
              type: 'contains',
              direction: 'forward',
              weight: 1.0
            });
            edges.push({
              source: fileId,
              target: classId,
              type: 'exports',
              direction: 'forward',
              weight: 0.8
            });
          }
        });
      }

      // Functions
      if (res.functions) {
        res.functions.forEach(fn => {
          // Check significance filter: exported or lines >= 10
          const lines = fn.endLine - fn.startLine + 1;
          const isSignificant = lines >= 10;

          if (isSignificant) {
            const fnId = `function:${filePath}:${fn.name}`;
            nodes.push({
              id: fnId,
              type: 'function',
              name: fn.name,
              filePath,
              lineRange: [fn.startLine, fn.endLine],
              summary: `Fungsi ${fn.name} untuk memproses operasi terkait.`,
              tags: ['kriptografi-chaos', 'fungsi-python'],
              complexity: getComplexity(lines)
            });

            // Contains and Exports edges
            edges.push({
              source: fileId,
              target: fnId,
              type: 'contains',
              direction: 'forward',
              weight: 1.0
            });
            edges.push({
              source: fileId,
              target: fnId,
              type: 'exports',
              direction: 'forward',
              weight: 0.8
            });
          }
        });
      }
    }
  });

  // Third pass: Create import edges based on batchImportData
  if (b.batchImportData) {
    Object.keys(b.batchImportData).forEach(srcFile => {
      const srcId = fileNodeIds[srcFile];
      if (!srcId) return;

      b.batchImportData[srcFile].forEach(targetFile => {
        // Find target ID. Since target could be in another batch, check if it's in fileSummaries (existing project file)
        const targetType = getNodeType(targetFile, fileSummaries[targetFile] ? 'code' : 'code'); // Default to code/file
        const targetPrefix = targetType === 'document' ? 'document:' : targetType === 'config' ? 'config:' : 'file:';
        const targetId = `${targetPrefix}${targetFile}`;

        edges.push({
          source: srcId,
          target: targetId,
          type: 'imports',
          direction: 'forward',
          weight: 0.7
        });
      });
    });
  }

  // Fourth pass: Create calls and other semantic edges
  extractData.results.forEach(res => {
    const filePath = res.path;
    const fileId = fileNodeIds[filePath];

    // Calls edges
    if (res.callGraph) {
      res.callGraph.forEach(call => {
        const callerId = `function:${filePath}:${call.caller}`;
        // Verify caller node exists in our generated nodes
        const callerExists = nodes.some(n => n.id === callerId || (n.type === 'class' && n.id === `class:${filePath}:${call.caller}`));
        if (!callerExists) return;

        // Try to resolve callee in current batch files or neighborMap
        let calleeId = null;
        let calleeFile = null;

        // Check if callee is in the same file
        if (res.functions && res.functions.some(f => f.name === call.callee)) {
          calleeId = `function:${filePath}:${call.callee}`;
          calleeFile = filePath;
        }

        // Check imports of current file to see if callee belongs to imported files
        if (!calleeId && b.batchImportData && b.batchImportData[filePath]) {
          b.batchImportData[filePath].forEach(impFile => {
            // Check exports of imported file from neighborMap or batches exportsByPath
            if (batchesData.exportsByPath[impFile] && batchesData.exportsByPath[impFile].includes(call.callee)) {
              calleeId = `function:${impFile}:${call.callee}`;
              calleeFile = impFile;
            }
          });
        }

        if (calleeId) {
          edges.push({
            source: callerId,
            target: calleeId,
            type: 'calls',
            direction: 'forward',
            weight: 0.8
          });
        }
      });
    }

    // Document edges
    if (res.fileCategory === 'docs' && filePath === 'DOKUMENTASI_SISTEM_MO_SIPINE.txt') {
      const codeFiles = ['sipine.py', 'video_core.py', 'audio_core.py', 'ai_optimizer.py', 'gui_video.py', 'gui_video_main.py', 'generator_nist.py', 'bifurkasi.py', 'lyapunov.py'];
      codeFiles.forEach(cf => {
        edges.push({
          source: fileId,
          target: `file:${cf}`,
          type: 'documents',
          direction: 'forward',
          weight: 0.5
        });
      });
    }

    // Configures edges
    if (res.fileCategory === 'config') {
      if (filePath === 'pyrightconfig.json') {
        const codeFiles = ['sipine.py', 'video_core.py', 'audio_core.py', 'ai_optimizer.py', 'gui_video.py', 'gui_video_main.py', 'generator_nist.py', 'bifurkasi.py', 'lyapunov.py'];
        codeFiles.forEach(cf => {
          edges.push({
            source: fileId,
            target: `file:${cf}`,
            type: 'configures',
            direction: 'forward',
            weight: 0.6
          });
        });
      }
    }
  });

  // Write batch JSON file
  const outFile = path.join(projectRoot, '.understand-anything', 'intermediate', `batch-${batchIdx}.json`);
  fs.writeFileSync(outFile, JSON.stringify({ nodes, edges }, null, 2));
  console.log(`Wrote batch-${batchIdx}.json with ${nodes.length} nodes and ${edges.length} edges.`);
});
console.log('Finished compiling all batch files successfully!');
