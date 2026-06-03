<script setup lang="ts">
import { message } from "ant-design-vue";
import { onMounted, ref, watch } from "vue";

import { deleteTrip, getTripDetail, listTrips } from "../services/api";
import type { Itinerary, TripSummaryItem } from "../types";

const props = defineProps<{
  active: boolean;
}>();

const emit = defineEmits<{
  openTrip: [itinerary: Itinerary];
}>();

const loading = ref(false);
const items = ref<TripSummaryItem[]>([]);
const deletingTripId = ref("");

async function loadTrips() {
  loading.value = true;
  try {
    const response = await listTrips();
    items.value = response.items;
  } catch {
    message.error("历史列表加载失败。");
  } finally {
    loading.value = false;
  }
}

async function openTrip(tripId: string) {
  try {
    const response = await getTripDetail(tripId);
    emit("openTrip", response.itinerary);
    message.success("已加载已保存行程。");
  } catch {
    message.error("读取行程详情失败。");
  }
}

async function removeTrip(tripId: string) {
  const confirmed = window.confirm("确定要删除这条已保存行程吗？删除后无法恢复。");
  if (!confirmed) return;
  deletingTripId.value = tripId;
  try {
    await deleteTrip(tripId);
    items.value = items.value.filter((item) => item.trip_id !== tripId);
    message.success("行程已删除。");
  } catch {
    message.error("删除行程失败。");
  } finally {
    deletingTripId.value = "";
  }
}

function formatTime(dateStr?: string | null): string {
  if (!dateStr) return "未记录";
  return dateStr.replace("T", " ").slice(0, 16);
}

function extractBudget(itineraryJson?: any): string {
  try {
    const b = itineraryJson?.budget_breakdown;
    if (b?.total) return `¥${Number(b.total).toFixed(0)}`;
    return "—";
  } catch {
    return "—";
  }
}

onMounted(() => { if (props.active) void loadTrips(); });
watch(() => props.active, (a) => { if (a) void loadTrips(); });
</script>

<template>
  <section>
    <!-- Header -->
    <div class="card-glow p-5 sm:p-7 mb-5 flex flex-col sm:flex-row sm:items-end justify-between gap-4">
      <div>
        <h2 class="text-2xl font-extrabold text-gray-700 mb-1">历史行程</h2>
        <p class="text-gray-400 text-sm">已保存到后端数据库的行程摘要</p>
      </div>
      <button
        class="btn-primary text-sm !rounded-xl"
        @click="loadTrips"
      >
        刷新列表
      </button>
    </div>

    <!-- States -->
    <div v-if="loading" class="card-glow p-8 text-center text-gray-400">正在加载历史列表...</div>
    <div v-else-if="items.length === 0" class="card-glow p-8 text-center text-gray-400">
      <div class="text-4xl mb-3">📭</div>
      <p>还没有已保存的行程</p>
      <p class="text-xs mt-1 text-gray-300">回到规划页生成并保存一条行程吧</p>
    </div>

    <!-- Horizontal cards -->
    <div v-else class="grid gap-4">
      <article
        v-for="item in items"
        :key="item.trip_id"
        class="card-glow p-5 sm:p-6
               flex flex-col sm:flex-row sm:items-center gap-4
               hover:shadow-[0_24px_60px_rgba(98,116,164,0.16)] transition-shadow duration-200"
      >
        <!-- City avatar -->
        <div class="shrink-0 w-14 h-14 sm:w-16 sm:h-16 rounded-2xl
                    bg-gradient-to-br from-brand-400 to-accent-500 text-white
                    flex items-center justify-center text-xl sm:text-2xl font-extrabold shadow-lg">
          {{ item.destination?.charAt(0) || "?" }}
        </div>

        <!-- Info -->
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2 mb-1">
            <h3 class="text-lg font-extrabold text-brand-700">{{ item.destination }}</h3>
            <span class="text-xs text-gray-300 bg-gray-100 px-2 py-0.5 rounded-full">{{ item.trip_id }}</span>
          </div>
          <p class="text-sm text-gray-500 line-clamp-2 leading-relaxed mb-2">{{ item.summary }}</p>
          <div class="flex flex-wrap items-center gap-3 text-xs text-gray-400">
            <span>🕐 创建: {{ formatTime(item.created_at) }}</span>
            <span v-if="item.updated_at !== item.created_at">✏️ 更新: {{ formatTime(item.updated_at) }}</span>
          </div>
        </div>

        <!-- Actions -->
        <div class="flex sm:flex-col gap-2 shrink-0">
          <button
            class="btn-primary text-xs !px-4 !py-2 !rounded-xl"
            @click="openTrip(item.trip_id)"
          >
            查看详情
          </button>
          <button
            class="border-none rounded-xl px-4 py-2 text-xs font-bold cursor-pointer
                   bg-red-50 text-red-500 hover:bg-red-100 transition-colors
                   disabled:opacity-60 disabled:cursor-wait"
            :disabled="deletingTripId === item.trip_id"
            @click="removeTrip(item.trip_id)"
          >
            {{ deletingTripId === item.trip_id ? "删除中..." : "删除" }}
          </button>
        </div>
      </article>
    </div>
  </section>
</template>
