"""Custom state hooks."""

from .globals import (
    Global as Global,
    create_global as create_global,
    use_global as use_global,
)
from .misc import (
    use_previous as use_previous,
    use_state_from as use_state_from,
)
from .task import (
    GlobalTask as GlobalTask,
    Task as Task,
    TaskStatus as TaskStatus,
    task as task,
    use_task as use_task,
)
