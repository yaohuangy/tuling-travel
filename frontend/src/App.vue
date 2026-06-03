<script setup lang="ts">
import { ref } from "vue";

import type { Itinerary } from "./types";
import History from "./views/History.vue";
import Home from "./views/Home.vue";
import Result from "./views/Result.vue";

const currentView = ref<"home" | "result" | "history">("home");
const latestItinerary = ref<Itinerary | null>(null);

function handleGenerated(itinerary: Itinerary) {
  latestItinerary.value = itinerary;
  currentView.value = "result";
}

function openTrip(itinerary: Itinerary) {
  latestItinerary.value = itinerary;
  currentView.value = "result";
}

function updateCurrentItinerary(itinerary: Itinerary) {
  latestItinerary.value = itinerary;
  currentView.value = "result";
}
</script>

<template>
  <div class="relative min-h-screen px-4 sm:px-6 pb-16 pt-10 overflow-hidden">
    <!-- Ambient glow -->
    <div class="absolute w-80 h-80 rounded-full blur-2xl opacity-50 pointer-events-none -top-28 -left-24 bg-brand-400/45"></div>
    <div class="absolute w-80 h-80 rounded-full blur-2xl opacity-25 pointer-events-none -right-20 bottom-32 bg-accent-600/25"></div>

    <!-- Header -->
    <header class="relative z-10 max-w-6xl mx-auto mb-7 text-center">
      <div class="inline-flex items-center px-4 py-2 rounded-full bg-white/70 text-brand-600 text-sm font-semibold tracking-wider shadow-[0_12px_30px_rgba(98,116,164,0.1)]">
        Trip Planner Demo
      </div>
      <h1 class="mt-4 text-white text-4xl sm:text-5xl font-bold leading-tight relative">
        智能旅行助手
        <div class="absolute -inset-x-6 -top-6 h-[220px] -z-10 rounded-[36px] bg-gradient-to-br from-brand-500 via-brand-500 to-accent-600 shadow-[0_32px_80px_rgba(95,110,172,0.3)]"></div>
      </h1>

      <!-- Tabs -->
      <div class="inline-flex gap-2.5 mt-6 p-2 rounded-2xl bg-white/15 backdrop-blur-[10px]">
        <button
          :class="[
            'border-none rounded-xl px-5 py-2.5 font-semibold text-sm cursor-pointer transition-colors',
            currentView === 'home'
              ? 'bg-white/90 text-brand-600'
              : 'bg-transparent text-white/85 hover:bg-white/10'
          ]"
          @click="currentView = 'home'"
        >
          规划页
        </button>
        <button
          :class="[
            'border-none rounded-xl px-5 py-2.5 font-semibold text-sm transition-colors',
            currentView === 'result'
              ? 'bg-white/90 text-brand-600'
              : latestItinerary
                ? 'bg-transparent text-white/85 hover:bg-white/10 cursor-pointer'
                : 'bg-transparent text-white/40 cursor-not-allowed'
          ]"
          :disabled="!latestItinerary"
          @click="currentView = 'result'"
        >
          结果页
        </button>
        <button
          :class="[
            'border-none rounded-xl px-5 py-2.5 font-semibold text-sm cursor-pointer transition-colors',
            currentView === 'history'
              ? 'bg-white/90 text-brand-600'
              : 'bg-transparent text-white/85 hover:bg-white/10'
          ]"
          @click="currentView = 'history'"
        >
          历史列表
        </button>
      </div>
    </header>

    <!-- Main content -->
    <main class="relative z-10 max-w-6xl mx-auto">
      <Home v-if="currentView === 'home'" @generated="handleGenerated" />
      <Result
        v-else-if="currentView === 'result'"
        :itinerary="latestItinerary"
        @back-home="currentView = 'home'"
        @view-history="currentView = 'history'"
        @updated="updateCurrentItinerary"
      />
      <History
        v-else
        :active="currentView === 'history'"
        @open-trip="openTrip"
      />
    </main>
  </div>
</template>
