<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Activity, ArrowDownToLine, ArrowRight, ArrowUpRight, Bell, BookOpen, Check, ChevronLeft, ChevronRight, CircleHelp, CircuitBoard, Clock3, Cpu, Database, Droplets, ExternalLink, Gamepad2, History as HistoryIcon, LayoutDashboard, Menu, Radio, RefreshCw, Settings2, ShieldCheck, Terminal, Thermometer, Wifi, WifiOff, X, Zap } from 'lucide-vue-next'
import TemperatureChart from './components/TemperatureChart.vue'
import { demoData, demoDevice } from './demo'
import type { History, Mode, Period, Status } from './types'

type View = 'overview' | 'equipment' | 'history' | 'settings'
const view = ref<View>('overview')
const mode = ref<Mode>(new URLSearchParams(location.search).get('demo') === '1' ? 'demo' : 'live')
const period = ref<Period>('1h')
const scenario = ref<'normal' | 'warning' | 'critical' | 'offline'>('normal')
const status = ref<Status | null>(null)
const history = ref<History | null>(null)
const error = ref('')
const loading = ref(false)
const mobileMenu = ref(false)
const showGuide = ref(false)
const showHumidity = ref(false)
const historyFilter = ref('all')
const page = ref(0)
const toast = ref('')
const clock = ref(Date.now())
const lastResponseAt = ref(Date.now())
let previousFocus: HTMLElement | null = null
let refreshTimer: ReturnType<typeof setInterval>
let clockTimer: ReturnType<typeof setInterval>
let toastTimer: ReturnType<typeof setTimeout>
let requestVersion = 0
let controller: AbortController | undefined
const navigation = [
  { id: 'overview' as const, label: 'Visão geral', icon: LayoutDashboard },
  { id: 'equipment' as const, label: 'Meu arcade', icon: Gamepad2 },
  { id: 'history' as const, label: 'Histórico', icon: HistoryIcon },
  { id: 'settings' as const, label: 'Conexão e limites', icon: Settings2 },
]
const periods: { id: Period; label: string }[] = [{ id: '1h', label: '1 hora' }, { id: '6h', label: '6 horas' }, { id: '24h', label: '24 horas' }, { id: '7d', label: '7 dias' }]
const device = computed(() => status.value?.device ?? demoDevice)
const latest = computed(() => status.value?.latest)
const readings = computed(() => history.value?.readings ?? [])
const estimatedServerTime = computed(() => status.value ? Date.parse(status.value.server_time) + clock.value - lastResponseAt.value : clock.value)
const isFresh = computed(() => Boolean(!error.value && status.value?.online && latest.value && estimatedServerTime.value - Date.parse(latest.value.time) <= device.value.stale_after_seconds * 1000))
const temperature = computed(() => latest.value?.temperature)
const condition = computed(() => !isFresh.value ? 'offline' : thermal(temperature.value!))
const conditionLabel = computed(() => ({ normal: 'Tudo certo por aqui', warning: 'Atenção à temperatura', critical: 'Temperatura crítica', offline: error.value ? 'Conexão indisponível' : 'Aguardando o sensor' }[condition.value]))
const lastAge = computed(() => latest.value ? Math.max(0, Math.floor((estimatedServerTime.value - Date.parse(latest.value.time)) / 1000)) : null)
const sourceLabel = computed(() => (({ 'mqtt-simulator': 'MQTT · simulador Python', 'esp32-wokwi': 'ESP32 · Wokwi', 'esp32-physical': 'ESP32 físico' } as Record<string, string>)[latest.value?.source ?? ''] ?? 'Atualização a cada 5s'))
const ageText = computed(() => lastAge.value === null ? 'Nenhuma leitura recebida' : lastAge.value < 60 ? `há ${lastAge.value}s` : lastAge.value < 3600 ? `há ${Math.floor(lastAge.value / 60)} min` : `há ${Math.floor(lastAge.value / 3600)} h`)
const filtered = computed(() => [...readings.value].reverse().filter(r => historyFilter.value === 'all' || thermal(r.temperature) === historyFilter.value))
const visibleRows = computed(() => filtered.value.slice(page.value * 12, page.value * 12 + 12))
const pages = computed(() => Math.max(1, Math.ceil(filtered.value.length / 12)))
const events = computed(() => [...readings.value].reverse().filter(r => thermal(r.temperature) !== 'normal').slice(0, 3))
const stats = computed(() => history.value?.statistics)
const ring = computed(() => ({ '--gauge': `${Math.max(0, Math.min(100, ((temperature.value ?? 0) / device.value.critical_temperature) * 100))}%` }))

function thermal(value: number) { return value >= device.value.critical_temperature ? 'critical' : value >= device.value.warning_temperature ? 'warning' : 'normal' }
function number(value: number | null | undefined, decimals = 1) { return value == null ? '—' : value.toLocaleString('pt-BR', { minimumFractionDigits: decimals, maximumFractionDigits: decimals }) }
function date(value: string, full = false) { return new Date(value).toLocaleString('pt-BR', full ? { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' } : { hour: '2-digit', minute: '2-digit', second: '2-digit' }) }
function go(next: View) { view.value = next; mobileMenu.value = false }
function notify(message: string) { toast.value = message; clearTimeout(toastTimer); toastTimer = setTimeout(() => toast.value = '', 4000) }
async function refresh() {
  const version = ++requestVersion
  controller?.abort()
  if (mode.value === 'demo') {
    const data = demoData(period.value, scenario.value)
    lastResponseAt.value = Date.now(); status.value = data.status; history.value = data.history; error.value = ''; loading.value = false
    return
  }
  loading.value = true
  const active = new AbortController()
  controller = active
  const timeout = setTimeout(() => active.abort(), 8000)
  try {
    const base = (import.meta.env.VITE_API_BASE_URL ?? '/api').replace(/\/$/, '')
    const fetchJson = async (path: string) => {
      const response = await fetch(`${base}${path}`, { signal: active.signal })
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      return response.json()
    }
    const [nextStatus, nextHistory] = await Promise.all([fetchJson('/status'), fetchJson(`/history?period=${period.value}`)])
    if (version !== requestVersion) return
    lastResponseAt.value = Date.now(); status.value = nextStatus; history.value = nextHistory; error.value = ''
  } catch {
    if (version === requestVersion) error.value = 'Não foi possível consultar os dados. Verifique o backend Python e o InfluxDB. As últimas leituras, se houver, estão desatualizadas.'
  } finally {
    clearTimeout(timeout)
    if (version === requestVersion) loading.value = false
  }
}
function exportCsv() {
  if (!readings.value.length) return
  const content = ['data_utc;temperatura_c;umidade_percentual;origem;modo', ...readings.value.map(r => `${r.time};${r.temperature};${r.humidity};${r.source};${mode.value}`)].join('\r\n')
  const url = URL.createObjectURL(new Blob(['\ufeff', content], { type: 'text/csv;charset=utf-8;' }))
  const link = document.createElement('a'); link.href = url; link.download = `arcadeos-${mode.value}-${period.value}.csv`; link.click(); URL.revokeObjectURL(url)
  notify(`Histórico exportado · ${readings.value.length} amostras`)
}
function keyboard(event: KeyboardEvent) {
  if (event.key === 'Escape') { showGuide.value = false; mobileMenu.value = false }
  if (event.key === 'Tab' && showGuide.value) {
    const focusable = [...document.querySelectorAll<HTMLElement>('.guide-modal button, .guide-modal a')]
    const first = focusable[0], last = focusable.at(-1)
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus() }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus() }
  }
}
watch(showGuide, async open => {
  if (open) { previousFocus = document.activeElement as HTMLElement; await nextTick(); document.querySelector<HTMLElement>('.guide-modal button')?.focus() }
  else previousFocus?.focus()
})
watch([mode, period, scenario], () => { status.value = null; history.value = null; page.value = 0; refresh() })
watch(historyFilter, () => page.value = 0)
watch(pages, value => { if (page.value >= value) page.value = value - 1 })
onMounted(() => { refresh(); refreshTimer = setInterval(() => { if (!loading.value) refresh() }, 5000); clockTimer = setInterval(() => clock.value = Date.now(), 1000); window.addEventListener('keydown', keyboard) })
onBeforeUnmount(() => { clearInterval(refreshTimer); clearInterval(clockTimer); clearTimeout(toastTimer); controller?.abort(); window.removeEventListener('keydown', keyboard) })
</script>

<template>
  <div class="app-shell">
    <button v-if="mobileMenu" class="sidebar-backdrop" aria-label="Fechar menu" @click="mobileMenu = false"></button>
    <aside class="sidebar" :class="{ open: mobileMenu }">
      <a href="#" class="brand" @click.prevent="go('overview')"><span class="brand-icon"><Gamepad2 :size="24" /></span><span>Arcade<span class="accent">OS</span><small>KEEP THE GAME ALIVE</small></span></a>
      <div class="workspace-label"><span class="workspace-dot"></span> Meu espaço <span class="version-tag">BETA</span></div>
      <p class="nav-caption">CENTRAL DE CONTROLE</p>
      <nav aria-label="Navegação principal"><button v-for="item in navigation" :key="item.id" :class="{ active: view === item.id }" :aria-current="view === item.id ? 'page' : undefined" @click="go(item.id)"><component :is="item.icon" :size="18" /><span>{{ item.label }}</span><span v-if="item.id === 'equipment'" class="nav-count">01</span></button></nav>
      <div class="sidebar-bottom">
        <div class="project-card"><CircuitBoard :size="22" /><p>Hardware encontra<br />o próximo nível.</p><span>PROJETO IoT · 1º BIMESTRE</span></div>
        <button class="help-button" @click="showGuide = true"><CircleHelp :size="17" /> Guia do projeto <ArrowUpRight :size="15" /></button>
        <div class="profile"><span class="avatar">P1</span><div><strong>Player One</strong><small>Administrador local</small></div><span class="profile-dot"></span></div>
      </div>
    </aside>

    <div class="main-shell">
      <header class="topbar">
        <div class="breadcrumb"><button class="icon-button mobile-toggle" aria-label="Abrir menu" @click="mobileMenu = true"><Menu :size="20" /></button><span>Workspace</span><ChevronRight :size="13" /><strong>{{ navigation.find(n => n.id === view)?.label }}</strong></div>
        <div class="topbar-actions"><span class="today">{{ new Date(clock).toLocaleDateString('pt-BR', { day: '2-digit', month: 'short', year: 'numeric' }) }}</span><span class="topbar-divider"></span><button class="icon-button" aria-label="Ver leituras em atenção" @click="go('history'); historyFilter = 'warning'"><Bell :size="18" /></button><span class="avatar small">P1</span></div>
      </header>

      <main>
        <div class="page-heading"><div><div class="eyebrow"><span></span> ARCADEOS / {{ view === 'overview' ? 'MISSION CONTROL' : view.toUpperCase() }}</div><h1>{{ view === 'overview' ? 'Seu arcade, sob controle.' : view === 'equipment' ? 'Conheça seu Player One.' : view === 'history' ? 'Cada leitura conta.' : 'Tudo conectado.' }}</h1><p>{{ view === 'overview' ? 'Acompanhe os sinais vitais da máquina. Deixe o jogo continuar.' : view === 'equipment' ? 'Um olhar sobre o hardware que mantém a diversão viva.' : view === 'history' ? 'Explore as medições e acompanhe o comportamento do gabinete.' : 'Confira o caminho dos dados e os limites do monitoramento.' }}</p></div><button class="button secondary export-top" :disabled="!readings.length" @click="exportCsv"><ArrowDownToLine :size="16" /> Exportar dados</button></div>

        <div class="control-strip"><div class="mode-control" aria-label="Origem dos dados"><button :class="{ selected: mode === 'live' }" :aria-pressed="mode === 'live'" @click="mode = 'live'"><Radio :size="14" /> Conexão IoT</button><button :class="{ selected: mode === 'demo' }" :aria-pressed="mode === 'demo'" @click="mode = 'demo'"><Gamepad2 :size="14" /> Demonstração</button></div><div class="refresh-status"><span :class="['tiny-dot', { green: isFresh }]" /> {{ mode === 'demo' ? 'Dados fictícios' : loading ? 'Consultando…' : sourceLabel }}<button class="icon-button" aria-label="Atualizar dados" :disabled="loading" @click="refresh"><RefreshCw :size="14" :class="{ spinning: loading }" /></button></div></div>
        <div v-if="mode === 'demo'" class="demo-banner"><div><Zap :size="16" /><span><strong>Modo de demonstração.</strong> Dados gerados no navegador, sem MQTT ou InfluxDB.</span></div><label>Cenário <select v-model="scenario"><option value="normal">Normal</option><option value="warning">Aquecimento</option><option value="critical">Crítico</option><option value="offline">Sem conexão</option></select></label></div>
        <div v-if="error" class="error-banner" role="alert"><WifiOff :size="18" /><span>{{ error }}</span><button @click="showGuide = true">Como conectar <ArrowRight :size="14" /></button></div>

        <template v-if="view === 'overview'">
          <section class="stats-grid" aria-label="Indicadores do gabinete">
            <article class="metric-card"><div class="metric-label">Temperatura atual <Thermometer :size="18" /></div><div class="metric-value">{{ number(temperature) }}<span>°C</span></div><div class="metric-bottom"><span :class="['status-pill', condition]"><span class="tiny-dot" />{{ !isFresh ? 'Sem leitura atual' : condition === 'normal' ? 'Dentro do limite' : condition === 'warning' ? 'Atenção' : 'Crítico' }}</span><span>Ar do gabinete</span></div></article>
            <article class="metric-card"><div class="metric-label">Umidade do ar <Droplets :size="18" /></div><div class="metric-value">{{ number(latest?.humidity) }}<span>%</span></div><div class="metric-bottom"><span class="muted-text">Umidade relativa</span><span class="sensor-tag">DHT22</span></div></article>
            <article class="metric-card"><div class="metric-label">Pico no período <Activity :size="18" /></div><div class="metric-value">{{ number(stats?.maximum) }}<span>°C</span></div><div class="metric-bottom"><span class="muted-text">{{ mode === 'demo' ? 'Exemplo ilustrativo' : 'Máximo das leituras brutas' }}</span><span>{{ periods.find(p => p.id === period)?.label }}</span></div></article>
            <article class="metric-card"><div class="metric-label">Estado do sensor <Wifi :size="18" /></div><div class="metric-value status-value" :class="{ accent: isFresh }"><span :class="['connection-light', { green: isFresh }]" />{{ isFresh ? 'Online' : 'Offline' }}</div><div class="metric-bottom"><span class="muted-text">Última leitura</span><span>{{ ageText }}</span></div></article>
          </section>

          <div class="dashboard-grid">
            <section class="panel history-panel"><div class="panel-heading"><div><h2>Temperatura ao longo do tempo</h2><p>O ritmo do seu arcade, leitura por leitura.</p></div><div class="period-control" aria-label="Período do gráfico"><button v-for="p in periods" :key="p.id" :class="{ selected: period === p.id }" :aria-pressed="period === p.id" @click="period = p.id">{{ p.id }}</button></div></div><div class="chart-legend"><span><i class="legend-dot lime"></i> Temperatura</span><span><i class="legend-line amber"></i> Atenção · {{ device.warning_temperature }}°C</span><span><i class="legend-line red"></i> Crítico · {{ device.critical_temperature }}°C</span></div><TemperatureChart v-if="readings.length" :readings="readings" :warning="device.warning_temperature" :critical="device.critical_temperature" :show-humidity="false" /><div v-else class="chart-empty"><Activity :size="30" /><strong>{{ loading ? 'Buscando as primeiras leituras…' : 'O próximo sinal começa aqui.' }}</strong><span>Conecte seu ESP32 ou explore o modo de demonstração.</span></div><div class="chart-footer"><span><Clock3 :size="13" /> {{ mode === 'demo' ? 'Histórico ilustrativo' : `InfluxDB · resolução ${history?.resolution ?? '—'}` }}</span><button class="text-link" @click="go('history')">Explorar histórico <ArrowUpRight :size="14" /></button></div></section>

            <section class="panel guardian-panel"><div class="panel-heading"><h2>Guardian status</h2><ShieldCheck :size="18" class="muted-text" /></div><div class="gauge" :class="condition" :style="ring"><div class="gauge-inner"><Gamepad2 :size="35" /><strong>{{ number(temperature) }}<small>°C</small></strong><span>AR DO GABINETE</span></div></div><h3 :class="{ accent: condition === 'normal' }">{{ conditionLabel }}</h3><p>{{ condition === 'normal' ? 'Temperatura abaixo do limite de atenção configurado.' : condition === 'warning' ? 'Acompanhe a evolução e confira a ventilação do gabinete.' : condition === 'critical' ? 'Verifique o equipamento e a ventilação do gabinete.' : 'O status será atualizado quando novas leituras chegarem.' }}</p><div class="guardian-threshold"><span>Limite de atenção</span><strong>{{ device.warning_temperature }} °C</strong></div><button class="text-link" @click="go('settings')">Ver limites de monitoramento <ArrowRight :size="14" /></button></section>

            <section class="panel device-panel"><div class="panel-heading"><h2>Seu equipamento <span class="small-count">01</span></h2><button class="text-link" @click="go('equipment')">Ver detalhes <ArrowUpRight :size="14" /></button></div><div class="device-row"><div class="device-icon"><Gamepad2 :size="32" /></div><div class="device-name"><h3>{{ device.name }}</h3><p>{{ device.location }} <span>·</span> {{ device.id }}</p><div class="device-chips"><span><Cpu :size="12" /> ESP32</span><span><Thermometer :size="12" /> DHT22</span></div></div><span :class="['status-pill', isFresh ? 'normal' : 'offline']"><span class="tiny-dot" />{{ isFresh ? 'Online' : 'Sem sinal' }}</span></div><div class="device-panel-footer"><span><Radio :size="13" /> {{ mode === 'demo' ? 'Conexão ilustrativa' : 'Telemetria via MQTT' }}</span><span>Intervalo esperado: 5s</span></div></section>

            <section class="panel events-panel"><div class="panel-heading"><h2>Leituras em atenção</h2><span class="small-count">{{ events.length }}</span></div><div v-if="!events.length" class="no-events"><Check :size="23" /><div><strong>{{ readings.length ? 'Nenhuma na amostragem' : 'Aguardando dados' }}</strong><p>{{ readings.length ? 'Sem valores acima do limite neste gráfico.' : 'As leituras aparecerão por aqui.' }}</p></div></div><div v-for="event in events" :key="event.time" class="event-row"><span :class="['event-icon', thermal(event.temperature)]"><Thermometer :size="15" /></span><div><strong>{{ thermal(event.temperature) === 'critical' ? 'Limite crítico atingido' : 'Temperatura elevada' }}</strong><span>{{ number(event.temperature) }} °C · {{ device.name }}</span></div><time>{{ date(event.time).slice(0, 5) }}</time></div><span class="events-note">{{ mode === 'demo' ? 'Eventos fictícios para apresentação.' : 'Últimas ocorrências na amostragem do gráfico.' }}</span></section>
          </div>
          <section class="pipeline-bar"><span class="pipeline-title"><CircuitBoard :size="16" /> O caminho de cada leitura</span><div><span>ESP32</span><ChevronRight :size="13" /><span>MQTT / Mosquitto</span><ChevronRight :size="13" /><span>Python</span><ChevronRight :size="13" /><span>InfluxDB</span><ChevronRight :size="13" /><strong>ArcadeOS <Zap :size="12" /></strong></div></section>
        </template>

        <template v-else-if="view === 'equipment'">
          <div class="equipment-grid"><section class="panel equipment-main"><div class="large-device-icon"><Gamepad2 :size="65" /></div><span class="eyebrow">PLAYER 01 / GABINETE MONITORADO</span><h2>{{ device.name }}</h2><p>{{ device.location }}</p><span :class="['status-pill', isFresh ? 'normal' : 'offline']">{{ isFresh ? 'Recebendo leituras' : 'Aguardando telemetria' }}</span><div class="equipment-readings"><div><Thermometer :size="20" /><strong>{{ number(temperature) }} °C</strong><span>Temperatura do ar</span></div><div><Droplets :size="20" /><strong>{{ number(latest?.humidity) }} %</strong><span>Umidade relativa</span></div></div></section><section class="panel specification"><div class="panel-heading"><h2>Ficha do hardware</h2><Cpu :size="20" /></div><dl><div><dt>Identificador</dt><dd>{{ device.id }}</dd></div><div><dt>Microcontrolador</dt><dd>ESP32 DevKit V1</dd></div><div><dt>Sensor</dt><dd>DHT22 · GPIO 4</dd></div><div><dt>Protocolo</dt><dd>MQTT 3.1.1</dd></div><div><dt>Broker</dt><dd>Eclipse Mosquitto</dd></div><div><dt>Origem da última leitura</dt><dd>{{ latest?.source ?? 'Ainda sem dados' }}</dd></div><div><dt>Última leitura</dt><dd>{{ latest ? date(latest.time, true) : '—' }}</dd></div></dl><div class="info-box"><ShieldCheck :size="20" /><p>O sensor acompanha o <strong>ar dentro do gabinete</strong>. Ele não mede diretamente a temperatura da CPU ou da GPU.</p></div><button class="button secondary" @click="showGuide = true"><BookOpen :size="16" /> Como conectar o ESP32</button></section></div>
          <section class="panel roadmap"><div><span class="eyebrow">PRÓXIMA FASE</span><h2>Preparado para subir de nível.</h2><p>Possibilidades para o 2º bimestre. Ainda não implementadas.</p></div><div><span><Wifi :size="18" /> Comandos bidirecionais</span><span><Zap :size="18" /> Controle de ventilação</span><span><Database :size="18" /> Cadastro de equipamentos</span></div></section>
        </template>

        <template v-else-if="view === 'history'">
          <section class="panel"><div class="panel-heading"><div><h2>Histórico de medições</h2><p>{{ mode === 'demo' ? 'Amostras fictícias do modo de demonstração.' : 'Dados persistidos no InfluxDB. Horários exibidos no fuso do navegador.' }}</p></div><select v-model="period" aria-label="Período do histórico"><option v-for="p in periods" :key="p.id" :value="p.id">Últimas {{ p.label }}</option></select></div><div class="history-controls"><label class="checkbox-label"><input type="checkbox" v-model="showHumidity" /> Mostrar umidade no gráfico</label><span>Resolução: {{ history?.resolution ?? '—' }}</span></div><TemperatureChart v-if="readings.length" :readings="readings" :warning="device.warning_temperature" :critical="device.critical_temperature" :show-humidity="showHumidity" /><div v-else class="chart-empty"><Database :size="32" /><strong>Nenhuma leitura neste período</strong><span>Verifique a conexão ou selecione outro intervalo.</span></div><div class="history-summary"><span>Mínima <strong>{{ number(stats?.minimum) }} °C</strong></span><span>Média <strong>{{ number(stats?.average) }} °C</strong></span><span>Máxima <strong>{{ number(stats?.maximum) }} °C</strong></span><span>Leituras brutas <strong>{{ stats?.count ?? 0 }}</strong></span></div></section>
          <section class="panel table-panel"><div class="panel-heading"><div><h2>Amostras do período</h2><p>O CSV contém a mesma amostragem do gráfico, com horários em UTC.</p></div><select v-model="historyFilter" aria-label="Filtrar por temperatura"><option value="all">Todas as situações</option><option value="normal">Normal</option><option value="warning">Atenção</option><option value="critical">Crítico</option></select></div><div class="table-scroll"><table><thead><tr><th>Data e horário</th><th>Temperatura</th><th>Umidade</th><th>Situação térmica</th><th>Origem</th></tr></thead><tbody><tr v-for="row in visibleRows" :key="row.time"><td>{{ date(row.time, true) }}</td><td class="table-temperature">{{ number(row.temperature) }} °C</td><td>{{ number(row.humidity) }} %</td><td><span :class="['status-pill', thermal(row.temperature)]">{{ { normal: 'Normal', warning: 'Atenção', critical: 'Crítico' }[thermal(row.temperature)] }}</span></td><td><code>{{ row.source }}</code></td></tr><tr v-if="!visibleRows.length"><td colspan="5" class="empty-table">Nenhuma amostra para este filtro.</td></tr></tbody></table></div><div class="pagination"><span>{{ filtered.length }} amostras · página {{ page + 1 }} de {{ pages }}</span><div><button class="icon-button" :disabled="page === 0" aria-label="Página anterior" @click="page--"><ChevronLeft :size="18" /></button><button class="icon-button" :disabled="page >= pages - 1" aria-label="Próxima página" @click="page++"><ChevronRight :size="18" /></button></div></div></section>
        </template>

        <template v-else>
          <div class="settings-grid"><section class="panel specification"><div class="panel-heading"><h2>Diagnóstico da conexão</h2><Radio :size="20" /></div><p class="settings-intro">{{ mode === 'demo' ? 'Estados ilustrativos. Ative Conexão IoT para verificar os serviços reais.' : 'Situação dos serviços informada pelo backend Python.' }}</p><dl><div><dt>API Python</dt><dd :class="status && !error ? 'accent' : 'muted-text'">{{ mode === 'demo' ? 'Simulada' : status && !error ? 'Disponível' : 'Indisponível' }}</dd></div><div><dt>MQTT / Mosquitto</dt><dd>{{ mode === 'demo' ? 'Simulado' : status?.mqtt_connected && !error ? 'Conectado' : 'Sem conexão' }}</dd></div><div><dt>InfluxDB</dt><dd>{{ mode === 'demo' ? 'Simulado' : status?.influx_connected && !error ? 'Disponível' : 'Sem conexão' }}</dd></div><div><dt>Gravadas nesta sessão</dt><dd>{{ status?.received ?? '—' }}</dd></div><div><dt>Mensagens rejeitadas</dt><dd>{{ status?.rejected ?? '—' }}</dd></div><div><dt>Falhas de gravação</dt><dd>{{ status?.write_failures ?? '—' }}</dd></div></dl><div v-if="status?.last_error" class="info-box">{{ status.last_error }}</div><button class="button secondary" @click="refresh"><RefreshCw :size="16" /> Verificar novamente</button></section><section class="panel specification"><div class="panel-heading"><h2>Limites do Guardian</h2><ShieldCheck :size="20" /></div><p class="settings-intro">Valores didáticos configurados no backend. Ajuste conforme o equipamento e as orientações do fabricante.</p><dl><div><dt><span class="tiny-dot green" /> Normal</dt><dd>Abaixo de {{ device.warning_temperature }} °C</dd></div><div><dt><span class="tiny-dot amber-bg" /> Atenção</dt><dd>{{ device.warning_temperature }} a menos de {{ device.critical_temperature }} °C</dd></div><div><dt><span class="tiny-dot red-bg" /> Crítico</dt><dd>A partir de {{ device.critical_temperature }} °C</dd></div><div><dt>Sensor sem sinal</dt><dd>Após {{ device.stale_after_seconds }} segundos</dd></div></dl><div class="info-box"><Terminal :size="20" /><p>Edite <code>backend/.env</code> e reinicie o Python para alterar estes limites. O painel não aciona ventiladores nesta etapa.</p></div></section></div>
          <section class="panel architecture"><div class="panel-heading"><div><h2>Do sensor até a tela</h2><p>Todas as camadas da primeira entrega.</p></div><CircuitBoard :size="22" /></div><div class="architecture-nodes"><div><Cpu /><strong>ESP32 + DHT22</strong><span>Gera a leitura</span></div><ArrowRight /><div><Radio /><strong>Mosquitto</strong><span>Distribui via MQTT</span></div><ArrowRight /><div><Terminal /><strong>Python</strong><span>Valida e processa</span></div><ArrowRight /><div><Database /><strong>InfluxDB</strong><span>Persiste o histórico</span></div><ArrowRight /><div><LayoutDashboard /><strong>Vue + Chart.js</strong><span>Apresenta os dados</span></div></div></section>
        </template>
        <footer class="page-footer"><span><Gamepad2 :size="14" /> ArcadeOS <span>v0.1.0</span></span><span>BUILT FOR THE LOVE OF THE GAME <span class="footer-pixel">✦</span></span></footer>
      </main>
    </div>
    <div v-if="toast" class="toast" role="status"><Check :size="18" />{{ toast }}</div>
    <div v-if="showGuide" class="modal-backdrop" @click.self="showGuide = false"><section class="guide-modal" role="dialog" aria-modal="true" aria-labelledby="guide-title"><div class="panel-heading"><span class="eyebrow">QUICK START</span><button class="icon-button" aria-label="Fechar guia" autofocus @click="showGuide = false"><X :size="20" /></button></div><h2 id="guide-title">Hora de conectar seu arcade.</h2><p>O modo IoT precisa dos serviços locais e de um dispositivo publicando leituras.</p><ol><li><strong>Inicie Mosquitto e InfluxDB 2.</strong><span>Use as configurações em <code>infra/</code> e o passo a passo do README.</span></li><li><strong>Configure e inicie o Python.</strong><span>Preencha <code>backend/.env</code> e execute <code>python -m uvicorn app.main:app --app-dir backend</code>.</span></li><li><strong>Conecte o ESP32 no Wokwi.</strong><span>Os arquivos estão em <code>firmware/arcadeos/</code>. O broker deve estar acessível ao simulador.</span></li><li><strong>Ative “Conexão IoT”.</strong><span>Altere a temperatura no sensor e acompanhe a nova leitura no painel.</span></li></ol><div class="info-box"><Wifi :size="20" /><p>O Wokwi público não acessa o <code>localhost</code>. Use o gateway privado ou um Mosquitto remoto protegido. Consulte <code>docs/WOKWI.md</code>.</p></div><a class="button primary" href="https://docs.wokwi.com/guides/esp32-wifi" target="_blank" rel="noopener noreferrer">Documentação do Wokwi <ExternalLink :size="15" /></a></section></div>
  </div>
</template>
