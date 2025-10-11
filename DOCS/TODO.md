# TODO List

## High Priority


## Med Priority


## Low Priority

### Class Recommendations for Refactoring

Based on current functionality, consider creating the following classes:


2. ProgressManager Class
- Handle all progress file operations
- Methods: `save()`, `load()`, `clear()`, `find_all()`
- Benefits: Centralized progress management, easier to maintain

3. DiskPretest Class
- Manage HDD pretest operations
- Methods: `run_pretest()`, `analyze_results()`, `recommend_algorithm()`
- Benefits: Isolated pretest logic, reusable

4. WipeStrategy Class (Abstract)
- Base class for different wiping strategies
- Subclasses: `StandardStrategy`, `AdaptiveStrategy`, `SmallChunkStrategy`
- Benefits: Strategy pattern for algorithm selection, extensible

5. DeviceWiper Class
- Main orchestration class
- Use DeviceDetector, ProgressManager, DiskPretest, WipeStrategy
- Methods: `wipe()`, `resume()`, `validate_device()`
- Benefits: Clean separation of concerns, testable components

