# =====================================================================
# FILE: analytics/wip_metrics.py
# =====================================================================
"""
Work-in-Process (WIP) and system time tracking for simulation models.

Provides methods for:
- Tracking WIP (entities currently in system) over time
- Calculating average WIP using time-weighted averages
- Calculating total time in system statistics
- Analyzing WIP by location/activity
"""

from typing import Dict, Any, List, Tuple
import numpy as np
import matplotlib.pyplot as plt


# =====================================================================
# FILE: analytics/wip_metrics.py
# =====================================================================
class WIPTracker:
    """
    Tracks Work-in-Process (WIP) metrics during simulation.
    
    WIP is tracked by monitoring entity creation and disposal events,
    providing time-weighted statistics on system occupancy.
    """
    
    def __init__(self, model):
        """
        Initialize WIP tracker.
        
        Args:
            model: SimulationModel instance
        """
        self.model = model
        self.wip_data = []  # List of (time, wip_count) tuples
        self._last_update_time = 0
        self._current_wip = 0
    
    def get_wip_summary(self) -> Dict[str, Any]:
        """
        Calculate WIP statistics from simulation data.
        
        Returns:
            Dictionary with WIP metrics including time-weighted average
        """
        # Build WIP timeline from entity creation/disposal events
        wip_timeline = self._build_wip_timeline()
        
        if not wip_timeline:
            return self._empty_wip_summary()
        
        # Calculate time-weighted average WIP
        avg_wip = self._calculate_time_weighted_wip(wip_timeline)
        
        # Calculate max WIP
        max_wip = max(count for _, count in wip_timeline)
        
        # Get final WIP (entities still in system)
        final_wip = wip_timeline[-1][1] if wip_timeline else 0
        
        return {
            'average_wip': avg_wip,
            'max_wip': max_wip,
            'final_wip': final_wip,
            'wip_timeline': wip_timeline
        }
    
    def _build_wip_timeline(self) -> List[Tuple[float, int]]:
        """
        Build WIP timeline from entity creation and disposal events.
        
        Returns:
            List of (time, wip_count) tuples
        """
        events = []
        
        # Add creation events (+1 to WIP)
        for create_block in self.model.create_blocks:
            # Entities are created at specific times based on inter-arrival
            # We need to reconstruct this from disposed entities
            pass
        
        # Add disposal events (-1 from WIP)
        for dispose_block in self.model.dispose_blocks:
            for entity in dispose_block.disposed_entities:
                creation_time = entity.creation_time
                disposal_time = entity.get_attribute('disposal_time', self.model.env.now)
                
                events.append((creation_time, +1))  # Entity enters system
                events.append((disposal_time, -1))  # Entity exits system
        
        # Sort events by time
        events.sort(key=lambda x: x[0])
        
        # Build timeline
        timeline = []
        current_wip = 0
        
        for time, change in events:
            current_wip += change
            timeline.append((time, current_wip))
        
        return timeline
    
    def _calculate_time_weighted_wip(self, timeline: List[Tuple[float, int]]) -> float:
        """
        Calculate time-weighted average WIP.
        
        Args:
            timeline: List of (time, wip_count) tuples
            
        Returns:
            Time-weighted average WIP
        """
        if not timeline:
            return 0.0
        
        # Filter to post-warm-up period
        warm_up = self.model.warm_up_period
        post_warmup_timeline = [(t, w) for t, w in timeline if t >= warm_up]
        
        if not post_warmup_timeline:
            return 0.0
        
        # Calculate time-weighted average
        total_area = 0.0
        prev_time = warm_up
        
        # Get initial WIP at warm-up boundary
        pre_warmup = [w for t, w in timeline if t <= warm_up]
        prev_wip = pre_warmup[-1] if pre_warmup else 0
        
        for time, wip in post_warmup_timeline:
            # Add rectangle area: width × height
            total_area += prev_wip * (time - prev_time)
            prev_time = time
            prev_wip = wip
        
        # Add final interval to simulation end
        total_area += prev_wip * (self.model.env.now - prev_time)
        
        # Divide by total time
        effective_time = self.model.env.now - warm_up
        
        return total_area / effective_time if effective_time > 0 else 0.0
    
    def _empty_wip_summary(self) -> Dict[str, Any]:
        """Return empty WIP summary."""
        return {
            'average_wip': 0,
            'max_wip': 0,
            'final_wip': 0,
            'wip_timeline': []
        }
    
    def get_system_time_summary(self) -> Dict[str, Any]:
        """
        Calculate total time in system statistics.
        
        Returns:
            Dictionary with system time metrics
        """
        if not self.model.dispose_blocks:
            return self._empty_system_time_summary()
        
        # Get post-warm-up entities
        post_warmup_entities = [
            e for dispose_block in self.model.dispose_blocks
            for e in dispose_block.disposed_entities
            if e.get_attribute('disposal_time', 0) >= self.model.warm_up_period
        ]
        
        if not post_warmup_entities:
            return self._empty_system_time_summary()
        
        # Calculate system times
        system_times = [e.get_attribute('system_time', 0) for e in post_warmup_entities]
        
        return {
            'average_system_time': np.mean(system_times),
            'std_system_time': np.std(system_times),
            'min_system_time': np.min(system_times),
            'max_system_time': np.max(system_times),
            'median_system_time': np.median(system_times),
            'num_entities': len(system_times)
        }
    
    def _empty_system_time_summary(self) -> Dict[str, Any]:
        """Return empty system time summary."""
        return {
            'average_system_time': 0,
            'std_system_time': 0,
            'min_system_time': 0,
            'max_system_time': 0,
            'median_system_time': 0,
            'num_entities': 0
        }
    
    def plot_wip_over_time(self):
        """Plot WIP evolution over time."""
        wip_summary = self.get_wip_summary()
        timeline = wip_summary['wip_timeline']
        
        if not timeline:
            print("No WIP data available to plot.")
            return

        # --- START MODIFICATION ---
        final_time = self.model.env.now        
        # 1. Ensure the timeline extends to the end of the simulation for plotting
        if timeline[-1][0] < final_time:
            # Append a point at the final time with the final WIP count
            final_wip_count = timeline[-1][1]
            timeline.append((final_time, final_wip_count))
        # --- END MODIFICATION ---
        
        times = [t for t, _ in timeline]
        wips = [w for _, w in timeline]
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Plot as step function
        ax.step(times, wips, where='post', linewidth=2, color='steelblue', label='WIP')
        
        # Add average line
        ax.axhline(y=wip_summary['average_wip'], color='red', linestyle='--', 
                  linewidth=2, label=f"Average WIP: {wip_summary['average_wip']:.2f}")
        
        # Mark warm-up period
        if self.model.warm_up_period > 0:
            ax.axvline(x=self.model.warm_up_period, color='orange', linestyle='--',
                      linewidth=2, label=f"Warm-up end (t={self.model.warm_up_period})")
            ax.axvspan(0, self.model.warm_up_period, alpha=0.2, color='orange')
        
        ax.set_xlabel('Simulation Time', fontsize=12, fontweight='bold')
        ax.set_ylabel('Work in Process (WIP)', fontsize=12, fontweight='bold')
        ax.set_title('Work in Process Over Time', fontsize=14, fontweight='bold')
        ax.legend(loc='best', framealpha=0.9)
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.show()
    
    def plot_system_time_distribution(self):
        """Plot distribution of total time in system."""
        if not self.model.dispose_blocks:
            print("No system time data available to plot.")
            return
        
        # Get post-warm-up entities
        post_warmup_entities = [
            e for dispose_block in self.model.dispose_blocks
            for e in dispose_block.disposed_entities
            if e.get_attribute('disposal_time', 0) >= self.model.warm_up_period
        ]
        
        if not post_warmup_entities:
            print("No post-warm-up entities to plot.")
            return
        
        system_times = [e.get_attribute('system_time', 0) for e in post_warmup_entities]
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
        
        # Histogram
        ax1.hist(system_times, bins=30, color='skyblue', edgecolor='black', alpha=0.7)
        ax1.axvline(x=np.mean(system_times), color='red', linestyle='--', 
                   linewidth=2, label=f'Mean: {np.mean(system_times):.2f}')
        ax1.axvline(x=np.median(system_times), color='green', linestyle='--',
                   linewidth=2, label=f'Median: {np.median(system_times):.2f}')
        ax1.set_xlabel('Total Time in System', fontsize=11, fontweight='bold')
        ax1.set_ylabel('Frequency', fontsize=11, fontweight='bold')
        ax1.set_title('System Time Distribution', fontsize=12, fontweight='bold')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Box plot
        ax2.boxplot(system_times, vert=True, patch_artist=True,
                   boxprops=dict(facecolor='lightblue', alpha=0.7))
        ax2.set_ylabel('Total Time in System', fontsize=11, fontweight='bold')
        ax2.set_title('System Time Box Plot', fontsize=12, fontweight='bold')
        ax2.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        plt.show()



# # =====================================================================
# # USAGE EXAMPLE
# # =====================================================================

# def example_usage():
#     """Example showing how to use WIP tracking."""
#     from core.simulation_model import SimulationModel
#     from analytics.reporting import SimulationReporter
#     from analytics.wip_metrics import WIPTracker
    
#     # Build and run model
#     model = SimulationModel()
#     # ... configure model ...
#     model.run_simulation(until=1000, warm_up_period=100)
    
#     # Option 1: Use WIPTracker directly
#     wip_tracker = WIPTracker(model)
#     wip_summary = wip_tracker.get_wip_summary()
#     print(f"Average WIP: {wip_summary['average_wip']:.2f}")
    
#     system_time_summary = wip_tracker.get_system_time_summary()
#     print(f"Average System Time: {system_time_summary['average_system_time']:.2f}")
    
#     # Plot WIP
#     wip_tracker.plot_wip_over_time()
#     wip_tracker.plot_system_time_distribution()
    
#     # Option 2: Use integrated reporter
#     reporter = SimulationReporter(model)
#     reporter.print_results_with_wip()  # Includes WIP metrics


# if __name__ == "__main__":
#     print("WIP and System Time Tracking Module")
#     print("="*60)
#     print("\nThis module provides:")
#     print("  1. Time-weighted average WIP calculation")
#     print("  2. System time statistics (avg, std, min, max, median)")
#     print("  3. Little's Law verification")
#     print("  4. WIP over time visualization")
#     print("  5. System time distribution plots")