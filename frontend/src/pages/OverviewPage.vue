<script setup>
import { computed, inject } from "vue";
import {
  ArrowRight,
  ChartNetwork,
  CheckCircle2,
  ChevronRight,
  Clock,
  Cpu,
  GitBranch,
  KeyRound,
  Settings2,
  Users,
  XCircle,
} from "lucide-vue-next";
import { I18N_KEY } from "../i18n";

const props = defineProps({
  agents: {
    type: Array,
    required: true,
  },
  workflows: {
    type: Array,
    required: true,
  },
  templates: {
    type: Array,
    required: true,
  },
  historyCount: {
    type: Number,
    default: 0,
  },
  settings: {
    type: Object,
    default: null,
  },
});

defineEmits(["navigate"]);

const i18n = inject(I18N_KEY, null);
const t = i18n?.t || ((key) => key);

const steps = computed(() => [
  { id: "01", title: t("overview.step1Title"), detail: t("overview.step1Desc"), tab: "agents", color: "blue" },
  { id: "02", title: t("overview.step2Title"), detail: t("overview.step2Desc"), tab: "workflows", color: "violet" },
  { id: "03", title: t("overview.step3Title"), detail: t("overview.step3Desc"), tab: "playground", color: "green" },
]);

const modelProfiles = computed(() => props.settings?.model_profiles || []);
const activeProfileId = computed(() => props.settings?.active_model_profile_id || "");
const activeProfile = computed(() => modelProfiles.value.find((p) => p.id === activeProfileId.value) || null);
const hasApiKey = computed(() => Boolean(props.settings?.skillhub_api_key));

const statusItems = computed(() => [
  {
    label: t("overview.statusModel"),
    ok: !!activeProfile.value,
    detail: activeProfile.value ? activeProfile.value.name : t("overview.statusNotConfigured"),
    icon: Cpu,
  },
  {
    label: t("overview.statusApiKey"),
    ok: hasApiKey.value,
    detail: hasApiKey.value ? t("overview.statusConfigured") : t("overview.statusNotConfigured"),
    icon: KeyRound,
  },
  {
    label: t("overview.statusAgents"),
    ok: props.agents.length > 0,
    detail: `${props.agents.length} ${t("overview.statusAgentsCount")}`,
    icon: Users,
  },
  {
    label: t("overview.statusWorkflows"),
    ok: props.workflows.length > 0,
    detail: `${props.workflows.length} ${t("overview.statusWorkflowsCount")}`,
    icon: GitBranch,
  },
]);
</script>

<template>
  <div class="page-stack page-overview">
    <section class="overview-grid">
      <div class="glass-panel hero-card">
        <span class="chip chip-hero">{{ t("overview.chip") }}</span>
        <h2>
          {{ t("overview.headline1") }}
          <br />
          {{ t("overview.headline2") }}
        </h2>
        <p>{{ t("overview.desc") }}</p>
        <div class="hero-orb"></div>
        <ChartNetwork :size="64" class="hero-watermark" />
      </div>

      <div class="stat-stack">
        <article class="glass-panel stat-tile stat-tile-blue" @click="$emit('navigate', 'agents')">
          <div class="stat-icon stat-icon-blue">
            <Users :size="22" />
          </div>
          <div>
            <div class="stat-label">{{ t("overview.agents") }}</div>
            <div class="stat-value">{{ props.agents.length }}</div>
          </div>
          <ChevronRight :size="18" class="stat-chevron" />
        </article>

        <article class="glass-panel stat-tile stat-tile-violet" @click="$emit('navigate', 'workflows')">
          <div class="stat-icon stat-icon-violet">
            <GitBranch :size="22" />
          </div>
          <div>
            <div class="stat-label">{{ t("overview.workflows") }}</div>
            <div class="stat-value">{{ props.workflows.length }}</div>
          </div>
          <ChevronRight :size="18" class="stat-chevron" />
        </article>

        <article class="glass-panel stat-tile stat-tile-green" @click="$emit('navigate', 'history')">
          <div class="stat-icon stat-icon-green">
            <Clock :size="22" />
          </div>
          <div>
            <div class="stat-label">{{ t("overview.history") }}</div>
            <div class="stat-value">{{ props.historyCount }}</div>
          </div>
          <ChevronRight :size="18" class="stat-chevron" />
        </article>
      </div>
    </section>

    <section class="glass-panel section-card">
      <div class="section-header">
        <div>
          <h3>
            <Settings2 :size="18" class="text-slate-400" />
            {{ t("overview.flowTitle") }}
          </h3>
          <p>{{ t("overview.flowDesc") }}</p>
        </div>
      </div>

      <div class="step-grid">
        <button
          v-for="step in steps"
          :key="step.id"
          class="step-card"
          :class="'step-card-' + step.color"
          @click="$emit('navigate', step.tab)"
        >
          <div class="step-line">
            <span class="step-index">{{ step.id }}</span>
            <span class="step-divider"></span>
          </div>
          <h4>
            {{ step.title }}
            <ArrowRight :size="15" class="step-arrow" />
          </h4>
          <p>{{ step.detail }}</p>
        </button>
      </div>
    </section>

    <section class="glass-panel section-card">
      <div class="section-header">
        <div>
          <h3>
            <Cpu :size="18" class="text-indigo-400" />
            {{ t("overview.statusTitle") }}
          </h3>
          <p>{{ t("overview.statusDesc") }}</p>
        </div>
        <button class="text-button" @click="$emit('navigate', 'settings')">
          {{ t("overview.statusGoSettings") }}
          <ArrowRight :size="14" />
        </button>
      </div>

      <div class="status-grid">
        <div
          v-for="item in statusItems"
          :key="item.label"
          class="status-item"
          :class="{ 'status-ok': item.ok, 'status-warn': !item.ok }"
        >
          <div class="status-item-left">
            <component :is="item.icon" :size="18" class="status-item-icon" />
            <span class="status-item-label">{{ item.label }}</span>
          </div>
          <div class="status-item-right">
            <span class="status-item-detail">{{ item.detail }}</span>
            <CheckCircle2 v-if="item.ok" :size="16" class="status-badge-ok" />
            <XCircle v-else :size="16" class="status-badge-warn" />
          </div>
        </div>
      </div>
    </section>
  </div>
</template>
