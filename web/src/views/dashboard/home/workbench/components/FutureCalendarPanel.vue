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

<style scoped src="../styles/future-calendar.css"></style>
