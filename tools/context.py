from dataclasses import dataclass
from typing import Any, Optional

@dataclass
class ToolsContext:
    role_repository: Any
    self_worker_name: Optional[str]
    agent_work_dir: str
    is_integration_test: bool 