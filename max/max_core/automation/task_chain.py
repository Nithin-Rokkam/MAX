"""
TaskChain — Sequential multi-step command execution for MAX (FR-15).
Executes a list of parsed commands one after another.
"""

import time


class TaskChain:
    def __init__(self, steps: list, orchestrator, delay_between: float = 0.5):
        """
        :param steps: list of raw command strings
        :param orchestrator: Orchestrator instance to execute each step
        :param delay_between: seconds to wait between steps
        """
        self.steps = steps
        self.orchestrator = orchestrator
        self.delay_between = delay_between

    def run(self) -> list[str]:
        """
        Executes all steps sequentially.
        Returns list of result messages from each step.
        """
        results = []
        for i, raw_cmd in enumerate(self.steps, start=1):
            print(f"\nMAX [Chain {i}/{len(self.steps)}]> {raw_cmd}")
            try:
                self.orchestrator.handle_raw_command(raw_cmd)
            except Exception as e:
                results.append(f"Step {i} error: {e}")
                continue
            results.append(f"Step {i} done: {raw_cmd}")
            if i < len(self.steps):
                time.sleep(self.delay_between)
        return results
