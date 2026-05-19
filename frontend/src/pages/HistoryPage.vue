<script setup>
import { inject, onMounted, ref, watch } from "vue";
import {
  Clock,
  GitBranch,
  History,
  Play,
  Search,
  Trash2,
} from "lucide-vue-next";
import { I18N_KEY } from "../i18n";
import {
  deleteConversation,
  fetchConversationsPage,
} from "../api";

const emit = defineEmits(["replay", "refresh"]);

const i18n = inject(I18N_KEY, null);
const t = i18n?.t || ((key) => key);
const workflowTypeLabel = i18n?.workflowTypeLabel || ((type) => type);

const items = ref([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(10);
const search = ref("");
const workflowType = ref("");
const loading = ref(false);
const deletingId = ref("");

const workflowTypeOptions = [
  { value: "", label: () => t("history.filterAll") },
  { value: "router_specialists", label: () => workflowTypeLabel("router_specialists") },
  { value: "planner_executor", label: () => workflowTypeLabel("planner_executor") },
  { value: "supervisor_dynamic", label: () => workflowTypeLabel("supervisor_dynamic") },
  { value: "single_agent_chat", label: () => workflowTypeLabel("single_agent_chat") },
  { value: "peer_handoff", label: () => workflowTypeLabel("peer_handoff") },
];

const totalPages = ref(1);

async function loadPage() {
  loading.value = true;
  try {
    const data = await fetchConversationsPage({
      page: page.value,
      pageSize: pageSize.value,
      workflowType: workflowType.value,
      search: search.value,
    });
    items.value = data.items || [];
    total.value = data.total || 0;
    totalPages.value = Math.max(1, Math.ceil(total.value / pageSize.value));
  } catch {
    items.value = [];
    total.value = 0;
    totalPages.value = 1;
  } finally {
    loading.value = false;
  }
}

function handleSearch() {
  page.value = 1;
  loadPage();
}

function handleFilterChange() {
  page.value = 1;
  loadPage();
}

function handlePrev() {
  if (page.value > 1) {
    page.value -= 1;
    loadPage();
  }
}

function handleNext() {
  if (page.value < totalPages.value) {
    page.value += 1;
    loadPage();
  }
}

async function handleDelete(id) {
  if (!confirm(t("history.deleteConfirm"))) return;
  deletingId.value = id;
  try {
    await deleteConversation(id);
    await loadPage();
  } finally {
    deletingId.value = "";
  }
}

function handleReplay(item) {
  emit("replay", item);
}

function formatTime(iso) {
  if (!iso) return "";
  try {
    const d = new Date(iso);
    return d.toLocaleString();
  } catch {
    return iso;
  }
}

function typeBadgeClass(type) {
  const map = {
    router_specialists: "badge-router",
    planner_executor: "badge-planner",
    supervisor_dynamic: "badge-supervisor",
    single_agent_chat: "badge-single",
    peer_handoff: "badge-peer",
  };
  return map[type] || "badge-default";
}

onMounted(() => {
  loadPage();
});

watch(workflowType, () => {
  handleFilterChange();
});
</script>

<template>
  <section class="history-page">
    <header class="history-header">
      <div class="history-header-text">
        <h2 class="history-title">
          <History :size="22" />
          {{ t("history.title") }}
        </h2>
        <p class="history-desc">{{ t("history.desc") }}</p>
      </div>
    </header>

    <div class="history-toolbar">
      <div class="history-search">
        <input
          v-model="search"
          type="text"
          class="history-search-input"
          :placeholder="t('history.searchPlaceholder')"
          @keyup.enter="handleSearch"
        />
        <Search :size="16" class="history-search-icon" />
      </div>
      <div class="history-filter">
        <button
          v-for="opt in workflowTypeOptions"
          :key="opt.value"
          class="history-filter-chip"
          :class="{ active: workflowType === opt.value }"
          @click="workflowType = opt.value"
        >
          {{ opt.label() }}
        </button>
      </div>
    </div>

    <div v-if="loading" class="history-loading">Loading...</div>

    <div v-else-if="items.length === 0" class="history-empty">
      {{ t("history.noResults") }}
    </div>

    <div v-else class="history-list">
      <article
        v-for="item in items"
        :key="item.id"
        class="history-card"
      >
        <div class="history-card-main">
          <div class="history-card-icon">
            <GitBranch :size="18" />
          </div>
          <div class="history-card-body">
            <div class="history-card-top">
              <span class="history-card-title">{{ item.title || item.user_input || "—" }}</span>
              <span class="history-type-badge" :class="typeBadgeClass(item.workflow_type)">
                {{ workflowTypeLabel(item.workflow_type) }}
              </span>
            </div>
            <div class="history-card-meta">
              <span class="history-card-input">{{ item.user_input ? (item.user_input.length > 80 ? item.user_input.slice(0, 80) + "..." : item.user_input) : "" }}</span>
            </div>
            <div class="history-card-bottom">
              <span class="history-card-time">
                <Clock :size="12" />
                {{ formatTime(item.updated_at || item.created_at) }}
              </span>
            </div>
          </div>
          <div class="history-card-actions">
            <button
              class="history-action-btn history-action-replay"
              @click="handleReplay(item)"
            >
              <Play :size="14" />
              {{ t("history.replay") }}
            </button>
            <button
              class="history-action-btn history-action-delete"
              :disabled="deletingId === item.id"
              @click="handleDelete(item.id)"
            >
              <Trash2 :size="14" />
            </button>
          </div>
        </div>
      </article>
    </div>

    <div v-if="totalPages > 1" class="history-pagination">
      <button
        class="history-page-btn"
        :disabled="page <= 1"
        @click="handlePrev"
      >
        {{ t("history.prev") }}
      </button>
      <span class="history-page-info">
        {{ t("history.page") }} {{ page }} / {{ totalPages }}
        &nbsp;·&nbsp;
        {{ t("history.total") }} {{ total }}
      </span>
      <button
        class="history-page-btn"
        :disabled="page >= totalPages"
        @click="handleNext"
      >
        {{ t("history.next") }}
      </button>
    </div>
  </section>
</template>
