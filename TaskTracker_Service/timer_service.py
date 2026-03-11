"""
Task Timer / Time Tracker Microservice
Tracks time spent on tasks via start/stop requests.
File-based communication via JSON files.
"""

import os
import json
import time
from datetime import datetime, timezone

REQUESTS_DIR = r"C:\Users\hassa\OneDrive\Desktop\Projects\PriorityPlanner\timer_requests"
RESPONSES_DIR = r"C:\Users\hassa\OneDrive\Desktop\Projects\PriorityPlanner\timer_responses"
LOGS_FILE = r"C:\Users\hassa\OneDrive\Desktop\Projects\PriorityPlanner\time_logs.json"

# In-memory active timers: { task_id: { session_id, start_time } }
active_timers = {}


def setup_directories():
    os.makedirs(REQUESTS_DIR, exist_ok=True)
    os.makedirs(RESPONSES_DIR, exist_ok=True)
    print("[INFO] Directories initialized")


def load_logs() -> list:
    """Load persisted time logs from file."""
    try:
        with open(LOGS_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_logs(logs: list):
    """Persist time logs to file."""
    with open(LOGS_FILE, 'w') as f:
        json.dump(logs, f, indent=2)


def format_duration(seconds: int) -> str:
    """Format seconds into human-readable string e.g. '2h 15m 30s'."""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    parts.append(f"{secs}s")
    return " ".join(parts)


def now_utc() -> str:
    """Return current UTC time as ISO string."""
    return datetime.now(timezone.utc).isoformat()


def handle_start(request_id: str, task_id: str, task_name: str):
    """Handle a start timer request."""
    if not task_id:
        return build_error(request_id, "Missing required field: task_id")

    if task_id in active_timers:
        return build_error(request_id, f"Timer already running for task_id: {task_id}. Stop it first.")

    session_id = f"session_{task_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    start_time = now_utc()

    active_timers[task_id] = {
        "session_id": session_id,
        "start_time": start_time,
        "task_name": task_name
    }

    print(f"[INFO] Timer started for task: {task_id} ({task_name})")
    return {
        "request_id": request_id,
        "status": "timer_started",
        "task_id": task_id,
        "task_name": task_name,
        "session_id": session_id,
        "start_time": start_time,
        "timestamp": now_utc()
    }


def handle_stop(request_id: str, task_id: str):
    """Handle a stop timer request."""
    if not task_id:
        return build_error(request_id, "Missing required field: task_id")

    if task_id not in active_timers:
        return build_error(request_id, f"No active timer found for task_id: {task_id}. Start a timer first.")

    session = active_timers.pop(task_id)
    stop_time = now_utc()

    start_dt = datetime.fromisoformat(session["start_time"])
    stop_dt = datetime.fromisoformat(stop_time)
    elapsed_seconds = int((stop_dt - start_dt).total_seconds())
    elapsed_minutes = round(elapsed_seconds / 60, 2)

    # Save to logs
    logs = load_logs()
    log_entry = {
        "session_id": session["session_id"],
        "task_id": task_id,
        "task_name": session["task_name"],
        "start_time": session["start_time"],
        "stop_time": stop_time,
        "elapsed_seconds": elapsed_seconds,
        "elapsed_minutes": elapsed_minutes,
        "duration_readable": format_duration(elapsed_seconds)
    }
    logs.append(log_entry)
    save_logs(logs)

    print(f"[INFO] Timer stopped for task: {task_id} | Duration: {format_duration(elapsed_seconds)}")
    return {
        "request_id": request_id,
        "status": "timer_stopped",
        "task_id": task_id,
        "task_name": session["task_name"],
        "session_id": session["session_id"],
        "start_time": session["start_time"],
        "stop_time": stop_time,
        "elapsed_seconds": elapsed_seconds,
        "elapsed_minutes": elapsed_minutes,
        "duration_readable": format_duration(elapsed_seconds),
        "timestamp": now_utc()
    }


def handle_logs(request_id: str, task_id: str = None):
    """Return time logs, optionally filtered by task_id."""
    logs = load_logs()

    if task_id:
        logs = [l for l in logs if l["task_id"] == task_id]

    if not logs:
        return {
            "request_id": request_id,
            "status": "success",
            "logs": [],
            "message": "No time logs found.",
            "timestamp": now_utc()
        }

    # Summary: total time per task
    summary = {}
    for log in logs:
        tid = log["task_id"]
        if tid not in summary:
            summary[tid] = {"task_name": log["task_name"], "total_seconds": 0, "sessions": 0}
        summary[tid]["total_seconds"] += log["elapsed_seconds"]
        summary[tid]["sessions"] += 1

    for tid in summary:
        summary[tid]["total_readable"] = format_duration(summary[tid]["total_seconds"])

    return {
        "request_id": request_id,
        "status": "success",
        "logs": logs,
        "summary": summary,
        "timestamp": now_utc()
    }


def build_error(request_id: str, message: str) -> dict:
    return {
        "request_id": request_id,
        "status": "error",
        "error_message": message,
        "timestamp": now_utc()
    }


def process_request(file_path: str):
    """Process a single timer request."""
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)

        request_id = data.get("request_id", "unknown")
        action = data.get("action", "").lower()
        task_id = data.get("task_id", "")
        task_name = data.get("task_name", task_id)

        print(f"\n[INFO] Processing request: {request_id} | Action: {action}")

        if action == "start":
            response = handle_start(request_id, task_id, task_name)
        elif action == "stop":
            response = handle_stop(request_id, task_id)
        elif action == "logs":
            response = handle_logs(request_id, task_id if task_id else None)
        else:
            response = build_error(request_id, f"Unknown action: '{action}'. Use 'start', 'stop', or 'logs'.")

        write_response(request_id, response)
        os.remove(file_path)

    except json.JSONDecodeError:
        print(f"[ERROR] Invalid JSON: {file_path}")
        os.remove(file_path)
    except Exception as e:
        print(f"[ERROR] Failed to process request: {e}")
        try:
            os.remove(file_path)
        except:
            pass


def write_response(request_id: str, response_data: dict):
    response_file = os.path.join(RESPONSES_DIR, f"timer_response_{request_id}.json")
    with open(response_file, 'w') as f:
        json.dump(response_data, f, indent=2)


def monitor_requests():
    print("=" * 60)
    print("TASK TIMER / TIME TRACKER MICROSERVICE STARTED")
    print("=" * 60)
    print(f"Monitoring: {REQUESTS_DIR}/")
    print(f"Responses:  {RESPONSES_DIR}/")
    print(f"Logs file:  {LOGS_FILE}")
    print("Press Ctrl+C to stop")
    print("=" * 60 + "\n")

    while True:
        try:
            request_files = [
                os.path.join(REQUESTS_DIR, f)
                for f in os.listdir(REQUESTS_DIR)
                if f.endswith('.json') and os.path.isfile(os.path.join(REQUESTS_DIR, f))
            ]
            for request_file in request_files:
                process_request(request_file)

            time.sleep(1)

        except KeyboardInterrupt:
            print("\n[INFO] Shutting down Task Timer Microservice")
            break
        except Exception as e:
            print(f"[ERROR] Monitoring error: {e}")
            time.sleep(3)


def main():
    setup_directories()
    monitor_requests()


if __name__ == "__main__":
    main()