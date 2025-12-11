function generateBarChartSVG(reports) {
    if (!reports || reports.length === 0) {
        return '<p>No data available for chart.</p>';
    }

    const chartWidth = 900;
    const chartHeight = 400;
    const margin = { top: 40, right: 20, bottom: 80, left: 60 };
    const width = chartWidth - margin.left - margin.right;
    const height = chartHeight - margin.top - margin.bottom;

    const maxCount = Math.max(1, ...reports.map(r => r.total_chats || 0));
    const tickCount = Math.min(5, Math.ceil(maxCount));

    const bandWidth = width / reports.length;
    const barWidth = bandWidth * 0.8;
    const barPadding = bandWidth * 0.2;

    const yScale = (value) => height - (value / maxCount) * height;

    const yTicks = Array.from({ length: tickCount + 1 }, (_, i) => (maxCount / tickCount) * i);
    const yAxisHTML = yTicks.map(tick => {
        const tickValue = Number.isInteger(tick) ? tick : tick.toFixed(1);
        return `
        <g transform="translate(0, ${yScale(tick)})">
            <line x2="${width}" stroke="#e0e0e0" stroke-width="0.5" />
            <text x="-10" y="5" text-anchor="end" font-size="12" fill="#5f6368">${tickValue}</text>
        </g>
    `;}).join('');

    const barsHTML = reports.map((report, i) => {
        const passed = report.total_passed || 0;
        const failed = report.total_failed || 0;
        const x = i * bandWidth + barPadding / 2;

        return `
            <g transform="translate(${x}, 0)">
                <rect y="${yScale(passed)}" width="${barWidth}" height="${(passed / maxCount) * height}" fill="rgba(75, 192, 75, 0.85)" />
                <rect y="${yScale(passed + failed)}" width="${barWidth}" height="${(failed / maxCount) * height}" fill="rgba(255, 99, 132, 0.85)" />
                <text x="${barWidth / 2}" y="${height + 20}" transform="rotate(45, ${barWidth / 2}, ${height + 20})" text-anchor="start" font-size="10" fill="#5f6368">${new Date(report.timestamp_started).toLocaleDateString()}</text>
            </g>
        `;
    }).join('');

    return `
        <svg width="${chartWidth}" height="${chartHeight}" font-family="Arial, sans-serif" style="background-color: transparent;">
            <text x="${chartWidth / 2}" y="25" text-anchor="middle" font-size="16" fill="#202124">Report Passed / Failed Counts</text>
            <g transform="translate(${margin.left}, ${margin.top})">
                <line x1="0" y1="0" x2="0" y2="${height}" stroke="#5f6368" />
                <line x1="0" y1="${height}" x2="${width}" y2="${height}" stroke="#5f6368" />
                <text transform="rotate(-90)" y="-45" x="${-height / 2}" text-anchor="middle" fill="#202124" font-size="14">Number of tests</text>
                ${yAxisHTML}
                ${barsHTML}
            </g>
            <g transform="translate(${chartWidth / 2 - 60}, ${chartHeight - 15})">
                <rect x="0" y="0" width="12" height="12" fill="rgba(75, 192, 75, 0.85)" />
                <text x="18" y="11" font-size="12" fill="#5f6368">Passed</text>
                <rect x="80" y="0" width="12" height="12" fill="rgba(255, 99, 132, 0.85)" />
                <text x="98" y="11" font-size="12" fill="#5f6368">Failed</text>
            </g>
        </svg>
    `;
}

function generateAllReportsHTML(reports, allExecutions, projectName) {
  const generationTimestamp = new Date().toUTCString();
  const sortedReports = [...reports].sort(
    (a, b) => new Date(a.timestamp_started).getTime() - new Date(b.timestamp_started).getTime()
  );
  const lastRunTimestamp = sortedReports.length > 0 ? new Date(Math.max(...sortedReports.map(r => new Date(r.timestamp_completed || r.timestamp_started).getTime()))).toUTCString() : 'N/A';

  const totalReports = sortedReports.length;
  const totalPassed = sortedReports.reduce((sum, r) => sum + r.total_passed, 0);
  const totalFailed = sortedReports.reduce((sum, r) => sum + r.total_failed, 0);
  const totalRuns = totalPassed + totalFailed;

  const tests = {};
  allExecutions.forEach(exec => {
    const title = exec.chat_title || 'Untitled Test';
    if (!tests[title]) {
      tests[title] = { title, runs: 0, passed: 0, failed: 0, reports: new Set() };
    }
    tests[title].runs++;
    if (exec.status === 'failed') {
      tests[title].failed++;
      tests[title].lastError = exec.error_message;
      tests[title].lastErrorScreenshot = (exec.images && exec.images.length > 0) ? exec.images[0].b64 : null;
    } else {
      tests[title].passed++;
    }
    tests[title].reports.add(exec.batch_report_id);
  });

  const uniqueTests = Object.values(tests);
  const testsFailedOnce = uniqueTests.filter(t => t.failed > 0);
  const topFailingTests = [...testsFailedOnce].sort((a, b) => b.failed - a.failed).slice(0, 5);

  const formatDate = (dateString) => dateString ? new Date(dateString).toLocaleString() : 'N/A';

  return `
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>All Test Reports - ${projectName}</title>
      <style>
        :root {
            --color-pass: #1e8e3e; --color-fail: #d93025; --color-other: #5f6368;
            --bg-pass: #e6f4ea; --bg-fail: #fce8e6; --bg-other: #f1f3f4;
            --border-color: #dadce0; --text-color: #202124; --text-color-light: #5f6368;
            --panel-bg: #f8f9fa; --body-bg: #ffffff;
        }
        body { font-family: Arial, sans-serif; margin: 20px; background-color: var(--body-bg); color: var(--text-color); }
        .container { max-width: 1200px; margin: auto; background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h1, h2, h3 { color: var(--text-color); border-bottom: 2px solid #eee; padding-bottom: 10px; margin-top: 25px; }
        table { width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 14px; }
        th, td { padding: 12px; border: 1px solid var(--border-color); text-align: left; }
        th { background-color: var(--panel-bg); }
        .status-passed { color: var(--color-pass); font-weight: bold; }
        .status-failed { color: var(--color-fail); font-weight: bold; }
        .screenshot { max-width: 80px; max-height: 60px; border-radius: 4px; border: 1px solid var(--border-color); }
        .header-stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 15px; margin-bottom: 20px; }
        .stat-box { background: var(--panel-bg); padding: 15px; border-radius: 8px; border: 1px solid var(--border-color); }
        .stat-title { font-weight: bold; color: var(--text-color-light); }
        .stat-value { font-size: 1.8em; font-weight: bold; color: var(--text-color); margin-top: 5px; }
        .footer { font-size: 0.9em; color: #777; margin-top: 20px; text-align: center; }
        pre { white-space: pre-wrap; word-break: break-all; font-size: 0.9em; max-height: 100px; overflow-y: auto; background: #f1f3f4; padding: 5px; border-radius: 4px; }
        .chart-container { background-color: var(--panel-bg); padding: 20px; border-radius: 8px; margin-top: 20px; text-align: center; border: 1px solid var(--border-color); }
      </style>
    </head>
    <body>
      <div class="container">
        <h1>All Test Reports for ${projectName}</h1>
        <p>Generated on: ${generationTimestamp}</p>
        <p>Last Run Timestamp: ${lastRunTimestamp}</p>
        
        <h2>Aggregated Statistics</h2>
        <div class="header-stats">
          <div class="stat-box"><div class="stat-title">Total Reports</div><div class="stat-value">${totalReports}</div></div>
          <div class="stat-box"><div class="stat-title">Total Test Runs</div><div class="stat-value">${totalRuns}</div></div>
          <div class="stat-box"><div class="stat-title">Passed Runs</div><div class="stat-value status-passed">${totalPassed}</div></div>
          <div class="stat-box"><div class="stat-title">Failed Runs</div><div class="stat-value status-failed">${totalFailed}</div></div>
          <div class="stat-box"><div class="stat-title">Unique Tests</div><div class="stat-value">${uniqueTests.length}</div></div>
          <div class="stat-box"><div class="stat-title">Tests Failing</div><div class="stat-value status-failed">${testsFailedOnce.length}</div></div>
        </div>

        <div class="chart-container">
            <h3>Pass / Fail Chart</h3>
            ${generateBarChartSVG(sortedReports)}
        </div>

        <h2>Top Failing Tests</h2>
        <table>
          <thead><tr><th>Test Title</th><th>Total Runs</th><th>Failed</th><th>Passed</th><th>Last Error</th><th>Screenshot</th></tr></thead>
          <tbody>
            ${topFailingTests.map(test => `
              <tr>
                <td>${test.title}</td>
                <td>${test.runs}</td>
                <td class="status-failed">${test.failed}</td>
                <td class="status-passed">${test.passed}</td>
                <td><pre>${test.lastError || 'N/A'}</pre></td>
                <td>${test.lastErrorScreenshot ? `<img src="data:image/png;base64,${test.lastErrorScreenshot}" class="screenshot" alt="Screenshot">` : 'N/A'}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>

        <h2>Reports Overview</h2>
        <table>
          <thead><tr><th>Report Name/Date</th><th>Total Tests</th><th>Passed</th><th>Failed</th></tr></thead>
          <tbody>
            ${sortedReports.slice().reverse().map(report => `
              <tr>
                <td>Report from ${formatDate(report.timestamp_started)}</td>
                <td>${report.total_chats}</td>
                <td class="status-passed">${report.total_passed}</td>
                <td class="status-failed">${report.total_failed}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>

        <div class="footer">
          <p>Barko Agent Report</p>
        </div>
      </div>
    </body>
    </html>
  `;
}

module.exports = { generateAllReportsHTML };
