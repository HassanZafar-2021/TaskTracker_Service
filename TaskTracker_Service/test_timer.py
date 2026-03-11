"""
Test Program for Task Timer / Time Tracker Microservice
Demonstrates all user stories with programmatic request/response via files.
"""

import os
import json
import time
from datetime import datetime

REQUESTS_DIR = "timer_requests"
RESPONSES_DIR = "timer_responses"


def create_request(request_id: str, action: str, task_id: str, task_name: str = ""):
    """Write a timer request file."""
    os.makedirs(REQUESTS_DIR, exist_ok=True)
    request = {
        "request_id": request_id,
        "action": action,
        "task_id": task_id,
        "task_name": task_name,
        "timestamp": datetime.now().isoformat()
    }
    request_file = os.path.join(REQUESTS_DIR, f"timer_request_{request_id}.json")
    with open(request_file, 'w') as f:
        json.dump(request, f, indent=2)
    print(f"[TEST] Request created: {request_id} | action={action} | task={task_id}")


def wait_for_response(request_id: str, timeout: int = 10):
    """Poll for response file."""
    response_file = os.path.join(RESPONSES_DIR, f"timer_response_{request_id}.json")
    start = time.time()
    while time.time() - start < timeout:
        if os.path.exists(response_file):
            with open(response_file, 'r') as f:
                return json.load(f)
        time.sleep(0.5)
    print(f"[TEST] ⚠ Timeout waiting for: {request_id}")
    return None


# ─────────────────────────────────────────────
# TEST 1: Start and Stop Timer (User Story #1)
# ─────────────────────────────────────────────
def test_start_stop():
    print("\n" + "=" * 60)
    print("TEST 1: START AND STOP TIMER (User Story #1)")
    print("=" * 60)

    print("\n--- Starting timer for task T001 ---")
    create_request("t001_start", "start", "T001", "Study for midterm")
    response = wait_for_response("t001_start")

    if response and response["status"] == "timer_started":
        print(f"  ✓ Timer started!")
        print(f"  Session ID: {response['session_id']}")
        print(f"  Start time: {response['start_time']}")
    else:
        print("  ✗ Failed to start timer")
        return

    print("\n--- Working on task for 3 seconds... ---")
    time.sleep(3)

    print("\n--- Stopping timer for task T001 ---")
    create_request("t001_stop", "stop", "T001", "Study for midterm")
    response = wait_for_response("t001_stop")

    if response and response["status"] == "timer_stopped":
        print(f"  ✓ Timer stopped!")
        print(f"  Elapsed: {response['duration_readable']}")
        print(f"  Elapsed seconds: {response['elapsed_seconds']}")
        print(f"  Elapsed minutes: {response['elapsed_minutes']}")
        print("\n[RESULT] ✓ TEST 1 PASSED")
    else:
        print("\n[RESULT] ✗ TEST 1 FAILED")


# ─────────────────────────────────────────────
# TEST 2: Duplicate Start (User Story #1 error case)
# ─────────────────────────────────────────────
def test_duplicate_start():
    print("\n" + "=" * 60)
    print("TEST 2: DUPLICATE START (Error Handling)")
    print("=" * 60)

    create_request("t002_start1", "start", "T002", "Review notes")
    response = wait_for_response("t002_start1")
    print(f"  First start: {response.get('status')}")

    time.sleep(1)

    create_request("t002_start2", "start", "T002", "Review notes")
    response = wait_for_response("t002_start2")

    if response and response["status"] == "error":
        print(f"  ✓ Error returned: {response['error_message']}")
        print("\n[RESULT] ✓ TEST 2 PASSED - Duplicate start handled correctly")
    else:
        print("\n[RESULT] ✗ TEST 2 FAILED")

    # Clean up - stop the timer
    create_request("t002_stop", "stop", "T002", "Review notes")
    wait_for_response("t002_stop")


# ─────────────────────────────────────────────
# TEST 3: Stop non-existent timer
# ─────────────────────────────────────────────
def test_stop_nonexistent():
    print("\n" + "=" * 60)
    print("TEST 3: STOP NON-EXISTENT TIMER (Error Handling)")
    print("=" * 60)

    create_request("t003_stop", "stop", "FAKE_TASK_999")
    response = wait_for_response("t003_stop")

    if response and response["status"] == "error":
        print(f"  ✓ Error returned: {response['error_message']}")
        print("\n[RESULT] ✓ TEST 3 PASSED")
    else:
        print("\n[RESULT] ✗ TEST 3 FAILED")


# ─────────────────────────────────────────────
# TEST 4: View Time Logs (User Story #2)
# ─────────────────────────────────────────────
def test_view_logs():
    print("\n" + "=" * 60)
    print("TEST 4: VIEW TIME LOGS (User Story #2)")
    print("=" * 60)

    # Create a quick timer log
    create_request("t004_start", "start", "T004", "Write report")
    wait_for_response("t004_start")
    time.sleep(2)
    create_request("t004_stop", "stop", "T004", "Write report")
    wait_for_response("t004_stop")
    time.sleep(1)

    # Request logs
    create_request("t004_logs", "logs", "")
    response = wait_for_response("t004_logs")

    if response and response["status"] == "success":
        logs = response.get("logs", [])
        summary = response.get("summary", {})
        print(f"\n  Total log entries: {len(logs)}")
        for task_id, data in summary.items():
            print(f"  Task {task_id} ({data['task_name']}): {data['total_readable']} across {data['sessions']} session(s)")
        print("\n[RESULT] ✓ TEST 4 PASSED")
    else:
        print("\n[RESULT] ✗ TEST 4 FAILED")


def main():
    print("\n" + "=" * 60)
    print("  TASK TIMER MICROSERVICE - TEST SUITE")
    print("=" * 60)
    print("\n⚠ Make sure timer_service.py is running in another terminal!")
    print("Starting tests in 3 seconds...\n")
    time.sleep(3)

    test_start_stop()
    time.sleep(2)

    test_duplicate_start()
    time.sleep(2)

    test_stop_nonexistent()
    time.sleep(2)

    test_view_logs()

    print("\n" + "=" * 60)
    print("  ALL TESTS COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    main()