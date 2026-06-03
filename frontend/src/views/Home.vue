<script setup lang="ts">
import axios from "axios";
import { computed, reactive, ref } from "vue";
import { message } from "ant-design-vue";

import { generateTrip } from "../services/api";
import type { Itinerary, TripRequestPayload } from "../types";

const emit = defineEmits<{
  generated: [itinerary: Itinerary];
}>();

const preferenceOptions = ["自然风景", "拍照", "美食", "古镇", "休闲"];
const dietaryOptions = ["少辣", "不吃香菜", "不吃葱"];
const extraNoteOptions = [
  "不想早起", "看日出", "看日落", "避开人流",
  "少走路", "拍照打卡", "当地美食", "适合老人小孩",
];

function formatDate(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

const today = new Date();
const todayPlus2 = new Date(today);
todayPlus2.setDate(todayPlus2.getDate() + 2);

const formState = reactive({
  destination: "大理",
  startDate: formatDate(today),
  endDate: formatDate(todayPlus2),
  travelers: 2,
  budget: 3200,
  hotelLevel: "舒适型",
  pace: "轻松",
  preferences: ["自然风景", "拍照", "美食"],
  dietaryPreferences: ["少辣"],
  selectedExtraNotes: ["不想早起", "看日落"],
  notes: "希望安排一个适合看日落的地点。",
});

const isSubmitting = ref(false);
const notesMaxLength = 200;

const dayCount = computed(() => {
  const start = new Date(formState.startDate);
  const end = new Date(formState.endDate);
  const diff = end.getTime() - start.getTime();
  return Number.isNaN(diff) ? 0 : Math.max(Math.floor(diff / 86400000) + 1, 0);
});

const notesRemaining = computed(() => notesMaxLength - formState.notes.length);

function togglePreference(tag: string) {
  const idx = formState.preferences.indexOf(tag);
  if (idx === -1) {
    formState.preferences.push(tag);
  } else {
    formState.preferences.splice(idx, 1);
  }
}

function toggleDietary(tag: string) {
  const idx = formState.dietaryPreferences.indexOf(tag);
  if (idx === -1) {
    formState.dietaryPreferences.push(tag);
  } else {
    formState.dietaryPreferences.splice(idx, 1);
  }
}

function toggleExtraNote(tag: string) {
  const idx = formState.selectedExtraNotes.indexOf(tag);
  if (idx === -1) {
    formState.selectedExtraNotes.push(tag);
  } else {
    formState.selectedExtraNotes.splice(idx, 1);
  }
}

async function handleSubmit() {
  const payload: TripRequestPayload = {
    destination: formState.destination,
    start_date: formState.startDate,
    end_date: formState.endDate,
    travelers: formState.travelers,
    budget: formState.budget,
    preferences: formState.preferences,
    pace: formState.pace,
    dietary_preferences: formState.dietaryPreferences,
    hotel_level: formState.hotelLevel,
    special_notes: [...formState.selectedExtraNotes, formState.notes].filter(Boolean).join("；"),
  };

  isSubmitting.value = true;
  try {
    const itinerary = await generateTrip(payload);
    message.success("行程生成成功，已切换到结果页。");
    emit("generated", itinerary);
  } catch (error) {
    console.error(error);
    if (axios.isAxiosError(error)) {
      if (error.code === "ECONNABORTED") {
        message.error("行程生成超时，模型返回较慢，请稍后再试。");
      } else if (error.response) {
        message.error(`行程生成失败：后端返回 ${error.response.status}。`);
      } else {
        message.error("行程生成失败，请检查前端到后端的连接。");
      }
    } else {
      message.error("行程生成失败，请检查后端地址或服务状态。");
    }
  } finally {
    isSubmitting.value = false;
  }
}
</script>

<template>
  <section class="grid gap-5">
    <!-- ===== 目的地与日期 - 带边框亮起卡片 ===== -->
    <div class="card-glow p-6 sm:p-8 relative overflow-hidden
                before:absolute before:inset-0 before:rounded-3xl before:p-[2px]
                before:bg-gradient-to-br before:from-brand-400/60 before:via-accent-500/30 before:to-brand-300/20
                before:-z-10 before:content-['']
                after:absolute after:inset-[2px] after:rounded-[22px] after:bg-white/90 after:-z-10 after:content-['']">
      <div class="section-heading !border-none !pb-2">
        <span class="text-lg">📍</span>
        <span>目的地与日期</span>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-4">
        <div class="lg:col-span-2">
          <label class="block mb-2 text-gray-500 text-xs font-semibold uppercase tracking-wide">目的地城市</label>
          <input
            v-model="formState.destination"
            placeholder="请输入目的地"
            class="w-full h-11 px-4 rounded-xl border border-brand-200/40 bg-white text-gray-800
                   outline-none focus:border-brand-400 focus:ring-[3px] focus:ring-brand-400/10 transition-all"
          />
        </div>
        <div class="lg:col-span-1.5">
          <label class="block mb-2 text-gray-500 text-xs font-semibold uppercase tracking-wide">开始日期</label>
          <input
            v-model="formState.startDate"
            class="w-full h-11 px-4 rounded-xl border border-brand-200/40 bg-white text-gray-800
                   outline-none focus:border-brand-400 focus:ring-[3px] focus:ring-brand-400/10 transition-all"
          />
        </div>
        <div class="lg:col-span-1.5">
          <label class="block mb-2 text-gray-500 text-xs font-semibold uppercase tracking-wide">结束日期</label>
          <input
            v-model="formState.endDate"
            class="w-full h-11 px-4 rounded-xl border border-brand-200/40 bg-white text-gray-800
                   outline-none focus:border-brand-400 focus:ring-[3px] focus:ring-brand-400/10 transition-all"
          />
        </div>
        <div class="sm:col-span-1 lg:col-span-1">
          <label class="block mb-2 text-gray-500 text-xs font-semibold uppercase tracking-wide">人数</label>
          <input
            type="number"
            :value="formState.travelers"
            @input="formState.travelers = Math.max(1, Number(($event.target as HTMLInputElement).value))"
            min="1"
            class="w-full h-11 px-4 rounded-xl border border-brand-200/40 bg-white text-gray-800
                   outline-none focus:border-brand-400 focus:ring-[3px] focus:ring-brand-400/10 transition-all"
          />
        </div>
        <div class="flex items-end">
          <div class="flex items-center justify-center w-full h-11 rounded-xl bg-gradient-to-br from-brand-400 to-accent-500 text-white font-bold text-sm">
            {{ dayCount }} 天
          </div>
        </div>
      </div>
    </div>

    <!-- ===== 偏好设置 ===== -->
    <div class="card-glow p-6 sm:p-8">
      <div class="section-heading">
        <span class="text-lg">⚙️</span>
        <span>偏好设置</span>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-5">
        <div>
          <label class="block mb-2 text-gray-500 text-xs font-semibold uppercase tracking-wide">节奏偏好</label>
          <select
            v-model="formState.pace"
            class="w-full h-11 px-4 rounded-xl border border-brand-200/40 bg-white text-gray-800
                   outline-none focus:border-brand-400 focus:ring-[3px] focus:ring-brand-400/10 transition-all"
          >
            <option value="轻松">轻松</option>
            <option value="适中">适中</option>
            <option value="紧凑">紧凑</option>
          </select>
        </div>
        <div>
          <label class="block mb-2 text-gray-500 text-xs font-semibold uppercase tracking-wide">住宿偏好</label>
          <select
            v-model="formState.hotelLevel"
            class="w-full h-11 px-4 rounded-xl border border-brand-200/40 bg-white text-gray-800
                   outline-none focus:border-brand-400 focus:ring-[3px] focus:ring-brand-400/10 transition-all"
          >
            <option value="舒适型">舒适型</option>
            <option value="高档型">高档型</option>
            <option value="经济型">经济型</option>
          </select>
        </div>
        <div>
          <label class="block mb-2 text-gray-500 text-xs font-semibold uppercase tracking-wide">预算 (元)</label>
          <input
            type="number"
            :value="formState.budget"
            @input="formState.budget = Math.max(0, Number(($event.target as HTMLInputElement).value))"
            min="0"
            class="w-full h-11 px-4 rounded-xl border border-brand-200/40 bg-white text-gray-800
                   outline-none focus:border-brand-400 focus:ring-[3px] focus:ring-brand-400/10 transition-all"
          />
        </div>
      </div>

      <!-- 旅行偏好 Chips -->
      <div class="mb-5">
        <label class="block mb-3 text-gray-500 text-xs font-semibold uppercase tracking-wide">旅行偏好 (可多选)</label>
        <div class="flex flex-wrap gap-2.5">
          <button
            v-for="tag in preferenceOptions"
            :key="tag"
            type="button"
            :class="[
              'px-4 py-2 rounded-full text-sm font-semibold border-none cursor-pointer transition-all duration-200',
              formState.preferences.includes(tag)
                ? 'bg-gradient-to-br from-brand-400 to-accent-500 text-white shadow-[0_4px_14px_rgba(109,130,222,0.35)] scale-105'
                : 'bg-gray-100 text-gray-500 hover:bg-gray-200 hover:text-gray-700'
            ]"
            @click="togglePreference(tag)"
          >
            {{ tag }}
          </button>
        </div>
      </div>

      <!-- 饮食偏好 Chips -->
      <div>
        <label class="block mb-3 text-gray-500 text-xs font-semibold uppercase tracking-wide">饮食偏好 (可多选)</label>
        <div class="flex flex-wrap gap-2.5">
          <button
            v-for="tag in dietaryOptions"
            :key="tag"
            type="button"
            :class="[
              'px-4 py-2 rounded-full text-sm font-semibold border-none cursor-pointer transition-all duration-200',
              formState.dietaryPreferences.includes(tag)
                ? 'bg-gradient-to-br from-emerald-400 to-teal-500 text-white shadow-[0_4px_14px_rgba(52,211,153,0.35)] scale-105'
                : 'bg-gray-100 text-gray-500 hover:bg-gray-200 hover:text-gray-700'
            ]"
            @click="toggleDietary(tag)"
          >
            {{ tag }}
          </button>
        </div>
      </div>
    </div>

    <!-- ===== 额外要求 ===== -->
    <div class="card-glow p-6 sm:p-8">
      <div class="section-heading">
        <span class="text-lg">💬</span>
        <span>额外要求 (可多选 + 补充)</span>
      </div>

      <!-- 结构化 Chips -->
      <div class="mb-4">
        <label class="block mb-3 text-gray-500 text-xs font-semibold uppercase tracking-wide">常用要求 (点击选择)</label>
        <div class="flex flex-wrap gap-2.5">
          <button
            v-for="tag in extraNoteOptions"
            :key="tag"
            type="button"
            :class="[
              'px-4 py-2 rounded-full text-sm font-semibold border-none cursor-pointer transition-all duration-200',
              formState.selectedExtraNotes.includes(tag)
                ? 'bg-gradient-to-br from-violet-400 to-purple-500 text-white shadow-[0_4px_14px_rgba(139,92,246,0.35)] scale-105'
                : 'bg-gray-100 text-gray-500 hover:bg-gray-200 hover:text-gray-700'
            ]"
            @click="toggleExtraNote(tag)"
          >
            {{ tag }}
          </button>
        </div>
      </div>

      <!-- 补充文本 -->
      <div>
        <label class="block mb-2 text-gray-500 text-xs font-semibold uppercase tracking-wide">补充说明</label>
        <textarea
          v-model="formState.notes"
          :maxlength="notesMaxLength"
          rows="2"
          placeholder="还有什么想补充的？例如具体景点、活动等..."
          class="w-full resize-y min-h-[60px] p-4 rounded-xl border border-brand-200/40 bg-white text-gray-800
                 outline-none focus:border-brand-400 focus:ring-[3px] focus:ring-brand-400/10 transition-all
                 text-sm leading-relaxed"
        ></textarea>
        <div class="flex justify-end mt-2">
          <span
            :class="[
              'text-xs font-medium transition-colors',
              notesRemaining < 20 ? 'text-red-400' : notesRemaining < 50 ? 'text-amber-500' : 'text-gray-400'
            ]"
          >
            剩余 {{ notesRemaining }} 字符
          </span>
        </div>
      </div>
    </div>

    <!-- ===== 提交按钮 ===== -->
    <div class="text-center py-2">
      <button
        class="btn-primary min-w-[220px] text-base"
        :disabled="isSubmitting"
        @click="handleSubmit"
      >
        {{ isSubmitting ? "正在生成中..." : "开始规划 ✨" }}
      </button>
      <p class="mt-3 text-gray-400 text-xs">
        当前已接入 /trip/generate，生成成功后会展示真实 itinerary
      </p>
    </div>
  </section>
</template>
