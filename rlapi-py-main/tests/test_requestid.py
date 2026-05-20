"""Tests for request ID counter."""
import pytest
import threading
from rlapi.requestid import RequestIDCounter


def test_request_id_counter():
    """Test that request ID counter increments correctly."""
    counter = RequestIDCounter()

    # First ID should be 0
    assert counter.get_id() == "PsyNetMessage_X_0"

    # Second ID should be 1
    assert counter.get_id() == "PsyNetMessage_X_1"

    # Third ID should be 2
    assert counter.get_id() == "PsyNetMessage_X_2"


def test_request_id_counter_thread_safety():
    """Test that request ID counter is thread-safe."""
    counter = RequestIDCounter()
    results = []
    lock = threading.Lock()

    def get_ids(count):
        local_results = []
        for _ in range(count):
            local_results.append(counter.get_id())
        with lock:
            results.extend(local_results)

    # Create multiple threads
    threads = []
    num_threads = 10
    ids_per_thread = 100

    for _ in range(num_threads):
        thread = threading.Thread(target=get_ids, args=(ids_per_thread,))
        threads.append(thread)
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    # Check that we got the expected number of IDs
    assert len(results) == num_threads * ids_per_thread

    # Check that all IDs are unique
    assert len(set(results)) == len(results)

    # Check that IDs are in the correct format
    for result in results:
        assert result.startswith("PsyNetMessage_X_")
        # Extract the number and verify it's an integer
        num = int(result.split("_")[-1])
        assert num >= 0


def test_request_id_format():
    """Test that request IDs have the correct format."""
    counter = RequestIDCounter()

    for i in range(10):
        request_id = counter.get_id()
        assert request_id == f"PsyNetMessage_X_{i}"
