/**
 * Figure-Ground Perception Stimulus Studio - Frontend App Engine
 */

document.addEventListener('DOMContentLoaded', () => {
  // Global State
  const state = {
    num_regions: 8,
    num_lobes: 6,
    closure: 'open',
    cap_amplitude: 18.0,
    fill_mode: 'outline',
    target_part: 'convex',
    convex_palette: ['yellow', 'orange', 'green', 'blue'],
    concave_palette: ['magenta', 'cyan', 'purple', 'pink'],
    background_color: 'white',
    amplitude: 22,
    sublobe_prob: 0.44,
    spine_wobble: 15.0,
    width_variability: 0.00,
    amplitude_variability: 0.20,
    lobe_height_variability: 0.00,
    probe_enabled: true,
    probe_region: 4,
    probe_size: 16,
    probe_color: 'red',
    seed: 42,
    width: 750,
    height: 260
  };

  let debounceTimer = null;

  // Pre-configured Presets
  const PRESETS = {
    outline: {
      num_regions: 8, num_lobes: 7, fill_mode: 'outline', sublobe_prob: 0.5, amplitude: 24,
      spine_wobble: 15, probe_enabled: true, probe_region: 4, seed: 101, width: 750, height: 260
    },
    binary: {
      num_regions: 8, num_lobes: 6, fill_mode: 'binary', sublobe_prob: 0.44, amplitude: 22,
      spine_wobble: 15, probe_enabled: true, probe_region: 4, seed: 102, width: 750, height: 260
    },
    colored: {
      num_regions: 8, num_lobes: 6, fill_mode: 'colored', target_part: 'convex',
      convex_palette: ['yellow', 'orange', 'green', 'blue'],
      concave_palette: ['magenta', 'cyan', 'purple', 'pink'],
      sublobe_prob: 0.44, amplitude: 22, spine_wobble: 15, probe_enabled: true, probe_region: 4, seed: 103
    },
    homogeneous: {
      num_regions: 8, num_lobes: 6, fill_mode: 'homogeneous', target_part: 'convex',
      convex_palette: ['gray'],
      concave_palette: ['yellow', 'magenta', 'cyan', 'orange'],
      sublobe_prob: 0.44, amplitude: 22, spine_wobble: 15, probe_enabled: true, probe_region: 4, seed: 104
    },
    closed: {
      num_regions: 7, num_lobes: 6, closure: 'closed', cap_amplitude: 18, fill_mode: 'binary',
      sublobe_prob: 0.44, amplitude: 22, spine_wobble: 15, probe_enabled: true, probe_region: 3, seed: 105
    }
  };

  // --- INITIALIZATION ---
  initEventListeners();
  renderColorTags('convex');
  renderColorTags('concave');
  syncUIFromState();
  triggerPreviewFetch();

  // --- EVENT LISTENERS BINDING ---
  function initEventListeners() {
    // Sliders
    const sliders = [
      { id: 'num_regions', key: 'num_regions', valId: 'val-num_regions', int: true },
      { id: 'num_lobes', key: 'num_lobes', valId: 'val-num_lobes', int: true },
      { id: 'cap_amplitude', key: 'cap_amplitude', valId: 'val-cap_amplitude', float: true },
      { id: 'amplitude', key: 'amplitude', valId: 'val-amplitude', int: true },
      { id: 'sublobe_prob', key: 'sublobe_prob', valId: 'val-sublobe_prob', float: true },
      { id: 'spine_wobble', key: 'spine_wobble', valId: 'val-spine_wobble', float: true },
      { id: 'width_variability', key: 'width_variability', valId: 'val-width_variability', float: true },
      { id: 'amplitude_variability', key: 'amplitude_variability', valId: 'val-amplitude_variability', float: true },
      { id: 'lobe_height_variability', key: 'lobe_height_variability', valId: 'val-lobe_height_variability', float: true },
      { id: 'probe_region', key: 'probe_region', valId: 'val-probe_region', int: true }
    ];

    sliders.forEach(s => {
      const el = document.getElementById(s.id);
      if (!el) return;
      el.addEventListener('input', (e) => {
        let val = e.target.value;
        if (s.int) val = parseInt(val, 10);
        if (s.float) val = parseFloat(val);
        state[s.key] = val;

        const valBadge = document.getElementById(s.valId);
        if (valBadge) {
          valBadge.textContent = s.float ? val.toFixed(2) : val;
        }

        // Auto-adjust probe region max slider if num_regions changes
        if (s.key === 'num_regions') {
          const prEl = document.getElementById('probe_region');
          if (prEl) {
            prEl.max = Math.max(0, val - 1);
            if (state.probe_region >= val) {
              state.probe_region = Math.floor(val / 2);
              prEl.value = state.probe_region;
              document.getElementById('val-probe_region').textContent = state.probe_region;
            }
          }

          // Enforce odd num_regions if closure is closed
          if (state.closure === 'closed' && val % 2 === 0) {
            state.num_regions = val + 1;
            el.value = state.num_regions;
            document.getElementById('val-num_regions').textContent = state.num_regions;
          }
        }

        onParamChange();
      });
    });

    // Closure Radio buttons
    document.querySelectorAll('input[name="closure"]').forEach(radio => {
      radio.addEventListener('change', (e) => {
        state.closure = e.target.value;
        const capWrap = document.getElementById('cap-amp-wrapper');
        const hint = document.getElementById('closure-hint');

        if (state.closure === 'closed') {
          capWrap.style.display = 'block';
          hint.textContent = 'Encloses convex regions with curved top/bottom caps (Auto-adjusts to odd regions)';
          if (state.num_regions % 2 === 0) {
            state.num_regions += 1;
            document.getElementById('num_regions').value = state.num_regions;
            document.getElementById('val-num_regions').textContent = state.num_regions;
          }
        } else {
          capWrap.style.display = 'none';
          hint.textContent = 'Standard open top/bottom horizontal frame lines';
        }
        onParamChange();
      });
    });

    // Dropdowns
    const fillModeEl = document.getElementById('fill_mode');
    fillModeEl.addEventListener('change', (e) => {
      state.fill_mode = e.target.value;
      updateFillModeUI();
      onParamChange();
    });

    const targetPartEl = document.getElementById('target_part');
    targetPartEl.addEventListener('change', (e) => {
      state.target_part = e.target.value;
      onParamChange();
    });

    // Inputs (Seed, Background, Dimensions)
    document.getElementById('seed').addEventListener('input', (e) => {
      state.seed = parseInt(e.target.value, 10) || 0;
      onParamChange();
    });

    document.getElementById('btn-random-seed').addEventListener('click', () => {
      state.seed = Math.floor(Math.random() * 999999);
      document.getElementById('seed').value = state.seed;
      onParamChange();
    });

    document.getElementById('background_color').addEventListener('change', (e) => {
      state.background_color = e.target.value.trim() || 'white';
      onParamChange();
    });

    document.getElementById('width').addEventListener('change', (e) => {
      state.width = parseInt(e.target.value, 10) || 750;
      onParamChange();
    });
    document.getElementById('height').addEventListener('change', (e) => {
      state.height = parseInt(e.target.value, 10) || 260;
      onParamChange();
    });

    // Probe options
    const probeChk = document.getElementById('probe_enabled');
    probeChk.addEventListener('change', (e) => {
      state.probe_enabled = e.target.checked;
      document.getElementById('probe-details-group').style.display = state.probe_enabled ? 'block' : 'none';
      onParamChange();
    });

    document.getElementById('probe_size').addEventListener('input', (e) => {
      state.probe_size = parseInt(e.target.value, 10) || 16;
      onParamChange();
    });
    document.getElementById('probe_color').addEventListener('change', (e) => {
      state.probe_color = e.target.value.trim() || 'red';
      onParamChange();
    });

    // Add Color Buttons
    document.getElementById('btn-add-cvx').addEventListener('click', () => addColor('convex'));
    document.getElementById('input-add-cvx').addEventListener('keypress', (e) => {
      if (e.key === 'Enter') addColor('convex');
    });

    document.getElementById('btn-add-cnc').addEventListener('click', () => addColor('concave'));
    document.getElementById('input-add-cnc').addEventListener('keypress', (e) => {
      if (e.key === 'Enter') addColor('concave');
    });

    // Reset Defaults
    document.getElementById('btn-reset-default').addEventListener('click', () => {
      Object.assign(state, PRESETS.colored);
      syncUIFromState();
      onParamChange(true);
    });

    // Preset Buttons
    document.querySelectorAll('.btn-preset').forEach(btn => {
      btn.addEventListener('click', () => {
        const key = btn.dataset.preset;
        if (PRESETS[key]) {
          Object.assign(state, PRESETS[key]);
          syncUIFromState();
          onParamChange(true);
        }
      });
    });

    // Manual Refresh Button
    document.getElementById('btn-refresh-preview').addEventListener('click', () => {
      triggerPreviewFetch();
    });

    // Copy Command Button
    document.getElementById('btn-copy-command').addEventListener('click', () => {
      const code = document.getElementById('cli-command-box').textContent;
      navigator.clipboard.writeText(code).then(() => {
        const btn = document.getElementById('btn-copy-command');
        btn.textContent = '✅ Copied!';
        setTimeout(() => { btn.textContent = '📋 Copy Command'; }, 2000);
      });
    });

    // Save Command File Button
    document.getElementById('btn-save-cmd-file').addEventListener('click', () => {
      const cmdText = document.getElementById('cli-command-box').textContent;
      fetch('/api/export_commands', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filepath: 'generated_stimulus_command.txt', command_text: cmdText })
      })
      .then(res => res.json())
      .then(data => {
        if (data.status === 'ok') {
          alert(`Commands successfully saved to text file:\n${data.filepath}`);
        } else {
          alert(`Error saving file: ${data.message}`);
        }
      });
    });

    // Modal Triggers
    const modalImport = document.getElementById('modal-import');
    const modalBatch = document.getElementById('modal-batch');

    document.getElementById('btn-import-cmd').addEventListener('click', () => {
      modalImport.style.display = 'flex';
    });
    document.getElementById('btn-close-import').addEventListener('click', () => {
      modalImport.style.display = 'none';
    });
    document.getElementById('btn-cancel-import').addEventListener('click', () => {
      modalImport.style.display = 'none';
    });

    document.getElementById('btn-apply-import').addEventListener('click', () => {
      const cmdText = document.getElementById('import-command-text').value.trim();
      if (!cmdText) return;

      fetch('/api/parse_command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: cmdText })
      })
      .then(res => res.json())
      .then(data => {
        if (data.status === 'ok') {
          Object.assign(state, data.params);
          syncUIFromState();
          modalImport.style.display = 'none';
          triggerPreviewFetch();
        } else {
          alert(`Could not parse command string: ${data.message}`);
        }
      });
    });

    document.getElementById('btn-export-cmd').addEventListener('click', () => {
      const cmdText = document.getElementById('cli-command-box').textContent;
      fetch('/api/export_commands', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filepath: 'exported_stimulus_commands.txt', command_text: cmdText })
      })
      .then(res => res.json())
      .then(data => {
        if (data.status === 'ok') {
          alert(`Exported settings command text file:\n${data.filepath}`);
        } else {
          alert(`Error exporting file: ${data.message}`);
        }
      });
    });

    document.getElementById('btn-open-batch').addEventListener('click', () => {
      modalBatch.style.display = 'flex';
    });
    document.getElementById('btn-close-batch').addEventListener('click', () => {
      modalBatch.style.display = 'none';
    });
    document.getElementById('btn-cancel-batch').addEventListener('click', () => {
      modalBatch.style.display = 'none';
    });

    document.getElementById('btn-start-batch').addEventListener('click', () => {
      const targetDir = document.getElementById('batch_target_dir').value.trim();
      const count = parseInt(document.getElementById('batch_count').value, 10) || 10;
      const prefix = document.getElementById('batch_prefix').value.trim() || 'stimulus';
      const seedMode = document.querySelector('input[name="batch_seed_mode"]:checked').value;

      const statusBox = document.getElementById('batch-status-box');
      const statusTitle = document.getElementById('batch-status-title');
      const statusMsg = document.getElementById('batch-status-msg');
      const logOut = document.getElementById('batch-log-output');

      statusBox.style.display = 'block';
      statusTitle.textContent = 'Generating Batch Stimuli...';
      statusMsg.textContent = `Creating ${count} images in '${targetDir}'...`;
      logOut.textContent = 'Processing files...';

      fetch('/api/batch_generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          settings: state,
          output_dir: targetDir,
          count: count,
          seed_mode: seedMode,
          prefix: prefix
        })
      })
      .then(res => res.json())
      .then(data => {
        if (data.status === 'ok') {
          statusTitle.textContent = '✅ Batch Generation Complete!';
          statusMsg.textContent = data.message;
          logOut.textContent = `Target Folder: ${data.output_dir}\nLog File: ${data.log_path}\nSample files generated:\n` + data.sample_files.map(f => ' - ' + f).join('\n');
        } else {
          statusTitle.textContent = '❌ Batch Generation Failed';
          statusMsg.textContent = data.message;
          logOut.textContent = 'Error during batch generation.';
        }
      });
    });
  }

  // --- PARAMETER CHANGE HANDLER ---
  function onParamChange(immediate = false) {
    updateFillModeUI();

    const autoRefresh = document.getElementById('chk-auto-refresh').checked;
    if (immediate || autoRefresh) {
      if (debounceTimer) clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        triggerPreviewFetch();
      }, immediate ? 0 : 150);
    }
  }

  // --- UI SYNC FROM STATE ---
  function syncUIFromState() {
    document.getElementById('num_regions').value = state.num_regions;
    document.getElementById('val-num_regions').textContent = state.num_regions;

    document.getElementById('num_lobes').value = state.num_lobes;
    document.getElementById('val-num_lobes').textContent = state.num_lobes;

    document.querySelector(`input[name="closure"][value="${state.closure}"]`).checked = true;
    document.getElementById('cap-amp-wrapper').style.display = (state.closure === 'closed') ? 'block' : 'none';

    document.getElementById('cap_amplitude').value = state.cap_amplitude;
    document.getElementById('val-cap_amplitude').textContent = parseFloat(state.cap_amplitude).toFixed(1);

    document.getElementById('fill_mode').value = state.fill_mode;
    document.getElementById('target_part').value = state.target_part;

    document.getElementById('amplitude').value = state.amplitude;
    document.getElementById('val-amplitude').textContent = state.amplitude;

    document.getElementById('sublobe_prob').value = state.sublobe_prob;
    document.getElementById('val-sublobe_prob').textContent = parseFloat(state.sublobe_prob).toFixed(2);

    document.getElementById('spine_wobble').value = state.spine_wobble;
    document.getElementById('val-spine_wobble').textContent = parseFloat(state.spine_wobble).toFixed(1);

    document.getElementById('width_variability').value = state.width_variability;
    document.getElementById('val-width_variability').textContent = parseFloat(state.width_variability).toFixed(2);

    document.getElementById('amplitude_variability').value = state.amplitude_variability;
    document.getElementById('val-amplitude_variability').textContent = parseFloat(state.amplitude_variability).toFixed(2);

    document.getElementById('lobe_height_variability').value = state.lobe_height_variability;
    document.getElementById('val-lobe_height_variability').textContent = parseFloat(state.lobe_height_variability).toFixed(2);

    document.getElementById('probe_enabled').checked = state.probe_enabled;
    document.getElementById('probe-details-group').style.display = state.probe_enabled ? 'block' : 'none';

    document.getElementById('probe_region').max = Math.max(0, state.num_regions - 1);
    document.getElementById('probe_region').value = state.probe_region;
    document.getElementById('val-probe_region').textContent = state.probe_region;

    document.getElementById('probe_size').value = state.probe_size;
    document.getElementById('probe_color').value = state.probe_color;

    document.getElementById('seed').value = state.seed;
    document.getElementById('width').value = state.width;
    document.getElementById('height').value = state.height;

    renderColorTags('convex');
    renderColorTags('concave');
    updateFillModeUI();
  }

  function updateFillModeUI() {
    const mode = state.fill_mode;
    const targetWrap = document.getElementById('target-part-wrapper');
    const cvxGroup = document.getElementById('cvx-palette-group');
    const cncGroup = document.getElementById('cnc-palette-group');

    if (mode === 'outline') {
      targetWrap.style.display = 'none';
      cvxGroup.style.display = 'none';
      cncGroup.style.display = 'none';
    } else if (mode === 'binary') {
      targetWrap.style.display = 'none';
      cvxGroup.style.display = 'none';
      cncGroup.style.display = 'none';
    } else if (mode === 'colored') {
      targetWrap.style.display = 'none';
      cvxGroup.style.display = 'block';
      cncGroup.style.display = 'block';
    } else if (mode === 'homogeneous') {
      targetWrap.style.display = 'block';
      cvxGroup.style.display = 'block';
      cncGroup.style.display = 'block';
    }
  }

  // --- COLOR TAGS MANAGER ---
  function addColor(type) {
    const inputId = type === 'convex' ? 'input-add-cvx' : 'input-add-cnc';
    const inputEl = document.getElementById(inputId);
    const val = inputEl.value.trim();
    if (!val) return;

    const list = type === 'convex' ? state.convex_palette : state.concave_palette;
    list.push(val);
    inputEl.value = '';
    renderColorTags(type);
    onParamChange();
  }

  function renderColorTags(type) {
    const containerId = type === 'convex' ? 'convex-tags-container' : 'concave-tags-container';
    const container = document.getElementById(containerId);
    const list = type === 'convex' ? state.convex_palette : state.concave_palette;

    container.innerHTML = '';
    list.forEach((col, idx) => {
      const chip = document.createElement('div');
      chip.className = 'color-chip';

      const swatch = document.createElement('span');
      swatch.className = 'chip-swatch';
      swatch.style.backgroundColor = col;

      const txt = document.createElement('span');
      txt.textContent = col;

      const removeBtn = document.createElement('button');
      removeBtn.className = 'chip-remove';
      removeBtn.innerHTML = '&times;';
      removeBtn.title = 'Remove color';
      removeBtn.addEventListener('click', () => {
        list.splice(idx, 1);
        renderColorTags(type);
        onParamChange();
      });

      chip.appendChild(swatch);
      chip.appendChild(txt);
      chip.appendChild(removeBtn);
      container.appendChild(chip);
    });
  }

  // --- LIVE PREVIEW API FETCH ---
  function triggerPreviewFetch() {
    const spinner = document.getElementById('preview-spinner');
    const imgEl = document.getElementById('stimulus-img');
    const placeholder = document.getElementById('preview-placeholder');

    spinner.style.display = 'block';

    fetch('/api/preview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(state)
    })
    .then(res => res.json())
    .then(data => {
      spinner.style.display = 'none';
      if (data.status === 'ok') {
        imgEl.src = data.image;
        imgEl.style.display = 'block';
        placeholder.style.display = 'none';
        
        document.getElementById('preview-dim').textContent = `${data.width} x ${data.height} px`;
        document.getElementById('cli-command-box').textContent = data.command;
      } else {
        placeholder.textContent = `Error rendering preview: ${data.message}`;
        placeholder.style.display = 'block';
      }
    })
    .catch(err => {
      spinner.style.display = 'none';
      placeholder.textContent = `Network error: ${err.message}`;
      placeholder.style.display = 'block';
    });
  }
});
