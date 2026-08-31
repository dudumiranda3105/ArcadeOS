import type { Device, History, Period, Reading, Status } from './types'

export const demoDevice: Device = {
  id: 'arcade-01', name: 'Player One', location: 'Gabinete principal', sensor: 'ESP32 + DHT22',
  warning_temperature: 35, critical_temperature: 40, stale_after_seconds: 30,
}
export function demoData(period: Period, scenario: 'normal' | 'warning' | 'critical' | 'offline'): { status: Status; history: History } {
  const now = Date.now()
  const duration = { '1h': 3600, '6h': 21600, '24h': 86400, '7d': 604800 }[period]
  const readings: Reading[] = Array.from({ length: 121 }, (_, i) => {
    const base = 28.8 + Math.sin(i / 8) * 1.8 + Math.sin(i / 2.5) * 0.5
    const peak = i > 91 && i < 106 ? Math.sin((i - 91) / 15 * Math.PI) * 8 : 0
    const target = scenario === 'critical' ? 42.3 : scenario === 'warning' ? 37.2 : 29.4
    const temperature = i > 112 ? base + (target - base) * ((i - 112) / 8) : base + peak
    return {
      time: new Date(now - ((120 - i) / 120) * duration * 1000 - (scenario === 'offline' ? 90000 : 0)).toISOString(),
      temperature: Math.round(temperature * 10) / 10,
      humidity: Math.round((47 + Math.sin(i / 12) * 3) * 10) / 10,
      source: 'demo-browser',
    }
  })
  const values = readings.map(r => r.temperature)
  return {
    status: {
      device: demoDevice, latest: readings.at(-1)!, online: scenario !== 'offline',
      thermal_status: scenario === 'offline' ? 'normal' : scenario,
      mqtt_connected: true, influx_connected: true, received: readings.length,
      rejected: 0, write_failures: 0, last_error: null, server_time: new Date(now).toISOString(),
    },
    history: { readings, period, resolution: 'amostras ilustrativas', statistics: {
      minimum: Math.min(...values), maximum: Math.max(...values),
      average: values.reduce((a, b) => a + b, 0) / values.length, count: values.length,
    } },
  }
}
