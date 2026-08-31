<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Chart, LineController, LineElement, PointElement, CategoryScale, LinearScale, Filler, Tooltip, Legend } from 'chart.js'
import type { Reading } from '../types'
Chart.register(LineController, LineElement, PointElement, CategoryScale, LinearScale, Filler, Tooltip, Legend)
const props = defineProps<{ readings: Reading[]; warning: number; critical: number; showHumidity: boolean }>()
const canvas = ref<HTMLCanvasElement | null>(null)
let chart: Chart<'line'> | undefined
function draw() {
  if (!canvas.value) return
  const ctx = canvas.value.getContext('2d')!
  const gradient = ctx.createLinearGradient(0, 0, 0, 290)
  gradient.addColorStop(0, 'rgba(183,244,83,.2)')
  gradient.addColorStop(1, 'rgba(183,244,83,0)')
  const datasets = [
    { label: 'Temperatura (°C)', data: props.readings.map(r => r.temperature), borderColor: '#b7f453', backgroundColor: gradient, fill: true, borderWidth: 2, tension: .32, pointRadius: 0, pointHitRadius: 12, yAxisID: 'y' },
    { label: 'Atenção (°C)', data: props.readings.map(() => props.warning), borderColor: '#ad8546', borderWidth: 1, borderDash: [5, 5], pointRadius: 0, fill: false, yAxisID: 'y' },
    { label: 'Crítico (°C)', data: props.readings.map(() => props.critical), borderColor: '#a75658', borderWidth: 1, borderDash: [5, 5], pointRadius: 0, fill: false, yAxisID: 'y' },
    ...(props.showHumidity ? [{ label: 'Umidade (%)', data: props.readings.map(r => r.humidity), borderColor: '#79b2ff', borderWidth: 2, pointRadius: 0, fill: false, tension: .3, yAxisID: 'humidity' }] : []),
  ]
  const labels = props.readings.map(r => new Date(r.time).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }))
  if (chart) {
    chart.data.labels = labels
    chart.data.datasets = datasets
    chart.options.scales!.humidity!.display = props.showHumidity
    chart.update('none')
    return
  }
  chart = new Chart(canvas.value, {
    type: 'line', data: { labels, datasets },
    options: {
      responsive: true, maintainAspectRatio: false, animation: false,
      interaction: { mode: 'index', intersect: false },
      plugins: { legend: { display: false }, tooltip: { backgroundColor: '#24282e', titleColor: '#f2f3f4', bodyColor: '#cbd0d6', padding: 12, filter: item => item.datasetIndex === 0 || item.datasetIndex === 3 } },
      scales: {
        x: { grid: { display: false }, border: { display: false }, ticks: { color: '#7e858f', maxTicksLimit: 7, maxRotation: 0, font: { size: 10 }, callback: function(value) { const label = this.getLabelForValue(Number(value)); return props.readings.length > 1 && new Date(props.readings.at(-1)!.time).getTime() - new Date(props.readings[0]!.time).getTime() > 86400000 ? label.slice(0, 5) : label.slice(-5) } } },
        y: { suggestedMin: 20, suggestedMax: 45, grid: { color: '#272b30' }, border: { display: false, dash: [3, 4] }, ticks: { color: '#7e858f', stepSize: 5, font: { size: 10 }, callback: value => `${value}°` } },
        humidity: { display: props.showHumidity, position: 'right', min: 0, max: 100, grid: { display: false }, ticks: { color: '#79b2ff', callback: value => `${value}%` }, border: { display: false } },
      },
    },
  })
}
onMounted(draw)
watch(() => [props.readings, props.showHumidity, props.warning, props.critical], draw)
onBeforeUnmount(() => chart?.destroy())
</script>

<template>
  <div class="chart-canvas"><canvas ref="canvas" role="img" aria-label="Histórico de temperatura do gabinete. Os mesmos dados estão disponíveis na tela Histórico e na exportação CSV."></canvas></div>
</template>
