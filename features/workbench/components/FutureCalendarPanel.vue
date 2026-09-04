<template>
	<aside
		class="calendar-panel glass"
		:class="{ collapsed: !expanded }"
		:role="expanded ? undefined : 'button'"
		:tabindex="expanded ? undefined : 0"
		:title="expanded ? undefined : '点击展开'"
		:aria-label="expanded ? undefined : '点击展开'"
		@click="onCollapsedStripClick"
		@keydown.enter.prevent="onCollapsedStripClick"
		@keydown.space.prevent="onCollapsedStripClick"
	>
		<button type="button" class="collapse-btn" @click.stop="$emit('update:expanded', !expanded)">
			<el-icon class="collapse-icon"><ArrowRight v-if="expanded" /><ArrowLeft v-else /></el-icon>
		</button>

		<div v-if="expanded" class="panel-inner">
			<div class="cal-upper">
				<header class="cal-header">
					<div class="cal-header-top">
						<div class="cal-title">
							<span class="cal-icon" aria-hidden="true">
								<el-icon><Calendar /></el-icon>
							</span>
							<div>
								<h3>交易日历</h3>
								<p>交割 · 宏观 · 策略分层标记</p>
							</div>
						</div>
						<el-select v-model="exchange" size="small" class="exchange-select">
							<el-option v-for="item in tradeCalExchanges" :key="item.value" :label="item.label" :value="item.value" />
						</el-select>
					</div>
				</header>

				<div class="month-bar">
					<button type="button" class="nav-btn" aria-label="上个月" @click="shiftMonth(-1)">
						<el-icon><ArrowLeft /></el-icon>
					</button>
					<div class="month-display">
						<strong>{{ year }}年{{ month }}月</strong>
					</div>
					<button type="button" class="nav-btn" aria-label="下个月" @click="shiftMonth(1)">
						<el-icon><ArrowRight /></el-icon>
					</button>
					<el-button size="small" class="today-btn" @click="goToday">今天</el-button>
				</div>

				<div class="filter-row">
					<div class="filter-tags">
						<button
							v-for="tag in filterTags"
							:key="tag.key"
							type="button"
							class="filter-chip"
							:class="{ 'is-active': calendarFilters[tag.key] }"
							:aria-pressed="calendarFilters[tag.key]"
							@click="calendarFilters[tag.key] = !calendarFilters[tag.key]"
						>
							{{ tag.label }}
						</button>
					</div>
				</div>

				<div class="calendar-shell" v-loading="calendarLoading">
					<div class="mark-legend" aria-label="标记图例">
						<span><i class="leg delivery" />交割</span>
						<span><i class="leg macro" />宏观</span>
						<span><i class="leg strategy" />策略</span>
						<span><i class="leg fee" />费率</span>
					</div>
					<div class="weekday-row">
						<span v-for="(label, index) in weekdays" :key="label" :class="{ weekend: index >= 5 }">{{ label }}</span>
					</div>
					<div class="calendar-grid">
						<div v-for="cell in monthCells" :key="cell.key" class="cell-slot">
							<button
								v-if="cell.date && cell.visible"
								type="button"
								class="day-cell"
								:class="{
									today: cell.isToday,
									selected: cell.date === selectedDate && !cell.isToday,
									weekend: cell.isWeekend,
									closed: cell.isClosed,
								}"
								@click="selectedDate = cell.date"
							>
								<span class="day-num" :class="{ strike: cell.isClosed }">{{ cell.day }}</span>
								<div v-if="cell.hasMarkers" class="marker-row">
									<span v-if="cell.markers.delivery" class="m-dot delivery" />
									<span v-if="cell.markers.macro" class="m-dot macro" />
									<span v-if="cell.markers.strategy" class="m-dot strategy" />
									<span v-if="cell.markers.fee" class="m-dot fee" />
								</div>
							</button>
						</div>
					</div>
				</div>
			</div>

			<div class="cal-lower detail-panel">
				<div class="detail-header">
					<h4>{{ selectedDate }}</h4>
					<span class="detail-badge">日详情</span>
				</div>

				<div class="detail-blocks">
					<section class="detail-block">
						<h5>主力合约交割</h5>
						<ul v-if="dayDetail.delivery.length" class="detail-list">
							<li v-for="item in dayDetail.delivery" :key="item.contract">
								<span>{{ item.name }}</span>
								<span class="detail-meta">{{ item.exchange }} · 剩余 {{ item.daysLeft }} 天</span>
							</li>
						</ul>
						<p v-else class="detail-empty">暂无交割提醒</p>
					</section>

					<section class="detail-block">
						<h5>交易时段</h5>
						<div class="session-list">
							<div v-for="item in dayDetail.sessions" :key="item.label" class="session-item">
								<span class="session-label">{{ item.label }}</span>
								<span class="session-time">{{ item.time }}</span>
							</div>
						</div>
					</section>

					<section class="detail-block">
						<h5>财经事件</h5>
						<ul v-if="dayDetail.macroEvents.length" class="detail-list">
							<li v-for="item in dayDetail.macroEvents" :key="item.name">
								<span>{{ item.name }}</span>
								<span class="detail-meta">{{ item.countdown }} · {{ item.impact }}</span>
							</li>
						</ul>
						<p v-else class="detail-empty">暂无宏观事件</p>
					</section>

					<section class="detail-block">
						<h5>运行策略</h5>
						<ul v-if="dayDetail.strategies.length" class="detail-list">
							<li v-for="item in dayDetail.strategies" :key="item.id">
								<span>{{ item.name }}</span>
								<span class="detail-meta" :class="item.expectedPnl >= 0 ? 'up' : 'down'">
									预估 {{ item.expectedPnl >= 0 ? '+' : '' }}{{ item.expectedPnl.toLocaleString() }}
								</span>
							</li>
						</ul>
						<p v-else class="detail-empty">暂无策略排期</p>
					</section>

					<section class="detail-block detail-block-wide">
						<h5>历史同日期回测</h5>
						<div class="backtest-stats">
							<div class="stat-chip">
								<span>去年</span>
								<strong>{{ (dayDetail.backtestCompare.lastYear * 100).toFixed(1) }}%</strong>
							</div>
							<div class="stat-chip">
								<span>前年</span>
								<strong>{{ (dayDetail.backtestCompare.twoYearsAgo * 100).toFixed(1) }}%</strong>
							</div>
							<div class="stat-chip">
								<span>均值</span>
								<strong>{{ (dayDetail.backtestCompare.avg * 100).toFixed(1) }}%</strong>
							</div>
						</div>
					</section>
				</div>
			</div>
		</div>

		<div v-else class="collapsed-label">日历</div>
	</aside>
</template>

<script setup lang="ts" name="FutureCalendarPanel">
import { ArrowLeft, ArrowRight, Calendar } from '@element-plus/icons-vue';
import { buildCalendarEvents, calendarDayDetail, tradeCalExchanges } from '../mockData';

const props = defineProps<{
	expanded: boolean;
}>();

const emit = defineEmits<{
	'update:expanded': [value: boolean];
}>();

const onCollapsedStripClick = () => {
	if (!props.expanded) emit('update:expanded', true);
};

const now = new Date();
const year = ref(now.getFullYear());
const month = ref(now.getMonth() + 1);
const exchange = ref('SHFE');
const selectedDate = ref(
	`${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`,
);
const calendarLoading = ref(false);

const weekdays = ['一', '二', '三', '四', '五', '六', '日'];
const dayDetail = calendarDayDetail;

const filterTags = [
	{ key: 'delivery' as const, label: '交割日' },
	{ key: 'fee' as const, label: '手续费调整' },
	{ key: 'macro' as const, label: '宏观数据' },
	{ key: 'strategy' as const, label: '策略启停日' },
];

const calendarFilters = ref({
	delivery: true,
	fee: true,
	macro: true,
	strategy: true,
});

const events = computed(() => buildCalendarEvents(year.value, month.value));

watch([year, month, exchange], () => {
	calendarLoading.value = false;
});

const getMarkers = (event?: {
	delivery?: string[];
	macro?: string[];
	strategy?: string[];
	fee?: boolean;
}) => {
	if (!event) {
		return { delivery: false, macro: false, strategy: false, fee: false };
	}
	return {
		delivery: calendarFilters.value.delivery && Boolean(event.delivery?.length),
		macro: calendarFilters.value.macro && Boolean(event.macro?.length),
		strategy: calendarFilters.value.strategy && Boolean(event.strategy?.length),
		fee: calendarFilters.value.fee && Boolean(event.fee),
	};
};

const isCellVisible = (event?: {
	delivery?: string[];
	macro?: string[];
	strategy?: string[];
	fee?: boolean;
}) => {
	if (!event) return true;
	const f = calendarFilters.value;
	if (f.delivery && event.delivery?.length) return true;
	if (f.fee && event.fee) return true;
	if (f.macro && event.macro?.length) return true;
	if (f.strategy && event.strategy?.length) return true;
	return !event.delivery?.length && !event.fee && !event.macro?.length && !event.strategy?.length;
};

const monthCells = computed(() => {
	const firstDay = new Date(year.value, month.value - 1, 1);
	const startOffset = (firstDay.getDay() + 6) % 7;
	const daysInMonth = new Date(year.value, month.value, 0).getDate();
	const cells = [];

	for (let i = 0; i < startOffset; i += 1) {
		cells.push({
			key: `empty-${i}`,
			date: '',
			day: 0,
			isToday: false,
			isWeekend: false,
			isClosed: false,
			visible: false,
			hasMarkers: false,
			markers: { delivery: false, macro: false, strategy: false, fee: false },
		});
	}

	for (let day = 1; day <= daysInMonth; day += 1) {
		const date = `${year.value}-${String(month.value).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
		const today = new Date();
		const isToday =
			today.getFullYear() === year.value && today.getMonth() + 1 === month.value && today.getDate() === day;
		const event = events.value[date];
		const markers = getMarkers(event);
		const hasMarkers = markers.delivery || markers.macro || markers.strategy || markers.fee;
		const weekday = new Date(year.value, month.value - 1, day).getDay();
		const isClosed = Boolean(event?.closed);

		cells.push({
			key: date,
			date,
			day,
			isToday,
			isWeekend: weekday === 0 || weekday === 6,
			isClosed,
			visible: isCellVisible(event),
			hasMarkers,
			markers,
		});
	}

	return cells;
});

const shiftMonth = (delta: number) => {
	const next = new Date(year.value, month.value - 1 + delta, 1);
	year.value = next.getFullYear();
	month.value = next.getMonth() + 1;
};

const goToday = () => {
	const today = new Date();
	year.value = today.getFullYear();
	month.value = today.getMonth() + 1;
	selectedDate.value = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
};
</script>

<style scoped>
.calendar-panel {
	--cal-brand: var(--brand-primary, #2e5cf6);
	--cal-brand-soft: var(--brand-primary-light-9, #ebf1fe);
	--cal-page: var(--surface-bg, #f5f7fa);
	--cal-card: var(--surface-card, var(--dash-surface, #ffffff));
	--cal-border: var(--border-default, var(--dash-border, #e5e6eb));
	--cal-heading: var(--text-primary, var(--dash-heading, #1d2129));
	--cal-muted: var(--text-tertiary, var(--dash-text-muted, #86909c));
	--cal-secondary: var(--text-secondary, var(--dash-text-secondary, #4e5969));

	position: relative;
	flex: 0 0 380px;
	width: 380px;
	height: 100%;
	min-height: 0;
	align-self: stretch;
	z-index: 20;
	overflow: hidden;
	background: var(--cal-card);
	border-radius: var(--dash-card-radius, 8px);
	transition: flex-basis 0.24s ease, width 0.24s ease;
}

.calendar-panel.collapsed {
	flex: 0 0 48px;
	width: 48px;
	cursor: pointer;
}

.collapse-btn {
	position: absolute;
	left: 0;
	top: 50%;
	transform: translate(-50%, -50%);
	width: 26px;
	height: 52px;
	border-radius: 10px 0 0 10px;
	cursor: pointer;
	z-index: 2;
	border: 1px solid var(--dash-border);
	background: var(--dash-surface);
	color: var(--dash-text-muted);
	box-shadow: -4px 0 12px rgba(15, 23, 42, 0.06);
}

.collapse-icon {
	width: 16px;
	height: 16px;
	font-size: 16px;
}

.collapse-btn:hover {
	color: var(--cal-brand);
	background: var(--cal-brand-soft);
}

.panel-inner {
	height: 100%;
	display: flex;
	flex-direction: column;
	overflow: hidden;
	padding: 14px 16px 14px 20px;
	gap: 12px;
}

.cal-upper {
	flex: 0 0 auto;
	display: flex;
	flex-direction: column;
	gap: 12px;
	overflow: hidden;
}

.cal-lower {
	flex: 1 1 0;
	min-height: 0;
	display: flex;
	flex-direction: column;
	overflow: hidden;
}

.cal-header {
	flex-shrink: 0;
}

.cal-header-top {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 12px;
}

.cal-title {
	display: flex;
	align-items: center;
	gap: 10px;
}

.cal-icon {
	width: 32px;
	height: 32px;
	border-radius: 8px;
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 18px;
	background: var(--cal-brand-soft);
	color: var(--cal-brand);
	border: 1px solid color-mix(in srgb, var(--cal-brand) 18%, transparent);
	flex-shrink: 0;

	.el-icon {
		width: 18px;
		height: 18px;
		font-size: 18px;
	}
}

.cal-header h3 {
	margin: 0;
	font-size: 15px;
	font-weight: 600;
	line-height: 1.3;
	color: var(--cal-heading);
}

.cal-header p {
	margin: 2px 0 0;
	font-size: 11px;
	line-height: 1.3;
	color: var(--cal-muted);
}

.exchange-select {
	width: 112px;
	flex-shrink: 0;
}

.month-bar {
	display: flex;
	align-items: center;
	gap: 8px;
	padding: 6px 8px 6px 6px;
	border-radius: 8px;
	background: var(--cal-page);
	border: 1px solid var(--cal-border);
	flex-shrink: 0;
}

.month-display {
	flex: 1;
	text-align: center;
	min-width: 0;
}

.month-display strong {
	font-size: 15px;
	font-weight: 600;
	letter-spacing: 0.02em;
	color: var(--cal-heading);
}

.nav-btn,
.today-btn {
	border: 1px solid var(--cal-border);
	background: var(--cal-card);
	color: var(--cal-secondary);
	cursor: pointer;
	transition: all 0.15s ease;
}

.today-btn.el-button {
	--el-button-bg-color: var(--cal-brand-soft);
	--el-button-text-color: var(--cal-brand);
	--el-button-border-color: color-mix(in srgb, var(--cal-brand) 22%, transparent);
	--el-button-hover-bg-color: var(--cal-brand-soft);
	--el-button-hover-text-color: var(--cal-brand);
	--el-button-hover-border-color: color-mix(in srgb, var(--cal-brand) 40%, transparent);
}

.nav-btn {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	width: 28px;
	height: 28px;
	padding: 0;
	border-radius: 8px;
	flex-shrink: 0;
}

.nav-btn .el-icon {
	width: 16px;
	height: 16px;
	font-size: 16px;
}

.nav-btn:hover,
.today-btn:hover {
	border-color: color-mix(in srgb, var(--cal-brand) 32%, transparent);
	color: var(--cal-brand);
	background: var(--cal-brand-soft);
}

.today-btn {
	border-radius: 8px;
	font-size: 12px;
	font-weight: 500;
	padding: 5px 12px;
	border-color: color-mix(in srgb, var(--cal-brand) 22%, transparent);
	color: var(--cal-brand);
	background: var(--cal-brand-soft);
	flex-shrink: 0;
}

.filter-row {
	flex-shrink: 0;
}

.filter-tags {
	display: flex;
	flex-wrap: wrap;
	gap: 8px;
}

.filter-chip {
	box-sizing: border-box;
	appearance: none;
	flex: 1 1 calc((100% - 8px) / 2);
	min-width: 0;
	height: 28px;
	padding: 0 8px;
	border-radius: 6px;
	border: 1px solid var(--cal-border);
	background: var(--cal-card);
	color: var(--cal-secondary);
	font-family: inherit;
	font-size: 12px;
	font-weight: 500;
	line-height: 26px;
	text-align: center;
	white-space: nowrap;
	cursor: pointer;
	transition: color 0.15s ease, background 0.15s ease, border-color 0.15s ease;
}

.filter-chip:hover {
	border-color: color-mix(in srgb, var(--cal-brand) 28%, transparent);
	color: var(--cal-brand);
	background: var(--cal-brand-soft);
}

.filter-chip.is-active {
	border-color: color-mix(in srgb, var(--cal-brand) 32%, transparent);
	background: var(--cal-brand-soft);
	color: var(--cal-brand);
	font-weight: 600;
}

.calendar-shell {
	flex-shrink: 0;
	padding: 0;
	overflow: hidden;
	border-radius: 8px;
	background: var(--cal-page);
	border: 1px solid var(--cal-border);
}

.mark-legend {
	display: flex;
	flex-wrap: wrap;
	align-items: center;
	gap: 8px 4px;
	padding: 8px 10px;
	margin: 0;
	border-bottom: 1px solid var(--cal-border);
	background: var(--cal-card);
	font-size: 11px;
	color: var(--cal-muted);
}

.mark-legend span {
	flex: 1 1 0;
	display: inline-flex;
	align-items: center;
	justify-content: center;
	gap: 5px;
	min-width: 0;
	white-space: nowrap;
}

.leg {
	width: 7px;
	height: 7px;
	border-radius: 50%;
	display: inline-block;
}

.leg.delivery {
	background: var(--danger);
}

.leg.macro {
	background: var(--warning);
}

.leg.strategy {
	background: var(--success);
}

.leg.fee {
	background: var(--cal-brand);
	border-radius: 2px;
	width: 6px;
	height: 6px;
}

.weekday-row {
	display: grid;
	grid-template-columns: repeat(7, 1fr);
	gap: 4px;
	margin: 0;
	padding: 8px 8px 4px;
	font-size: 11px;
	text-align: center;
	font-weight: 500;
	color: var(--cal-muted);
}

.weekday-row span.weekend {
	color: var(--danger);
	opacity: 0.75;
}

.calendar-grid {
	display: grid;
	grid-template-columns: repeat(7, 1fr);
	gap: 4px;
	padding: 4px 8px 8px;
}

.cell-slot {
	min-height: 0;
}

.day-cell {
	position: relative;
	width: 100%;
	aspect-ratio: 1;
	border-radius: 6px;
	cursor: pointer;
	padding: 4px 2px 3px;
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: space-between;
	border: 1px solid transparent;
	background: var(--cal-card);
	transition: all 0.12s ease;
}

.day-cell:hover:not(.today) {
	border-color: color-mix(in srgb, var(--cal-brand) 28%, transparent);
	box-shadow: 0 2px 8px rgba(46, 92, 246, 0.08);
	transform: translateY(-1px);
}

.day-cell.weekend:not(.today) {
	background: color-mix(in srgb, var(--cal-page) 70%, var(--cal-card));
}

.day-cell.closed {
	opacity: 0.5;
}

.day-cell.today {
	background: var(--cal-brand);
	border-color: var(--cal-brand);
	box-shadow: 0 4px 12px color-mix(in srgb, var(--cal-brand) 28%, transparent);
	color: #fff;
}

.day-cell.selected:not(.today) {
	border-color: var(--cal-brand);
	box-shadow: 0 0 0 1px var(--cal-brand-soft);
}

.day-num {
	font-size: 12px;
	font-weight: 600;
	line-height: 1;
	color: inherit;
}

.day-cell:not(.today) .day-num {
	color: var(--cal-heading);
}

.day-num.strike {
	text-decoration: line-through;
	opacity: 0.7;
}

.marker-row {
	display: flex;
	gap: 3px;
	align-items: center;
	justify-content: center;
	min-height: 8px;
}

.m-dot {
	width: 5px;
	height: 5px;
	border-radius: 50%;
	flex-shrink: 0;
}

.m-dot.delivery {
	background: var(--danger);
}

.m-dot.macro {
	background: var(--warning);
}

.m-dot.strategy {
	background: var(--success);
}

.m-dot.fee {
	background: var(--cal-brand);
	border-radius: 1px;
	width: 4px;
	height: 4px;
}

.detail-panel {
	margin-top: 0;
	padding-top: 4px;
	border-top: 1px solid var(--cal-border);
}

.detail-header {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 8px;
	margin-bottom: 8px;
	flex-shrink: 0;
}

.detail-header h4 {
	margin: 0;
	font-size: 14px;
	font-weight: 600;
	color: var(--cal-heading);
}

.detail-badge {
	font-size: 10px;
	padding: 2px 8px;
	border-radius: 6px;
	border: 1px solid color-mix(in srgb, var(--cal-brand) 22%, transparent);
	background: var(--cal-brand-soft);
	color: var(--cal-brand);
}

.detail-blocks {
	flex: 1;
	min-height: 0;
	overflow-y: auto;
	display: grid;
	grid-template-columns: 1fr 1fr;
	gap: 8px;
	align-content: start;
}

.detail-block {
	padding: 10px;
	border-radius: 8px;
	background: var(--cal-page);
	border: 1px solid var(--cal-border);
	font-size: 11px;
}

.detail-block-wide {
	grid-column: 1 / -1;
}

.detail-block h5 {
	margin: 0 0 6px;
	font-size: 10px;
	font-weight: 600;
	color: var(--cal-muted);
	text-transform: uppercase;
	letter-spacing: 0.04em;
}

.detail-list {
	margin: 0;
	padding: 0;
	list-style: none;
}

.detail-list li {
	display: flex;
	flex-direction: column;
	gap: 2px;
	padding: 4px 0;
	border-bottom: 1px dashed var(--cal-border);
	color: var(--dash-text);
}

.detail-list li:last-child {
	border-bottom: none;
	padding-bottom: 0;
}

.detail-meta {
	font-size: 10px;
	color: var(--cal-muted);
}

.detail-meta.up {
	color: var(--price-up, var(--market-rise));
}

.detail-meta.down {
	color: var(--price-down, var(--market-fall));
}

.detail-empty {
	margin: 0;
	font-size: 10px;
	color: var(--cal-muted);
}

.session-list {
	display: flex;
	flex-direction: column;
	gap: 4px;
}

.session-item {
	display: flex;
	justify-content: space-between;
	gap: 8px;
	font-size: 10px;
}

.session-label {
	color: var(--cal-secondary);
}

.session-time {
	color: var(--cal-muted);
	text-align: right;
}

.backtest-stats {
	display: flex;
	gap: 8px;
}

.stat-chip {
	flex: 1;
	padding: 8px;
	border-radius: 8px;
	background: var(--cal-card);
	border: 1px solid var(--cal-border);
	text-align: center;
}

.stat-chip span {
	display: block;
	font-size: 10px;
	color: var(--cal-muted);
}

.stat-chip strong {
	font-size: 13px;
	color: var(--cal-heading);
}

.collapsed-label {
	writing-mode: vertical-rl;
	margin: 48px auto 0;
	font-size: 12px;
	color: var(--cal-muted);
	letter-spacing: 0.2em;
	pointer-events: none;
}

:deep(.exchange-select .el-input__wrapper) {
	background: var(--cal-card);
	box-shadow: 0 0 0 1px var(--cal-border) inset;
	border-radius: 6px;
}

:deep(.exchange-select .el-input__wrapper:hover),
:deep(.exchange-select .el-input__wrapper.is-focus) {
	box-shadow: 0 0 0 1px color-mix(in srgb, var(--cal-brand) 40%, transparent) inset;
}
</style>
