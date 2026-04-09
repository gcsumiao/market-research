(function () {
  if (window.ReportCharts) return;

  const SVG_NS = 'http://www.w3.org/2000/svg';

  function el(name, attrs, text) {
    const node = document.createElementNS(SVG_NS, name);
    if (attrs) {
      Object.keys(attrs).forEach((key) => {
        if (attrs[key] !== undefined && attrs[key] !== null) {
          node.setAttribute(key, attrs[key]);
        }
      });
    }
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function fmtNumber(value, decimals) {
    return Number(value).toLocaleString(undefined, {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals
    });
  }

  function formatValue(value, format) {
    if (format && typeof format === 'function') return format(value);
    const config = format || {};
    const prefix = config.prefix || '';
    const suffix = config.suffix || '';
    const decimals = config.decimals !== undefined ? config.decimals : 0;
    return prefix + fmtNumber(value, decimals) + suffix;
  }

  function niceMax(value) {
    if (value <= 0) return 1;
    const power = Math.pow(10, Math.floor(Math.log10(value)));
    const scaled = value / power;
    let step = 1;
    if (scaled > 8) step = 10;
    else if (scaled > 4) step = 5;
    else if (scaled > 2) step = 2.5;
    else if (scaled > 1) step = 2;
    return step * power;
  }

  function tooltip() {
    let node = document.querySelector('.report-chart-tooltip');
    if (!node) {
      node = document.createElement('div');
      node.className = 'report-chart-tooltip';
      document.body.appendChild(node);
    }
    return node;
  }

  function showTooltip(evt, payload) {
    const node = tooltip();
    node.innerHTML = '';
    const title = document.createElement('span');
    title.className = 'report-chart-tooltip-title';
    title.textContent = payload.title;
    node.appendChild(title);
    (payload.lines || []).forEach((line) => {
      const child = document.createElement('span');
      child.className = 'report-chart-tooltip-line';
      child.textContent = line;
      node.appendChild(child);
    });
    node.classList.add('visible');
    moveTooltip(evt);
  }

  function moveTooltip(evt) {
    const node = tooltip();
    const width = node.offsetWidth || 220;
    const height = node.offsetHeight || 60;
    let x = evt.clientX + 14;
    let y = evt.clientY + 14;
    if (x + width > window.innerWidth - 12) x = evt.clientX - width - 14;
    if (y + height > window.innerHeight - 12) y = evt.clientY - height - 14;
    node.style.left = x + 'px';
    node.style.top = y + 'px';
  }

  function hideTooltip() {
    tooltip().classList.remove('visible');
  }

  function bindTooltip(node, payloadFactory) {
    const handler = (evt) => showTooltip(evt, payloadFactory());
    node.addEventListener('mouseenter', handler);
    node.addEventListener('mousemove', moveTooltip);
    node.addEventListener('mouseleave', hideTooltip);
    node.addEventListener('focus', handler);
    node.addEventListener('blur', hideTooltip);
    node.addEventListener('click', handler);
    node.classList.add('report-chart-hit');
    node.setAttribute('tabindex', '0');
  }

  function makeHost(def) {
    const target = document.querySelector(def.selector);
    if (!target) return null;
    const wrap = target.closest('.chart-wrap') || target.closest('.chart-single') || target.parentElement;
    if (wrap) {
      wrap.querySelectorAll('.chart-help, .chart-hotspot, .chart-tooltip').forEach((node) => node.remove());
    }
    const replaceNode = target.closest('.interactive-chart') || target;
    const host = document.createElement('div');
    host.className = 'report-chart-host';
    replaceNode.replaceWith(host);
    return { host, wrap };
  }

  function makeCard(def) {
    const card = document.createElement('div');
    card.className = 'report-chart-card';
    if (def.cardClass) card.className += ' ' + def.cardClass;
    if (def.title) {
      const title = document.createElement('div');
      title.className = 'report-chart-title';
      title.textContent = def.title;
      card.appendChild(title);
    }
    return card;
  }

  function makeSvg(width, height) {
    const svg = el('svg', {
      class: 'report-chart-svg',
      viewBox: `0 0 ${width} ${height}`,
      role: 'img',
      'aria-label': 'Interactive report chart'
    });
    return svg;
  }

  function addLegend(card, items) {
    if (!items || !items.length) return;
    const legend = document.createElement('div');
    legend.className = 'report-chart-legend';
    items.forEach((item) => {
      const row = document.createElement('div');
      row.className = 'report-chart-legend-item';
      const swatch = document.createElement('span');
      swatch.className = 'report-chart-swatch' + (item.kind === 'line' ? ' line' : '');
      swatch.style.background = item.color;
      row.appendChild(swatch);
      row.appendChild(document.createTextNode(item.label));
      legend.appendChild(row);
    });
    card.appendChild(legend);
  }

  function addPieLegend(card, slices, format, options) {
    const legend = document.createElement('div');
    legend.className = 'report-chart-pie-legend';
    if (options && options.compact) legend.classList.add('compact');
    if (options && options.columns) {
      legend.style.gridTemplateColumns = `repeat(${options.columns}, minmax(0, 1fr))`;
    }
    slices.forEach((slice) => {
      const row = document.createElement('div');
      row.className = 'report-chart-legend-item';
      const swatch = document.createElement('span');
      swatch.className = 'report-chart-swatch';
      swatch.style.background = slice.color;
      row.appendChild(swatch);
      const label = document.createElement('div');
      label.className = 'report-chart-label';
      const name = document.createElement('span');
      name.textContent = slice.name;
      label.appendChild(name);
      if (slice.meta) {
        const meta = document.createElement('span');
        meta.className = 'report-chart-meta';
        meta.textContent = slice.meta;
        label.appendChild(meta);
      } else {
        const meta = document.createElement('span');
        meta.className = 'report-chart-meta';
        meta.textContent = formatValue(slice.value, format);
        label.appendChild(meta);
      }
      row.appendChild(label);
      legend.appendChild(row);
    });
    card.appendChild(legend);
  }

  function renderAxes(svg, chart, xTicks, yTicks, yFormat, y2Ticks, y2Format) {
    svg.appendChild(el('line', {
      x1: chart.left, y1: chart.top + chart.height,
      x2: chart.left + chart.width, y2: chart.top + chart.height,
      class: 'report-chart-axis'
    }));
    svg.appendChild(el('line', {
      x1: chart.left, y1: chart.top,
      x2: chart.left, y2: chart.top + chart.height,
      class: 'report-chart-axis'
    }));
    if (y2Ticks) {
      svg.appendChild(el('line', {
        x1: chart.left + chart.width, y1: chart.top,
        x2: chart.left + chart.width, y2: chart.top + chart.height,
        class: 'report-chart-axis'
      }));
    }
    yTicks.forEach((tick) => {
      const y = chart.top + chart.height - tick.ratio * chart.height;
      svg.appendChild(el('line', {
        x1: chart.left, y1: y, x2: chart.left + chart.width, y2: y,
        class: 'report-chart-gridline'
      }));
      svg.appendChild(el('text', {
        x: chart.left - 8, y: y + 4, 'text-anchor': 'end',
        class: 'report-chart-tick'
      }, formatValue(tick.value, yFormat)));
    });
    if (y2Ticks) {
      y2Ticks.forEach((tick) => {
        const y = chart.top + chart.height - tick.ratio * chart.height;
        svg.appendChild(el('text', {
          x: chart.left + chart.width + 8, y: y + 4, 'text-anchor': 'start',
          class: 'report-chart-tick'
        }, formatValue(tick.value, y2Format)));
      });
    }
    xTicks.forEach((tick) => {
      svg.appendChild(el('text', {
        x: tick.x, y: chart.top + chart.height + 18,
        'text-anchor': 'middle', class: 'report-chart-tick'
      }, tick.label));
    });
  }

  function renderLine(def, mount) {
    const width = 860;
    const height = def.height || 340;
    const chart = { left: 62, top: 34, width: width - 106, height: height - 82 };
    const maxValue = def.max || niceMax(Math.max.apply(null, def.series.flatMap((s) => s.values)));
    const card = makeCard(def);
    const svg = makeSvg(width, height);
    card.appendChild(svg);
    addLegend(card, def.series.map((s) => ({ label: s.name, color: s.color, kind: 'line' })));
    mount.host.appendChild(card);

    const xStep = def.labels.length > 1 ? chart.width / (def.labels.length - 1) : chart.width;
    const yTicks = [0, 0.25, 0.5, 0.75, 1].map((ratio) => ({ ratio, value: maxValue * ratio }));
    const xTicks = def.labels.map((label, index) => ({ label, x: chart.left + xStep * index }));
    renderAxes(svg, chart, xTicks, yTicks, def.yFormat);

    def.series.forEach((series) => {
      const points = series.values.map((value, index) => {
        const x = chart.left + xStep * index;
        const y = chart.top + chart.height - (value / maxValue) * chart.height;
        return { x, y, value, label: def.labels[index] };
      });
      svg.appendChild(el('polyline', {
        fill: 'none',
        stroke: series.color,
        'stroke-width': 3,
        points: points.map((p) => `${p.x},${p.y}`).join(' ')
      }));
      points.forEach((point) => {
        svg.appendChild(el('circle', { cx: point.x, cy: point.y, r: 4.5, fill: series.color }));
        const hit = el('circle', { cx: point.x, cy: point.y, r: 11, fill: 'transparent' });
        bindTooltip(hit, () => ({
          title: `${series.name} · ${point.label}`,
          lines: [formatValue(point.value, series.format || def.yFormat)].concat(series.note ? [series.note] : [])
        }));
        svg.appendChild(hit);
      });
    });
  }

  function renderStackedBarLine(def, mount) {
    const width = 860;
    const height = def.height || 340;
    const chart = { left: 62, top: 34, width: width - 110, height: height - 82 };
    const stackMax = def.max || niceMax(Math.max.apply(null, def.labels.map((_, idx) =>
      def.stacks.reduce((sum, stack) => sum + stack.values[idx], 0)
    )));
    const lineMax = def.line.axis === 'right'
      ? (def.line.max || niceMax(Math.max.apply(null, def.line.values)))
      : stackMax;
    const card = makeCard(def);
    const svg = makeSvg(width, height);
    card.appendChild(svg);
    addLegend(card, def.stacks.map((s) => ({ label: s.name, color: s.color }))
      .concat([{ label: def.line.name, color: def.line.color, kind: 'line' }]));
    mount.host.appendChild(card);

    const groupWidth = chart.width / def.labels.length;
    const barWidth = groupWidth * 0.46;
    const yTicks = [0, 0.25, 0.5, 0.75, 1].map((ratio) => ({ ratio, value: stackMax * ratio }));
    const y2Ticks = def.line.axis === 'right'
      ? [0, 0.25, 0.5, 0.75, 1].map((ratio) => ({ ratio, value: lineMax * ratio }))
      : null;
    const xTicks = def.labels.map((label, index) => ({
      label,
      x: chart.left + groupWidth * index + groupWidth / 2
    }));
    renderAxes(svg, chart, xTicks, yTicks, def.yFormat, y2Ticks, def.line.format);

    const linePoints = [];
    def.labels.forEach((label, index) => {
      const x = chart.left + groupWidth * index + groupWidth / 2 - barWidth / 2;
      let running = 0;
      def.stacks.forEach((stack) => {
        const value = stack.values[index];
        const h = (value / stackMax) * chart.height;
        const y = chart.top + chart.height - h - (running / stackMax) * chart.height;
        const rect = el('rect', {
          x, y, width: barWidth, height: h,
          fill: stack.color
        });
        bindTooltip(rect, () => ({
          title: `${stack.name} · ${label}`,
          lines: [formatValue(value, stack.format || def.yFormat)]
        }));
        svg.appendChild(rect);
        running += value;
      });
      const lineValue = def.line.values[index];
      const maxForLine = def.line.axis === 'right' ? lineMax : stackMax;
      linePoints.push({
        x: chart.left + groupWidth * index + groupWidth / 2,
        y: chart.top + chart.height - (lineValue / maxForLine) * chart.height,
        label,
        value: lineValue
      });
    });
    svg.appendChild(el('polyline', {
      fill: 'none',
      stroke: def.line.color,
      'stroke-width': 3,
      points: linePoints.map((p) => `${p.x},${p.y}`).join(' ')
    }));
    linePoints.forEach((point) => {
      svg.appendChild(el('circle', { cx: point.x, cy: point.y, r: 4.5, fill: def.line.color }));
      const hit = el('circle', { cx: point.x, cy: point.y, r: 11, fill: 'transparent' });
      bindTooltip(hit, () => ({
        title: `${def.line.name} · ${point.label}`,
        lines: [formatValue(point.value, def.line.format || def.yFormat)]
      }));
      svg.appendChild(hit);
    });
  }

  function renderBarLine(def, mount) {
    const width = 860;
    const height = def.height || 340;
    const chart = { left: 62, top: 34, width: width - 110, height: height - 82 };
    const barMax = def.bar.max || niceMax(Math.max.apply(null, def.bar.values));
    const lineMax = def.line.max || niceMax(Math.max.apply(null, def.line.values));
    const card = makeCard(def);
    const svg = makeSvg(width, height);
    card.appendChild(svg);
    addLegend(card, [
      { label: def.bar.name, color: def.bar.color },
      { label: def.line.name, color: def.line.color, kind: 'line' }
    ]);
    mount.host.appendChild(card);

    const groupWidth = chart.width / def.labels.length;
    const barWidth = groupWidth * 0.46;
    const yTicks = [0, 0.25, 0.5, 0.75, 1].map((ratio) => ({ ratio, value: barMax * ratio }));
    const y2Ticks = [0, 0.25, 0.5, 0.75, 1].map((ratio) => ({ ratio, value: lineMax * ratio }));
    const xTicks = def.labels.map((label, index) => ({
      label,
      x: chart.left + groupWidth * index + groupWidth / 2
    }));
    renderAxes(svg, chart, xTicks, yTicks, def.bar.format, y2Ticks, def.line.format);

    const linePoints = [];
    def.labels.forEach((label, index) => {
      const value = def.bar.values[index];
      const h = (value / barMax) * chart.height;
      const x = chart.left + groupWidth * index + (groupWidth - barWidth) / 2;
      const y = chart.top + chart.height - h;
      const rect = el('rect', {
        x, y, width: barWidth, height: h,
        fill: Array.isArray(def.bar.color) ? def.bar.color[index] : def.bar.color
      });
      bindTooltip(rect, () => ({
        title: `${def.bar.name} · ${label}`,
        lines: [formatValue(value, def.bar.format)]
      }));
      svg.appendChild(rect);
      linePoints.push({
        x: chart.left + groupWidth * index + groupWidth / 2,
        y: chart.top + chart.height - (def.line.values[index] / lineMax) * chart.height,
        label,
        value: def.line.values[index]
      });
    });
    svg.appendChild(el('polyline', {
      fill: 'none',
      stroke: def.line.color,
      'stroke-width': 3,
      points: linePoints.map((p) => `${p.x},${p.y}`).join(' ')
    }));
    linePoints.forEach((point) => {
      svg.appendChild(el('circle', { cx: point.x, cy: point.y, r: 4.5, fill: def.line.color }));
      const hit = el('circle', { cx: point.x, cy: point.y, r: 11, fill: 'transparent' });
      bindTooltip(hit, () => ({
        title: `${def.line.name} · ${point.label}`,
        lines: [formatValue(point.value, def.line.format)]
      }));
      svg.appendChild(hit);
    });
  }

  function renderHorizontalBar(def, mount) {
    const width = 860;
    const height = def.height || Math.max(260, def.labels.length * 28 + 60);
    const chart = { left: 160, top: 22, width: width - 220, height: height - 44 };
    const max = def.max || niceMax(Math.max.apply(null, def.values));
    const card = makeCard(def);
    const svg = makeSvg(width, height);
    card.appendChild(svg);
    mount.host.appendChild(card);

    const rowHeight = chart.height / def.labels.length;
    [0, 0.25, 0.5, 0.75, 1].forEach((ratio) => {
      const x = chart.left + chart.width * ratio;
      svg.appendChild(el('line', {
        x1: x, y1: chart.top, x2: x, y2: chart.top + chart.height,
        class: 'report-chart-gridline'
      }));
      svg.appendChild(el('text', {
        x, y: chart.top + chart.height + 16, 'text-anchor': 'middle',
        class: 'report-chart-tick'
      }, formatValue(max * ratio, def.format)));
    });
    svg.appendChild(el('line', {
      x1: chart.left, y1: chart.top + chart.height,
      x2: chart.left + chart.width, y2: chart.top + chart.height,
      class: 'report-chart-axis'
    }));

    def.labels.forEach((label, index) => {
      const y = chart.top + rowHeight * index + rowHeight * 0.18;
      const h = rowHeight * 0.62;
      const w = (def.values[index] / max) * chart.width;
      svg.appendChild(el('text', {
        x: chart.left - 10, y: y + h / 2 + 4, 'text-anchor': 'end',
        class: 'report-chart-tick'
      }, label));
      const rect = el('rect', {
        x: chart.left, y, width: w, height: h,
        fill: Array.isArray(def.color) ? def.color[index] : def.color
      });
      bindTooltip(rect, () => ({
        title: label,
        lines: [formatValue(def.values[index], def.format)].concat(def.meta && def.meta[index] ? [def.meta[index]] : [])
      }));
      svg.appendChild(rect);
    });
  }

  function polarToCartesian(cx, cy, r, angle) {
    return {
      x: cx + r * Math.cos(angle),
      y: cy + r * Math.sin(angle)
    };
  }

  function arcPath(cx, cy, r, startAngle, endAngle) {
    const start = polarToCartesian(cx, cy, r, startAngle);
    const end = polarToCartesian(cx, cy, r, endAngle);
    const largeArc = endAngle - startAngle > Math.PI ? 1 : 0;
    return [
      `M ${cx} ${cy}`,
      `L ${start.x} ${start.y}`,
      `A ${r} ${r} 0 ${largeArc} 1 ${end.x} ${end.y}`,
      'Z'
    ].join(' ');
  }

  function renderPie(def, mount) {
    const width = def.width || 860;
    const height = def.height || 340;
    const card = makeCard(def);
    const svg = makeSvg(width, height);
    card.appendChild(svg);
    addPieLegend(card, def.slices, def.format, {
      compact: !!def.legendCompact,
      columns: def.legendColumns
    });
    mount.host.appendChild(card);

    const cx = def.centerX || Math.round(width * 0.36);
    const cy = def.centerY || Math.round(height * 0.5);
    const r = def.radius || Math.round(Math.min(width, height) * 0.28);
    const total = def.slices.reduce((sum, slice) => sum + slice.value, 0);
    let current = -Math.PI / 2;
    def.slices.forEach((slice) => {
      const angle = (slice.value / total) * Math.PI * 2;
      const path = el('path', {
        d: arcPath(cx, cy, r, current, current + angle),
        fill: slice.color,
        stroke: '#fff',
        'stroke-width': 2
      });
      bindTooltip(path, () => ({
        title: slice.name,
        lines: [formatValue(slice.value, def.format)].concat(slice.meta ? [slice.meta] : [])
      }));
      svg.appendChild(path);
      current += angle;
    });
  }

  function render(def) {
    const mount = makeHost(def);
    if (!mount) return;
    if (def.type === 'line') renderLine(def, mount);
    else if (def.type === 'stackedBarLine') renderStackedBarLine(def, mount);
    else if (def.type === 'barLine') renderBarLine(def, mount);
    else if (def.type === 'horizontalBar') renderHorizontalBar(def, mount);
    else if (def.type === 'pie') renderPie(def, mount);
  }

  function applyVerdictPills(scope) {
    if (!scope) return;
    const verdictMap = {
      'PASS': 'vp-pass',
      'STRONG PASS': 'vp-strong',
      'CONDITIONAL PASS': 'vp-cond',
      'CONDITIONAL': 'vp-cond',
      'WEAK PASS': 'vp-weak',
      'FAIL': 'vp-fail',
      'WEAK': 'vp-weak',
      'PASS ON PAPER': 'vp-pass',
      'PASS AS DEFENSIVE PLAY': 'vp-pass',
      'PASS FOR NICHE / FAIL FOR CATEGORY': 'vp-neutral',
      'CONDITIONAL GO / LEAN NO-GO': 'vp-cond'
    };
    scope.querySelectorAll('tbody tr td:nth-child(2)').forEach((cell) => {
      if (cell.querySelector('.verdict-pill')) return;
      const label = cell.textContent.trim().replace(/\s+/g, ' ');
      const tone = verdictMap[label];
      if (!tone) return;
      cell.innerHTML = '<span class="verdict-pill ' + tone + '">' + label + '</span>';
    });
  }

  function renderAll(defs) {
    defs.forEach(render);
  }

  window.ReportCharts = {
    renderAll,
    applyVerdictPills
  };
})();
