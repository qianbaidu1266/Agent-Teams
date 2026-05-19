<script setup>
import { computed, inject, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import {
  CheckCircle2,
  Copy,
  Download,
  Folder,
  GripVertical,
  KeyRound,
  Link2,
  Pencil,
  Play,
  Plus,
  RefreshCw,
  Save,
  Search,
  Settings2,
  Trash2,
  X,
  Bot,
  Brain,
  BrainCircuit,
  Code,
  Cpu,
  Eye,
  Flame,
  Globe,
  Heart,
  Lightbulb,
  Mic,
  PencilLine,
  Rocket,
  Shield,
  Sparkles,
  Star,
  Wand2,
  Zap,
} from "lucide-vue-next";
import { I18N_KEY } from "../i18n";
import { createIcon, deleteIcon, searchSkillsFromSkillhub, installSkillFromSkillhub } from "../api";

const props = defineProps({
  settings: {
    type: Object,
    default: null,
  },
  saving: {
    type: Boolean,
    default: false,
  },
  icons: {
    type: Array,
    default: () => [],
  },
});

const emit = defineEmits(["save", "icons-changed"]);
const i18n = inject(I18N_KEY, null);
const t = i18n?.t || ((key) => key);

const form = reactive({
  model_profiles: [],
  active_model_profile_id: "",
  agent_output_dir: "",
  skillhub_api_key: "",
});
const editingProfileId = ref("");
const editingOutputDir = ref(false);
const copiedOutputDir = ref(false);
const editingSkillhubKey = ref(false);

const skillhubSearchQuery = ref("");
const skillhubSearchResults = ref([]);
const skillhubSearching = ref(false);
const skillhubSearchMessage = ref("");
const skillhubInstallingId = ref("");
const skillhubModalOpen = ref(false);
const skillhubSelectedSkills = ref(new Set());
const skillhubBatchInstalling = ref(false);

function collapseAll() {
  editingProfileId.value = "";
  editingOutputDir.value = false;
  editingSkillhubKey.value = false;
}

function handleDocumentClick(event) {
  const settingsCard = event.target.closest(".settings-card");
  const skillhubModal = event.target.closest(".skillhub-modal-panel");
  if (!settingsCard && !skillhubModal) {
    collapseAll();
  }
}

onMounted(() => document.addEventListener("click", handleDocumentClick));
onUnmounted(() => document.removeEventListener("click", handleDocumentClick));
const providerPresets = [
  {
    id: "moonshot",
    label: "月之暗面",
    name: "Kimi",
    base_url: "https://api.moonshot.cn/v1",
    model: "moonshot-v1-8k",
  },
  {
    id: "zhipu",
    label: "智谱",
    name: "Zhipu",
    base_url: "https://open.bigmodel.cn/api/paas/v4",
    model: "glm-4.5",
  },
  {
    id: "minimax",
    label: "MiniMax",
    name: "MiniMax",
    base_url: "https://api.minimaxi.com/v1",
    model: "MiniMax-M2.7",
  },
  {
    id: "custom",
    label: "其他",
    name: "",
    base_url: "https://api.openai.com/v1",
    model: "",
  },
];

function makeProfile(index = 0) {
  return {
    id: `profile_${Date.now()}_${index}`,
    provider: "custom",
    name: index === 0 ? "Default" : `Profile ${index + 1}`,
    api_key: "",
    base_url: "https://api.openai.com/v1",
    model: "gpt-4o-mini",
  };
}

watch(
  () => props.settings,
  (value) => {
    const profiles = Array.isArray(value?.model_profiles) ? value.model_profiles : [];
    form.model_profiles = profiles.length
      ? profiles.map((profile) => ({ provider: profile.provider || "custom", ...profile }))
      : [makeProfile(0)];
    form.active_model_profile_id =
      value?.active_model_profile_id || form.model_profiles[0]?.id || "";
    form.agent_output_dir = String(value?.agent_output_dir || "");
    form.skillhub_api_key = String(value?.skillhub_api_key || "");
    if (!form.model_profiles.some((profile) => profile.id === editingProfileId.value)) {
      editingProfileId.value = "";
    }
  },
  { immediate: true },
);

const hasProfiles = computed(() => form.model_profiles.length > 0);

function addProfile() {
  const next = makeProfile(form.model_profiles.length);
  form.model_profiles = [...form.model_profiles, next];
  if (!form.active_model_profile_id) {
    form.active_model_profile_id = next.id;
  }
  editingProfileId.value = next.id;
}

function duplicateProfile(profile) {
  const duplicated = {
    ...profile,
    id: `profile_${Date.now()}_${form.model_profiles.length}`,
    name: `${profile.name} Copy`,
  };
  form.model_profiles = [...form.model_profiles, duplicated];
}

function applyProviderPreset(profile, presetId) {
  const preset = providerPresets.find((item) => item.id === presetId);
  if (!preset) return;
  profile.provider = preset.id;
  if (preset.name) {
    profile.name = preset.name;
  }
  profile.base_url = preset.base_url;
  profile.model = preset.model;
}

function removeProfile(profileId) {
  if (props.saving) return;
  if (form.model_profiles.length <= 1) return;
  form.model_profiles = form.model_profiles.filter((profile) => profile.id !== profileId);
  if (form.active_model_profile_id === profileId) {
    form.active_model_profile_id = form.model_profiles[0]?.id || "";
  }
  if (editingProfileId.value === profileId) {
    editingProfileId.value = "";
  }
  submitModelProfiles();
}

function toggleEditProfile(profileId) {
  editingProfileId.value = editingProfileId.value === profileId ? "" : profileId;
}

function profileInitial(name) {
  const raw = String(name || "").trim();
  return raw ? raw.slice(0, 1).toUpperCase() : "M";
}

function buildPayload() {
  return {
    model_profiles: form.model_profiles.map((profile) => ({ ...profile })),
    active_model_profile_id: form.active_model_profile_id || form.model_profiles[0]?.id || null,
    agent_output_dir: String(form.agent_output_dir || "").trim(),
    skillhub_api_key: String(form.skillhub_api_key || "").trim(),
  };
}

function submitModelProfiles() {
  if (props.saving) return;
  collapseAll();
  emit("save", buildPayload());
}

function submitAgentOutputDir() {
  if (props.saving) return;
  collapseAll();
  emit("save", buildPayload());
}

function activateAndSave(profileId) {
  if (props.saving) return;
  collapseAll();
  form.active_model_profile_id = profileId;
  submitModelProfiles();
}

function toggleEditOutputDir() {
  editingOutputDir.value = !editingOutputDir.value;
}

function copyOutputDir() {
  const dir = String(form.agent_output_dir || "").trim();
  if (!dir) return;
  navigator.clipboard.writeText(dir).then(() => {
    copiedOutputDir.value = true;
    setTimeout(() => {
      copiedOutputDir.value = false;
    }, 1800);
  });
}

function cancelOutputDirEdit() {
  form.agent_output_dir = String(props.settings?.agent_output_dir || "");
  editingOutputDir.value = false;
}

const presetIcons = [
  { id: "bot", label: "Bot", component: Bot },
  { id: "brain", label: "Brain", component: Brain },
  { id: "brain-circuit", label: "Brain Circuit", component: BrainCircuit },
  { id: "code", label: "Code", component: Code },
  { id: "cpu", label: "CPU", component: Cpu },
  { id: "eye", label: "Eye", component: Eye },
  { id: "flame", label: "Flame", component: Flame },
  { id: "globe", label: "Globe", component: Globe },
  { id: "heart", label: "Heart", component: Heart },
  { id: "lightbulb", label: "Lightbulb", component: Lightbulb },
  { id: "mic", label: "Mic", component: Mic },
  { id: "pencil", label: "Pencil", component: PencilLine },
  { id: "rocket", label: "Rocket", component: Rocket },
  { id: "search", label: "Search", component: Search },
  { id: "shield", label: "Shield", component: Shield },
  { id: "sparkles", label: "Sparkles", component: Sparkles },
  { id: "star", label: "Star", component: Star },
  { id: "wand", label: "Wand", component: Wand2 },
  { id: "zap", label: "Zap", component: Zap },
];

const iconComponentMap = Object.fromEntries(presetIcons.map((i) => [i.id, i.component]));

const newIconName = ref("");
const newIconLabel = ref("");
const newIconSvg = ref("");
const addingIcon = ref(false);
const savingIcon = ref(false);
const iconMessage = ref("");
const iconMessageType = ref("success");

function resolveIconComponent(iconName) {
  return iconComponentMap[iconName] || null;
}

async function handleAddIcon() {
  const name = newIconName.value.trim();
  const label = newIconLabel.value.trim();
  iconMessage.value = "";
  if (!name || !label) {
    iconMessageType.value = "error";
    iconMessage.value = t("settings.iconNameRequired");
    return;
  }
  savingIcon.value = true;
  try {
    await createIcon({
      name,
      label,
      category: "custom",
      svg_content: newIconSvg.value.trim() || null,
    });
    newIconName.value = "";
    newIconLabel.value = "";
    newIconSvg.value = "";
    iconMessageType.value = "success";
    iconMessage.value = t("settings.iconAdded");
    emit("icons-changed");
    setTimeout(() => { iconMessage.value = ""; }, 3000);
  } catch (error) {
    iconMessageType.value = "error";
    iconMessage.value = String(error.message || error);
  } finally {
    savingIcon.value = false;
  }
}

async function handleDeleteIcon(iconId) {
  iconMessage.value = "";
  try {
    await deleteIcon(iconId);
    iconMessageType.value = "success";
    iconMessage.value = t("settings.iconDeleted");
    emit("icons-changed");
    setTimeout(() => { iconMessage.value = ""; }, 3000);
  } catch (error) {
    iconMessageType.value = "error";
    iconMessage.value = String(error.message || error);
  }
}

function toggleEditSkillhubKey() {
  if (!editingSkillhubKey.value) {
    form.skillhub_api_key = String(props.settings?.skillhub_api_key || "");
  }
  editingSkillhubKey.value = !editingSkillhubKey.value;
}

function cancelSkillhubKeyEdit() {
  form.skillhub_api_key = String(props.settings?.skillhub_api_key || "");
  editingSkillhubKey.value = false;
}

function submitSkillhubKey() {
  if (props.saving) return;
  collapseAll();
  emit("save", buildPayload());
}

async function handleSearchSkillhub() {
  if (skillhubSearching.value) return;
  const query = skillhubSearchQuery.value.trim() || "search";
  skillhubSearching.value = true;
  skillhubSearchMessage.value = "Searching...";
  try {
    const result = await searchSkillsFromSkillhub(query, 30);
    skillhubSearchResults.value = result.skills || [];
    skillhubSearchMessage.value = result.total > 0 ? `Found ${result.total} skills` : "No skills found";
    skillhubSelectedSkills.value = new Set();
  } catch (error) {
    skillhubSearchMessage.value = `Search failed: ${error.message || error}`;
    skillhubSearchResults.value = [];
  } finally {
    skillhubSearching.value = false;
  }
}

function toggleSkillSelection(sourceSkillId) {
  if (skillhubSelectedSkills.value.has(sourceSkillId)) {
    skillhubSelectedSkills.value.delete(sourceSkillId);
  } else {
    skillhubSelectedSkills.value.add(sourceSkillId);
  }
  skillhubSelectedSkills.value = new Set(skillhubSelectedSkills.value);
}

function isSkillSelected(sourceSkillId) {
  return skillhubSelectedSkills.value.has(sourceSkillId);
}

function openSkillhubModal() {
  skillhubModalOpen.value = true;
  skillhubSearchQuery.value = "";
  skillhubSearchResults.value = [];
  skillhubSearchMessage.value = "";
  skillhubSelectedSkills.value = new Set();
}

function closeSkillhubModal() {
  skillhubModalOpen.value = false;
}

async function handleBatchInstallSkills() {
  if (skillhubBatchInstalling.value || skillhubSelectedSkills.value.size === 0) return;
  skillhubBatchInstalling.value = true;
  const selectedIds = Array.from(skillhubSelectedSkills.value);
  let installed = 0;
  let failed = 0;
  for (const sourceSkillId of selectedIds) {
    try {
      const skill = skillhubSearchResults.value.find(s => s.source_skill_id === sourceSkillId);
      await installSkillFromSkillhub(sourceSkillId, skill?.name);
      installed++;
    } catch {
      failed++;
    }
  }
  skillhubSearchMessage.value = `Installed ${installed} skills${failed > 0 ? `, ${failed} failed` : ""}`;
  emit("icons-changed");
  skillhubSelectedSkills.value = new Set();
  setTimeout(() => { skillhubSearchMessage.value = ""; }, 3000);
  skillhubBatchInstalling.value = false;
}

async function handleInstallSkillhubSkill(skill) {
  if (skillhubInstallingId.value) return;
  skillhubInstallingId.value = skill.source_skill_id;
  try {
    await installSkillFromSkillhub(skill.source_skill_id, skill.name);
    skillhubSearchMessage.value = `Installed: ${skill.name}`;
    emit("icons-changed");
    setTimeout(() => { skillhubSearchMessage.value = ""; }, 2000);
  } catch (error) {
    skillhubSearchMessage.value = `Install failed: ${error.message || error}`;
  } finally {
    skillhubInstallingId.value = "";
  }
}
</script>

<template>
  <section class="page-stack settings-page">
    <div class="manager-topbar">
      <div>
        <h2>{{ t("settings.title") }}</h2>
        <p>{{ t("settings.desc") }}</p>
      </div>
    </div>

    <section class="glass-panel section-card settings-card">
      <div class="section-header">
        <div>
          <h3>
            <Settings2 :size="18" class="text-slate-400" />
            {{ t("settings.modelProfiles") }}
          </h3>
          <p>{{ t("settings.modelProfilesDesc") }}</p>
        </div>
        <button type="button" class="text-button" @click="addProfile">
          <Plus :size="14" />
          {{ t("settings.addProfile") }}
        </button>
      </div>

      <div v-if="hasProfiles" class="settings-profile-list compact">
        <article
          v-for="profile in form.model_profiles"
          :key="profile.id"
          class="settings-profile-row"
          :class="{
            active: form.active_model_profile_id === profile.id,
            editing: editingProfileId === profile.id,
          }"
        >
          <div class="settings-profile-row-main">
            <div class="settings-profile-reorder">
              <GripVertical :size="18" />
            </div>

            <div class="settings-profile-avatar">
              {{ profileInitial(profile.name) }}
            </div>

            <div class="settings-profile-copy">
              <div class="settings-profile-name-text">{{ profile.name }}</div>
              <div class="settings-profile-url-text">{{ profile.base_url }}</div>
            </div>

            <div class="settings-profile-row-actions">
              <button
                type="button"
                class="settings-profile-activate inline"
                :class="{ active: form.active_model_profile_id === profile.id }"
                @click="activateAndSave(profile.id)"
              >
                <Play v-if="form.active_model_profile_id !== profile.id" :size="14" />
                <CheckCircle2 v-else :size="14" />
                {{ form.active_model_profile_id === profile.id ? t("settings.active") : t("settings.setActive") }}
              </button>

              <button
                type="button"
                class="settings-profile-icon-action"
                @click="toggleEditProfile(profile.id)"
              >
                <Pencil :size="16" />
              </button>

              <button
                type="button"
                class="settings-profile-icon-action"
                @click="duplicateProfile(profile)"
              >
                <Copy :size="16" />
              </button>

              <button
                type="button"
                class="settings-profile-icon-action"
                :disabled="form.model_profiles.length <= 1"
                @click="removeProfile(profile.id)"
              >
                <Trash2 :size="16" />
              </button>
            </div>
          </div>

          <div v-if="editingProfileId === profile.id" class="settings-profile-editor">
            <div class="settings-profile-editor-head" @click="toggleEditProfile(profile.id)">
              <strong>{{ t("settings.editProfile") }}</strong>
            </div>

            <div class="settings-form-grid">
              <div class="settings-provider-picker">
                <span class="settings-provider-label">{{ t("settings.providerPreset") }}</span>
                <div class="settings-provider-list">
                  <button
                    v-for="preset in providerPresets"
                    :key="preset.id"
                    type="button"
                    class="settings-provider-pill"
                    :class="{ active: profile.provider === preset.id }"
                    @click="applyProviderPreset(profile, preset.id)"
                  >
                    {{ preset.label }}
                  </button>
                </div>
              </div>

              <label class="settings-field">
                <span>{{ t("settings.profileName") }}</span>
                <input
                  v-model="profile.name"
                  type="text"
                  :placeholder="t('settings.profileNamePlaceholder')"
                />
              </label>

              <label class="settings-field">
                <span><KeyRound :size="14" /> {{ t("settings.apiKey") }}</span>
                <input
                  v-model="profile.api_key"
                  type="password"
                  autocomplete="off"
                  :placeholder="t('settings.apiKeyPlaceholder')"
                />
              </label>

              <label class="settings-field">
                <span><Link2 :size="14" /> {{ t("settings.baseUrl") }}</span>
                <input
                  v-model="profile.base_url"
                  type="text"
                  :placeholder="t('settings.baseUrlPlaceholder')"
                />
              </label>

              <label class="settings-field">
                <span>{{ t("settings.model") }}</span>
                <input
                  v-model="profile.model"
                  type="text"
                  :placeholder="t('settings.modelPlaceholder')"
                />
              </label>
            </div>

            <div class="settings-profile-editor-actions">
              <button
                type="button"
                class="primary-button"
                :disabled="saving"
                @click="submitModelProfiles"
              >
                <Save :size="16" />
                {{ saving ? t("settings.saving") : t("settings.saveProfile") }}
              </button>
              <button
                type="button"
                class="ghost-button"
                :disabled="saving"
                @click="toggleEditProfile(profile.id)"
              >
                {{ t("settings.closeEditor") }}
              </button>
            </div>
          </div>

        </article>
      </div>
    </section>

    <section class="glass-panel section-card settings-card">
      <div class="section-header">
        <div>
          <h3>
            <Folder :size="18" class="text-slate-400" />
            {{ t("settings.agentOutputDir") }}
          </h3>
          <p>{{ t("settings.agentOutputDirDesc") }}</p>
        </div>
      </div>

      <div class="settings-output-dir-list">
        <article
          class="settings-output-dir-row-card"
          :class="{ editing: editingOutputDir }"
        >
          <div class="settings-output-dir-row-main">
            <div class="settings-output-dir-avatar">
              <Folder :size="20" />
            </div>

            <div class="settings-output-dir-copy">
              <div class="settings-output-dir-label">{{ t("settings.agentOutputDir") }}</div>
              <div class="settings-output-dir-path">{{ form.agent_output_dir || t("settings.agentOutputDirPlaceholder") }}</div>
            </div>

            <div class="settings-output-dir-row-actions">
              <button
                type="button"
                class="settings-profile-icon-action"
                :disabled="!form.agent_output_dir"
                @click="copyOutputDir"
              >
                <CheckCircle2 v-if="copiedOutputDir" :size="16" class="text-green-500" />
                <Copy v-else :size="16" />
              </button>

              <button
                type="button"
                class="settings-profile-icon-action"
                @click="toggleEditOutputDir"
              >
                <Pencil :size="16" />
              </button>
            </div>
          </div>

          <div v-if="editingOutputDir" class="settings-output-dir-editor">
            <div class="settings-output-dir-editor-head" @click="toggleEditOutputDir">
              <strong>{{ t("settings.editAgentOutputDir") }}</strong>
            </div>

            <label class="settings-field">
              <span>{{ t("settings.agentOutputDir") }}</span>
              <input
                v-model="form.agent_output_dir"
                type="text"
                :placeholder="t('settings.agentOutputDirPlaceholder')"
                @keydown.enter.prevent="submitAgentOutputDir"
              />
            </label>

            <div class="settings-output-dir-editor-actions">
              <button
                type="button"
                class="primary-button"
                :disabled="saving"
                @click="submitAgentOutputDir"
              >
                <Save :size="16" />
                {{ saving ? t("settings.saving") : t("settings.saveAgentOutputDir") }}
              </button>
              <button
                type="button"
                class="ghost-button"
                :disabled="saving"
                @click="cancelOutputDirEdit"
              >
                {{ t("settings.closeEditor") }}
              </button>
            </div>
          </div>
        </article>
      </div>
    </section>

    <section class="glass-panel section-card settings-card">
      <div class="section-header">
        <div>
          <h3>
            <Download :size="18" class="text-slate-400" />
            SkillHub
          </h3>
          <p>Search and install skills from SkillHub marketplace</p>
        </div>
      </div>

      <div class="settings-skillhub-key-row">
        <div class="settings-skillhub-key-info">
          <KeyRound :size="18" />
          <div>
            <div class="settings-skillhub-key-label">SkillHub API Key</div>
            <div class="settings-skillhub-key-value">
              {{ form.skillhub_api_key ? '••••' + form.skillhub_api_key.slice(-4) : 'Not configured' }}
            </div>
          </div>
        </div>
        <button type="button" class="settings-profile-icon-action" @click="toggleEditSkillhubKey">
          <Pencil :size="16" />
        </button>
      </div>

      <div v-if="editingSkillhubKey" class="settings-skillhub-key-editor">
        <label class="settings-field">
          <span>SkillHub API Key</span>
          <input
            v-model="form.skillhub_api_key"
            type="password"
            placeholder="Enter your SkillHub API key"
          />
        </label>
        <div class="settings-skillhub-key-actions">
          <button type="button" class="primary-button" :disabled="saving" @click="submitSkillhubKey">
            <Save :size="16" />
            {{ saving ? 'Saving...' : 'Save' }}
          </button>
          <button type="button" class="ghost-button" @click="cancelSkillhubKeyEdit">
            Cancel
          </button>
        </div>
      </div>

      <div class="settings-skillhub-actions">
        <button
          type="button"
          class="primary-button"
          :disabled="!form.skillhub_api_key"
          @click="openSkillhubModal"
        >
          <Search :size="16" />
          Search Skills
        </button>
      </div>
    </section>

    <div v-if="skillhubModalOpen" class="skillhub-modal-overlay" @click="closeSkillhubModal">
      <section class="skillhub-modal-panel" @click.stop>
        <header class="skillhub-modal-header">
          <h3>Search Skills from SkillHub</h3>
          <button type="button" class="skillhub-modal-close" @click="closeSkillhubModal">
            <X :size="20" />
          </button>
        </header>

        <div class="skillhub-modal-search">
          <input
            v-model="skillhubSearchQuery"
            type="text"
            class="skillhub-modal-search-input"
            placeholder="Search skills..."
            @keyup.enter="handleSearchSkillhub"
          />
          <button
            type="button"
            class="skillhub-modal-search-btn"
            :disabled="skillhubSearching"
            @click="handleSearchSkillhub"
          >
            <Search :size="16" />
            {{ skillhubSearching ? 'Searching...' : 'Search' }}
          </button>
        </div>

        <div v-if="skillhubSearchMessage" class="skillhub-modal-message">
          {{ skillhubSearchMessage }}
        </div>

        <div v-if="skillhubSearchResults.length > 0" class="skillhub-modal-results">
          <div class="skillhub-modal-results-header">
            <span>{{ skillhubSearchResults.length }} skills found</span>
            <span v-if="skillhubSelectedSkills.size > 0">{{ skillhubSelectedSkills.size }} selected</span>
          </div>
          <div class="skillhub-modal-results-list">
            <div
              v-for="skill in skillhubSearchResults"
              :key="skill.source_skill_id"
              class="skillhub-modal-result-item"
              :class="{ selected: isSkillSelected(skill.source_skill_id) }"
              @click="toggleSkillSelection(skill.source_skill_id)"
            >
              <div class="skillhub-modal-result-checkbox">
                <CheckCircle2 v-if="isSkillSelected(skill.source_skill_id)" :size="18" />
                <div v-else class="skillhub-modal-checkbox-empty"></div>
              </div>
              <div class="skillhub-modal-result-info">
                <div class="skillhub-modal-result-name">{{ skill.name }}</div>
                <div class="skillhub-modal-result-desc">{{ skill.description }}</div>
              </div>
            </div>
          </div>
        </div>

        <footer class="skillhub-modal-footer">
          <button type="button" class="ghost-button" @click="closeSkillhubModal">
            Cancel
          </button>
          <button
            type="button"
            class="primary-button"
            :disabled="skillhubSelectedSkills.size === 0 || skillhubBatchInstalling"
            @click="handleBatchInstallSkills"
          >
            <Download :size="16" />
            {{ skillhubBatchInstalling ? 'Installing...' : `Install Selected (${skillhubSelectedSkills.size})` }}
          </button>
        </footer>
      </section>
    </div>

    <section class="glass-panel section-card settings-card">
      <div class="section-header">
        <div>
          <h3>
            <Sparkles :size="18" class="text-slate-400" />
            {{ t("settings.iconLibrary") }}
          </h3>
          <p>{{ t("settings.iconLibraryDesc") }}</p>
        </div>
        <button type="button" class="text-button" @click="addingIcon = !addingIcon; iconMessage = ''">
          <Plus :size="14" />
          {{ t("settings.addIcon") }}
        </button>
      </div>

      <div v-if="addingIcon" class="settings-icon-add-form">
        <div v-if="iconMessage" class="settings-icon-message" :class="'settings-icon-message-' + iconMessageType">
          {{ iconMessage }}
        </div>
        <div class="settings-icon-add-row">
          <label class="settings-field">
            <span>{{ t("settings.iconName") }}</span>
            <input v-model="newIconName" type="text" placeholder="my-icon" />
          </label>
          <label class="settings-field">
            <span>{{ t("settings.iconLabel") }}</span>
            <input v-model="newIconLabel" type="text" placeholder="My Icon" />
          </label>
        </div>
        <label class="settings-field">
          <span>{{ t("settings.iconSvg") }}</span>
          <textarea v-model="newIconSvg" rows="3" placeholder="<svg>...</svg> (optional)"></textarea>
        </label>
        <div class="settings-icon-add-actions">
          <button
            type="button"
            class="primary-button"
            :disabled="savingIcon"
            @click="handleAddIcon"
          >
            <Save :size="16" />
            {{ t("settings.saveIcon") }}
          </button>
          <button type="button" class="ghost-button" @click="addingIcon = false">
            {{ t("settings.closeEditor") }}
          </button>
        </div>
      </div>

      <div class="settings-icon-grid">
        <div
          v-for="icon in icons"
          :key="icon.id"
          class="settings-icon-item"
          :class="{ 'settings-icon-custom': icon.category === 'custom' }"
        >
          <component v-if="resolveIconComponent(icon.name)" :is="resolveIconComponent(icon.name)" :size="22" />
          <span v-else class="settings-icon-svg-preview" v-html="icon.svg_content || ''"></span>
          <span class="settings-icon-label">{{ icon.label }}</span>
          <span class="settings-icon-category">{{ icon.category }}</span>
          <button
            v-if="icon.category === 'custom'"
            type="button"
            class="settings-icon-delete"
            @click="handleDeleteIcon(icon.id)"
          >
            <Trash2 :size="12" />
          </button>
        </div>
      </div>
    </section>
  </section>
</template>
