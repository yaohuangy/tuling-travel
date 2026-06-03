<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { message } from "ant-design-vue";

import AmapTripMap from "../components/AmapTripMap.vue";
import {
  editTrip,
  fetchWeatherForecast,
  getMarkdownExportUrl,
  getPdfExportUrl,
  saveTrip,
} from "../services/api";
import type { Itinerary, WeatherForecastResponse } from "../types";

const props = defineProps<{
  itinerary: Itinerary | null;
}>();

const emit = defineEmits<{
  backHome: [];
  viewHistory: [];
  updated: [itinerary: Itinerary];
}>();

// ---- reactive state ----
const saving = ref(false);
const exportingPdf = ref(false);
const exportingMarkdown = ref(false);
const editing = ref(false);
const editScope = ref("day_1");
const editInstruction = ref("这一天节奏更轻松一点，减少固定安排。");
const weatherLoading = ref(false);
const weatherError = ref("");
const weather = ref<WeatherForecastResponse | null>(null);
const showFab = ref(true);

// ---- helpers ----
function formatShortDate(dateText?: string | null): string {
  if (!dateText) return "待定";
  const parts = dateText.split("-");
  if (parts.length !== 3) return dateText;
  return `${parts[1]}-${parts[2]}`;
}

function formatWeatherDate(dateText?: string | null, week?: string | null): string {
  const weekdayMap: Record<string, string> = {
    "1": "周一", "2": "周二", "3": "周三", "4": "周四", "5": "周五", "6": "周六", "7": "周日",
  };
  const weekday = week ? weekdayMap[week] || `周${week}` : "";
  return [formatShortDate(dateText), weekday].filter(Boolean).join(" ");
}

const dayCount = computed(() => props.itinerary?.days.length ?? 0);
const tripDateRange = computed(() => {
  if (!props.itinerary?.days.length) return "待定";
  const first = props.itinerary.days[0]?.date;
  const last = props.itinerary.days[props.itinerary.days.length - 1]?.date;
  return `${first || "?"} ~ ${last || "?"}`;
});

const weatherText = computed(() => {
  if (!weather.value) return "";
  return weather.value.days.map((d) => `${d.day_weather || ""}${d.night_weather || ""}`).join(" ");
});

const weatherSummary = computed(() => {
  if (!weather.value?.days.length) return "暂无天气";
  const today = weather.value.days[0];
  return `${today.day_weather || "?"} ${today.day_temp || "?"}°`;
});

const hasRainyWeather = computed(() =>
  ["雨", "阵雨", "雷阵雨", "小雨", "中雨", "大雨"].some((k) => weatherText.value.includes(k))
);

const technicalTipKeywords = ["LLM", "RAG", "LangChain", "Chroma", "演示", "测试", "规则", "模型", "源码"];
const sunnyTipKeywords = ["防晒", "太阳", "日照", "晒"];

const displayTips = computed(() => {
  if (!props.itinerary) return [];
  let tips = props.itinerary.tips.map((t) => t.trim()).filter(Boolean)
    .filter((t) => !technicalTipKeywords.some((k) => t.includes(k)));

  if (hasRainyWeather.value) {
    tips = tips.filter((t) => !sunnyTipKeywords.some((k) => t.includes(k)));
    tips.push("天气可能有雨，建议随身带伞或轻便雨衣。");
    tips.push("阴雨天路面湿滑，洱海边和古镇石板路建议穿防滑鞋。");
  }

  const unique = Array.from(new Set(tips));
  return unique.length ? unique : [
    `建议根据${props.itinerary.destination}当天实时天气准备雨具或薄外套。`,
    "古镇、生态廊道和石板路更适合慢慢走，鞋子尽量选择舒适防滑的款式。",
  ];
});

function buildVisibleItinerary(): Itinerary | null {
  if (!props.itinerary) return null;
  return { ...props.itinerary, tips: displayTips.value };
}

// ---- budget donut chart ----
interface BudgetSlice {
  label: string;
  value: number;
  color: string;
  percent: number;
  dashArray: string;
  dashOffset: string;
}

const budgetColors: Record<string, string> = {
  tickets: "#f59e0b",
  hotel: "#8b5cf6",
  meals: "#10b981",
  transport: "#3b82f6",
  other: "#6b7280",
};

const budgetSlices = computed<BudgetSlice[]>(() => {
  if (!props.itinerary) return [];
  const b = props.itinerary.budget_breakdown;
  const items = [
    { label: "门票", value: b.tickets, key: "tickets" },
    { label: "住宿", value: b.hotel, key: "hotel" },
    { label: "餐饮", value: b.meals, key: "meals" },
    { label: "交通", value: b.transport, key: "transport" },
    { label: "其他", value: b.other, key: "other" },
  ].filter((i) => i.value > 0);

  const total = items.reduce((s, i) => s + i.value, 0) || 1;
  const circumference = 2 * Math.PI * 40; // r=40
  let accumulated = 0;

  return items.map((item) => {
    const percent = item.value / total;
    const dashLen = percent * circumference;
    const offset = -accumulated;
    accumulated += dashLen;
    return {
      label: item.label,
      value: item.value,
      color: budgetColors[item.key] || "#6b7280",
      percent,
      dashArray: `${dashLen} ${circumference - dashLen}`,
      dashOffset: String(offset),
    };
  });
});

// ---- map points ----
const mapPoints = computed(() => {
  if (!props.itinerary) return [];
  return props.itinerary.days.flatMap((day) =>
    day.spots.map((spot) => ({
      key: `${day.day_index}-${spot.name}`,
      dayIndex: day.day_index,
      date: day.date || "待定",
      theme: day.theme || "未命名主题",
      name: spot.name,
      address: spot.address || spot.location || "待补充",
      latitude: spot.latitude,
      longitude: spot.longitude,
      poiId: spot.poi_id,
      imageUrl: spot.image_url,
      description: spot.description || "暂无说明",
    }))
  );
});

// ---- weather ----
async function loadWeather() {
  if (!props.itinerary?.destination) { weather.value = null; return; }
  weatherLoading.value = true;
  weatherError.value = "";
  try {
    weather.value = await fetchWeatherForecast(props.itinerary.destination);
  } catch {
    weather.value = null;
    weatherError.value = "天气信息加载失败。";
  } finally {
    weatherLoading.value = false;
  }
}

watch(() => props.itinerary?.destination, () => { void loadWeather(); }, { immediate: true });
watch(() => props.itinerary?.trip_id, () => {
  const firstDay = props.itinerary?.days[0];
  editScope.value = firstDay ? `day_${firstDay.day_index}` : "day_1";
}, { immediate: true });

// ---- actions ----
async function handleSave() {
  const toSave = buildVisibleItinerary();
  if (!toSave) return;
  saving.value = true;
  try { await saveTrip(toSave); message.success("行程已保存，可以去历史列表查看。"); }
  catch { message.error("保存行程失败。"); }
  finally { saving.value = false; }
}

async function openPdfExport() {
  const toExport = buildVisibleItinerary();
  if (!toExport) return;
  const w = window.open("about:blank", "_blank");
  exportingPdf.value = true;
  try {
    await saveTrip(toExport);
    const url = getPdfExportUrl(toExport.trip_id);
    if (w) w.location.href = url; else window.location.href = url;
  } catch { w?.close(); message.error("导出 PDF 前同步当前行程失败。"); }
  finally { exportingPdf.value = false; }
}

async function openMarkdownExport() {
  const toExport = buildVisibleItinerary();
  if (!toExport) return;
  const w = window.open("about:blank", "_blank");
  exportingMarkdown.value = true;
  try {
    await saveTrip(toExport);
    const url = getMarkdownExportUrl(toExport.trip_id);
    if (w) w.location.href = url; else window.location.href = url;
  } catch { w?.close(); message.error("导出 Markdown 前同步当前行程失败。"); }
  finally { exportingMarkdown.value = false; }
}

async function handleEdit() {
  if (!props.itinerary) return;
  const instruction = editInstruction.value.trim();
  if (!instruction) { message.warning("请先输入想如何调整行程。"); return; }
  editing.value = true;
  try {
    const updated = await editTrip({
      trip_id: props.itinerary.trip_id,
      current_itinerary: props.itinerary,
      user_instruction: instruction,
      edit_scope: editScope.value,
      preserve_constraints: ["保留预算结构", "保留目的地和旅行日期"],
    });
    emit("updated", updated);
    message.success("行程已智能调整。");
  } catch { message.error("智能调整失败，请稍后再试。"); }
  finally { editing.value = false; }
}
</script>

<template>
  <!-- ===== Empty state ===== -->
  <section v-if="!itinerary" class="grid place-items-center min-h-[360px]">
    <div class="card-glow max-w-lg p-9 text-center">
      <h2 class="text-2xl font-bold text-gray-700 mb-3">还没有生成结果</h2>
      <p class="text-gray-400 mb-5 leading-relaxed">先回到规划页生成一条 itinerary，结果页就会开始展示真实数据。</p>
      <button class="btn-secondary" @click="$emit('backHome')">返回规划页</button>
    </div>
  </section>

  <!-- ===== Result content ===== -->
  <section v-else class="relative">
    <!-- ---- Top overview cards ---- -->
    <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4 mb-5">
      <div class="card-glow p-4 text-center">
        <div class="text-xs text-gray-400 font-semibold uppercase tracking-wide mb-1">行程天数</div>
        <div class="text-2xl font-extrabold text-brand-600">{{ dayCount }} <span class="text-sm font-normal text-gray-400">天</span></div>
        <div class="text-xs text-gray-400 mt-0.5 truncate">{{ tripDateRange }}</div>
      </div>
      <div class="card-glow p-4 text-center">
        <div class="text-xs text-gray-400 font-semibold uppercase tracking-wide mb-1">预估总预算</div>
        <div class="text-2xl font-extrabold text-brand-600">¥{{ itinerary.estimated_budget.toFixed(0) }}</div>
        <div class="text-xs text-gray-400 mt-0.5">{{ itinerary.destination }}</div>
      </div>
      <div class="card-glow p-4 text-center">
        <div class="text-xs text-gray-400 font-semibold uppercase tracking-wide mb-1">今日天气</div>
        <div class="text-2xl font-extrabold text-sky-500">{{ weatherSummary }}</div>
        <div class="text-xs text-gray-400 mt-0.5">{{ weather?.city || itinerary.destination }}</div>
      </div>
      <div class="card-glow p-4 text-center">
        <div class="text-xs text-gray-400 font-semibold uppercase tracking-wide mb-1">目的地</div>
        <div class="text-2xl font-extrabold text-brand-600">{{ itinerary.destination }}</div>
        <div class="text-xs text-gray-400 mt-0.5">{{ itinerary.days.length }} 日行程</div>
      </div>
    </div>

    <!-- ---- Summary & Tips ---- -->
    <div class="card-glow p-5 sm:p-7 mb-5">
      <h3 class="text-lg font-bold text-gray-700 mb-2">📋 行程概览</h3>
      <p class="text-gray-500 leading-relaxed mb-4">{{ itinerary.summary }}</p>
      <div v-if="displayTips.length" class="p-4 rounded-2xl bg-gradient-to-br from-brand-50 to-accent-50/30 border border-brand-100/50">
        <h4 class="text-sm font-extrabold text-gray-600 mb-2">💡 旅行提示</h4>
        <ul class="grid gap-1.5 list-disc list-inside text-gray-500 text-sm leading-relaxed">
          <li v-for="tip in displayTips" :key="tip">{{ tip }}</li>
        </ul>
      </div>
    </div>

    <!-- ---- Budget section (donut chart + grid) ---- -->
    <div class="card-glow p-5 sm:p-7 mb-5">
      <h3 class="text-lg font-bold text-gray-700 mb-4">💰 预算明细</h3>
      <div class="flex flex-col sm:flex-row items-center gap-6">
        <!-- SVG Donut -->
        <div class="relative w-48 h-48 shrink-0">
          <svg viewBox="0 0 100 100" class="w-full h-full -rotate-90">
            <circle cx="50" cy="50" r="40" fill="none" stroke="#f1f5f9" stroke-width="12" />
            <circle
              v-for="(slice, idx) in budgetSlices"
              :key="idx"
              cx="50" cy="50" r="40" fill="none"
              :stroke="slice.color" stroke-width="12"
              :stroke-dasharray="slice.dashArray"
              :stroke-dashoffset="slice.dashOffset"
              stroke-linecap="round"
            />
          </svg>
          <div class="absolute inset-0 flex flex-col items-center justify-center">
            <span class="text-xs text-gray-400">总计</span>
            <span class="text-lg font-extrabold text-gray-800">¥{{ itinerary.estimated_budget.toFixed(0) }}</span>
          </div>
        </div>
        <!-- Legend -->
        <div class="grid grid-cols-2 gap-x-6 gap-y-2">
          <div v-for="slice in budgetSlices" :key="slice.label" class="flex items-center gap-2">
            <span class="w-3 h-3 rounded-sm shrink-0" :style="{ backgroundColor: slice.color }"></span>
            <span class="text-sm text-gray-500">{{ slice.label }}</span>
            <span class="text-sm font-bold text-gray-700 ml-auto">¥{{ slice.value.toFixed(0) }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- ---- Map ---- -->
    <div class="card-glow p-5 sm:p-7 mb-5">
      <h3 class="text-lg font-bold text-gray-700 mb-4">🗺️ 景点地图</h3>
      <div class="min-h-[300px]">
        <AmapTripMap :points="mapPoints" />
      </div>
    </div>

    <!-- ---- Weather (horizontal scroll cards) ---- -->
    <div class="card-glow p-5 sm:p-7 mb-5 overflow-hidden">
      <h3 class="text-lg font-bold text-gray-700 mb-4">🌤️ 天气预报</h3>

      <div v-if="weatherLoading" class="text-gray-400 text-sm">正在加载天气信息...</div>
      <div v-else-if="weatherError" class="text-gray-400 text-sm">{{ weatherError }}</div>
      <div v-else-if="weather" class="flex gap-3 overflow-x-auto pb-2 -mx-1 px-1 snap-x scrollbar-thin">
        <article
          v-for="day in weather.days"
          :key="`${day.date}-${day.week}`"
          class="snap-start shrink-0 w-[150px] p-4 rounded-2xl bg-gradient-to-b from-white to-brand-50/50 border border-brand-100/40 text-center"
        >
          <div class="text-xs font-bold text-gray-600 mb-2">{{ formatWeatherDate(day.date, day.week) }}</div>
          <div class="text-2xl mb-2">
            {{ day.day_weather?.includes("雨") ? "🌧️" : day.day_weather?.includes("云") ? "⛅" : "☀️" }}
          </div>
          <div class="text-xl font-extrabold text-sky-500 mb-1">
            {{ day.day_temp || "-" }}°<span class="text-sm text-gray-400"> / {{ day.night_temp || "-" }}°</span>
          </div>
          <div class="text-xs text-gray-400">白天 {{ day.day_weather || "?" }}</div>
          <div class="text-xs text-gray-400">夜间 {{ day.night_weather || "?" }}</div>
          <div class="text-xs text-gray-300 mt-1">{{ day.day_wind || "" }}</div>
        </article>
      </div>
      <div v-else class="text-gray-400 text-sm">暂无天气信息。</div>
    </div>

    <!-- ---- Edit ---- -->
    <div class="card-glow p-5 sm:p-7 mb-5">
      <h3 class="text-lg font-bold text-gray-700 mb-4">✏️ 智能调整行程</h3>
      <div class="grid grid-cols-1 sm:grid-cols-[1fr_140px] gap-3 items-end mb-3">
        <label class="grid gap-1.5 text-sm font-bold text-gray-600">
          调整范围
          <select
            v-model="editScope"
            class="w-full h-11 px-4 rounded-xl border border-brand-200/40 bg-white text-gray-800
                   outline-none focus:border-brand-400 focus:ring-[3px] focus:ring-brand-400/10 transition-all"
          >
            <option
              v-for="day in itinerary.days"
              :key="day.day_index"
              :value="`day_${day.day_index}`"
            >
              第{{ day.day_index }}天 · {{ day.theme || "未命名主题" }}
            </option>
          </select>
        </label>
        <button
          class="btn-primary h-11 text-sm"
          :disabled="editing"
          @click="handleEdit"
        >
          {{ editing ? "调整中..." : "智能调整" }}
        </button>
      </div>
      <textarea
        v-model="editInstruction"
        rows="3"
        placeholder="例如：第二天轻松一点，不要安排太满；第三天想换成适合看日落的地点。"
        class="w-full resize-y min-h-[90px] p-4 rounded-xl border border-brand-200/40 bg-white text-gray-800
               outline-none focus:border-brand-400 focus:ring-[3px] focus:ring-brand-400/10 transition-all text-sm leading-relaxed"
      ></textarea>
    </div>

    <!-- ---- Daily timeline ---- -->
    <div class="card-glow p-5 sm:p-7 mb-5">
      <h3 class="text-lg font-bold text-gray-700 mb-4">📅 每日行程</h3>

      <div class="relative">
        <!-- Vertical line -->
        <div class="absolute left-[19px] sm:left-[23px] top-2 bottom-2 w-0.5 bg-gradient-to-b from-brand-300 via-accent-400 to-brand-300"></div>

        <div v-for="day in itinerary.days" :key="day.day_index" class="relative flex gap-4 sm:gap-6 pb-6 last:pb-0">
          <!-- Timeline node -->
          <div class="relative z-10 shrink-0 w-10 h-10 sm:w-12 sm:h-12 rounded-full
                      bg-gradient-to-br from-brand-400 to-accent-500 text-white
                      flex flex-col items-center justify-center text-xs sm:text-sm font-extrabold
                      shadow-[0_4px_14px_rgba(109,130,222,0.3)]">
            <span>{{ day.day_index }}</span>
          </div>

          <!-- Day card -->
          <div class="flex-1 min-w-0 rounded-2xl bg-white border border-brand-100/40 shadow-sm p-4 sm:p-5
                      hover:shadow-md hover:border-brand-200/60 transition-all duration-200">
            <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1 mb-3">
              <h4 class="font-bold text-gray-700 text-base sm:text-lg">
                {{ day.theme || "第" + day.day_index + "天" }}
              </h4>
              <span class="text-xs text-gray-400 bg-gray-100 px-3 py-1 rounded-full w-fit">
                {{ formatShortDate(day.date) }}
              </span>
            </div>

            <div class="grid gap-2.5 text-sm">
              <!-- Spot -->
              <div v-if="day.spots[0]" class="flex items-start gap-2.5 p-3 rounded-xl bg-amber-50/60">
                <span class="shrink-0 mt-0.5">📍</span>
                <div class="min-w-0">
                  <span class="font-semibold text-gray-700">{{ day.spots[0].name }}</span>
                  <p class="text-gray-400 text-xs mt-0.5">{{ day.spots[0].description }}</p>
                  <p v-if="day.spots[0].address" class="text-gray-300 text-xs mt-1 truncate">{{ day.spots[0].address }}</p>
                </div>
              </div>

              <!-- Meal -->
              <div v-if="day.meals[0]" class="flex items-center gap-2.5 p-3 rounded-xl bg-emerald-50/60">
                <span class="shrink-0">🍽️</span>
                <div>
                  <span class="font-semibold text-gray-700">{{ day.meals[0].name }}</span>
                  <span class="text-gray-400 text-xs ml-1">({{ day.meals[0].meal_type }})</span>
                  <p v-if="day.meals[0].notes" class="text-gray-400 text-xs mt-0.5">{{ day.meals[0].notes }}</p>
                </div>
              </div>

              <!-- Hotel -->
              <div v-if="day.hotel" class="flex items-center gap-2.5 p-3 rounded-xl bg-purple-50/60">
                <span class="shrink-0">🏨</span>
                <div>
                  <span class="font-semibold text-gray-700">{{ day.hotel.name }}</span>
                  <span class="text-gray-400 text-xs ml-1">({{ day.hotel.level || "未标注" }})</span>
                </div>
              </div>

              <!-- Transport -->
              <div v-if="day.transport[0]" class="flex items-center gap-2.5 p-3 rounded-xl bg-blue-50/60">
                <span class="shrink-0">🚗</span>
                <div>
                  <span class="text-gray-600">{{ day.transport[0].mode }}</span>
                  <span class="text-gray-400 text-xs ml-1">
                    {{ day.transport[0].from_place || "出发" }} → {{ day.transport[0].to_place || "到达" }}
                  </span>
                  <span class="text-gray-400 text-xs ml-2">
                    {{ day.transport[0].distance_km != null ? day.transport[0].distance_km.toFixed(2) + 'km' : day.transport[0].duration || '' }}
                  </span>
                </div>
              </div>

              <!-- Notes -->
              <div v-if="day.notes.length" class="flex gap-2.5 p-3 rounded-xl bg-gray-50/60">
                <span class="shrink-0">📝</span>
                <p class="text-gray-400 text-xs leading-relaxed">{{ day.notes[day.notes.length - 1] }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ---- FAB: floating save/export ---- -->
    <div
      v-show="showFab"
      class="fixed bottom-6 right-4 sm:right-8 z-50 flex flex-col sm:flex-row gap-2.5
             p-3 rounded-2xl bg-white/90 backdrop-blur-xl shadow-[0_16px_48px_rgba(98,116,164,0.2)]
             border border-brand-100/40"
    >
      <button
        class="btn-secondary text-xs !px-4 !py-2.5"
        @click="$emit('backHome')"
      >
        ← 返回
      </button>
      <button
        class="btn-secondary text-xs !px-4 !py-2.5"
        @click="$emit('viewHistory')"
      >
        历史
      </button>
      <button
        class="btn-primary text-xs !px-4 !py-2.5 !rounded-xl"
        :disabled="saving"
        @click="handleSave"
      >
        {{ saving ? "保存中..." : "💾 保存" }}
      </button>
      <button
        class="border-none rounded-xl px-4 py-2.5 text-xs font-bold cursor-pointer
               bg-sky-50 text-sky-600 hover:bg-sky-100 transition-colors disabled:opacity-70"
        :disabled="exportingPdf"
        @click="openPdfExport"
      >
        {{ exportingPdf ? "准备中..." : "📄 PDF" }}
      </button>
      <button
        class="border-none rounded-xl px-4 py-2.5 text-xs font-bold cursor-pointer
               bg-emerald-50 text-emerald-600 hover:bg-emerald-100 transition-colors disabled:opacity-70"
        :disabled="exportingMarkdown"
        @click="openMarkdownExport"
      >
        {{ exportingMarkdown ? "准备中..." : "📝 MD" }}
      </button>
    </div>
  </section>
</template>

<style scoped>
.scrollbar-thin::-webkit-scrollbar {
  height: 4px;
}
.scrollbar-thin::-webkit-scrollbar-track {
  background: transparent;
}
.scrollbar-thin::-webkit-scrollbar-thumb {
  background: rgba(109, 130, 222, 0.2);
  border-radius: 99px;
}
</style>
