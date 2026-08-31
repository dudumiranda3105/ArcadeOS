export type Period = '1h' | '6h' | '24h' | '7d'
export type Mode = 'live' | 'demo'
export type ThermalStatus = 'normal' | 'warning' | 'critical'
export interface Reading {
  time: string
  temperature: number
  humidity: number
  source: string
}
export interface Device {
  id: string
  name: string
  location: string
  sensor: string
  warning_temperature: number
  critical_temperature: number
  stale_after_seconds: number
}
export interface Status {
  device: Device
  latest: Reading | null
  online: boolean
  thermal_status: ThermalStatus | null
  mqtt_connected: boolean
  influx_connected: boolean
  received: number
  rejected: number
  write_failures: number
  last_error: string | null
  server_time: string
}
export interface History {
  readings: Reading[]
  period: Period
  resolution: string
  statistics: { minimum: number | null; maximum: number | null; average: number | null; count: number }
}
