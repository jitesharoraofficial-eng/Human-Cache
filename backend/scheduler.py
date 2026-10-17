"""
Autonomous Background Memory Coach Scheduler.

Runs periodic retention checks, memory status recalculation,
grounded resource preparation, and proactive notification generation
for all active registered users without requiring manual dashboard visits.

Features:
- Single-instance lock to prevent duplicate runs across reloader/workers
- Periodic execution loop (every 60 seconds by default, configurable)
- Graceful shutdown support
- Direct execution for tests / standalone workers
"""

import asyncio
import logging
import threading
import time
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.models import User
from backend.memory_engine import refresh_user_memory_states
from backend.notification_engine import run_proactive_notification_cycle

from backend.logging_config import setup_secure_logging

logger = logging.getLogger("memory_coach_scheduler")
setup_secure_logging()

class MemoryCoachScheduler:
    def __init__(self, interval_seconds: int = 60):
        self.interval_seconds = interval_seconds
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

    def run_cycle_for_all_users(self, db_session: Optional[Session] = None) -> dict:
        """
        Executes a single proactive retention evaluation cycle across all active users.
        Can be called directly by background jobs or during tests.
        """
        close_db = False
        if db_session is not None:
            db = db_session
        else:
            db = SessionLocal()
            close_db = True

        stats = {"users_scanned": 0, "notifications_generated": 0, "errors": 0}
        try:
            users = db.query(User).filter(User.is_active == True).all()
            for user in users:
                try:
                    stats["users_scanned"] += 1
                    # 1. Recalculate retentions & mark due topics (respects no_need_suppressed)
                    refresh_user_memory_states(db, user.id)
                    # 2. Pre-generate/reuse grounded resources & emit proactive notifications
                    generated = run_proactive_notification_cycle(db, user.id)
                    stats["notifications_generated"] += len(generated)
                except Exception as user_err:
                    stats["errors"] += 1
                    logger.error(f"Error during memory cycle for user {user.id}: {user_err}")
            return stats
        finally:
            if close_db:
                db.close()

    def _worker_loop(self):
        logger.info(f"Memory Coach Scheduler loop started (interval: {self.interval_seconds}s)")
        # Brief warmup delay before first evaluation so backend startup finishes smoothly
        warmup_remaining = 10.0
        while warmup_remaining > 0 and not self._stop_event.is_set():
            time.sleep(1.0)
            warmup_remaining -= 1.0

        while not self._stop_event.is_set():
            try:
                cycle_stats = self.run_cycle_for_all_users()
                if cycle_stats["notifications_generated"] > 0:
                    logger.info(f"Memory Coach cycle completed: {cycle_stats}")
            except Exception as e:
                logger.error(f"Scheduler worker error: {e}")

            # Sleep in small increments to respond quickly to stop event
            sleep_chunk = 1.0
            elapsed = 0.0
            while elapsed < self.interval_seconds and not self._stop_event.is_set():
                time.sleep(sleep_chunk)
                elapsed += sleep_chunk

        logger.info("Memory Coach Scheduler loop stopped.")

    def _acquire_process_lease(self) -> bool:
        """
        Attempts to acquire a cross-process lease lock using a local lockfile.
        Prevents duplicate scheduler loops across Uvicorn reload child processes or multi-worker setups.
        """
        import os
        lock_path = "memory_coach_worker.lock"
        try:
            # Check if existing lockfile is active and not stale (> 5 minutes old)
            if os.path.exists(lock_path):
                try:
                    mtime = os.path.getmtime(lock_path)
                    if (time.time() - mtime) > 300: # Stale lock from crashed process
                        os.remove(lock_path)
                    else:
                        with open(lock_path, "r") as f:
                            pid_str = f.read().strip()
                            if pid_str and pid_str != str(os.getpid()):
                                logger.info(f"Memory Coach Scheduler already owned by process {pid_str}. Skipping secondary instance.")
                                return False
                except Exception:
                    pass

            with open(lock_path, "w") as f:
                f.write(str(os.getpid()))
            return True
        except Exception as e:
            logger.warning(f"Could not acquire scheduler process lock: {e}")
            return False

    def _release_process_lease(self):
        import os
        lock_path = "memory_coach_worker.lock"
        try:
            if os.path.exists(lock_path):
                with open(lock_path, "r") as f:
                    pid_str = f.read().strip()
                if pid_str == str(os.getpid()):
                    os.remove(lock_path)
        except Exception:
            pass

    def start(self):
        with self._lock:
            if self._running:
                return
            if not self._acquire_process_lease():
                return
            self._running = True
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._worker_loop, daemon=True, name="MemoryCoachWorker")
            self._thread.start()
            logger.info("Memory Coach Scheduler background worker launched with single-owner lease.")

    def stop(self):
        with self._lock:
            if not self._running:
                return
            self._stop_event.set()
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=3.0)
            self._release_process_lease()
            self._running = False
            logger.info("Memory Coach Scheduler background worker terminated.")

# Global singleton instance
memory_coach_scheduler = MemoryCoachScheduler(interval_seconds=60)
