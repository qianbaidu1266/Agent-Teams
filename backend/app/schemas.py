from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


WorkflowType = Literal[
    "router_specialists",
    "planner_executor",
    "supervisor_dynamic",
    "single_agent_chat",
    "peer_handoff",
]
BuiltinCapability = Literal[
    "filesystem",
    "fs_list",
    "fs_read",
    "fs_write",
]
TraceEventType = Literal[
    "run_started",
    "node_entered",
    "node_exited",
    "route_selected",
    "message_generated",
    "state_updated",
    "run_finished",
]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SkillDefinitionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=200)
    instruction: str = Field(min_length=1)


class SkillDefinition(SkillDefinitionCreate):
    id: str
    source_provider: str | None = None
    source_skill_id: str | None = None
    tool: dict[str, Any] | None = None
    local_path: str | None = None
    runtime_preflight: dict[str, Any] | None = None


class SkillSyncRequest(BaseModel):
    provider: Literal["skillhub"] = "skillhub"
    query: str | None = Field(default="search", max_length=80)
    limit: int = Field(default=40, ge=1, le=100)


class SkillSearchRequest(BaseModel):
    query: str = Field(default="search", max_length=80)
    limit: int = Field(default=20, ge=1, le=100)


class SkillSearchResult(BaseModel):
    source_skill_id: str
    name: str
    description: str
    instruction: str
    tool: dict[str, Any] | None = None


class SkillSearchResponse(BaseModel):
    query: str
    total: int
    skills: list[SkillSearchResult]


class SkillSyncResponse(BaseModel):
    provider: str
    query: str
    fetched: int
    imported: int
    updated: int


class SkillInstallResponse(BaseModel):
    skill_id: str
    skill_name: str
    source_provider: str | None = None
    source_skill_id: str | None = None
    downloaded_files: int = 0
    tool_enabled: bool = False
    message: str


class AgentModelConfig(BaseModel):
    model: str | None = None
    temperature: float | None = Field(default=None, ge=0, le=2)
    top_p: float | None = Field(default=None, ge=0, le=1)
    top_k: int | None = Field(default=None, ge=1)


class AgentDefinitionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=200)
    system_prompt: str = Field(min_length=1)
    model: str | None = None
    model_config_override: AgentModelConfig | None = None
    icon: str | None = None
    skill_ids: list[str] = Field(default_factory=list)
    builtin_capabilities: list[BuiltinCapability] = Field(default_factory=list)


class AgentDefinition(AgentDefinitionCreate):
    id: str


class AgentDefinitionUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=200)
    system_prompt: str = Field(min_length=1)
    model: str | None = None
    model_config_override: AgentModelConfig | None = None
    icon: str | None = None
    skill_ids: list[str] = Field(default_factory=list)
    builtin_capabilities: list[BuiltinCapability] = Field(default_factory=list)


class WorkflowDefinitionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    type: WorkflowType
    specialist_agent_ids: list[str] = Field(default_factory=list)
    router_prompt: str = Field(
        default="You are a workflow router. Pick the best specialist based on user intent."
    )
    finalizer_enabled: bool = True


class WorkflowDefinition(WorkflowDefinitionCreate):
    id: str


class WorkflowDefinitionUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    type: WorkflowType
    specialist_agent_ids: list[str] = Field(default_factory=list)
    router_prompt: str = Field(
        default="You are a workflow router. Pick the best specialist based on user intent."
    )
    finalizer_enabled: bool = True


class WorkflowTemplate(BaseModel):
    type: WorkflowType
    label: str
    description: str
    required_agent_count: int


class WorkflowNode(BaseModel):
    id: str
    label: str
    kind: Literal["start", "logic", "agent", "final", "end", "group"]
    parent_id: str | None = None
    icon: str | None = None


class WorkflowEdge(BaseModel):
    source: str
    target: str
    label: str | None = None


class WorkflowGraph(BaseModel):
    nodes: list[WorkflowNode]
    edges: list[WorkflowEdge]


class TraceEvent(BaseModel):
    type: TraceEventType
    title: str
    detail: str
    at: str = Field(default_factory=utc_now_iso)
    payload: dict[str, Any] = Field(default_factory=dict)


class RunArtifacts(BaseModel):
    route_agent_id: str | None = None
    route_agent_name: str | None = None
    route_reason: str | None = None
    specialist_answer: str | None = None
    final_answer: str | None = None


class WorkflowRunRequest(BaseModel):
    workflow_id: str
    user_input: str = Field(min_length=1)
    conversation_id: str | None = None


class WorkflowRunResponse(BaseModel):
    workflow_id: str
    user_input: str
    assistant_message: str
    trace: list[TraceEvent]
    graph: WorkflowGraph
    artifacts: RunArtifacts
    conversation_id: str | None = None


class ConversationCreate(BaseModel):
    workflow_id: str = Field(min_length=1)


class Conversation(ConversationCreate):
    id: str
    title: str | None = None
    workflow_type: str = ""
    user_input: str = ""
    created_at: str
    updated_at: str


class Message(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    agent_name: str | None = None
    created_at: str


class ConversationDetail(Conversation):
    messages: list[Message] = Field(default_factory=list)
    trace: list[dict[str, Any]] = Field(default_factory=list)
    graph: dict[str, Any] = Field(default_factory=dict)


class ConversationPage(BaseModel):
    items: list[Conversation]
    total: int
    page: int
    page_size: int


class ModelProfile(BaseModel):
    id: str
    provider: str = "custom"
    name: str = "Default"
    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o-mini"


class EnvVarEntry(BaseModel):
    key: str = Field(min_length=1)
    value: str = ""


class AppSettings(BaseModel):
    model_profiles: list[ModelProfile] = Field(default_factory=list)
    active_model_profile_id: str | None = None
    env_vars: list[EnvVarEntry] = Field(default_factory=list)
    env_path: str = ""
    agent_output_dir: str = ""
    skillhub_api_key: str = ""


class IconDefinitionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    label: str = Field(min_length=1, max_length=80)
    category: str = Field(default="preset", max_length=40)
    svg_content: str | None = None


class IconDefinition(IconDefinitionCreate):
    id: str
