// ReviewGuard AI - Chart.js Configuration

let sentimentChartInstance = null;
let authenticityChartInstance = null;
let aspectChartInstance = null;

// Dynamic Theme Colors
const getThemeColors = (theme) => {
    const isDark = theme === 'dark';
    return {
        text: isDark ? '#E2E8F0' : '#0F172A',
        grid: isDark ? '#2E3A4E' : '#E2E8F0',
        tooltipsBg: isDark ? '#1E293B' : '#FFFFFF',
        tooltipsBorder: isDark ? '#334155' : '#E2E8F0'
    };
};

// Initialize Charts with Data
function renderAnalysisCharts(sentimentData, fakeCount, genuineCount, aspectsData) {
    const theme = localStorage.getItem('theme') || 'dark';
    const colors = getThemeColors(theme);
    
    // Destroy existing instances if refreshing
    if (sentimentChartInstance) sentimentChartInstance.destroy();
    if (authenticityChartInstance) authenticityChartInstance.destroy();
    if (aspectChartInstance) aspectChartInstance.destroy();
    
    // 1. Sentiment Pie Chart
    const ctxSentiment = document.getElementById('sentimentPieChart');
    if (ctxSentiment) {
        sentimentChartInstance = new Chart(ctxSentiment, {
            type: 'doughnut',
            data: {
                labels: ['Positive 😊', 'Neutral 😐', 'Negative 😔'],
                datasets: [{
                    data: [sentimentData.positive || 0, sentimentData.neutral || 0, sentimentData.negative || 0],
                    backgroundColor: ['#14B8A6', '#64748B', '#EF4444'],
                    borderColor: theme === 'dark' ? '#131A26' : '#FFFFFF',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { color: colors.text, font: { family: 'Inter' } }
                    }
                }
            }
        });
    }
    
    // 2. Authenticity Bar Chart (Fake vs Genuine)
    const ctxAuth = document.getElementById('authenticityBarChart');
    if (ctxAuth) {
        authenticityChartInstance = new Chart(ctxAuth, {
            type: 'bar',
            data: {
                labels: ['Genuine Reviews', 'Fake Reviews'],
                datasets: [{
                    label: 'Reviews Count',
                    data: [genuineCount, fakeCount],
                    backgroundColor: ['#22C55E', '#EF4444'],
                    borderRadius: 8,
                    barThickness: 35
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: {
                        grid: { color: colors.grid },
                        ticks: { color: colors.text, stepSize: 1 }
                    },
                    x: {
                        grid: { display: false },
                        ticks: { color: colors.text }
                    }
                }
            }
        });
    }
    
    // 3. Aspects Frequency Horizontal Bar Chart
    const ctxAspect = document.getElementById('aspectsChart');
    if (ctxAspect) {
        const labels = Object.keys(aspectsData || {});
        const data = Object.values(aspectsData || {});
        
        aspectChartInstance = new Chart(ctxAspect, {
            type: 'bar',
            data: {
                labels: labels.length ? labels : ['battery', 'camera', 'screen', 'price'],
                datasets: [{
                    label: 'Mentions',
                    data: data.length ? data : [0, 0, 0, 0],
                    backgroundColor: '#2563EB',
                    borderRadius: 6,
                    barThickness: 20
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: {
                        grid: { color: colors.grid },
                        ticks: { color: colors.text, stepSize: 1 }
                    },
                    y: {
                        grid: { display: false },
                        ticks: { color: colors.text }
                    }
                }
            }
        });
    }
}

// Global hook for live theme switching
window.refreshChartsTheme = (newTheme) => {
    const colors = getThemeColors(newTheme);
    
    const updateChartOptions = (chart) => {
        if (!chart) return;
        
        // Update scales labels colors if present
        if (chart.options.scales) {
            if (chart.options.scales.x) {
                chart.options.scales.x.ticks.color = colors.text;
                if (chart.options.scales.x.grid) chart.options.scales.x.grid.color = colors.grid;
            }
            if (chart.options.scales.y) {
                chart.options.scales.y.ticks.color = colors.text;
                if (chart.options.scales.y.grid) chart.options.scales.y.grid.color = colors.grid;
            }
        }
        
        // Update legend labels
        if (chart.options.plugins && chart.options.plugins.legend && chart.options.plugins.legend.labels) {
            chart.options.plugins.legend.labels.color = colors.text;
        }
        
        // Update border colors on slices
        if (chart.data.datasets && chart.data.datasets[0]) {
            chart.data.datasets[0].borderColor = newTheme === 'dark' ? '#131A26' : '#FFFFFF';
        }
        
        chart.update();
    };
    
    updateChartOptions(sentimentChartInstance);
    updateChartOptions(authenticityChartInstance);
    updateChartOptions(aspectChartInstance);
};
