const fs = require('fs');
const path = require('path');

const projectRoot = 'C:\\Skripsi';
const commitHash = 'b9ff58fe10e5e92c900b0a95c193521b6bf9393d';

const graphFile = path.join(projectRoot, '.understand-anything', 'intermediate', 'assembled-graph.json');
const layersFile = path.join(projectRoot, '.understand-anything', 'intermediate', 'layers.json');
const tourFile = path.join(projectRoot, '.understand-anything', 'intermediate', 'tour.json');

const graphData = JSON.parse(fs.readFileSync(graphFile, 'utf8'));
const layersData = JSON.parse(fs.readFileSync(layersFile, 'utf8'));
const tourData = JSON.parse(fs.readFileSync(tourFile, 'utf8'));

// Assemble full knowledge graph
const fullGraph = {
  version: "1.0.0",
  project: {
    name: "MO-SiPINE",
    languages: ["json", "python", "txt"],
    frameworks: ["Tkinter", "Numba", "OpenCV", "Pillow", "matplotlib", "scipy", "numpy", "scikit-image", "ffmpeg"],
    description: "Sistem kriptografi video dan audio berbasis peta chaos Modulo Sine-PWLCM (MO-SiPINE) dengan antarmuka GUI Tkinter dan kompilasi Numba JIT.",
    analyzedAt: new Date().toISOString(),
    gitCommitHash: commitHash
  },
  nodes: graphData.nodes,
  edges: graphData.edges,
  layers: layersData,
  tour: tourData
};

// Validate that every layer and tour node ID exists in nodes list
const nodeIds = new Set(fullGraph.nodes.map(n => n.id));
const issues = [];
const warnings = [];

// Clean up layers
fullGraph.layers.forEach(layer => {
  if (!layer.nodeIds) layer.nodeIds = [];
  const validNodeIds = [];
  layer.nodeIds.forEach(id => {
    if (nodeIds.has(id)) {
      validNodeIds.push(id);
    } else {
      issues.push(`Layer '${layer.id}' referenced missing node '${id}' - removed.`);
    }
  });
  layer.nodeIds = validNodeIds;
});

// Clean up tour
fullGraph.tour.forEach((step, idx) => {
  if (!step.nodeIds) step.nodeIds = [];
  const validNodeIds = [];
  step.nodeIds.forEach(id => {
    if (nodeIds.has(id)) {
      validNodeIds.push(id);
    } else {
      issues.push(`Tour step[${idx}] '${step.title}' referenced missing node '${id}' - removed.`);
    }
  });
  step.nodeIds = validNodeIds;
});

// Check for orphan nodes
const edgeEndpoints = new Set();
fullGraph.edges.forEach(e => {
  edgeEndpoints.add(e.source);
  edgeEndpoints.add(e.target);
});
fullGraph.nodes.forEach(n => {
  if (!edgeEndpoints.has(n.id)) {
    warnings.push(`Node '${n.id}' has no edges (orphan).`);
  }
});

// Save assembled graph
fs.writeFileSync(graphFile, JSON.stringify(fullGraph, null, 2));
console.log(`Successfully assembled full graph in intermediate/assembled-graph.json.`);

// Save review.json
const reviewOutput = {
  issues,
  warnings,
  stats: {
    totalNodes: fullGraph.nodes.length,
    totalEdges: fullGraph.edges.length,
    totalLayers: fullGraph.layers.length,
    tourSteps: fullGraph.tour.length,
    nodeTypes: fullGraph.nodes.reduce((a, n) => { a[n.type] = (a[n.type]||0)+1; return a; }, {}),
    edgeTypes: fullGraph.edges.reduce((a, e) => { a[e.type] = (a[e.type]||0)+1; return a; }, {})
  }
};
const reviewFile = path.join(projectRoot, '.understand-anything', 'intermediate', 'review.json');
fs.writeFileSync(reviewFile, JSON.stringify(reviewOutput, null, 2));
console.log(`Saved validation review to intermediate/review.json. Issues: ${issues.length}, Warnings: ${warnings.length}`);
