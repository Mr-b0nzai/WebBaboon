import time
from functools import wraps
from typing import Dict, Any, Callable, List
import threading
from statistics import mean, median, stdev
from datetime import datetime

# Global performance metrics storage
metrics: Dict[str, List[float]] = {}
operation_counts: Dict[str, int] = {}
metrics_enabled = False
metrics_lock = threading.Lock()
nested_calls: Dict[int, Dict[str, float]] = {}  # Track nested calls by thread ID and function name

def _clear_metrics():
    """Internal function to clear metrics data."""
    global metrics, operation_counts, nested_calls
    with metrics_lock:
        metrics.clear()
        operation_counts.clear()
        nested_calls.clear()

def enable_metrics():
    """Enable performance metrics collection."""
    global metrics_enabled
    metrics_enabled = True

def disable_metrics():
    """Disable performance metrics collection."""
    global metrics_enabled
    metrics_enabled = False

def reset_metrics():
    """Reset all performance metrics."""
    _clear_metrics()
    enable_metrics()

def timing_decorator(func: Callable) -> Callable:
    """Decorator to measure function execution time with nested call tracking."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not metrics_enabled:
            return func(*args, **kwargs)

        thread_id = threading.get_ident()
        if thread_id not in nested_calls:
            nested_calls[thread_id] = {}

        # Get current time and subtract time spent in nested calls
        start_time = time.time()
        nested_time = nested_calls[thread_id].get(func.__name__, 0)
        nested_calls[thread_id][func.__name__] = 0  # Reset for this call
        
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            end_time = time.time()
            total_time = end_time - start_time
            # Get any nested call time that accumulated during this call
            nested_time += nested_calls[thread_id].get(func.__name__, 0)
            # Calculate actual time spent in this function
            duration = total_time - nested_time
            
            # Update parent's nested time if this is a nested call
            parent = next((fname for fname in nested_calls[thread_id] if fname != func.__name__), None)
            if parent:
                nested_calls[thread_id][parent] = nested_calls[thread_id].get(parent, 0) + total_time

            # Update metrics
            with metrics_lock:
                if func.__name__ not in metrics:
                    metrics[func.__name__] = []
                    operation_counts[func.__name__] = 0
                if duration > 0:  # Only record positive durations
                    metrics[func.__name__].append(duration)
                    operation_counts[func.__name__] += 1

            # Reset nested time for this function
            nested_calls[thread_id][func.__name__] = 0
            
    return wrapper

def calculate_stats(timings: List[float]) -> Dict[str, float]:
    """Calculate detailed statistics for a list of timings."""
    if not timings:
        return {
            'avg': 0.0,
            'median': 0.0,
            'min': 0.0,
            'max': 0.0,
            'std_dev': 0.0,
            'total': 0.0,
            'calls': 0
        }
    
    try:
        stats = {
            'avg': mean(timings),
            'median': median(timings),
            'min': min(timings),
            'max': max(timings),
            'total': sum(timings),
            'std_dev': stdev(timings) if len(timings) > 1 else 0.0
        }
    except Exception:
        stats = {
            'avg': 0.0,
            'median': 0.0,
            'min': 0.0,
            'max': 0.0,
            'total': 0.0,
            'std_dev': 0.0
        }
        
    return stats

def print_metrics():
    """Print detailed performance metrics for all measured functions."""
    print("\nPerformance Metrics:")
    header = f"{'Function Name':<30} {'Calls':<8} {'Avg (ms)':<10} {'Med (ms)':<10} {'Min (ms)':<10} {'Max (ms)':<10} {'Total (s)':<10}"
    print("-" * len(header))
    print(header)
    print("-" * len(header))
    
    total_time = 0.0
    exclusive_time = {}
    
    # Calculate exclusive time for each function
    for func_name, timings in metrics.items():
        stats = calculate_stats(timings)
        exclusive_time[func_name] = stats['total']
        
    # Sort by exclusive time
    for func_name, timings in sorted(metrics.items(), key=lambda x: exclusive_time[x[0]], reverse=True):
        stats = calculate_stats(timings)
        calls = operation_counts.get(func_name, len(timings))
        
        if stats['total'] > 0:  # Only show functions that took measurable time
            print(f"{func_name:<30} {calls:<8} "
                f"{stats['avg']*1000:>9.1f} {stats['median']*1000:>9.1f} "
                f"{stats['min']*1000:>9.1f} {stats['max']*1000:>9.1f} "
                f"{exclusive_time[func_name]:>9.2f}")
            total_time += exclusive_time[func_name]
    
    print("-" * len(header))
    print(f"Total execution time: {total_time:.3f} seconds")

def get_metrics_summary() -> Dict[str, Any]:
    """Get a dictionary containing all metrics and their statistics."""
    summary = {}
    for func_name, timings in metrics.items():
        summary[func_name] = {
            'stats': calculate_stats(timings),
            'calls': operation_counts.get(func_name, len(timings))
        }
    return summary
