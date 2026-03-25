import threading
import sys
import io
import time
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime

class TaskManager:
    def __init__(self):
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def create_task(self, name: str, func, *args, **kwargs) -> str:
        task_id = str(uuid.uuid4())
        with self._lock:
            self.tasks[task_id] = {
                "id": task_id,
                "name": name,
                "status": "pending",
                "logs": [],
                "created_at": datetime.now().isoformat(),
                "finished_at": None,
                "result": None,
                "error": None
            }
        
        # Start in thread
        thread = threading.Thread(target=self._run_task, args=(task_id, func, *args), kwargs=kwargs)
        thread.daemon = True
        thread.start()
        
        return task_id

    def _run_task(self, task_id: str, func, *args, **kwargs):
        with self._lock:
            self.tasks[task_id]["status"] = "running"
        
        # Capture stdout
        output_buffer = io.StringIO()
        original_stdout = sys.stdout
        
        class LoggerStream:
            def __init__(self, buffer, task_ref):
                self.buffer = buffer
                self.task_ref = task_ref

            def write(self, s):
                self.buffer.write(s)
                original_stdout.write(s)
                # Parse logs into lines and append to task logs
                if s.strip():
                    with threading.Lock(): # Simple lock for logs
                         self.task_ref["logs"].append({
                             "time": datetime.now().isoformat(),
                             "msg": s.strip()
                         })

            def flush(self):
                self.buffer.flush()
                original_stdout.flush()

        # Note: Global sys.stdout redirect is risky for concurrent tasks 
        # but suitable for this specific use case (likely sequential interaction)
        sys.stdout = LoggerStream(output_buffer, self.tasks[task_id])
        
        try:
            result = func(*args, **kwargs)
            with self._lock:
                self.tasks[task_id]["status"] = "completed"
                self.tasks[task_id]["result"] = result
        except Exception as e:
            with self._lock:
                self.tasks[task_id]["status"] = "failed"
                self.tasks[task_id]["error"] = str(e)
            print(f"Error in task {task_id}: {e}")
        finally:
            sys.stdout = original_stdout
            with self._lock:
                self.tasks[task_id]["finished_at"] = datetime.now().isoformat()

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        return self.tasks.get(task_id)

    def get_logs(self, task_id: str, since_index: int = 0) -> List[Dict[str, Any]]:
        task = self.tasks.get(task_id)
        if not task:
            return []
        return task["logs"][since_index:]

    def list_tasks(self) -> List[Dict[str, Any]]:
        return list(self.tasks.values())

# Global instance
manager = TaskManager()
