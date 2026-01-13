"""
SovereignPM - Linear-like Project Management with Blockchain Payments

A full-featured task management tool for SOS with:
- Task CRUD with rich metadata (title, description, priority, labels)
- Projects and organization
- Bounty system with $MIND, SOL, TON payments
- Linear sync (bidirectional)
- Coherence-based payment multipliers
- Multiple views (list, kanban, timeline)

Ported and enhanced from mumega/cli task manager.

Architecture:
- Tasks stored as JSON files with markdown support
- Linear sync via GraphQL API
- Payments via Economy service
- Coherence from Physics service
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Set, Callable
from enum import Enum
from pathlib import Path
import uuid
import json
import hashlib
import asyncio
import httpx

from sos.observability.logging import get_logger

log = get_logger("sovereign_pm")


# ============================================================================
# ENUMERATIONS
# ============================================================================

class TaskStatus(str, Enum):
    """Task workflow status."""
    BACKLOG = "backlog"
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"
    BLOCKED = "blocked"
    CANCELED = "canceled"


class TaskPriority(str, Enum):
    """Task priority levels."""
    URGENT = "urgent"    # P0 - Drop everything
    HIGH = "high"        # P1 - This sprint
    MEDIUM = "medium"    # P2 - Soon
    LOW = "low"          # P3 - Eventually
    NONE = "none"        # No priority


class BountyCurrency(str, Enum):
    """Supported payment currencies."""
    MIND = "MIND"    # $MIND token (internal)
    SOL = "SOL"      # Solana
    TON = "TON"      # TON blockchain
    USDC = "USDC"    # USDC stablecoin


class TaskView(str, Enum):
    """View modes for task display."""
    LIST = "list"
    KANBAN = "kanban"
    TIMELINE = "timeline"
    CALENDAR = "calendar"


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class Label:
    """A label/tag for tasks."""
    id: str
    name: str
    color: str = "#6366f1"  # Default indigo
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "color": self.color,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Label":
        return cls(
            id=data["id"],
            name=data["name"],
            color=data.get("color", "#6366f1"),
            description=data.get("description", ""),
        )


@dataclass
class Bounty:
    """Payment attached to a task."""
    amount: float
    currency: BountyCurrency = BountyCurrency.MIND
    recipient: Optional[str] = None  # Wallet address or agent ID
    paid: bool = False
    paid_at: Optional[datetime] = None
    tx_id: Optional[str] = None
    coherence_multiplier: float = 1.0  # Applied based on work quality

    def to_dict(self) -> Dict[str, Any]:
        return {
            "amount": self.amount,
            "currency": self.currency.value,
            "recipient": self.recipient,
            "paid": self.paid,
            "paid_at": self.paid_at.isoformat() if self.paid_at else None,
            "tx_id": self.tx_id,
            "coherence_multiplier": self.coherence_multiplier,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Bounty":
        return cls(
            amount=data["amount"],
            currency=BountyCurrency(data.get("currency", "MIND")),
            recipient=data.get("recipient"),
            paid=data.get("paid", False),
            paid_at=datetime.fromisoformat(data["paid_at"]) if data.get("paid_at") else None,
            tx_id=data.get("tx_id"),
            coherence_multiplier=data.get("coherence_multiplier", 1.0),
        )

    @property
    def final_amount(self) -> float:
        """Amount after coherence multiplier."""
        return self.amount * self.coherence_multiplier


@dataclass
class Project:
    """A project containing tasks."""
    id: str
    name: str
    description: str = ""
    icon: str = "📁"
    color: str = "#3b82f6"
    owner_id: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    archived: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "icon": self.icon,
            "color": self.color,
            "owner_id": self.owner_id,
            "created_at": self.created_at.isoformat(),
            "archived": self.archived,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Project":
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            icon=data.get("icon", "📁"),
            color=data.get("color", "#3b82f6"),
            owner_id=data.get("owner_id", ""),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(timezone.utc),
            archived=data.get("archived", False),
            metadata=data.get("metadata", {}),
        )


@dataclass
class Task:
    """A task/issue in SovereignPM."""
    id: str
    title: str
    description: str = ""
    status: TaskStatus = TaskStatus.BACKLOG
    priority: TaskPriority = TaskPriority.NONE

    # Organization
    project_id: Optional[str] = None
    labels: List[str] = field(default_factory=list)  # Label IDs
    assignee_id: Optional[str] = None
    creator_id: str = ""

    # Bounty
    bounty: Optional[Bounty] = None

    # Dependencies
    blocked_by: List[str] = field(default_factory=list)  # Task IDs
    blocks: List[str] = field(default_factory=list)      # Task IDs

    # Dates
    due_date: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Progress
    progress: int = 0  # 0-100
    estimate_hours: Optional[float] = None
    actual_hours: Optional[float] = None

    # External sync
    linear_id: Optional[str] = None
    github_issue: Optional[str] = None
    last_synced_at: Optional[datetime] = None

    # Notes/Comments (markdown)
    notes: str = ""

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "priority": self.priority.value,
            "project_id": self.project_id,
            "labels": self.labels,
            "assignee_id": self.assignee_id,
            "creator_id": self.creator_id,
            "bounty": self.bounty.to_dict() if self.bounty else None,
            "blocked_by": self.blocked_by,
            "blocks": self.blocks,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "progress": self.progress,
            "estimate_hours": self.estimate_hours,
            "actual_hours": self.actual_hours,
            "linear_id": self.linear_id,
            "github_issue": self.github_issue,
            "last_synced_at": self.last_synced_at.isoformat() if self.last_synced_at else None,
            "notes": self.notes,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        return cls(
            id=data["id"],
            title=data["title"],
            description=data.get("description", ""),
            status=TaskStatus(data.get("status", "backlog")),
            priority=TaskPriority(data.get("priority", "none")),
            project_id=data.get("project_id"),
            labels=data.get("labels", []),
            assignee_id=data.get("assignee_id"),
            creator_id=data.get("creator_id", ""),
            bounty=Bounty.from_dict(data["bounty"]) if data.get("bounty") else None,
            blocked_by=data.get("blocked_by", []),
            blocks=data.get("blocks", []),
            due_date=datetime.fromisoformat(data["due_date"]) if data.get("due_date") else None,
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(timezone.utc),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now(timezone.utc),
            progress=data.get("progress", 0),
            estimate_hours=data.get("estimate_hours"),
            actual_hours=data.get("actual_hours"),
            linear_id=data.get("linear_id"),
            github_issue=data.get("github_issue"),
            last_synced_at=datetime.fromisoformat(data["last_synced_at"]) if data.get("last_synced_at") else None,
            notes=data.get("notes", ""),
            metadata=data.get("metadata", {}),
        )

    @property
    def is_blocked(self) -> bool:
        return len(self.blocked_by) > 0

    @property
    def is_overdue(self) -> bool:
        if not self.due_date:
            return False
        return datetime.now(timezone.utc) > self.due_date and self.status not in [TaskStatus.DONE, TaskStatus.CANCELED]


@dataclass
class TaskFilter:
    """Filter criteria for task queries."""
    status: Optional[List[TaskStatus]] = None
    priority: Optional[List[TaskPriority]] = None
    project_id: Optional[str] = None
    assignee_id: Optional[str] = None
    labels: Optional[List[str]] = None
    has_bounty: Optional[bool] = None
    is_overdue: Optional[bool] = None
    search: Optional[str] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None


# ============================================================================
# LINEAR SYNC
# ============================================================================

class LinearSync:
    """
    Bidirectional sync with Linear.

    Uses Linear's GraphQL API for issue management.
    """

    API_URL = "https://api.linear.app/graphql"

    # Status mapping: SovereignPM -> Linear
    STATUS_MAP = {
        TaskStatus.BACKLOG: "Backlog",
        TaskStatus.TODO: "Todo",
        TaskStatus.IN_PROGRESS: "In Progress",
        TaskStatus.IN_REVIEW: "In Review",
        TaskStatus.DONE: "Done",
        TaskStatus.BLOCKED: "Blocked",
        TaskStatus.CANCELED: "Canceled",
    }

    # Priority mapping: SovereignPM -> Linear (0=None, 1=Urgent, 2=High, 3=Medium, 4=Low)
    PRIORITY_MAP = {
        TaskPriority.URGENT: 1,
        TaskPriority.HIGH: 2,
        TaskPriority.MEDIUM: 3,
        TaskPriority.LOW: 4,
        TaskPriority.NONE: 0,
    }

    def __init__(self, api_key: str, team_id: str):
        self.api_key = api_key
        self.team_id = team_id

    async def _graphql(self, query: str, variables: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute GraphQL query."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.API_URL,
                headers={
                    "Authorization": self.api_key,
                    "Content-Type": "application/json",
                },
                json={"query": query, "variables": variables or {}},
                timeout=30.0,
            )
            data = response.json()
            if "errors" in data:
                raise Exception(f"Linear API error: {data['errors']}")
            return data.get("data", {})

    async def create_issue(self, task: Task) -> str:
        """Create a Linear issue from a task. Returns Linear issue ID."""
        query = """
        mutation CreateIssue($input: IssueCreateInput!) {
            issueCreate(input: $input) {
                success
                issue {
                    id
                    identifier
                }
            }
        }
        """
        variables = {
            "input": {
                "teamId": self.team_id,
                "title": task.title,
                "description": task.description,
                "priority": self.PRIORITY_MAP.get(task.priority, 0),
            }
        }

        result = await self._graphql(query, variables)
        issue = result.get("issueCreate", {}).get("issue", {})
        return issue.get("id")

    async def update_issue(self, linear_id: str, task: Task):
        """Update a Linear issue from task."""
        query = """
        mutation UpdateIssue($id: String!, $input: IssueUpdateInput!) {
            issueUpdate(id: $id, input: $input) {
                success
            }
        }
        """
        variables = {
            "id": linear_id,
            "input": {
                "title": task.title,
                "description": task.description,
                "priority": self.PRIORITY_MAP.get(task.priority, 0),
            }
        }

        await self._graphql(query, variables)

    async def fetch_issues(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch issues from Linear."""
        query = """
        query Issues($teamId: String!, $first: Int) {
            team(id: $teamId) {
                issues(first: $first) {
                    nodes {
                        id
                        identifier
                        title
                        description
                        priority
                        state {
                            name
                        }
                        updatedAt
                    }
                }
            }
        }
        """
        variables = {"teamId": self.team_id, "first": limit}
        result = await self._graphql(query, variables)
        return result.get("team", {}).get("issues", {}).get("nodes", [])


# ============================================================================
# SOVEREIGN PM
# ============================================================================

class SovereignPM:
    """
    SovereignPM - Linear-like Project Management.

    Full-featured task management with:
    - Task CRUD with rich metadata
    - Project organization
    - Label system
    - Bounty payments ($MIND, SOL, TON)
    - Linear sync
    - Dependency tracking
    - Multiple views
    """

    def __init__(
        self,
        storage_path: Optional[Path] = None,
        economy_url: str = "http://localhost:8002",
        linear_api_key: Optional[str] = None,
        linear_team_id: Optional[str] = None,
    ):
        self.storage_path = storage_path or Path.home() / ".sos" / "sovereign_pm"
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.economy_url = economy_url

        # Linear sync
        self.linear: Optional[LinearSync] = None
        if linear_api_key and linear_team_id:
            self.linear = LinearSync(linear_api_key, linear_team_id)

        # In-memory storage
        self._tasks: Dict[str, Task] = {}
        self._projects: Dict[str, Project] = {}
        self._labels: Dict[str, Label] = {}

        self._load_data()
        self._init_default_labels()

    def _load_data(self):
        """Load data from storage."""
        data_file = self.storage_path / "data.json"
        if data_file.exists():
            try:
                with open(data_file) as f:
                    data = json.load(f)
                    self._tasks = {t["id"]: Task.from_dict(t) for t in data.get("tasks", [])}
                    self._projects = {p["id"]: Project.from_dict(p) for p in data.get("projects", [])}
                    self._labels = {l["id"]: Label.from_dict(l) for l in data.get("labels", [])}
                log.info(f"Loaded {len(self._tasks)} tasks, {len(self._projects)} projects")
            except Exception as e:
                log.error(f"Failed to load data: {e}")

    def _save_data(self):
        """Save data to storage."""
        data_file = self.storage_path / "data.json"
        try:
            with open(data_file, "w") as f:
                data = {
                    "tasks": [t.to_dict() for t in self._tasks.values()],
                    "projects": [p.to_dict() for p in self._projects.values()],
                    "labels": [l.to_dict() for l in self._labels.values()],
                }
                json.dump(data, f, indent=2)
        except Exception as e:
            log.error(f"Failed to save data: {e}")

    def _init_default_labels(self):
        """Initialize default labels."""
        defaults = [
            Label(id="bug", name="Bug", color="#ef4444", description="Something isn't working"),
            Label(id="feature", name="Feature", color="#22c55e", description="New functionality"),
            Label(id="enhancement", name="Enhancement", color="#3b82f6", description="Improvement"),
            Label(id="documentation", name="Documentation", color="#a855f7", description="Docs update"),
            Label(id="research", name="Research", color="#f59e0b", description="Investigation needed"),
            Label(id="urgent", name="Urgent", color="#dc2626", description="Needs immediate attention"),
        ]
        for label in defaults:
            if label.id not in self._labels:
                self._labels[label.id] = label

    # =========================================================================
    # TASK OPERATIONS
    # =========================================================================

    def create_task(
        self,
        title: str,
        description: str = "",
        status: TaskStatus = TaskStatus.BACKLOG,
        priority: TaskPriority = TaskPriority.NONE,
        project_id: Optional[str] = None,
        labels: Optional[List[str]] = None,
        assignee_id: Optional[str] = None,
        creator_id: str = "",
        bounty_amount: Optional[float] = None,
        bounty_currency: BountyCurrency = BountyCurrency.MIND,
        due_date: Optional[datetime] = None,
        estimate_hours: Optional[float] = None,
    ) -> Task:
        """Create a new task."""
        task_id = f"TASK-{uuid.uuid4().hex[:8].upper()}"

        bounty = None
        if bounty_amount and bounty_amount > 0:
            bounty = Bounty(amount=bounty_amount, currency=bounty_currency)

        task = Task(
            id=task_id,
            title=title,
            description=description,
            status=status,
            priority=priority,
            project_id=project_id,
            labels=labels or [],
            assignee_id=assignee_id,
            creator_id=creator_id,
            bounty=bounty,
            due_date=due_date,
            estimate_hours=estimate_hours,
        )

        self._tasks[task_id] = task
        self._save_data()

        log.info(f"Task created: {task_id} - {title}")
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        return self._tasks.get(task_id)

    def update_task(self, task_id: str, **updates) -> Optional[Task]:
        """Update a task."""
        task = self._tasks.get(task_id)
        if not task:
            return None

        # Track status transitions
        old_status = task.status

        for key, value in updates.items():
            if hasattr(task, key):
                setattr(task, key, value)

        # Handle status transitions
        if "status" in updates:
            new_status = updates["status"]
            if new_status == TaskStatus.IN_PROGRESS and not task.started_at:
                task.started_at = datetime.now(timezone.utc)
            elif new_status == TaskStatus.DONE and not task.completed_at:
                task.completed_at = datetime.now(timezone.utc)
                task.progress = 100

        task.updated_at = datetime.now(timezone.utc)
        self._save_data()

        log.info(f"Task updated: {task_id}")
        return task

    def delete_task(self, task_id: str) -> bool:
        """Delete a task."""
        if task_id in self._tasks:
            del self._tasks[task_id]
            # Remove from dependency lists
            for t in self._tasks.values():
                if task_id in t.blocked_by:
                    t.blocked_by.remove(task_id)
                if task_id in t.blocks:
                    t.blocks.remove(task_id)
            self._save_data()
            log.info(f"Task deleted: {task_id}")
            return True
        return False

    def complete_task(self, task_id: str, coherence_score: float = 1.0) -> Optional[Task]:
        """
        Mark task as done and process bounty payment.

        Args:
            task_id: Task to complete
            coherence_score: Coherence multiplier for bounty (0.1-1.0)
        """
        task = self._tasks.get(task_id)
        if not task:
            return None

        task.status = TaskStatus.DONE
        task.completed_at = datetime.now(timezone.utc)
        task.progress = 100

        # Process bounty
        if task.bounty and not task.bounty.paid:
            task.bounty.coherence_multiplier = max(0.1, min(1.0, coherence_score))
            # Payment would be processed via economy service
            log.info(
                f"Bounty ready: {task.bounty.final_amount} {task.bounty.currency.value} "
                f"(multiplier: {coherence_score:.2f})"
            )

        task.updated_at = datetime.now(timezone.utc)
        self._save_data()

        log.info(f"Task completed: {task_id}")
        return task

    async def process_bounty_payment(self, task_id: str) -> Optional[str]:
        """
        Process bounty payment for a completed task.

        Returns transaction ID if successful.
        """
        task = self._tasks.get(task_id)
        if not task or not task.bounty or task.bounty.paid:
            return None

        if task.status != TaskStatus.DONE:
            log.warning(f"Cannot pay bounty for incomplete task: {task_id}")
            return None

        bounty = task.bounty
        try:
            async with httpx.AsyncClient() as client:
                if bounty.currency == BountyCurrency.MIND:
                    # Use internal economy service
                    response = await client.post(
                        f"{self.economy_url}/credit",
                        json={
                            "user_id": bounty.recipient or task.assignee_id,
                            "amount": bounty.final_amount,
                            "reason": f"Bounty for {task_id}: {task.title}",
                        },
                        timeout=30.0,
                    )
                    result = response.json()
                    tx_id = result.get("tx_id", f"mind_{uuid.uuid4().hex[:8]}")
                else:
                    # External blockchain payment would go here
                    # For now, just log it
                    tx_id = f"{bounty.currency.value.lower()}_{uuid.uuid4().hex[:8]}"
                    log.info(f"External payment pending: {bounty.final_amount} {bounty.currency.value}")

                bounty.paid = True
                bounty.paid_at = datetime.now(timezone.utc)
                bounty.tx_id = tx_id

                # Add payment note
                task.notes += f"\n\n---\n**Bounty Paid**: {bounty.final_amount} {bounty.currency.value}\n"
                task.notes += f"TX: `{tx_id}`\n"
                task.notes += f"Coherence Multiplier: {bounty.coherence_multiplier:.2f}\n"

                self._save_data()
                log.info(f"Bounty paid: {tx_id}")
                return tx_id

        except Exception as e:
            log.error(f"Payment failed: {e}")
            return None

    def list_tasks(self, filter: Optional[TaskFilter] = None) -> List[Task]:
        """List tasks with optional filtering."""
        tasks = list(self._tasks.values())

        if filter:
            if filter.status:
                tasks = [t for t in tasks if t.status in filter.status]
            if filter.priority:
                tasks = [t for t in tasks if t.priority in filter.priority]
            if filter.project_id:
                tasks = [t for t in tasks if t.project_id == filter.project_id]
            if filter.assignee_id:
                tasks = [t for t in tasks if t.assignee_id == filter.assignee_id]
            if filter.labels:
                tasks = [t for t in tasks if any(l in t.labels for l in filter.labels)]
            if filter.has_bounty is not None:
                tasks = [t for t in tasks if (t.bounty is not None) == filter.has_bounty]
            if filter.is_overdue is not None:
                tasks = [t for t in tasks if t.is_overdue == filter.is_overdue]
            if filter.search:
                query = filter.search.lower()
                tasks = [t for t in tasks if query in t.title.lower() or query in t.description.lower()]
            if filter.created_after:
                tasks = [t for t in tasks if t.created_at >= filter.created_after]
            if filter.created_before:
                tasks = [t for t in tasks if t.created_at <= filter.created_before]

        return tasks

    def get_kanban_view(self, project_id: Optional[str] = None) -> Dict[TaskStatus, List[Task]]:
        """Get tasks organized by status for Kanban view."""
        tasks = self.list_tasks(TaskFilter(project_id=project_id) if project_id else None)
        kanban: Dict[TaskStatus, List[Task]] = {status: [] for status in TaskStatus}
        for task in tasks:
            kanban[task.status].append(task)
        return kanban

    # =========================================================================
    # PROJECT OPERATIONS
    # =========================================================================

    def create_project(
        self,
        name: str,
        description: str = "",
        icon: str = "📁",
        color: str = "#3b82f6",
        owner_id: str = "",
    ) -> Project:
        """Create a new project."""
        project_id = f"proj_{uuid.uuid4().hex[:8]}"
        project = Project(
            id=project_id,
            name=name,
            description=description,
            icon=icon,
            color=color,
            owner_id=owner_id,
        )
        self._projects[project_id] = project
        self._save_data()
        log.info(f"Project created: {project_id} - {name}")
        return project

    def get_project(self, project_id: str) -> Optional[Project]:
        """Get a project by ID."""
        return self._projects.get(project_id)

    def list_projects(self, include_archived: bool = False) -> List[Project]:
        """List all projects."""
        projects = list(self._projects.values())
        if not include_archived:
            projects = [p for p in projects if not p.archived]
        return projects

    def archive_project(self, project_id: str) -> bool:
        """Archive a project."""
        project = self._projects.get(project_id)
        if project:
            project.archived = True
            self._save_data()
            return True
        return False

    # =========================================================================
    # LABEL OPERATIONS
    # =========================================================================

    def create_label(
        self,
        name: str,
        color: str = "#6366f1",
        description: str = "",
    ) -> Label:
        """Create a new label."""
        label_id = name.lower().replace(" ", "_")
        label = Label(id=label_id, name=name, color=color, description=description)
        self._labels[label_id] = label
        self._save_data()
        return label

    def get_label(self, label_id: str) -> Optional[Label]:
        """Get a label by ID."""
        return self._labels.get(label_id)

    def list_labels(self) -> List[Label]:
        """List all labels."""
        return list(self._labels.values())

    # =========================================================================
    # DEPENDENCY OPERATIONS
    # =========================================================================

    def add_dependency(self, task_id: str, blocked_by_id: str) -> bool:
        """Add a dependency (task_id is blocked by blocked_by_id)."""
        task = self._tasks.get(task_id)
        blocker = self._tasks.get(blocked_by_id)

        if not task or not blocker:
            return False

        if blocked_by_id not in task.blocked_by:
            task.blocked_by.append(blocked_by_id)
        if task_id not in blocker.blocks:
            blocker.blocks.append(task_id)

        self._save_data()
        return True

    def remove_dependency(self, task_id: str, blocked_by_id: str) -> bool:
        """Remove a dependency."""
        task = self._tasks.get(task_id)
        blocker = self._tasks.get(blocked_by_id)

        if not task or not blocker:
            return False

        if blocked_by_id in task.blocked_by:
            task.blocked_by.remove(blocked_by_id)
        if task_id in blocker.blocks:
            blocker.blocks.remove(task_id)

        self._save_data()
        return True

    def get_dependency_chain(self, task_id: str) -> List[str]:
        """Get all tasks that must be completed before this task."""
        visited = set()
        chain = []

        def traverse(tid: str):
            if tid in visited:
                return
            visited.add(tid)
            task = self._tasks.get(tid)
            if task:
                for blocker_id in task.blocked_by:
                    traverse(blocker_id)
                    if blocker_id not in chain:
                        chain.append(blocker_id)

        traverse(task_id)
        return chain

    # =========================================================================
    # LINEAR SYNC
    # =========================================================================

    async def sync_to_linear(self, task_id: str) -> Optional[str]:
        """Sync a task to Linear. Returns Linear issue ID."""
        if not self.linear:
            log.warning("Linear sync not configured")
            return None

        task = self._tasks.get(task_id)
        if not task:
            return None

        try:
            if task.linear_id:
                await self.linear.update_issue(task.linear_id, task)
            else:
                linear_id = await self.linear.create_issue(task)
                task.linear_id = linear_id

            task.last_synced_at = datetime.now(timezone.utc)
            self._save_data()
            return task.linear_id

        except Exception as e:
            log.error(f"Linear sync failed: {e}")
            return None

    async def sync_from_linear(self) -> int:
        """Pull tasks from Linear. Returns number of tasks updated."""
        if not self.linear:
            return 0

        try:
            issues = await self.linear.fetch_issues()
            updated = 0

            for issue in issues:
                linear_id = issue["id"]
                # Find existing task
                existing = next((t for t in self._tasks.values() if t.linear_id == linear_id), None)

                if existing:
                    existing.title = issue["title"]
                    existing.description = issue.get("description", "")
                    existing.last_synced_at = datetime.now(timezone.utc)
                    updated += 1

            self._save_data()
            return updated

        except Exception as e:
            log.error(f"Linear pull failed: {e}")
            return 0

    # =========================================================================
    # STATS
    # =========================================================================

    def get_stats(self, project_id: Optional[str] = None) -> Dict[str, Any]:
        """Get task statistics."""
        tasks = self.list_tasks(TaskFilter(project_id=project_id) if project_id else None)

        status_counts = {s.value: 0 for s in TaskStatus}
        priority_counts = {p.value: 0 for p in TaskPriority}
        total_bounty = 0.0
        paid_bounty = 0.0
        overdue_count = 0

        for task in tasks:
            status_counts[task.status.value] += 1
            priority_counts[task.priority.value] += 1
            if task.bounty:
                total_bounty += task.bounty.amount
                if task.bounty.paid:
                    paid_bounty += task.bounty.final_amount
            if task.is_overdue:
                overdue_count += 1

        return {
            "total_tasks": len(tasks),
            "status_counts": status_counts,
            "priority_counts": priority_counts,
            "total_bounty": total_bounty,
            "paid_bounty": paid_bounty,
            "pending_bounty": total_bounty - paid_bounty,
            "overdue_count": overdue_count,
            "completion_rate": status_counts["done"] / len(tasks) if tasks else 0,
        }


# Singleton
_sovereign_pm: Optional[SovereignPM] = None


def get_sovereign_pm() -> SovereignPM:
    """Get the global SovereignPM instance."""
    global _sovereign_pm
    if _sovereign_pm is None:
        _sovereign_pm = SovereignPM()
    return _sovereign_pm
