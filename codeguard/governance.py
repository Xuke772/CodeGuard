import re
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from codeguard.tools import RiskLevel


class HITLStatus(str, Enum):
    IDLE = "IDLE"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    APPROVED = "APPROVED"
    DENIED = "DENIED"


@dataclass
class ApprovalRequest:
    action_name: str
    action_params: dict
    risk_detail: str
    status: HITLStatus = HITLStatus.AWAITING_APPROVAL
    timestamp: float = field(default_factory=time.time)


BLOCKED_COMMANDS = [
    (r"rm\s+-rf\s+/", "Recursive delete of root filesystem"),
    (r"rm\s+-rf\s+~", "Recursive delete of home directory"),
    (r"rm\s+-rf\s+\$HOME", "Recursive delete of home directory"),
    (r"format\s+[A-Z]:", "Disk format command"),
    (r"\bsudo\b", "Superuser command"),
    (r"git\s+push\s+.*--force.*\b(main|master)\b", "Force push to main/master branch"),
    (r"git\s+push\s+-f\s+.*\b(main|master)\b", "Force push to main/master branch"),
    (r"chmod\s+.*777\s+/", "World-writable permission on root"),
    (r"chmod\s+-R\s+777", "Recursive world-writable permission"),
    (r">\s*/dev/sda", "Write to block device"),
    (r"dd\s+if=.*of=/dev/", "Write to block device with dd"),
    (r"mkfs\.", "Filesystem creation command"),
    (r":\(\)\s*\{\s*:\|:&\s*\};:", "Fork bomb"),
]

HITL_COMMANDS = [
    (r"rm\s+-rf", "Recursive delete"),
    (r"git\s+push", "Git push"),
    (r"pip\s+install", "Python package installation"),
    (r"npm\s+install", "Node package installation"),
    (r"curl\b.*\b-o\b", "Download file with curl"),
    (r"wget\b", "Download file with wget"),
    (r"\bdocker\b", "Docker command"),
    (r"git\s+commit", "Git commit"),
]

SENSITIVE_FILES = [
    ".env", ".env.local", ".env.production",
    "credentials.json", "credentials.yaml", "credentials.yml",
    "secrets.yaml", "secrets.yml", "secret.key",
    "id_rsa", "id_ed25519", "*.pem", "*.key",
]


def classify_command(command: str) -> RiskLevel:
    if not command or not command.strip():
        return RiskLevel.SAFE
    for pattern, _ in BLOCKED_COMMANDS:
        if re.search(pattern, command, re.IGNORECASE):
            return RiskLevel.BLOCK
    for pattern, _ in HITL_COMMANDS:
        if re.search(pattern, command, re.IGNORECASE):
            return RiskLevel.HITL_REQUIRED
    return RiskLevel.SAFE


def classify_file_path(path: str, project_root: str) -> RiskLevel:
    try:
        proj = Path(project_root).resolve()
    except (OSError, TypeError):
        return RiskLevel.HITL_REQUIRED
    p = Path(path)
    if not p.is_absolute():
        p = proj / p
    resolved = p.resolve()
    filename = resolved.name.lower()
    for sensitive in SENSITIVE_FILES:
        if sensitive.startswith("*."):
            if filename.endswith(sensitive[1:]):
                return RiskLevel.BLOCK
        elif filename == sensitive:
            return RiskLevel.BLOCK
    parts = resolved.parts
    if len(parts) >= 2 and parts[1] in ("etc", "sys", "proc"):
        if parts[0] == "/" or parts[0].endswith(":\\"):
            return RiskLevel.BLOCK
    try:
        resolved.relative_to(proj)
        return RiskLevel.SAFE
    except ValueError:
        return RiskLevel.HITL_REQUIRED


class HITLStateMachine:
    def __init__(self, timeout: float = 60.0):
        self.status = HITLStatus.IDLE
        self.pending_request: ApprovalRequest | None = None
        self.timeout = timeout
        self._request_time: float = 0.0

    def request_approval(self, action_name: str, params: dict, risk_detail: str) -> ApprovalRequest:
        if self.status != HITLStatus.IDLE:
            raise ValueError(f"Cannot request approval in state {self.status}")
        self.status = HITLStatus.AWAITING_APPROVAL
        self._request_time = time.time()
        self.pending_request = ApprovalRequest(
            action_name=action_name,
            action_params=params,
            risk_detail=risk_detail,
        )
        return self.pending_request

    def approve(self) -> None:
        if self.status != HITLStatus.AWAITING_APPROVAL:
            raise ValueError(f"Cannot approve in state {self.status}")
        self.status = HITLStatus.APPROVED
        if self.pending_request:
            self.pending_request.status = HITLStatus.APPROVED

    def deny(self) -> None:
        if self.status != HITLStatus.AWAITING_APPROVAL:
            raise ValueError(f"Cannot deny in state {self.status}")
        self.status = HITLStatus.DENIED
        if self.pending_request:
            self.pending_request.status = HITLStatus.DENIED

    def check_timeout(self) -> bool:
        if self.status != HITLStatus.AWAITING_APPROVAL:
            return False
        if time.time() - self._request_time > self.timeout:
            self.status = HITLStatus.DENIED
            if self.pending_request:
                self.pending_request.status = HITLStatus.DENIED
            return True
        return False

    def reset(self) -> None:
        self.status = HITLStatus.IDLE
        self.pending_request = None
        self._request_time = 0.0


class GuardrailEngine:
    def __init__(self):
        self._custom_rules: list[tuple[str, RiskLevel, str]] = []
        self._tool_risk_levels: dict[str, RiskLevel] = {
            "read_file": RiskLevel.SAFE,
            "write_file": RiskLevel.HITL_REQUIRED,
            "execute_shell": RiskLevel.HITL_REQUIRED,
            "run_tests": RiskLevel.SAFE,
            "search_code": RiskLevel.SAFE,
        }

    def add_rule(self, pattern: str, risk_level: RiskLevel, description: str) -> None:
        self._custom_rules.append((pattern, risk_level, description))

    def evaluate(self, tool_name: str, params: dict, project_root: str) -> RiskLevel:
        if tool_name == "execute_shell":
            cmd = params.get("command", "")
            for pattern, risk_level, _ in self._custom_rules:
                if re.search(pattern, cmd, re.IGNORECASE):
                    return risk_level
            return classify_command(cmd)
        if tool_name == "write_file":
            path = params.get("path", "")
            return classify_file_path(path, project_root)
        return self._tool_risk_levels.get(tool_name, RiskLevel.HITL_REQUIRED)