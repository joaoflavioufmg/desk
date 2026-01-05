# ======================================================
# AUTO-GENERATED FILE — DESK PROJECT
# Dependency-aware | PEP8 formatted
# DO NOT EDIT MANUALLY
# ======================================================

from abc import ABC, abstractmethod
from analytics.financial import FinancialAnalyzer
from analytics.metrics import MetricsCollector
from analytics.wip_metrics import WIPTracker
from base_block import BaseBlock
from blocks.create_block import CreateBlock
from blocks.decide_block import DecideBlock
from blocks.dispose_block import DisposeBlock
from blocks.process_block import MultiProcessBlock
from blocks.process_block import ProcessBlock, MultiProcessBlock
from core.base_block import BaseBlock
from core.entity import Entity, EventLogger
from core.simulation_model import SimulationModel
from dataclasses import dataclass
from dataclasses import dataclass, field
from datetime import datetime
from entity import Entity, EventLogger
from enum import Enum
from event_tracer import EventTracer
from itertools import groupby
from metrics import MetricsCollector
from model_variables import ModelVariableTracker
from pathlib import Path
from tabnanny import verbose
from tkinter import messagebox
from tkinter import ttk
from typing import Any, Callable, Dict, List, Optional, Tuple
from typing import Any, Optional
from typing import Callable
from typing import Callable, Dict, List, Any, Optional
from typing import Dict
from typing import Dict, Any
from typing import Dict, Any, List
from typing import Dict, Any, List, Callable, Optional
from typing import Dict, Any, List, Optional, Union, Callable, Set
from typing import Dict, Any, List, Tuple
from typing import Dict, Any, List, Tuple, Callable
from typing import Dict, Callable, Optional
from typing import Dict, List
from typing import Dict, List, Any, Callable, Optional, Tuple
from typing import Dict, List, Tuple, Optional, Any
from typing import Dict, Set, List
from typing import List, Tuple
from typing import Optional
from typing import Optional, Callable
from typing import Optional, Callable, Dict, Any
from typing import Optional, List
from typing import Optional, List, Set
from validation.resource_validator import ResourceValidator
from validation.stability import StabilityAnalyzer
import ast
import autopep8
import itertools
import math
import matplotlib.pyplot as plt
import numpy as np
import os
import pandas as pd
import queue
import random
import re
import scipy.stats as stats
import seaborn as sns
import simpy
import statistics
import sys
import threading
import time
import tkinter as tk




# ======================================================
# FILE: analytics\financial.py
# ======================================================

# =====================================================================
# FILE: analytics/financial.py
# =====================================================================
"""
Financial analysis tools for simulation models.

Provides methods for:
- Calculating revenue, costs, and profit from entity attributes
- Generating financial balance sheets
- Visualizing financial breakdowns
"""


# =====================================================================
# FILE: analytics/financial.py
# =====================================================================
class FinancialAnalyzer:
    """Analyzes financial metrics from simulation results."""

    def __init__(self, model):
        """
        Initialize financial analyzer.

        Args:
            model: SimulationModel instance with completed simulation
        """
        self.model = model

    def get_financial_summary(self) -> Dict[str, Any]:
        """
        Calculate financial summary from disposed entities.

        Returns:
            Dictionary with total revenue, costs by activity, and net profit
        """
        if not self.model.dispose_blocks:
            return self._empty_summary()

        post_warmup_entities = self._get_post_warmup_entities()

        if not post_warmup_entities:
            return self._empty_summary()

        total_revenue = 0
        costs_by_activity = {}

        for entity in post_warmup_entities:
            # print(f"[DEBUG ACTIVITY_NAME] {entity.data.items()}")
            for key, value in entity.data.items():
                if 'revenue' in key.lower() and isinstance(value, (int, float)):
                    total_revenue += value

                if '_cost' in key.lower() and isinstance(value, (int, float)):
                    # activity_name = key.replace('_cost', '')
                    # extract activity name from "BlockName_cost"
                    activity_name = key.replace('_cost', '').split('_')[
                        0] if '_' in key else key
                    # print(f"[DEBUG ACTIVITY_NAME] {activity_name}")
                    if activity_name not in costs_by_activity:
                        costs_by_activity[activity_name] = 0
                    costs_by_activity[activity_name] += value

        total_costs = sum(costs_by_activity.values())
        net_profit = total_revenue - total_costs
        n_entities = len(post_warmup_entities)

        return {
            'total_revenue': total_revenue,
            'total_costs': total_costs,
            'net_profit': net_profit,
            'costs_by_activity': costs_by_activity,
            'num_entities': n_entities,
            'avg_revenue_per_entity': total_revenue / n_entities if n_entities else 0,
            'avg_cost_per_entity': total_costs / n_entities if n_entities else 0,
            'avg_profit_per_entity': net_profit / n_entities if n_entities else 0
        }

    def _empty_summary(self) -> Dict[str, Any]:
        """Return empty financial summary."""
        return {
            'total_revenue': 0,
            'total_costs': 0,
            'net_profit': 0,
            'costs_by_activity': {},
            'num_entities': 0,
            'avg_revenue_per_entity': 0,
            'avg_cost_per_entity': 0,
            'avg_profit_per_entity': 0
        }

    def _get_post_warmup_entities(self):
        """Get entities disposed after warm-up period."""
        return [
            e for dispose_block in self.model.dispose_blocks
            for e in dispose_block.disposed_entities
            if e.get_attribute('disposal_time', 0) >= self.model.warm_up_period
        ]

    def print_financial_summary(self):
        """Print formatted financial balance sheet."""
        financial_data = self.get_financial_summary()

        print("\n" + "=" * 60)
        print("FINANCIAL BALANCE SHEET")
        print("=" * 60)

        print(
            f"\nBased on {financial_data['num_entities']} entities (post warm-up)")

        self._print_revenue_section(financial_data)
        self._print_costs_section(financial_data)
        self._print_profit_section(financial_data)

        print("=" * 60)

    def _print_revenue_section(self, data: Dict):
        """Print revenue section."""
        print("\nREVENUE:")
        print(f"  Total Revenue: ${data['total_revenue']:,.2f}")
        print(f"  Average per Entity: ${data['avg_revenue_per_entity']:,.2f}")

    def _print_costs_section(self, data: Dict):
        """Print costs section."""
        print("\nCOSTS BY ACTIVITY:")
        if data['costs_by_activity']:
            for activity, cost in sorted(data['costs_by_activity'].items(),
                                         key=lambda x: x[1], reverse=True):
                percentage = (cost / data['total_costs']
                              * 100) if data['total_costs'] > 0 else 0
                print(f"  {activity}: ${cost:,.2f} ({percentage:.1f}%)")
        else:
            print("  No cost data available")

        print(f"\n  Total Costs: ${data['total_costs']:,.2f}")
        print(f"  Average per Entity: ${data['avg_cost_per_entity']:,.2f}")

    def _print_profit_section(self, data: Dict):
        """Print profit section with analysis."""
        print("\n" + "-" * 60)
        print(f"NET PROFIT: ${data['net_profit']:,.2f}")
        print(f"   Average per Entity: ${data['avg_profit_per_entity']:,.2f}")

        if data['total_revenue'] > 0:
            profit_margin = (data['net_profit'] / data['total_revenue']) * 100
            print(f"   Profit Margin: {profit_margin:.1f}%")

            if profit_margin > 20:
                print("   Excellent profit margin")
            elif profit_margin > 10:
                print("   Good profit margin")
            elif profit_margin > 0:
                print("   Low profit margin")
            else:
                print("   Operating at a loss!")

    def plot_financial_breakdown(self):
        """Create visualizations for financial data."""
        financial_data = self.get_financial_summary()

        if not financial_data['costs_by_activity']:
            print("No financial data available to plot.")
            return

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

        # Pie chart: Cost distribution
        activities = list(financial_data['costs_by_activity'].keys())
        costs = list(financial_data['costs_by_activity'].values())

        ax1.pie(costs, labels=activities, autopct='%1.1f%%', startangle=90)
        ax1.set_title('Cost Distribution by Activity',
                      fontsize=14, fontweight='bold')

        # Bar chart: Revenue vs Costs vs Profit
        categories = ['Revenue', 'Costs', 'Net Profit']
        values = [
            financial_data['total_revenue'],
            financial_data['total_costs'],
            financial_data['net_profit']
        ]
        colors = ['green', 'red',
                  'blue' if financial_data['net_profit'] >= 0 else 'darkred']

        bars = ax2.bar(categories, values, color=colors,
                       alpha=0.7, edgecolor='black')
        ax2.set_ylabel('Amount ($)', fontsize=12, fontweight='bold')
        ax2.set_title('Financial Overview', fontsize=14, fontweight='bold')
        ax2.grid(axis='y', alpha=0.3)

        # Add value labels on bars
        for bar, value in zip(bars, values):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height,
                     f'${value:,.0f}',
                     ha='center', va='bottom' if value >= 0 else 'top',
                     fontweight='bold', fontsize=10)

        plt.tight_layout()
        plt.show()



# ======================================================
# FILE: core\event_tracer.py
# ======================================================

# =====================================================================
# FILE: core/event_tracer.py
# =====================================================================

class EventTracer:
    """
    Traces and prints simulation events in a human-readable format.

    Provides verbose output for debugging and understanding simulation flow.
    """

    # Event icons
    ICONS = {
        'generate': '✨',
        'arrival': '🧍',
        'queue': '⏳',
        'service_start': '✅',
        'service_end': '🎯',
        'departure': '🚶',
        'decide': '🔀',
        'interrupt': '⚠️',
        'preempt': '🚨'
    }

    def __init__(self, env,
                 entity_filter: Optional[Set[str]] = None,
                 resource_filter: Optional[Set[str]] = None,
                 event_type_filter: Optional[Set[str]] = None,
                 time_range: Optional[tuple] = None):
        """
        Initialize event tracer with optional filters.

        Args:
            env: SimPy environment
            entity_filter: Set of entity IDs to trace (e.g., {'Patient_0', 'Patient_5'})
            resource_filter: Set of resource names to trace (e.g., {'doctors', 'nurses'})
            event_type_filter: Set of event types to trace (e.g., {'queue', 'service_start'})
            time_range: Tuple of (start_time, end_time) to limit trace output
        """
        self.env = env
        self.event_count = 0
        self.start_time = datetime.now()

        # Filters
        self.entity_filter = entity_filter
        self.resource_filter = resource_filter
        self.event_type_filter = event_type_filter
        self.time_range = time_range

        # Storage for post-simulation filtering
        self.all_events: List[dict] = []
        self.store_all = True  # Always store for later filtering

    def set_filters(self, entity_filter: Optional[Set[str]] = None,
                    resource_filter: Optional[Set[str]] = None,
                    event_type_filter: Optional[Set[str]] = None,
                    time_range: Optional[tuple] = None):
        """Update filters dynamically."""
        if entity_filter is not None:
            self.entity_filter = entity_filter
        if resource_filter is not None:
            self.resource_filter = resource_filter
        if event_type_filter is not None:
            self.event_type_filter = event_type_filter
        if time_range is not None:
            self.time_range = time_range

    def clear_filters(self):
        """Remove all filters."""
        self.entity_filter = None
        self.resource_filter = None
        self.event_type_filter = None
        self.time_range = None

    def _should_trace(self, event_type: str, entity_id: str, resource_name: Optional[str],
                      time: float) -> bool:
        """Check if event passes all active filters."""
        # Time range filter
        if self.time_range:
            start, end = self.time_range
            if time < start or time > end:
                return False

        # Entity filter
        if self.entity_filter and entity_id not in self.entity_filter:
            return False

        # Resource filter
        if self.resource_filter:
            if resource_name is None:
                return False

            # ✅ FIX: Handle multi-resource activities (comma-separated resources)
            # Split resource_name by comma and check if ANY match the filter
            resource_names_in_event = [r.strip()
                                       for r in resource_name.split(',')]

            # Check if any filtered resource is present in this event
            if not any(filter_resource in resource_names_in_event
                       for filter_resource in self.resource_filter):
                return False

        # Event type filter
        if self.event_type_filter and event_type.lower() not in self.event_type_filter:
            return False

        return True

    def print_header(self):
        """Print trace header."""
        print("\n" + "=" * 120)
        print("=== SIMULATION EVENT TRACE ===")

        # Show active filters
        filters_active = []
        if self.entity_filter:
            filters_active.append(
                f"Entities: {', '.join(sorted(self.entity_filter))}")
        if self.resource_filter:
            filters_active.append(
                f"Resources: {', '.join(sorted(self.resource_filter))}")
        if self.event_type_filter:
            filters_active.append(
                f"Events: {', '.join(sorted(self.event_type_filter))}")
        if self.time_range:
            filters_active.append(
                f"Time: [{self.time_range[0]:.2f}, {self.time_range[1]:.2f}]")

        if filters_active:
            print("FILTERS ACTIVE: " + " | ".join(filters_active))

        print("=" * 120)
        print(
            f"{'Time':<8} | {'Event':<22}  | {'Entity':<15} | {'Resource':<30} | {'Details':<50}")
        print("-" * 120)

    def print_footer(self):
        """Print trace footer."""
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        print("-" * 120)
        print(f"End of trace — {end_time.strftime('%H:%M:%S')} | "
              f"Events shown: {self.event_count} | Total stored: {len(self.all_events)} | "
              f"Duration: {duration:.2f}s")
        print("=" * 120)

    def trace(self, event_type: str, entity_id: str, resource_name: Optional[str] = None,
              details: str = "", time_override: Optional[float] = None):
        """
        Trace a single event.

        Args:
            event_type: Type of event (generate, arrival, queue, service_start, etc.)
            entity_id: ID of the entity
            resource_name: Name of resource involved (if any)
            details: Additional details to display
            time_override: Override current time (for retroactive logging)
        """
        time = time_override if time_override is not None else self.env.now

        # Store all events for later filtering
        event_data = {
            'time': time,
            'event_type': event_type,
            'entity_id': entity_id,
            'resource_name': resource_name,
            'details': details
        }
        self.all_events.append(event_data)

        # Check if should print now (based on filters)
        if not self._should_trace(event_type, entity_id, resource_name, time):
            return

        # Print event
        icon = self.ICONS.get(event_type.lower(), '•')
        event_name = f"{icon} {event_type.upper()}"
        # resource_str = resource_name if resource_name else ""
        # ✅ FIX: Format resource string with usage/capacity
        resource_str = self._format_resource_string(
            resource_name) if resource_name else ""

        print(
            f"{time:>7.2f}  | {event_name:<22} | {entity_id:<15} | {resource_str:<30} | {details}")
        self.event_count += 1

    def _format_resource_string(self, resource_name: str) -> str:
        """
        Format resource string with current usage and capacity.

        Args:
            resource_name: Name of resource(s), possibly comma-separated

        Returns:
            Formatted string like "[3/30] Troncos" or "[2/4] doctors, [1/3] nurses"
        """
        if not resource_name:
            return ""

        # Handle multi-resource activities (comma-separated)
        resource_names = [r.strip() for r in resource_name.split(',')]
        formatted_parts = []

        for res_name in resource_names:
            # Try to find the resource object in the model
            resource_obj = self._find_resource_by_name(res_name)

            if resource_obj:
                # Get current usage and capacity
                current_usage = resource_obj.count
                capacity = resource_obj.capacity
                formatted_parts.append(
                    f"[{current_usage}/{capacity}] {res_name}")
            else:
                # If resource not found, just use the name
                formatted_parts.append(res_name)

        return ", ".join(formatted_parts)

    def _find_resource_by_name(self, resource_name: str):
        """
        Find resource object by name from the model.

        Args:
            resource_name: Name of the resource

        Returns:
            Resource object or None if not found
        """
        # Access the model through env.model if it exists
        if not hasattr(self.env, 'model'):
            return None

        model = self.env.model

        if not hasattr(model, 'resources'):
            return None

        # Direct lookup
        if resource_name in model.resources:
            return model.resources[resource_name]

        # Fuzzy match (case-insensitive)
        for res_name, res_obj in model.resources.items():
            if res_name.lower() == resource_name.lower():
                return res_obj

        return None

    def replay_trace(self, entity_filter: Optional[Set[str]] = None,
                     resource_filter: Optional[Set[str]] = None,
                     event_type_filter: Optional[Set[str]] = None,
                     time_range: Optional[tuple] = None,
                     entity_pattern: Optional[str] = None):
        """
        Replay stored events with different filters.

        Args:
            entity_filter: Set of specific entity IDs to show
            resource_filter: Set of resource names to show
            event_type_filter: Set of event types to show
            time_range: Tuple of (start_time, end_time)
            entity_pattern: Regex pattern for entity ID matching (e.g., r'^Patient_[1-5]$')
        """
        # Temporarily save old filters
        old_entity_filter = self.entity_filter
        old_resource_filter = self.resource_filter
        old_event_type_filter = self.event_type_filter
        old_time_range = self.time_range

        # Apply new filters
        if entity_pattern:
            # Convert pattern to entity set
            pattern = re.compile(entity_pattern)
            matched_entities = {e['entity_id'] for e in self.all_events
                                if pattern.match(e['entity_id'])}
            self.entity_filter = matched_entities
        else:
            self.entity_filter = entity_filter

        self.resource_filter = resource_filter
        self.event_type_filter = event_type_filter
        self.time_range = time_range

        # Reset counter
        self.event_count = 0

        # Print header
        self.print_header()

        # Replay events
        for event in self.all_events:
            if self._should_trace(event['event_type'], event['entity_id'],
                                  event['resource_name'], event['time']):
                icon = self.ICONS.get(event['event_type'].lower(), '•')
                event_name = f"{icon} {event['event_type'].upper()}"
                resource_str = event['resource_name'] if event['resource_name'] else ""
                # ✅ FIX: Format resource string with usage/capacity
                # resource_str = self._format_resource_string(event['resource_name']) if event['resource_name'] else ""

                print(f"{event['time']:>7.2f}  | {event_name:<22} | "
                      f"{event['entity_id']:<15} | {resource_str:<30} | {event['details']}")
                self.event_count += 1

        # Print footer
        self.print_footer()

        # Restore old filters
        self.entity_filter = old_entity_filter
        self.resource_filter = old_resource_filter
        self.event_type_filter = old_event_type_filter
        self.time_range = old_time_range

    def get_entity_journey(self, entity_id: str) -> List[dict]:
        """
        Get complete journey of a specific entity.

        Args:
            entity_id: Entity ID to trace

        Returns:
            List of event dictionaries for this entity
        """
        return [e for e in self.all_events if e['entity_id'] == entity_id]

    def print_entity_journey(self, entity_id: str):
        """
        Print formatted journey of a specific entity.

        Args:
            entity_id: Entity ID to trace
        """
        journey = self.get_entity_journey(entity_id)

        if not journey:
            print(f"\nNo events found for entity: {entity_id}")
            return

        print("\n" + "=" * 80)
        print(f"=== ENTITY JOURNEY: {entity_id} ===")
        print("=" * 80)

        # Calculate statistics
        start_time = journey[0]['time']
        end_time = journey[-1]['time']
        total_time = end_time - start_time

        # Find queue and service times
        queue_times = []
        service_times = []
        resources_used = set()

        print(f"{'Time':<8} | {'Event':<22} | {'Resource':<30} | {'Details':<30}")
        print("-" * 80)

        for event in journey:
            icon = self.ICONS.get(event['event_type'].lower(), '•')
            event_name = f"{icon} {event['event_type'].upper()}"
            resource_str = event['resource_name'] if event['resource_name'] else ""
            # resource_str = self._format_resource_string(event['resource_name']) if event['resource_name'] else ""

            print(
                f"{event['time']:>7.2f}  | {event_name:<21} | {resource_str:<30} | {event['details']}")

            # Extract statistics
            if event['resource_name']:
                resources_used.add(event['resource_name'])

            if 'queue_time=' in event['details']:
                try:
                    qt = float(event['details'].split(
                        'queue_time=')[1].split(',')[0])
                    queue_times.append(qt)
                except:
                    pass

            if 'service_time=' in event['details']:
                try:
                    st = float(event['details'].split(
                        'service_time=')[1].split(',')[0])
                    service_times.append(st)
                except:
                    pass

        print("-" * 80)
        print(f"\nJOURNEY SUMMARY:")
        # ✅ NEW: Check if journey is incomplete
        has_departure = any(e['event_type'] == 'departure' for e in journey)
        if total_time == 0 or not has_departure:
            print(
                f"  ⚠️  WARNING: Incomplete journey (entity still in system at simulation end)")
        print(f"  Total time in system: {total_time:.2f} minutes")
        print(f"  Number of events: {len(journey)}")
        print(
            f"  Resources used: {', '.join(sorted(resources_used)) if resources_used else 'None'}")

        # ✅ FIX: Prevent division by zero
        if queue_times:
            queue_total = sum(queue_times)
            queue_pct = (queue_total / total_time *
                         100) if total_time > 0 else 0.0
            print(f"  Total queue time: {queue_total:.2f} ({queue_pct:.1f}%)")

        if service_times:
            service_total = sum(service_times)
            service_pct = (service_total / total_time *
                           100) if total_time > 0 else 0.0
            print(
                f"  Total service time: {service_total:.2f} ({service_pct:.1f}%)")
        print("=" * 80)

    def get_statistics(self) -> dict:
        """Get statistics about traced events."""
        entity_counts = {}
        resource_counts = {}
        event_type_counts = {}

        for event in self.all_events:
            # Count entities
            entity_id = event['entity_id']
            entity_counts[entity_id] = entity_counts.get(entity_id, 0) + 1

            # Count resources
            if event['resource_name']:
                resource_counts[event['resource_name']] = \
                    resource_counts.get(event['resource_name'], 0) + 1

            # Count event types
            event_type = event['event_type']
            event_type_counts[event_type] = event_type_counts.get(
                event_type, 0) + 1

        return {
            'total_events': len(self.all_events),
            'unique_entities': len(entity_counts),
            'entity_counts': entity_counts,
            'resource_counts': resource_counts,
            'event_type_counts': event_type_counts,
            'time_span': (self.all_events[0]['time'], self.all_events[-1]['time'])
            if self.all_events else (0, 0)
        }

    def print_statistics(self):
        """Print summary statistics of trace."""
        stats = self.get_statistics()

        print("\n" + "=" * 60)
        print("=== TRACE STATISTICS ===")
        print("=" * 60)
        print(f"Total events: {stats['total_events']}")
        print(f"Unique entities: {stats['unique_entities']}")
        print(
            f"Time span: {stats['time_span'][0]:.2f} - {stats['time_span'][1]:.2f}")

        print("\nEvents by type:")
        for event_type, count in sorted(stats['event_type_counts'].items(),
                                        key=lambda x: x[1], reverse=True):
            print(f"  {event_type:.<20} {count:>6}")

        print("\nEvents by resource:")
        for resource, count in sorted(stats['resource_counts'].items(),
                                      key=lambda x: x[1], reverse=True):
            print(f"  {resource:.<20} {count:>6}")

        print("\nTop 10 most active entities:")
        sorted_entities = sorted(stats['entity_counts'].items(),
                                 key=lambda x: x[1], reverse=True)[:10]
        for entity_id, count in sorted_entities:
            print(f"  {entity_id:.<20} {count:>6} events")

        print("=" * 60)



# ======================================================
# FILE: core\entity.py
# ======================================================

# =====================================================================
# FILE: core/entity.py
# =====================================================================


# =====================================================================
# FILE: core/entity.py
# =====================================================================
@dataclass
class Entity:
    """Represents an entity flowing through the simulation."""
    id: str
    creation_time: float
    data: Dict[str, Any] = field(default_factory=dict)
    route_history: List[str] = field(default_factory=list)
    priority: int = 0  # Lower numbers = higher priority (0 = highest)

    def add_attribute(self, key: str, value: Any):
        self.data[key] = value

    def get_attribute(self, key: str, default=None):
        return self.data.get(key, default)


class EventLogger:
    """Logs events in BupaR format during simulation."""

    def __init__(self):
        self.events = []

    def log_event(self, case_id: str, activity: str, timestamp: float,
                  lifecycle: str, resource: str = None, **attributes):
        """Log a single event."""
        event = {
            'case_id': case_id,
            'activity': activity,
            'timestamp': timestamp,
            'lifecycle': lifecycle,
            'resource': resource
        }
        event.update(attributes)
        self.events.append(event)

    def get_dataframe(self) -> pd.DataFrame:
        """Return events as a pandas DataFrame."""
        df = pd.DataFrame(self.events)
        df = df.sort_values(['case_id', 'timestamp']).reset_index(drop=True)
        return df

    def export_to_csv(self, filename: str = "event_log_bupar.csv"):
        """Export to CSV in BupaR format."""
        df = self.get_dataframe()
        df.to_csv(filename, index=False)
        print(f"Event log exported to {filename}")
        print(f"Total events: {len(df)}")
        print(f"Total cases: {df['case_id'].nunique()}")
        return df



# ======================================================
# FILE: core\base_block.py
# ======================================================

# =====================================================================
# FILE: core/BaseBlock.py
# =====================================================================

# =====================================================================
# FILE: core/BaseBlock.py
# =====================================================================
class BaseBlock(ABC):
    """Abstract base class for all blocks."""

    def __init__(self, name: str, env: simpy.Environment, event_logger: EventLogger = None):
        self.name = name
        self.env = env
        self.next_block: Optional['BaseBlock'] = None
        self.statistics = {}
        self.event_logger = event_logger
        self.attributes_to_assign = {}  # NEW: Generic attribute assignment
        self.attributes_to_modify = {}  # NEW: Dynamic attribute modifications
        self.activity_priority = None  # NEW: Activity-specific priority
        # NEW: Get tracer from model
        self.tracer = getattr(env.model, 'event_tracer', None)

    def _trace(self, event_type: str, entity: Entity, resource_name: Optional[str] = None,
               details: str = ""):
        """Helper method to trace events if verbose mode is enabled."""
        if self.tracer:
            self.tracer.trace(event_type, entity.id, resource_name, details)

    def assign_attributes(self, **attributes):
        """
        Configure attributes to assign to entities passing through this block.

        Args:
            **attributes: Key-value pairs where values can be:
                - Fixed values (int, float, str)
                - Callable functions that return values

        Example:
            block.assign_attributes(
                cost=100,
                revenue=lambda: random.uniform(200, 300),
                category="outpatient"
            )
        """
        self.attributes_to_assign = attributes

    def modify_attributes(self, **modifications):
        """
        Configure dynamic attribute modifications for entities.

        Args:
            **modifications: Key-value pairs where:
                - Key: attribute name to modify
                - Value: function that takes current value and returns new value

        Example:
            # Decrement sede by 1
            beber.modify_attributes(sede=lambda current: current - 1)

            # Increase cost by 10%
            activity.modify_attributes(cost=lambda current: current * 1.1)

            # Conditional modification
            activity.modify_attributes(
                priority=lambda current: max(0, current - 1)
            )
        """
        self.attributes_to_modify = modifications

    def set_activity_priority(self, priority: int):
        """
        Set the priority level for this activity.

        Args:
            priority: Integer priority (lower = higher priority, 0 = highest)

        Example:
            servir.set_activity_priority(0)  # Highest priority
            lavar.set_activity_priority(1)   # Lower priority
        """
        self.activity_priority = priority

    def _apply_attributes(self, entity: Entity):
        """Apply configured attributes to entity."""

        assigned_attrs = []  # ✅ NEW: Track assigned attributes

        for attr_name, attr_value in self.attributes_to_assign.items():
            if callable(attr_value):
                value = attr_value()
            else:
                value = attr_value

            entity.add_attribute(attr_name, value)
            # print(f"[DEBUG ATTRIBUTE 1]: {attr_name}: {value}")
            entity.add_attribute(f"{self.name}_{attr_name}", value)
            # print(f"[DEBUG ATTRIBUTE 2]: {self.name}_{attr_name}: {value}")

            # ✅ NEW: Record what was assigned
            assigned_attrs.append((attr_name, value))

            # ✅ Debug print
            # print(f"[DEBUG] {attr_name}: {value}")

        return assigned_attrs  # ✅ NEW: Return list of (name, value) tuples

    def _modify_attributes(self, entity: Entity):
        """
        Apply dynamic attribute modifications to entity.

        NEW: Modifies existing attributes based on configured functions.
        """
        modified_attrs = []  # ✅ NEW: Track modifications

        for attr_name, modification_func in self.attributes_to_modify.items():
            # Get current value (with default of 0)
            current_value = entity.get_attribute(attr_name, 0)

            # Apply modification function
            new_value = modification_func(current_value)

            # ✅ Debug print
            # print(f"[DEBUG] {attr_name}: old={current_value} -> new={new_value}")

            # Update attribute
            entity.add_attribute(attr_name, new_value)

            # ✅ NEW: Record what was modified (old -> new)
            modified_attrs.append((attr_name, current_value, new_value))

        # ✅ NEW: Return list of (name, old_value, new_value) tuples
        return modified_attrs

    def connect_to(self, next_block: 'BaseBlock'):
        """Connect this block to the next block in the flow."""
        self.next_block = next_block

    @abstractmethod
    def process_entity(self, entity: Entity):
        """Process an entity through this block. Must be implemented by subclasses."""
        pass

    def log_start(self, entity: Entity, resource_name: str = None):
        """Log activity start."""
        if self.event_logger:
            self.event_logger.log_event(
                case_id=entity.id,
                activity=self.name,
                timestamp=self.env.now,
                lifecycle='start',
                resource=resource_name,
                priority=entity.priority,
                activity_priority=self.activity_priority  # NEW: Log activity priority
            )

    def log_complete(self, entity: Entity, resource_name: str = None):
        """Log activity completion."""
        if self.event_logger:
            self.event_logger.log_event(
                case_id=entity.id,
                activity=self.name,
                timestamp=self.env.now,
                lifecycle='complete',
                resource=resource_name,
                priority=entity.priority,
                activity_priority=self.activity_priority  # NEW: Log activity priority
            )

    def send_to_next(self, entity: Entity):
        """Send entity to the next connected block."""
        if self.next_block:
            yield from self.next_block.process_entity(entity)
        else:
            # Entity exits the system
            yield self.env.timeout(0)

    def update_statistics(self, key: str, value: Any):
        """Update block statistics."""
        self.statistics[key] = value



# ======================================================
# FILE: core\model_variables.py
# ======================================================

# =====================================================================
# FILE: core/model_variables.py
# =====================================================================


@dataclass
class ModelVariable:
    """
    Represents a custom model state variable to monitor during simulation.

    Attributes:
        name: Variable name
        initial_value: Starting value
        description: Human-readable description
        unit: Unit of measurement (e.g., '%', 'units', 'R$')
        calculate_fn: Optional function to calculate value dynamically
    """
    name: str
    initial_value: Any = 0
    description: str = ""
    unit: str = ""
    calculate_fn: Optional[Callable] = None
    history: List[Tuple[float, Any]] = field(default_factory=list)

    def record(self, time: float, value: Any):
        """Record a value at a specific time."""
        self.history.append((time, value))

    def get_current_value(self) -> Any:
        """Get the most recent recorded value."""
        if self.history:
            return self.history[-1][1]
        return self.initial_value

    def get_average(self, start_time: float = 0) -> float:
        """Calculate time-weighted average after start_time."""
        if not self.history:
            return self.initial_value

        filtered = [(t, v) for t, v in self.history if t >= start_time]
        if not filtered:
            return self.initial_value

        # Time-weighted average
        total_area = 0
        prev_time = start_time
        prev_value = self.initial_value

        for time, value in filtered:
            total_area += prev_value * (time - prev_time)
            prev_time = time
            prev_value = value

        # Add final segment
        if filtered:
            final_time = filtered[-1][0]
            total_time = final_time - start_time
            return total_area / total_time if total_time > 0 else prev_value

        return self.initial_value

    def get_final_value(self) -> Any:
        """Get the final recorded value."""
        if self.history:
            return self.history[-1][1]
        return self.initial_value


class ModelVariableTracker:
    """
    Tracks and manages custom model state variables during simulation.

    Usage:
        tracker = ModelVariableTracker(model)

        # Define variables
        tracker.add_variable('percentual_falhas', 
                           initial_value=0, 
                           description='Percentual de falhas',
                           unit='%')

        # Update during simulation
        tracker.update('percentual_falhas', model.env.now, 15.5)

        # Analyze after simulation
        tracker.plot_variable('percentual_falhas')
        avg = tracker.get_average('percentual_falhas')
    """

    def __init__(self, model):
        """
        Initialize variable tracker.

        Args:
            model: SimulationModel instance
        """
        self.model = model
        self.variables: Dict[str, ModelVariable] = {}

    def add_variable(self, name: str, initial_value: Any = 0,
                     description: str = "", unit: str = "",
                     calculate_fn: Optional[Callable] = None):
        """
        Add a new variable to track.

        Args:
            name: Variable name
            initial_value: Starting value
            description: Human-readable description
            unit: Unit of measurement
            calculate_fn: Optional function to calculate value dynamically
                         Function signature: calculate_fn(model) -> value

        Example:
            tracker.add_variable(
                'percentual_falhas',
                initial_value=0,
                description='Percentual de entidades que falharam',
                unit='%',
                calculate_fn=lambda m: (m.num_falhas / m.num_total * 100) if m.num_total > 0 else 0
            )
        """
        var = ModelVariable(
            name=name,
            initial_value=initial_value,
            description=description,
            unit=unit,
            calculate_fn=calculate_fn
        )
        self.variables[name] = var

        # Record initial value
        var.record(self.model.env.now, initial_value)

        if verbose:
            print(f"Variable added: {name} = {initial_value} {unit}")

    def update(self, name: str, time: Optional[float] = None, value: Any = None):
        """
        Update a variable's value.

        Args:
            name: Variable name
            time: Timestamp (None = use current simulation time)
            value: New value (None = calculate using calculate_fn)

        Example:
            tracker.update('percentual_falhas', model.env.now, 12.5)
            tracker.update('percentual_falhas')  # Auto-calculate
        """
        if name not in self.variables:
            raise ValueError(
                f"Variable '{name}' not found. Add it first with add_variable()")

        var = self.variables[name]

        # Use current simulation time if not provided
        if time is None:
            time = self.model.env.now

        # Calculate value if function provided and value not given
        if value is None:
            if var.calculate_fn:
                value = var.calculate_fn(self.model)
            else:
                raise ValueError(
                    f"No value provided and no calculate_fn defined for '{name}'")

        var.record(time, value)

    def get_current(self, name: str) -> Any:
        """Get current value of a variable."""
        if name not in self.variables:
            raise ValueError(f"Variable '{name}' not found")
        return self.variables[name].get_current_value()

    def get_average(self, name: str, start_time: Optional[float] = None) -> float:
        """
        Get time-weighted average of a variable.

        Args:
            name: Variable name
            start_time: Start time for average (None = use warm_up_period)
        """
        if name not in self.variables:
            raise ValueError(f"Variable '{name}' not found")

        if start_time is None:
            start_time = self.model.warm_up_period

        return self.variables[name].get_average(start_time)

    def get_final(self, name: str) -> Any:
        """Get final value of a variable."""
        if name not in self.variables:
            raise ValueError(f"Variable '{name}' not found")
        return self.variables[name].get_final_value()

    def plot_variable(self, name: str, show_warm_up: bool = True):
        """
        Plot variable evolution over time.

        Args:
            name: Variable name
            show_warm_up: Mark warm-up period on plot
        """
        if name not in self.variables:
            raise ValueError(f"Variable '{name}' not found")

        var = self.variables[name]

        if not var.history:
            print(f"No data recorded for variable '{name}'")
            return

        times = [t for t, _ in var.history]
        values = [v for _, v in var.history]

        fig, ax = plt.subplots(figsize=(12, 6))

        # Plot as step function
        ax.step(times, values, where='post', linewidth=2,
                color='steelblue', label=f'{name}')

        # Add average line (post warm-up)
        avg = self.get_average(name)
        ax.axhline(y=avg, color='red', linestyle='--', linewidth=2,
                   label=f'Average (post warm-up): {avg:.2f} {var.unit}')

        # Mark warm-up period
        if show_warm_up and self.model.warm_up_period > 0:
            ax.axvline(x=self.model.warm_up_period, color='orange',
                       linestyle='--', linewidth=2,
                       label=f'Warm-up end (t={self.model.warm_up_period})')
            ax.axvspan(0, self.model.warm_up_period, alpha=0.2, color='orange')

        # Formatting
        ax.set_xlabel('Simulation Time', fontsize=12, fontweight='bold')
        ax.set_ylabel(f'{name} ({var.unit})', fontsize=12, fontweight='bold')

        title = f'{name}'
        if var.description:
            title += f'\n{var.description}'
        ax.set_title(title, fontsize=14, fontweight='bold')

        ax.legend(loc='best', framealpha=0.9)
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.show()

    def plot_all_variables(self, show_warm_up: bool = True):
        """Plot all tracked variables in subplots."""
        if not self.variables:
            print("No variables to plot")
            return

        n_vars = len(self.variables)
        fig, axes = plt.subplots(n_vars, 1, figsize=(12, 4 * n_vars))

        if n_vars == 1:
            axes = [axes]

        fig.suptitle('Model State Variables Over Time',
                     fontsize=14, fontweight='bold')

        for idx, (name, var) in enumerate(self.variables.items()):
            ax = axes[idx]

            if not var.history:
                ax.text(0.5, 0.5, f'No data for {name}',
                        ha='center', va='center', transform=ax.transAxes)
                continue

            times = [t for t, _ in var.history]
            values = [v for _, v in var.history]

            ax.step(times, values, where='post', linewidth=2,
                    color='steelblue', label=name)

            avg = self.get_average(name)
            ax.axhline(y=avg, color='red', linestyle='--', linewidth=1.5,
                       label=f'Avg: {avg:.2f} {var.unit}')

            if show_warm_up and self.model.warm_up_period > 0:
                ax.axvline(x=self.model.warm_up_period, color='orange',
                           linestyle='--', linewidth=1.5)
                ax.axvspan(0, self.model.warm_up_period,
                           alpha=0.2, color='orange')

            ax.set_ylabel(f'{name} ({var.unit})',
                          fontsize=10, fontweight='bold')
            ax.legend(loc='best', framealpha=0.9, fontsize=9)
            ax.grid(True, alpha=0.3)

        axes[-1].set_xlabel('Simulation Time', fontsize=12, fontweight='bold')
        plt.tight_layout()
        plt.show()

    def print_summary(self):
        """Print summary of all tracked variables."""
        print("\n" + "=" * 70)
        print("MODEL STATE VARIABLES SUMMARY")
        print("=" * 70)

        if not self.variables:
            print("No variables tracked")
            return

        for name, var in self.variables.items():
            print(f"\n{name}:")
            if var.description:
                print(f"  Description: {var.description}")
            print(f"  Initial value: {var.initial_value} {var.unit}")
            print(f"  Final value: {self.get_final(name)} {var.unit}")
            print(
                f"  Average (post warm-up): {self.get_average(name):.2f} {var.unit}")
            print(f"  Data points recorded: {len(var.history)}")

        print("=" * 70)

    def get_dataframe(self) -> pd.DataFrame:
        """
        Export all variable histories as a pandas DataFrame.

        Returns:
            DataFrame with columns: time, variable_name, value
        """
        data = []
        for name, var in self.variables.items():
            for time, value in var.history:
                data.append({
                    'time': time,
                    'variable': name,
                    'value': value
                })

        return pd.DataFrame(data)

    def export_to_csv(self, filename: str = "model_variables.csv"):
        """Export variable histories to CSV."""
        df = self.get_dataframe()
        df.to_csv(filename, index=False)
        print(f"Model variables exported to {filename}")


# =====================================================================
# INTEGRATION: Add to SimulationModel class
# =====================================================================
# Add this to SimulationModel.__init__():
#
#     self.variable_tracker = ModelVariableTracker(self)
#
# Add this method to SimulationModel:
#
    # def add_model_variable(self, name: str, initial_value: Any = 0,
    #                       description: str = "", unit: str = "",
    #                       calculate_fn: Optional[Callable] = None):
    #     """Add a custom model variable to track."""
    #     self.variable_tracker.add_variable(
    #         name, initial_value, description, unit, calculate_fn
    #     )

    # def update_model_variable(self, name: str, value: Any = None):
    #     """Update a model variable."""
    #     self.variable_tracker.update(name, value=value)


# =====================================================================
# USAGE EXAMPLES
# =====================================================================
def example_usage():
    """Example showing how to use ModelVariableTracker."""

    # Assuming you have a model
    model = SimulationModel()

    # Create tracker
    tracker = ModelVariableTracker(model)

    # Example 1: Simple counter variable
    tracker.add_variable(
        'num_falhas',
        initial_value=0,
        description='Número total de falhas',
        unit='unidades'
    )

    # Example 2: Percentage with auto-calculation
    tracker.add_variable(
        'percentual_falhas',
        initial_value=0,
        description='Percentual de entidades que falharam',
        unit='%',
        calculate_fn=lambda m: (
            tracker.get_current('num_falhas') / m.entity_count * 100
            if m.entity_count > 0 else 0
        )
    )

    # Example 3: Financial metric
    tracker.add_variable(
        'lucro_acumulado',
        initial_value=0,
        description='Lucro acumulado total',
        unit='R$'
    )

    # During simulation:
    # Update manually
    tracker.update('num_falhas', model.env.now, 5)
    tracker.update('lucro_acumulado', model.env.now, 1250.50)

    # Auto-calculate percentual
    tracker.update('percentual_falhas')

    # After simulation:
    tracker.print_summary()
    tracker.plot_variable('percentual_falhas')
    tracker.plot_all_variables()
    tracker.export_to_csv()


# =====================================================================
# EXAMPLE: Integration in ProcessBlock
# =====================================================================
"""
In your ProcessBlock, you can update model variables like this:

class ProcessBlock(BaseBlock):
    def process_entity(self, entity: Entity):
        # ... existing code ...
        
        # Check if entity failed some condition
        if some_failure_condition:
            # Increment failure counter
            if hasattr(self.env, 'model') and hasattr(self.env.model, 'variable_tracker'):
                tracker = self.env.model.variable_tracker
                
                current_failures = tracker.get_current('num_falhas')
                tracker.update('num_falhas', self.env.now, current_failures + 1)
                
                # Auto-update percentage
                tracker.update('percentual_falhas')
        
        # ... continue processing ...
"""



# ======================================================
# FILE: blocks\process_block.py
# ======================================================

# =====================================================================
# FILE: blocks/process_block.py
# =====================================================================

# =====================================================================
# FILE: blocks/process_block.py
# =====================================================================
class ProcessBlock(BaseBlock):
    """
    PROCESS block - performs delay operation with optional resource seizure.

    Can operate in two modes:
    1. With resource: seize resource, delay, release resource (traditional queue)
    2. Without resource: pure delay operation (no queueing)

    Args:
        name: Block name
        env: SimPy environment
        delay_time: Function returning delay duration
        resource: Optional resource to seize (None = pure delay)
        resource_units: Number of resource units to seize (default 1)
        event_logger: Optional event logger
    """

    def __init__(self, name: str, env: simpy.Environment,
                 delay_time: Callable[[], float],
                 resource: Optional[simpy.Resource] = None,
                 resource_units: int = 1,
                 event_logger: EventLogger = None):
        super().__init__(name, env, event_logger)
        self.resource = resource
        self.delay_time = delay_time
        self.resource_units = resource_units
        self.entities_processed = 0
        self.total_delay_time = 0.0
        self.total_queue_time = 0.0
        self.resource_data = []  # (time, in_service, queue_length)
        self.max_queue_length = 0
        self.max_in_service = 0
        self.resource_name = None  # Store resource name for logging

    def set_resource_name(self, name: str):
        """Set the resource name for event logging."""
        self.resource_name = name

    def process_entity(self, entity: Entity):
        """
        Process an entity through delay operation with optional resource usage.
            If resource is None: performs pure delay
            If resource exists: seizes resource, delays, releases resource

        Process an entity with activity-based priority and attribute modification.        
        NEW: Uses activity_priority if set, otherwise uses entity priority.
        """
        entity.route_history.append(self.name)

        if self.resource is None:
            # Pure delay mode (no resource)
            yield from self._process_without_resource(entity)
        else:
            # Resource-based mode (traditional queue)
            yield from self._process_with_resource(entity)

    def _process_without_resource(self, entity: Entity):
        """Process entity with pure delay (no resource seizure)."""
        # Log activity start
        self.log_start(entity, resource_name=None)

        # Calculate delay
        if hasattr(self.env, 'model') and hasattr(self.env.model, 'safe_delay_time'):
            delay = self.env.model.safe_delay_time(self.delay_time)
        else:
            delay = max(0.0, self.delay_time())

        # Perform delay
        yield self.env.timeout(delay)

        # Update statistics
        self.entities_processed += 1
        self.total_delay_time += delay
        entity.add_attribute(f"{self.name}_service_time", delay)
        entity.add_attribute(f"{self.name}_queue_time", 0.0)  # No queueing

        # Apply configured attributes
        self._apply_attributes(entity)

        # Log activity complete
        self.log_complete(entity, resource_name=None)

        # Continue to next block
        # yield from self.send_to_next(entity)
        self.env.process(self.send_to_next(entity))
        yield self.env.timeout(0)

    def _process_with_resource(self, entity: Entity):
        """Process entity with resource seizure (traditional queue behavior)."""
        self._monitor_resource()

        # 🔄 RETRY LOOP - handles preemption during acquisition OR service
        while True:
            queue_start = self.env.now

            # Determine priority for this activity
            request_priority = (self.activity_priority
                                if self.activity_priority is not None
                                else entity.priority)

            # Create list of requests according to resource_units
            requests = []
            for _ in range(self.resource_units):
                if isinstance(self.resource, simpy.PreemptiveResource):
                    # ⚠️ Use preempt=False during request
                    # Preemption will still occur during service timeout
                    req = self.resource.request(
                        priority=request_priority, preempt=False)
                elif isinstance(self.resource, simpy.PriorityResource):
                    req = self.resource.request(priority=request_priority)
                else:
                    req = self.resource.request()
                requests.append(req)

            acquired = []
            try:
                # NEW: Trace queue entry
                queue_length = len(self.resource.queue)
                self._trace('queue', entity, self.resource_name,
                            f"waiting, queue_length={queue_length}")

                # ⚠️ ACQUISITION - can be preempted here too!
                yield simpy.AllOf(self.env, requests)
                acquired = requests

                self._monitor_resource()
                # self.log_start(entity, self.resource_name)

                # Record queue time
                queue_time = self.env.now - queue_start
                self.total_queue_time += queue_time
                entity.add_attribute(f"{self.name}_queue_time", queue_time)

                # ⚠️ SERVICE - can be preempted here
                if hasattr(self.env, 'model') and hasattr(self.env.model, 'safe_delay_time'):
                    delay = self.env.model.safe_delay_time(self.delay_time)
                else:
                    delay = max(0.0, self.delay_time())

                # NEW: Trace service start
                utilization = self.resource.count / self.resource.capacity
                self._trace('service_start', entity, self.resource_name,
                            f"service_time={delay:.2f}, queue_time={queue_time:.2f}")

                self.log_start(entity, self.resource_name)

                yield self.env.timeout(delay)

                # ✅ SUCCESS - completed without interruption
                self.entities_processed += 1
                self.total_delay_time += delay
                entity.add_attribute(f"{self.name}_service_time", delay)

                # self._apply_attributes(entity)
                # ✅ MODIFIED: Capture assigned attributes
                assigned_attrs = self._apply_attributes(entity)
                # self._modify_attributes(entity)  # NEW: Apply dynamic modifications
                modified_attrs = self._modify_attributes(entity)

                # # NEW: Trace service end
                # utilization = self.resource.count / self.resource.capacity
                # self._trace('service_end', entity, self.resource_name,
                #            f"use={utilization:.0%}")

                # ✅ MODIFIED: Include attributes in trace
                utilization = self.resource.count / self.resource.capacity
                details = f"use={utilization:.0%}"

                # # Add attribute info if any were assigned
                # if assigned_attrs:
                #     attr_strs = [f"{name}={value}" for name, value in assigned_attrs]
                #     details += f", Attrib: {', '.join(attr_strs)}"

                # Collect all attribute changes
                attr_changes = []

                # Add assigned attributes
                if assigned_attrs:
                    for name, value in assigned_attrs:
                        if isinstance(value, float):
                            attr_changes.append(f"{name}={value:.2f}")
                        else:
                            attr_changes.append(f"{name}={value}")

                # Add modified attributes (show old->new)
                if modified_attrs:
                    for name, old_val, new_val in modified_attrs:
                        if isinstance(new_val, float):
                            attr_changes.append(
                                f"{name}: {old_val:.2f}→{new_val:.2f}")
                        else:
                            attr_changes.append(f"{name}: {old_val}→{new_val}")

                # Append to details if any changes occurred
                if attr_changes:
                    details += f", Attrib: {', '.join(attr_changes)}"

                self._trace('service_end', entity, self.resource_name, details)

                self.log_complete(entity, self.resource_name)

                break  # Exit retry loop - we're done!

            except simpy.Interrupt as interrupt:
                # NEW: Trace preemption
                self._trace('interrupt', entity, self.resource_name,
                            f"preempted by higher priority")

                # 🚨 PREEMPTED (during acquisition or service)
                if self.event_logger:
                    # Determine if interrupted during service or acquisition
                    lifecycle = 'interrupt' if acquired else 'interrupt_queue'

                    self.event_logger.log_event(
                        case_id=entity.id,
                        activity=self.name,
                        timestamp=self.env.now,
                        lifecycle=lifecycle,
                        resource=self.resource_name,
                        priority=entity.priority,
                        activity_priority=self.activity_priority
                    )
                # Resources will be released in finally block
                # Loop continues to retry from the beginning
                continue

            finally:
                # 🔓 Always release all acquired units
                for req in acquired:
                    try:
                        self.resource.release(req)
                    except:
                        pass
                self._monitor_resource()

        self._monitor_resource()

        # Continue to next block
        # yield from self.send_to_next(entity)
        self.env.process(self.send_to_next(entity))
        yield self.env.timeout(0)

    def _monitor_resource(self):
        """Monitor resource state for statistics (only if resource exists)."""
        if self.resource is None:
            return  # Skip monitoring if no resource

        current_queue_length = len(self.resource.queue)
        current_in_service = self.resource.count

        self.max_queue_length = max(
            self.max_queue_length, current_queue_length)
        self.max_in_service = max(self.max_in_service, current_in_service)

        # Always collect data for warm-up analysis
        data_point = (self.env.now, current_in_service, current_queue_length)
        self.resource_data.append(data_point)


class MultiProcessBlock(BaseBlock):
    """PROCESS block that can seize multiple resources simultaneously with activity priority."""

    def __init__(self, name: str, env: simpy.Environment,
                 resource_requirements: Dict[simpy.Resource, int],
                 delay_time: Callable[[], float],
                 event_logger: EventLogger = None):
        """
        Args:
            resource_requirements: Dict mapping resources to units needed
                                 e.g., {nurses: 1, doctors: 1, pharmacy_staff: 1}
            delay_time: Function returning service time
        """
        super().__init__(name, env, event_logger)
        self.resource_requirements = resource_requirements
        self.delay_time = delay_time
        self.entities_processed = 0
        self.resource_names = {}
        self.total_delay_time = 0.0
        self.total_queue_time = 0.0
        # Dict of resource -> [(time, in_service, queue_length)]
        self.resource_data = {}
        self.max_metrics = {}    # Dict of resource -> {max_queue, max_service}

        # Initialize monitoring for each resource
        for resource in resource_requirements.keys():
            self.resource_data[resource] = []
            self.max_metrics[resource] = {
                'max_queue_length': 0, 'max_in_service': 0}

    def set_resource_names(self, resource_names: Dict[simpy.Resource, str]):
        """Set resource names for logging."""
        self.resource_names = resource_names

    def process_entity(self, entity: Entity):
        """Process entity through multi-resource seize-delay-release."""
        entity.route_history.append(self.name)

        # Record queue entry time
        queue_start = self.env.now

        # Monitor all resources before seizing
        self._monitor_all_resources()

        while True:  # Loop for retry on preemption

            # Determine priority for this activity
            request_priority = (self.activity_priority
                                if self.activity_priority is not None
                                else entity.priority)

            # Create all resource requests with their resources
            requests = []
            for resource, units in self.resource_requirements.items():
                for _ in range(units):
                    if isinstance(resource, simpy.PreemptiveResource):
                        req = resource.request(
                            priority=request_priority, preempt=True)  # Enable preemption
                    elif isinstance(resource, simpy.PriorityResource):
                        req = resource.request(priority=request_priority)
                    else:
                        req = resource.request()
                    requests.append((resource, req))

            acquired_resources = []
            try:

                # ✅ FIX 1: Trace queue entry BEFORE acquiring resources
                # Build combined resource string
                resources_str = ", ".join([self.resource_names.get(r, "Unknown")
                                          for r, _ in requests])

                # Calculate total queue length across all required resources
                total_queue_length = sum(len(r.queue) for r, _ in requests)

                self._trace('queue', entity, resources_str,
                            f"waiting for all resources, total_queue={total_queue_length}")

                # Acquire all resources simultaneously
                yield simpy.AllOf(self.env, [req for _, req in requests])
                acquired_resources = requests

                # Log activity start with all resources
                resources_str = ", ".join([self.resource_names.get(r, "Unknown")
                                           for r, _ in acquired_resources])
                self.log_start(entity, resources_str)

                # Record queue time and monitor state after seizing all
                queue_time = self.env.now - queue_start
                self.total_queue_time += queue_time
                entity.add_attribute(f"{self.name}_queue_time", queue_time)
                self._monitor_all_resources()

                # Process (delay) - all resources are now held (use safe delay time)
                # #############################################################
                # Para Evitar erros de dados negativos no modelo
                # #############################################################
                if hasattr(self.env, 'model') and hasattr(self.env.model, 'safe_delay_time'):
                    # If the model has the safe_delay_time method, use it
                    delay = self.env.model.safe_delay_time(self.delay_time)
                else:
                    # Fallback: ensure non-negative manually
                    delay = max(0.0, self.delay_time())

                # ✅ FIX 2: Trace service start AFTER acquiring all resources
                # Calculate average utilization across all resources
                avg_utilization = sum(
                    r.count / r.capacity for r, _ in acquired_resources) / len(acquired_resources)

                self._trace('service_start', entity, resources_str,
                            f"service_time={delay:.2f}, queue_time={queue_time:.2f}")

                self.log_start(entity, resources_str)

                try:
                    yield self.env.timeout(delay)
                except simpy.Interrupt:
                    # ✅ FIX 3: Trace preemption/interrupt
                    self._trace('interrupt', entity, resources_str,
                                f"preempted by higher priority")

                    # Preempted: log, release, and retry
                    if self.event_logger:
                        self.event_logger.log_event(
                            case_id=entity.id,
                            activity=self.name,
                            timestamp=self.env.now,
                            lifecycle='interrupt',
                            resource=resources_str,
                            priority=entity.priority,
                            activity_priority=self.activity_priority
                        )
                    continue  # Retry seizure from the top

                # Update statistics
                self.entities_processed += 1
                self.total_delay_time += delay
                entity.add_attribute(f"{self.name}_service_time", delay)

                # self._apply_attributes(entity) # NEW: Apply configured attributes (e.g., cost, revenue)
                # ✅ MODIFIED: Capture assigned and modified attributes
                # Apply configured attributes (e.g., cost, revenue)
                assigned_attrs = self._apply_attributes(entity)
                # self._modify_attributes(entity)  # NEW: Apply dynamic modifications
                modified_attrs = self._modify_attributes(entity)

                # ✅ FIX 4: Trace service end AFTER service completion
                # Calculate average utilization across all resources
                avg_utilization = sum(
                    r.count / r.capacity for r, _ in acquired_resources) / len(acquired_resources)

                # ✅ MODIFIED: Include attributes in trace
                details = f"use={avg_utilization:.0%}"

                # self._trace('service_end', entity, resources_str,
                #            f"use={avg_utilization:.0%}")

                # # Add attribute info if any were assigned
                # if assigned_attrs:
                #     attr_strs = [f"{name}={value}" for name, value in assigned_attrs]
                #     details += f", Attrib: {', '.join(attr_strs)}"

                # Collect all attribute changes
                attr_changes = []

                # Add assigned attributes
                if assigned_attrs:
                    for name, value in assigned_attrs:
                        if isinstance(value, float):
                            attr_changes.append(f"{name}={value:.2f}")
                        else:
                            attr_changes.append(f"{name}={value}")

                # Add modified attributes (show old->new)
                if modified_attrs:
                    for name, old_val, new_val in modified_attrs:
                        if isinstance(new_val, float):
                            attr_changes.append(
                                f"{name}: {old_val:.2f}→{new_val:.2f}")
                        else:
                            attr_changes.append(f"{name}: {old_val}→{new_val}")

                # Append to details if any changes occurred
                if attr_changes:
                    details += f", Attrib: {', '.join(attr_changes)}"

                self._trace('service_end', entity, resources_str, details)

                # Log activity complete
                self.log_complete(entity, resources_str)

                break  # Success, exit retry loop

            finally:
                # Release all acquired resources
                for resource, req in acquired_resources:
                    resource.release(req)

                # Monitor resources after release
                self._monitor_all_resources()

        # Send to next block
        self.env.process(self.send_to_next(entity))
        yield self.env.timeout(0)

    def _monitor_all_resources(self):
        """Monitor state of all resources."""
        for resource in self.resource_requirements.keys():
            current_queue_length = len(resource.queue)
            current_in_service = resource.count

            # Update max metrics
            self.max_metrics[resource]['max_queue_length'] = max(
                self.max_metrics[resource]['max_queue_length'],
                current_queue_length
            )
            self.max_metrics[resource]['max_in_service'] = max(
                self.max_metrics[resource]['max_in_service'],
                current_in_service
            )

            # Store data point
            data_point = (self.env.now, current_in_service,
                          current_queue_length)
            self.resource_data[resource].append(data_point)



# ======================================================
# FILE: blocks\decide_block.py
# ======================================================

# =====================================================================
# FILE: blocks/decide_block.py (GENERIC CONDITIONS VERSION)
# =====================================================================

# =====================================================================
# FILE: blocks/decide_block.py
# =====================================================================
class DecideBlock(BaseBlock):
    """
    DECIDE block - route entities based on conditions, probabilities, or time.

    Supports multiple decision types:
    1. "probability" - Route based on probability distribution
    2. "condition" - Route based on entity attributes
    3. "condition_generic" - Route based on generic expressions (entity, model, resources)
    4. "time_condition" - Route based on simulation time

    NEW: Generic condition evaluation with access to:
    - Entity attributes
    - Model state
    - Resource states (queue length, utilization, etc.)
    - Simulation time
    - Custom model variables
    """

    def __init__(self, name: str, env: simpy.Environment,
                 decision_type: str = "probability",
                 track_decisions: bool = True,
                 event_logger: EventLogger = None):
        super().__init__(name, env, event_logger)
        self.decision_type = decision_type
        self.routes = {}
        self.decision_counts = {}
        self.track_decisions = track_decisions

    def add_route(self, route_name: str,
                  next_block: 'BaseBlock',
                  probability: Optional[float] = None,
                  condition: Optional[Callable[[Entity], bool]] = None,
                  condition_generic: Optional[Callable[[
                      Entity, Any], bool]] = None,
                  time_condition: Optional[Callable[[float], bool]] = None):
        """
        Add a routing option.

        Args:
            route_name: Name of the route
            next_block: Target block for this route
            probability: Probability for this route (for "probability" type)
            condition: Function(entity) -> bool (for "condition" type)
            condition_generic: Function(entity, context) -> bool (for "condition_generic" type)
            time_condition: Function(time) -> bool (for "time_condition" type)

        Examples:
            # 1. Probability-based routing
            decide.add_route("high_priority", block1, probability=0.3)

            # 2. Entity-only condition
            decide.add_route("vip", block2, 
                           condition=lambda e: e.priority == 0)

            # 3. Generic condition with entity attributes
            decide.add_route("thirsty", block3,
                           condition_generic=lambda e, ctx: e.get_attribute('sede', 0) > 2)

            # 4. Generic condition with resource state
            decide.add_route("short_queue", block4,
                           condition_generic=lambda e, ctx: len(ctx['resources']['nurses'].queue) < 5)

            # 5. Generic condition with model variables
            decide.add_route("low_failure_rate", block5,
                           condition_generic=lambda e, ctx: ctx['model'].variable_tracker.get_current('percentual_falhas') < 10)

            # 6. Complex generic condition
            decide.add_route("priority_and_available", block6,
                           condition_generic=lambda e, ctx: (
                               e.priority == 0 and 
                               ctx['resources']['doctors'].count < ctx['resources']['doctors'].capacity and
                               ctx['time'] < 480  # Before 8 hours
                           ))

            # 7. Time-based routing
            decide.add_route("day_shift", block7, 
                           time_condition=lambda t: (t % 1440) < 720)
        """
        self.routes[route_name] = {
            'block': next_block,
            'probability': probability,
            'condition': condition,
            'condition_generic': condition_generic,
            'time_condition': time_condition
        }
        self.decision_counts[route_name] = 0

    def process_entity(self, entity: Entity):
        """Route entity based on decision type."""
        entity.route_history.append(self.name)

        chosen_route = None

        if self.decision_type == "probability":
            chosen_route = self._choose_by_probability()
        elif self.decision_type == "condition":
            chosen_route = self._choose_by_condition(entity)
        elif self.decision_type == "condition_generic":
            chosen_route = self._choose_by_condition_generic(entity)
        elif self.decision_type == "time_condition":
            chosen_route = self._choose_by_time_condition()
        else:
            raise ValueError(f"Invalid decision type: {self.decision_type}")

        if chosen_route and chosen_route in self.routes:
            self.decision_counts[chosen_route] += 1
            next_block = self.routes[chosen_route]['block']
            entity.add_attribute(f"{self.name}_decision", chosen_route)

            # NEW: Trace decision
            self._trace('decide', entity, details=f"route={chosen_route}")

            # Log decision as an event
            if self.event_logger:
                self.event_logger.log_event(
                    case_id=entity.id,
                    activity=f"{self.name}_{chosen_route}",
                    timestamp=self.env.now,
                    lifecycle='complete',
                    decision=chosen_route,
                    decision_time=self.env.now
                )

            # Update model variables if tracking enabled
            if self.track_decisions and hasattr(self.env, 'model'):
                self._update_decision_variables(
                    route_name=chosen_route, entity=entity)

            self.env.process(next_block.process_entity(entity))
            yield self.env.timeout(0)
        else:
            # No valid route found - entity exits
            yield self.env.timeout(0)

    def _choose_by_probability(self) -> Optional[str]:
        """Choose route based on probabilities."""
        rand = random.random()
        cumulative = 0.0

        for route_name, route_info in self.routes.items():
            prob = route_info.get('probability', 0)
            cumulative += prob
            if rand <= cumulative:
                return route_name

        return None

    def _choose_by_condition(self, entity: Entity) -> Optional[str]:
        """
        Choose route based on entity-only conditions.

        Routes are evaluated in the order they were added.
        Returns the first route whose condition evaluates to True.
        """
        for route_name, route_info in self.routes.items():
            condition = route_info.get('condition')
            if condition and condition(entity):
                return route_name

        return None

    def _choose_by_condition_generic(self, entity: Entity) -> Optional[str]:
        """
        Choose route based on generic conditions with full context.

        Provides access to:
        - entity: The entity being routed
        - model: The simulation model
        - resources: Dictionary of all resources
        - time: Current simulation time
        - variables: Model variable tracker (if available)

        Routes are evaluated in the order they were added.
        Returns the first route whose condition evaluates to True.
        """
        # Build context dictionary with all available information
        context = self._build_decision_context(entity)

        for route_name, route_info in self.routes.items():
            condition_generic = route_info.get('condition_generic')
            if condition_generic:
                try:
                    if condition_generic(entity, context):
                        return route_name
                except Exception as e:
                    print(
                        f"WARNING: Error evaluating condition for route '{route_name}': {e}")
                    continue

        return None

    def _build_decision_context(self, entity: Entity) -> Dict[str, Any]:
        """
        Build context dictionary for generic condition evaluation.

        Returns:
            Dictionary with:
            - 'model': Reference to simulation model
            - 'resources': Dictionary of all resources
            - 'time': Current simulation time
            - 'variables': Variable tracker (if available)
            - 'entity': The entity being evaluated
        """
        context = {
            'time': self.env.now,
            'entity': entity
        }

        # Add model reference if available
        if hasattr(self.env, 'model'):
            model = self.env.model
            context['model'] = model

            # Add resources dictionary
            context['resources'] = model.resources

            # Add variable tracker if available
            if hasattr(model, 'variable_tracker'):
                context['variables'] = model.variable_tracker

            # Add useful derived information
            context['entity_count'] = model.entity_count
            context['warm_up_period'] = model.warm_up_period

            # Add resource utilization info
            context['resource_utilization'] = {}
            for res_name, resource in model.resources.items():
                context['resource_utilization'][res_name] = {
                    'queue_length': len(resource.queue),
                    'in_use': resource.count,
                    'capacity': resource.capacity,
                    'available': resource.capacity - resource.count,
                    'utilization': resource.count / resource.capacity if resource.capacity > 0 else 0
                }

        return context

    def _choose_by_time_condition(self) -> Optional[str]:
        """
        Choose route based on simulation time conditions.

        Routes are evaluated in order until one matches.
        Returns the first route whose time_condition evaluates to True.
        """
        current_time = self.env.now

        for route_name, route_info in self.routes.items():
            time_condition = route_info.get('time_condition')
            if time_condition and time_condition(current_time):
                return route_name

        return None

    def _update_decision_variables(self, route_name: str, entity: Entity):
        """
        Update model variables based on decision route taken.

        Automatically tracks decision counts in model variables if they exist.
        """
        if not hasattr(self.env, 'model'):
            return

        model = self.env.model

        if hasattr(model, 'variable_tracker'):
            tracker = model.variable_tracker

            # Try to update route-specific counter
            var_name = f'{self.name}_{route_name}_count'
            if var_name in tracker.variables:
                current = tracker.get_current(var_name)
                tracker.update(var_name, self.env.now, current + 1)


# # =====================================================================
# # EXAMPLES: Generic Condition Usage
# # =====================================================================
# def example_generic_conditions():
#     """
#     Examples demonstrating the power of generic conditions.
#     """

#     # Example 1: Route based on resource queue length
#     decide_queue = DecideBlock(
#         "DecideByQueue", env,
#         decision_type="condition_generic",
#         event_logger=event_logger
#     )

#     decide_queue.add_route(
#         "nurse_short_queue", nurse_block,
#         condition_generic=lambda e, ctx: len(ctx['resources']['nurses'].queue) < 3
#     )

#     decide_queue.add_route(
#         "doctor_short_queue", doctor_block,
#         condition_generic=lambda e, ctx: len(ctx['resources']['doctors'].queue) < 3
#     )

#     decide_queue.add_route(
#         "any_available", default_block,
#         condition_generic=lambda e, ctx: True  # Fallback
#     )


#     # Example 2: Route based on resource utilization
#     decide_utilization = DecideBlock(
#         "DecideByUtilization", env,
#         decision_type="condition_generic",
#         event_logger=event_logger
#     )

#     decide_utilization.add_route(
#         "low_utilization_route", fast_track_block,
#         condition_generic=lambda e, ctx: (
#             ctx['resource_utilization']['nurses']['utilization'] < 0.7
#         )
#     )

#     decide_utilization.add_route(
#         "high_utilization_route", slow_track_block,
#         condition_generic=lambda e, ctx: (
#             ctx['resource_utilization']['nurses']['utilization'] >= 0.7
#         )
#     )


#     # Example 3: Route based on model variables
#     decide_quality = DecideBlock(
#         "DecideByQuality", env,
#         decision_type="condition_generic",
#         event_logger=event_logger
#     )

#     decide_quality.add_route(
#         "extra_inspection", inspection_block,
#         condition_generic=lambda e, ctx: (
#             ctx['variables'].get_current('percentual_falhas') > 5.0
#         )
#     )

#     decide_quality.add_route(
#         "normal_flow", normal_block,
#         condition_generic=lambda e, ctx: (
#             ctx['variables'].get_current('percentual_falhas') <= 5.0
#         )
#     )


#     # Example 4: Complex multi-criteria decision
#     decide_complex = DecideBlock(
#         "ComplexDecision", env,
#         decision_type="condition_generic",
#         event_logger=event_logger
#     )

#     decide_complex.add_route(
#         "vip_express", vip_block,
#         condition_generic=lambda e, ctx: (
#             e.priority == 0 and  # High priority entity
#             ctx['time'] < 480 and  # Before 8 hours
#             ctx['resource_utilization']['vip_staff']['available'] > 0  # Staff available
#         )
#     )

#     decide_complex.add_route(
#         "regular_available", regular_block,
#         condition_generic=lambda e, ctx: (
#             ctx['resource_utilization']['regular_staff']['utilization'] < 0.8 and
#             len(ctx['resources']['regular_staff'].queue) < 5
#         )
#     )

#     decide_complex.add_route(
#         "overflow", overflow_block,
#         condition_generic=lambda e, ctx: True  # Catch-all
#     )


#     # Example 5: Route based on entity attribute AND resource state
#     decide_hybrid = DecideBlock(
#         "HybridDecision", env,
#         decision_type="condition_generic",
#         event_logger=event_logger
#     )

#     decide_hybrid.add_route(
#         "thirsty_and_available", beverage_block,
#         condition_generic=lambda e, ctx: (
#             e.get_attribute('sede', 0) > 2 and  # Entity is thirsty
#             len(ctx['resources']['copos'].queue) < 10  # Not too crowded
#         )
#     )

#     decide_hybrid.add_route(
#         "not_thirsty", skip_beverage_block,
#         condition_generic=lambda e, ctx: e.get_attribute('sede', 0) <= 2
#     )

#     decide_hybrid.add_route(
#         "wait_later", wait_block,
#         condition_generic=lambda e, ctx: True  # If crowded, wait
#     )


#     # Example 6: Dynamic routing based on time of day AND system load
#     decide_shift = DecideBlock(
#         "ShiftBasedRouting", env,
#         decision_type="condition_generic",
#         event_logger=event_logger
#     )

#     decide_shift.add_route(
#         "day_shift_express", day_express_block,
#         condition_generic=lambda e, ctx: (
#             (ctx['time'] % 1440) < 720 and  # Day shift (0-12 hours)
#             ctx['resource_utilization']['day_staff']['utilization'] < 0.6
#         )
#     )

#     decide_shift.add_route(
#         "night_shift_regular", night_regular_block,
#         condition_generic=lambda e, ctx: (
#             (ctx['time'] % 1440) >= 720 and  # Night shift (12-24 hours)
#             ctx['resource_utilization']['night_staff']['available'] > 0
#         )
#     )

#     decide_shift.add_route(
#         "overflow_routing", overflow_block,
#         condition_generic=lambda e, ctx: True
#     )


# # =====================================================================
# # COMPLETE EXAMPLE: Restaurant with Smart Routing
# # =====================================================================
# def build_restaurant_with_smart_routing():
#     """
#     Restaurant model with intelligent routing based on:
#     - Customer thirst level
#     - Table availability
#     - Server queue length
#     - Time of day
#     """

#     model = SimulationModel()
#     HOURS = 60
#     event_logger = EventLogger()

#     # Resources
#     garcons = model.add_resource("Garcons", 3, "regular")
#     copos = model.add_resource("Copos", 50, "regular")
#     mesas = model.add_resource("Mesas", 20, "regular")

#     # Create arrivals
#     chegadas = CreateBlock(
#         "Chegadas", model.env,
#         inter_arrival_time=lambda: random.expovariate(1/5),
#         entity_prefix="Cliente",
#         max_arrivals=500,
#         event_logger=event_logger
#     )

#     # Assign initial thirst level
#     chegadas.assign_attributes(
#         sede=lambda: random.randint(0, 5)
#     )

#     # SMART DECISION: Should customer get a drink first?
#     decide_bebida = DecideBlock(
#         "DecideBebida", model.env,
#         decision_type="condition_generic",
#         event_logger=event_logger
#     )

#     # Route 1: Very thirsty AND drinks available -> Go directly to drink
#     decide_bebida.add_route(
#         "beber_primeiro", beber_block,
#         condition_generic=lambda e, ctx: (
#             e.get_attribute('sede', 0) >= 4 and  # Very thirsty
#             len(ctx['resources']['copos'].queue) < 15 and  # Not too crowded
#             ctx['resource_utilization']['garcons']['available'] > 0  # Server available
#         )
#     )

#     # Route 2: Not very thirsty OR drinks crowded -> Go to table first
#     decide_bebida.add_route(
#         "mesa_primeiro", sentar_block,
#         condition_generic=lambda e, ctx: (
#             e.get_attribute('sede', 0) < 4 or  # Not so thirsty
#             len(ctx['resources']['copos'].queue) >= 15  # Drink station crowded
#         )
#     )

#     # Route 3: Moderate thirst AND short server queue -> Get drink
#     decide_bebida.add_route(
#         "beber_se_rapido", beber_block,
#         condition_generic=lambda e, ctx: (
#             e.get_attribute('sede', 0) >= 2 and
#             len(ctx['resources']['garcons'].queue) < 3
#         )
#     )

#     # Route 4: Fallback - go to table
#     decide_bebida.add_route(
#         "mesa_fallback", sentar_block,
#         condition_generic=lambda e, ctx: True
#     )

#     # Define blocks (simplified)
#     beber_block = ProcessBlock("Beber", model.env, resource=copos,
#                                delay_time=lambda: random.uniform(2, 4),
#                                event_logger=event_logger)
#     beber_block.set_resource_name('Copos')
#     beber_block.modify_attributes(sede=lambda current: max(0, current - 3))

#     sentar_block = ProcessBlock("Sentar", model.env, resource=mesas,
#                                 delay_time=lambda: random.gauss(30, 5),
#                                 event_logger=event_logger)
#     sentar_block.set_resource_name('Mesas')

#     servir_block = ProcessBlock("Servir", model.env, resource=garcons,
#                                 delay_time=lambda: random.uniform(5, 10),
#                                 event_logger=event_logger)
#     servir_block.set_resource_name('Garcons')

#     dispose = DisposeBlock("Dispose", model.env, event_logger=event_logger)

#     # Add blocks
#     for block in [chegadas, decide_bebida, beber_block, sentar_block,
#                   servir_block, dispose]:
#         model.add_block(block)

#     # Connect flow
#     chegadas.connect_to(decide_bebida)
#     # decide_bebida routes are configured above
#     beber_block.connect_to(sentar_block)
#     sentar_block.connect_to(servir_block)
#     servir_block.connect_to(dispose)

#     return model, event_logger


# # =====================================================================
# # UTILITY: Add method to print decision statistics
# # =====================================================================
# def print_decision_statistics(model):
#     """Print detailed statistics about all decision blocks."""

#     from blocks.decide_block import DecideBlock

#     print("\n" + "="*70)
#     print("DECISION BLOCK STATISTICS")
#     print("="*70)

#     for block_name, block in model.blocks.items():
#         if isinstance(block, DecideBlock):
#             print(f"\n{block_name} (type: {block.decision_type}):")
#             print(f"  Total decisions: {sum(block.decision_counts.values())}")
#             print(f"  Routes:")

#             total = sum(block.decision_counts.values())
#             for route_name, count in sorted(block.decision_counts.items(),
#                                            key=lambda x: x[1], reverse=True):
#                 percentage = (count / total * 100) if total > 0 else 0
#                 print(f"    {route_name}: {count} ({percentage:.1f}%)")

#     print("="*70)



# ======================================================
# FILE: validation\resource_validator.py
# ======================================================

# Key
# Always validate (it's automatic by default)
# Use print_resource_summary() during development
# resource_units must be ≤ capacity (critical rule)
# Validation prevents deadlocks before they happen
# Clear error messages tell you exactly what to fix

# When to Disable Validation
# ⚠️ Rarely! Only when:

# You're 100% certain configuration is correct
# Running thousands of replications (validate once, then skip)
# Debugging other issues and need to bypass

# Validation Checks
# Check                   Level       Description
# Units > Capacity        ❌ ERROR    DEADLOCK - stops simulation
# Units == Capacity       ⚠️ WARNING  May create bottleneck
# Units > 50%             ℹ️ INFO      High resource usage
# Unregistered Resource   ❌ ERROR    Resource not found
# Wrong Type              ⚠️ WARNING  Priority mismatch

# =====================================================================
# FILE: validation/resource_validator.py
# =====================================================================
"""
Resource configuration validation for simulation models.

Validates that:
- Resource units requested don't exceed capacity
- Resources exist before being used
- No duplicate resource names
- Valid resource types
- Consistent resource usage across blocks
"""


class ResourceValidationError(Exception):
    """Raised when resource configuration is invalid."""
    """
    Resource configuration validation for simulation models.
    Validates that:
    - Resource units requested don't exceed capacity
    - Resources exist before being used
    - No duplicate resource names
    - Valid resource types
    - Consistent resource usage across blocks
    """
    # print(">>> VALIVAÇÃO DE RECURSOS!")
    pass


class ResourceValidator:
    """
    Validates resource configurations in simulation models.

    Performs comprehensive checks to catch configuration errors before
    simulation runtime, providing clear error messages for fixes.

    Supports ProcessBlocks with and without resources (pure delay operations).
    """

    def __init__(self, model):
        """
        Initialize resource validator.

        Args:
            model: SimulationModel instance to validate
        """
        self.model = model
        self.errors = []
        self.warnings = []

    def validate_all(self, raise_on_error: bool = True) -> bool:
        """
        Run all validation checks.

        Args:
            raise_on_error: If True, raise exception on errors; if False, return status

        Returns:
            True if all validations pass, False otherwise

        Raises:
            ResourceValidationError: If validation fails and raise_on_error=True
        """
        self.errors = []
        self.warnings = []

        # Run all validation checks
        self._validate_resource_definitions()
        self._validate_resource_units()
        self._validate_resource_references()
        self._validate_resource_types()
        self._validate_multi_resource_blocks()

        # Print results
        self._print_validation_results()

        # Handle errors
        if self.errors:
            if raise_on_error:
                error_msg = self._format_error_message()
                raise ResourceValidationError(error_msg)
            return False

        return True

    def _validate_resource_definitions(self):
        """Check for duplicate resource names and invalid capacities."""
        seen_names = set()

        for name, resource in self.model.resources.items():
            # Check for duplicates (shouldn't happen with dict, but check anyway)
            if name in seen_names:
                self.errors.append(
                    f"DUPLICATE RESOURCE: '{name}' is defined multiple times"
                )
            seen_names.add(name)

            # Check capacity
            if resource.capacity <= 0:
                self.errors.append(
                    f"INVALID CAPACITY: Resource '{name}' has capacity "
                    f"{resource.capacity} (must be > 0)"
                )

            # Warning for very high capacity
            if resource.capacity > 1000:
                self.warnings.append(
                    f"HIGH CAPACITY: Resource '{name}' has unusually high capacity "
                    f"({resource.capacity}). Is this intentional?"
                )

    def _validate_resource_units(self):
        """Validate that resource units don't exceed capacity."""

        for block_name, block in self.model.blocks.items():
            if isinstance(block, ProcessBlock):
                self._validate_single_resource_block(block_name, block)
            elif isinstance(block, MultiProcessBlock):
                self._validate_multi_resource_block_units(block_name, block)

    def _validate_single_resource_block(self, block_name: str, block):
        """Validate ProcessBlock resource configuration."""
        resource = block.resource

        # ✅ NEW: Skip validation if block has no resource (pure delay mode)
        if resource is None:
            return  # No resource = no validation needed

        units_requested = getattr(block, 'resource_units', 1)

        # Find resource name
        resource_name = self._find_resource_name(resource)

        if resource_name:
            capacity = resource.capacity

            # CRITICAL ERROR: Units exceed capacity
            if units_requested > capacity:
                self.errors.append(
                    f"RESOURCE OVERALLOCATION: Block '{block_name}' requests "
                    f"{units_requested} units of '{resource_name}', but capacity is "
                    f"only {capacity}. This will cause DEADLOCK!"
                )

            # WARNING: Using full capacity (might cause bottleneck)
            elif units_requested == capacity:
                self.warnings.append(
                    f"FULL RESOURCE USE: Block '{block_name}' uses ALL {capacity} "
                    f"units of '{resource_name}'. This may create a bottleneck."
                )

            # WARNING: Units > 50% of capacity
            elif units_requested > capacity * 0.5:
                utilization_pct = (units_requested / capacity) * 100
                self.warnings.append(
                    f"HIGH RESOURCE USE: Block '{block_name}' uses {units_requested} "
                    f"of {capacity} units ({utilization_pct:.0f}%) of '{resource_name}'. "
                    f"Consider if this is appropriate."
                )
        else:
            self.errors.append(
                f"UNKNOWN RESOURCE: Block '{block_name}' uses a resource that "
                f"is not registered in the model"
            )

    def _validate_multi_resource_block_units(self, block_name: str, block):
        """Validate MultiProcessBlock resource requirements."""
        for resource, units_requested in block.resource_requirements.items():
            resource_name = self._find_resource_name(resource)

            if resource_name:
                capacity = resource.capacity

                # CRITICAL ERROR: Units exceed capacity
                if units_requested > capacity:
                    self.errors.append(
                        f"RESOURCE OVERALLOCATION: Block '{block_name}' requests "
                        f"{units_requested} units of '{resource_name}', but capacity is "
                        f"only {capacity}. This will cause DEADLOCK!"
                    )

                # WARNING: Using full capacity
                elif units_requested == capacity:
                    self.warnings.append(
                        f"FULL RESOURCE USE: Block '{block_name}' uses ALL {capacity} "
                        f"units of '{resource_name}'. Combined with other resources, "
                        f"this may create significant bottleneck."
                    )
            else:
                self.errors.append(
                    f"UNKNOWN RESOURCE: Block '{block_name}' uses a resource that "
                    f"is not registered in the model"
                )

    def _validate_resource_references(self):
        """Check that all referenced resources exist."""

        registered_resources = set(self.model.resources.values())

        for block_name, block in self.model.blocks.items():
            if isinstance(block, ProcessBlock):
                # ✅ NEW: Skip if no resource (pure delay mode)
                if block.resource is None:
                    continue

                if block.resource not in registered_resources:
                    self.errors.append(
                        f"UNREGISTERED RESOURCE: Block '{block_name}' uses a resource "
                        f"that was not added via model.add_resource()"
                    )

            elif isinstance(block, MultiProcessBlock):
                for resource in block.resource_requirements.keys():
                    if resource not in registered_resources:
                        self.errors.append(
                            f"UNREGISTERED RESOURCE: Block '{block_name}' uses a resource "
                            f"that was not added via model.add_resource()"
                        )

    def _validate_resource_types(self):
        """Validate resource types (Regular vs Priority vs Preemptive)."""

        for block_name, block in self.model.blocks.items():
            if isinstance(block, (ProcessBlock, MultiProcessBlock)):
                resources = []

                if isinstance(block, ProcessBlock):
                    # ✅ NEW: Skip if no resource
                    if block.resource is not None:
                        resources = [block.resource]
                else:
                    resources = list(block.resource_requirements.keys())

                for resource in resources:
                    resource_name = self._find_resource_name(resource)

                    if resource_name:
                        # Check if resource type matches usage
                        if isinstance(resource, simpy.PriorityResource):
                            # Priority resource should be used with priority entities
                            if not self._has_priority_generator():
                                self.warnings.append(
                                    f"PRIORITY MISMATCH: Resource '{resource_name}' is "
                                    f"PriorityResource but no entities have priorities. "
                                    f"Consider using regular Resource instead."
                                )

                        # Check for PreemptiveResource (if supported)
                        if isinstance(resource, simpy.PreemptiveResource):
                            self.warnings.append(
                                f"PREEMPTIVE RESOURCE: '{resource_name}' is PreemptiveResource. "
                                f"Ensure your code handles preemption correctly."
                            )

    def _validate_multi_resource_blocks(self):
        """Validate blocks that require multiple resources simultaneously."""

        for block_name, block in self.model.blocks.items():
            if isinstance(block, MultiProcessBlock):
                total_units = sum(block.resource_requirements.values())

                # WARNING: Requesting many resources
                if total_units > 5:
                    self.warnings.append(
                        f"COMPLEX RESOURCE REQUIREMENTS: Block '{block_name}' "
                        f"requires {total_units} total resource units across "
                        f"{len(block.resource_requirements)} resources. "
                        f"This may increase chance of deadlock."
                    )

                # Check for potential deadlock with other multi-resource blocks
                self._check_circular_dependencies(block_name, block)

    def _check_circular_dependencies(self, block_name: str, block):
        """
        Check for potential circular dependencies in resource requirements.

        This is a simplified check - full deadlock detection is complex.
        """

        block_resources = set(block.resource_requirements.keys())

        for other_name, other_block in self.model.blocks.items():
            if other_name == block_name:
                continue

            if isinstance(other_block, MultiProcessBlock):
                other_resources = set(other_block.resource_requirements.keys())

                # If blocks share resources, potential for deadlock
                if block_resources.intersection(other_resources):
                    self.warnings.append(
                        f"SHARED RESOURCES: Blocks '{block_name}' and '{other_name}' "
                        f"both require some of the same resources. This could lead to "
                        f"deadlock if not carefully designed. Review the model logic."
                    )
                    break  # Only warn once per block

    def _has_priority_generator(self) -> bool:
        """Check if any CreateBlock has priority generator."""

        for block in self.model.blocks.values():
            if isinstance(block, CreateBlock):
                if block.priority_generator is not None:
                    return True
        return False

    def _find_resource_name(self, resource_obj) -> Optional[str]:
        """Find resource name from resource object."""
        if resource_obj is None:
            return None

        for name, res in self.model.resources.items():
            if res == resource_obj:
                return name
        return None

    def _print_validation_results(self):
        """Print validation results with color coding."""
        if not self.errors and not self.warnings:
            print("\n" + "=" * 70)
            print("RESOURCE VALIDATION: ALL CHECKS PASSED")
            print("=" * 70)
            return

        print("\n" + "=" * 70)
        print("RESOURCE VALIDATION RESULTS")
        print("=" * 70)

        if self.errors:
            print(f"\nCRITICAL ERRORS FOUND: {len(self.errors)}")
            print("-" * 70)
            for i, error in enumerate(self.errors, 1):
                print(f"{i}. {error}")

        if self.warnings:
            print(f"\nWARNINGS: {len(self.warnings)}")
            print("-" * 70)
            for i, warning in enumerate(self.warnings, 1):
                print(f"{i}. {warning}")

        print("=" * 70)

    def _format_error_message(self) -> str:
        """Format errors into exception message."""
        msg = f"\n{len(self.errors)} CRITICAL RESOURCE CONFIGURATION ERROR(S) FOUND:\n\n"
        for i, error in enumerate(self.errors, 1):
            msg += f"{i}. {error}\n"
        msg += "\nFIX THESE ERRORS BEFORE RUNNING SIMULATION!"
        return msg

    def print_resource_summary(self):
        """Print summary of all resources and their usage."""

        print("\n" + "=" * 70)
        print("RESOURCE CONFIGURATION SUMMARY")
        print("=" * 70)

        # ✅ NEW: Count resource-free blocks
        delay_only_blocks = []

        for name, resource in sorted(self.model.resources.items()):
            capacity = resource.capacity
            resource_type = self._get_resource_type_name(resource)

            print(f"\nResource: {name}")
            print(f"  Type: {resource_type}")
            print(f"  Capacity: {capacity} units")

            # Find blocks using this resource
            using_blocks = []
            total_max_usage = 0

            for block_name, block in self.model.blocks.items():
                if isinstance(block, ProcessBlock):
                    # ✅ NEW: Track delay-only blocks separately
                    if block.resource is None:
                        delay_only_blocks.append(block_name)
                    elif block.resource == resource:
                        units = getattr(block, 'resource_units', 1)
                        using_blocks.append((block_name, units))
                        total_max_usage = max(total_max_usage, units)

                elif isinstance(block, MultiProcessBlock):
                    if resource in block.resource_requirements:
                        units = block.resource_requirements[resource]
                        using_blocks.append((block_name, units))
                        total_max_usage = max(total_max_usage, units)

            if using_blocks:
                print(f"  Used by {len(using_blocks)} block(s):")
                for block_name, units in using_blocks:
                    pct = (units / capacity * 100) if capacity > 0 else 0
                    print(
                        f"    - {block_name}: {units} units ({pct:.0f}% of capacity)")

                print(f"  Maximum single allocation: {total_max_usage} units "
                      f"({total_max_usage/capacity*100:.0f}% of capacity)")
            else:
                print(f"  WARNING: Resource not used by any block!")

        # ✅ NEW: Print delay-only blocks summary
        if delay_only_blocks:
            print("\n" + "-" * 70)
            print("DELAY-ONLY BLOCKS (No Resource Required):")
            print(f"  Found {len(delay_only_blocks)} pure delay block(s):")
            for block_name in delay_only_blocks:
                print(f"    - {block_name} (pure delay operation)")
            print("  Note: These blocks perform time delays without consuming resources.")

        print("=" * 70)

    def _get_resource_type_name(self, resource) -> str:
        """Get human-readable resource type name."""
        if isinstance(resource, simpy.PreemptiveResource):
            return "PreemptiveResource"
        elif isinstance(resource, simpy.PriorityResource):
            return "PriorityResource"
        elif isinstance(resource, simpy.Resource):
            return "Resource"
        else:
            return "Unknown"


# # =====================================================================
# # Integration with SimulationModel
# # =====================================================================
# def add_validation_to_model():
#     """
#     Add these methods to core/simulation_model.py
#     """
#     pass  # See implementation below


# # Example additions to SimulationModel class:
# """
# # FILE: core/simulation_model.py

# class SimulationModel:
#     # ... existing code ...

#     def validate_resources(self, raise_on_error: bool = True) -> bool:
#         '''
#         Validate resource configuration before running simulation.

#         Args:
#             raise_on_error: If True, raise exception on errors

#         Returns:
#             True if validation passes, False otherwise
#         '''
#         from validation.resource_validator import ResourceValidator

#         validator = ResourceValidator(self)
#         return validator.validate_all(raise_on_error=raise_on_error)

#     def print_resource_summary(self):
#         '''Print summary of all resources and their usage.'''
#         from validation.resource_validator import ResourceValidator

#         validator = ResourceValidator(self)
#         validator.print_resource_summary()

#     def run_simulation(self, check_system: bool = False,
#                       validate_resources: bool = True,  # NEW parameter
#                       until: float = None,
#                       seed: int = None,
#                       warm_up_period: float = 0.0):
#         '''Run the simulation with optional resource validation.'''

#         # NEW: Validate resources before running
#         if validate_resources:
#             self.validate_resources(raise_on_error=True)

#         # ... rest of existing run_simulation code ...
# """


# # =====================================================================
# # USAGE EXAMPLES
# # =====================================================================

# def example_catching_errors():
#     """Example showing how validator catches errors."""
#     from core.simulation_model import SimulationModel
#     from blocks.process_block import ProcessBlock
#     from blocks.create_block import CreateBlock
#     import random

#     model = SimulationModel()

#     # Create resources
#     nursesT = model.add_resource("nursesT", 1, "priority")  # Only 1 nurse
#     doctors = model.add_resource("doctors", 4, "priority")

#     # Create blocks
#     arrivals = CreateBlock(
#         "Arrivals", model.env,
#         inter_arrival_time=lambda: random.expovariate(1/4),
#         entity_prefix="Patient"
#     )

#     # ERROR: Requesting 2 units when capacity is only 1
#     triage = ProcessBlock(
#         "Triage", model.env,
#         resource=nursesT,
#         delay_time=lambda: random.uniform(2, 5),
#         resource_units=2  # <-- THIS WILL CAUSE ERROR!
#     )

#     model.add_block(arrivals)
#     model.add_block(triage)
#     arrivals.connect_to(triage)

#     try:
#         # This will catch the error BEFORE simulation starts
#         model.run_simulation(until=1000, validate_resources=True)
#     except Exception as e:
#         print(f"Caught error: {e}")
#         print("\nThe validator prevented a deadlock situation!")


# def example_validation_workflow():
#     """Example showing complete validation workflow."""
#     from core.simulation_model import SimulationModel
#     from validation.resource_validator import ResourceValidator

#     # Build model
#     model = SimulationModel()
#     # ... add resources and blocks ...

#     # Option 1: Validate explicitly before running
#     validator = ResourceValidator(model)

#     # Check without raising exception
#     if not validator.validate_all(raise_on_error=False):
#         print("Validation failed! Review errors above.")
#         # Print detailed resource summary
#         validator.print_resource_summary()
#         return

#     # Option 2: Let run_simulation validate automatically
#     model.run_simulation(
#         until=1000,
#         validate_resources=True  # Default True
#     )

#     # Option 3: Skip validation (not recommended)
#     model.run_simulation(
#         until=1000,
#         validate_resources=False  # Use with caution!
#     )


# if __name__ == "__main__":
#     print("Resource Validation Module")
#     print("="*70)
#     print("\nThis module provides:")
#     print("  1. Detection of resource overallocation (units > capacity)")
#     print("  2. Validation of resource types (Priority, Preemptive, Regular)")
#     print("  3. Detection of unregistered resources")
#     print("  4. Warning for potential deadlocks")
#     print("  5. Resource usage summary")
#     print("\nValidation runs automatically before simulation starts")
#     print("to catch configuration errors early!")



# ======================================================
# FILE: validation\warmup.py
# ======================================================

# =====================================================================
# FILE: validation/warmup.py
# =====================================================================


# =====================================================================
# FILE: validation/warmup.py
# =====================================================================
class WarmUpAnalyzer:
    """Analyzes warm-up period requirements."""

    def __init__(self, model):
        self.model = model

    def analyze_warm_up_period(self):
        """Analyze data to suggest adequate warm-up period."""

        print("\n🔍 ANALISE DE WARM-UP:")
        print("=" * 50)

        resource_blocks = self._group_blocks_by_resource()

        for resource_name, blocks in resource_blocks.items():
            all_data = self._collect_resource_data(resource_name, blocks)

            if not all_data or len(all_data) < 100:
                continue

            all_data.sort(key=lambda x: x[0])
            capacity = self.model.resources[resource_name].capacity

            # Calculate utilization over time
            times = [point[0] for point in all_data]
            utilizations = [point[1] / capacity for point in all_data]

            # Find stabilization point
            stabilization_time = self._find_stabilization_point(
                times, utilizations)

            print(f"📋 {resource_name}:")
            if stabilization_time:
                print(
                    f"   Estabilizacao detectada em: t={stabilization_time:.1f}")
                print(f"   Warm-up sugerido: {stabilization_time * 1.2:.1f} "
                      f"(20% de margem)")
            else:
                print("   Sistema pode nao ter estabilizado completamente")

            # Calculate final utilization
            final_utilizations = utilizations[-min(100, len(utilizations)//4):]
            avg_final_util = np.mean(final_utilizations) * 100
            print(f"   Utilizacao final media: {avg_final_util:.1f}%")

        print("\nRECOMENDACOES:")
        print("• Observe os graficos para identificar quando a utilizacao se estabiliza")
        print("• O periodo de warm-up deve ser pelo menos ate o ponto de estabilizacao")
        print("• Use 20-30% de margem adicional sobre o tempo de estabilizacao")
        print("• Sistemas complexos podem precisar de warm-up mais longo")
        print("=" * 50)

    def _group_blocks_by_resource(self) -> dict:
        """Group process blocks by resource."""

        resource_blocks = {}

        for block in self.model.blocks.values():
            if isinstance(block, ProcessBlock):
                resource_name = self._find_resource_name(block.resource)
                if resource_name:
                    if resource_name not in resource_blocks:
                        resource_blocks[resource_name] = []
                    resource_blocks[resource_name].append(block)

            elif isinstance(block, MultiProcessBlock):
                for res in block.resource_requirements.keys():
                    resource_name = self._find_resource_name(res)
                    if resource_name:
                        if resource_name not in resource_blocks:
                            resource_blocks[resource_name] = []
                        resource_blocks[resource_name].append(block)

        return resource_blocks

    def _find_resource_name(self, resource_obj) -> str:
        """Find resource name from object."""
        for name, res in self.model.resources.items():
            if res == resource_obj:
                return name
        return None

    def _collect_resource_data(self, resource_name: str, blocks: List) -> List:
        """Collect resource data from blocks."""

        all_data = []
        for block in blocks:
            if isinstance(block, ProcessBlock):
                all_data.extend(block.resource_data)
            elif isinstance(block, MultiProcessBlock):
                resource_obj = self.model.resources[resource_name]
                if resource_obj in block.resource_data:
                    all_data.extend(block.resource_data[resource_obj])

        return all_data

    def _find_stabilization_point(self, times: List[float],
                                  utilizations: List[float]) -> float:
        """Find when variance stabilizes (system reaches steady state)."""
        window_size = min(50, len(utilizations) // 4)
        variances = []
        variance_times = []

        for i in range(window_size, len(utilizations) - window_size):
            window = utilizations[i-window_size:i+window_size]
            variance = np.var(window)
            variances.append(variance)
            variance_times.append(times[i])

        if not variances:
            return None

        # Find when variance stabilizes (< 50% of initial variance)
        initial_variance = np.mean(variances[:min(20, len(variances))])
        stabilization_threshold = initial_variance * 0.5

        for i, var in enumerate(variances):
            if var < stabilization_threshold:
                # Verify it stays stable
                stable_period = variances[i:i+min(20, len(variances)-i)]
                if (len(stable_period) >= 10 and
                        all(v < stabilization_threshold for v in stable_period)):
                    return variance_times[i]

        return None



# ======================================================
# FILE: validation\stability.py
# ======================================================

# =====================================================================
# FILE: validation/stability.py
# =====================================================================


# =====================================================================
# FILE: validation/stability.py
# =====================================================================
class StabilityAnalyzer:
    """Analyzes system stability and capacity."""

    def __init__(self, model):
        self.model = model

    def check_system_stability(self, sample_size: int = 1000) -> float:
        """
        Verify if system is mathematically stable.

        Args:
            sample_size: Number of samples for statistical estimation

        Returns:
            Stability index (>1.0 = stable, <1.0 = unstable)
        """
        print("\n🔍 VERIFICACAO DE ESTABILIDADE DO SISTEMA:")
        print("=" * 50)

        # Calculate arrival rate
        total_arrival_rate = self._calculate_arrival_rate(sample_size)
        print(f"📊 Taxa total de chegada estimada: "
              f"{total_arrival_rate * 60:.1f} entidades/hora")

        # Find bottleneck resource
        bottleneck_rate, bottleneck_resource = self._find_bottleneck(
            sample_size)
        system_capacity = bottleneck_rate

        print(f"📊 CAPACIDADE DO SISTEMA (gargalo em {bottleneck_resource}): "
              f"{system_capacity * 60:.1f} entidades/hora")

        # Calculate stability index
        stability = (system_capacity / total_arrival_rate
                     if total_arrival_rate > 0 else float('inf'))
        print(f"🎯 INDICE DE ESTABILIDADE: {stability:.2f}")

        self._print_stability_assessment(stability)
        print("=" * 50)

        return stability

    def _calculate_arrival_rate(self, sample_size: int) -> float:
        """Calculate total system arrival rate."""
        total_arrival_rate = 0

        for create_block in self.model.create_blocks:
            samples = [create_block.inter_arrival_time()
                       for _ in range(sample_size)]
            avg_interarrival = statistics.mean(samples)
            arrival_rate = 1 / avg_interarrival if avg_interarrival > 0 else 0
            total_arrival_rate += arrival_rate
            print(f"Taxa de chegada ({create_block.name}): "
                  f"{arrival_rate:.2f} entidades/min "
                  f"({arrival_rate*60:.1f}/h)")

        return total_arrival_rate

    def _find_bottleneck(self, sample_size: int) -> tuple:
        """
        Find bottleneck resource (lowest capacity).

        Returns:
            (bottleneck_rate, bottleneck_resource_name)
        """
        # from blocks.process_block import ProcessBlock, MultiProcessBlock

        bottleneck_rate = float('inf')
        bottleneck_resource = None

        # Group process blocks by resource
        resource_process_blocks = self._group_process_blocks_by_resource()

        for resource_name, process_blocks in resource_process_blocks.items():
            if resource_name in self.model.resources:
                resource = self.model.resources[resource_name]

                # Find slowest process block for this resource
                slowest_rate = self._calculate_resource_rate(
                    process_blocks, sample_size)

                # Resource capacity = capacity × service rate
                resource_capacity = resource.capacity * slowest_rate
                resource_type = ("Priority" if isinstance(resource,
                                                          simpy.PriorityResource) else
                                 "Preemptive" if isinstance(resource,
                                                            simpy.PreemptiveResource)
                                 else "Regular")

                print(f"  📋 {resource_name} ({resource_type}): "
                      f"{resource.capacity} × {slowest_rate:.3f}/min = "
                      f"{resource_capacity:.3f}/min ({resource_capacity * 60:.1f}/h)")

                if resource_capacity < bottleneck_rate:
                    bottleneck_rate = resource_capacity
                    bottleneck_resource = resource_name

        return bottleneck_rate, bottleneck_resource

    def _group_process_blocks_by_resource(self) -> Dict[str, List]:
        """Group process blocks by the resources they use."""

        resource_process_blocks = {}

        for block in self.model.blocks.values():
            if isinstance(block, ProcessBlock):
                resource_name = self._find_resource_name(block.resource)
                if resource_name:
                    if resource_name not in resource_process_blocks:
                        resource_process_blocks[resource_name] = []
                    resource_process_blocks[resource_name].append(block)

            elif isinstance(block, MultiProcessBlock):
                for resource, units_required in block.resource_requirements.items():
                    resource_name = self._find_resource_name(resource)
                    if resource_name:
                        if resource_name not in resource_process_blocks:
                            resource_process_blocks[resource_name] = []
                        resource_process_blocks[resource_name].append(
                            (block, units_required))

        return resource_process_blocks

    def _find_resource_name(self, resource_obj) -> str:
        """Find resource name from object."""
        for name, res in self.model.resources.items():
            if res == resource_obj:
                return name
        return None

    def _calculate_resource_rate(self, process_blocks: List,
                                 sample_size: int) -> float:
        """Calculate effective service rate for a resource."""
        # from blocks.process_block import MultiProcessBlock

        slowest_rate = float('inf')

        for item in process_blocks:
            if isinstance(item, tuple):  # MultiProcessBlock with units
                process_block, units_required = item
                samples = [process_block.delay_time()
                           for _ in range(sample_size)]
                avg_service_time = statistics.mean(samples)
                service_rate = (1 / avg_service_time
                                if avg_service_time > 0 else 0)
                effective_rate = service_rate / units_required
            else:  # Regular ProcessBlock
                process_block = item
                samples = [process_block.delay_time()
                           for _ in range(sample_size)]
                avg_service_time = statistics.mean(samples)
                service_rate = (1 / avg_service_time
                                if avg_service_time > 0 else 0)
                effective_rate = service_rate

            if effective_rate < slowest_rate:
                slowest_rate = effective_rate

        return slowest_rate

    def _print_stability_assessment(self, stability: float):
        """Print assessment of stability index."""
        if stability > 1.2:
            print("✅ Sistema SUPER dimensionado (capacidade >> demanda)")
        elif stability > 1.05:
            print("✅ Sistema estavel (capacidade > demanda)")
        elif stability > 0.95:
            print("⚠️ Sistema NO LIMITE (capacidade ≈ demanda) - cuidado!")
        elif stability > 0.8:
            print("🚨 Sistema INSTAVEL (demanda > capacidade)")
        else:
            print("💥 COLAPSO IMINENTE (demanda >> capacidade)")



# ======================================================
# FILE: core\simulation_model.py
# ======================================================

# =====================================================================
# FILE: core/simulation_model.py
# =====================================================================


# =====================================================================
# FILE: core/simulation_model.py
# =====================================================================
class SimulationModel:
    """
    Core simulation model orchestration.

    Responsibilities:
    - Manage simulation environment
    - Manage blocks and resources
    - Run simulation with warm-up handling
    - Provide basic results access

    Does NOT handle:
    - Metrics calculation (see analytics.metrics)
    - Plotting (see analytics.plotting)
    - Stability analysis (see validation.stability)
    - Warm-up analysis (see validation.warmup)
    """

    def __init__(self, verbose: bool = False,
                 entity_filter: Optional[Set[str]] = None,
                 resource_filter: Optional[Set[str]] = None,
                 event_type_filter: Optional[Set[str]] = None,
                 time_range: Optional[tuple] = None):
        """
        Initialize simulation model.

        Args:
            verbose: Enable event tracing
            entity_filter: Set of entity IDs to trace
            resource_filter: Set of resource names to trace
            event_type_filter: Set of event types to trace
            time_range: Tuple of (start_time, end_time) for tracing
        """
        self.env = simpy.Environment()
        self.env.model = self  # For safe_delay_time access
        self.blocks: Dict[str, 'BaseBlock'] = {}
        # self.resources: Dict[str, Union[simpy.Resource, simpy.PriorityResource]] = {}
        self.resources: Dict[str, Union[
            simpy.Resource,
            simpy.PriorityResource,
            simpy.PreemptiveResource]] = {}
        self.create_blocks: List['CreateBlock'] = []
        self.dispose_blocks: List['DisposeBlock'] = []
        self.stability_result: Optional[float] = None
        self.warm_up_period: float = 0.0
        self.is_warm_up_complete: bool = False
        self.variable_tracker = ModelVariableTracker(self)
        self.verbose = verbose  # NEW
        if verbose:
            self.event_tracer = EventTracer(
                self.env,
                entity_filter=entity_filter,
                resource_filter=resource_filter,
                event_type_filter=event_type_filter,
                time_range=time_range
            )
        else:
            self.event_tracer = None

    def validate_resources(self, raise_on_error: bool = True) -> bool:
        """
        Validate resource configuration before running simulation.

        Checks for:
        - Resource units exceeding capacity (CRITICAL)
        - Unregistered resources
        - Resource type mismatches
        - Potential deadlocks

        Args:
            raise_on_error: If True, raise exception on errors; 
                          if False, return False

        Returns:
            True if validation passes, False otherwise

        Raises:
            ResourceValidationError: If critical errors found and raise_on_error=True
        """

        validator = ResourceValidator(self)
        return validator.validate_all(raise_on_error=raise_on_error)

    def add_resource(self, name: str, capacity: int,
                     resource_type: str = "regular") -> Union[simpy.Resource,
                                                              simpy.PriorityResource]:
        """
        Add a resource to the model.

        Args:
            name: Resource name
            capacity: Resource capacity
            resource_type: "regular" or "priority"

        Returns:
            The created resource object
        """
        if resource_type == "preemptive":
            resource = simpy.PreemptiveResource(self.env, capacity=capacity)
        elif resource_type == "priority":
            resource = simpy.PriorityResource(self.env, capacity)
        else:
            resource = simpy.Resource(self.env, capacity)

        self.resources[name] = resource
        return resource

    def add_block(self, block: 'BaseBlock'):
        """Add a block to the model."""
        # from blocks.create_block import CreateBlock
        # from blocks.dispose_block import DisposeBlock

        self.blocks[block.name] = block

        # Track special block types
        if isinstance(block, CreateBlock):
            self.create_blocks.append(block)
        elif isinstance(block, DisposeBlock):
            self.dispose_blocks.append(block)

    def connect_blocks(self, from_block_name: str, to_block_name: str):
        """Connect two blocks in sequence."""
        if from_block_name not in self.blocks or to_block_name not in self.blocks:
            raise ValueError(
                f"Block not found: {from_block_name} or {to_block_name}")

        self.blocks[from_block_name].connect_to(self.blocks[to_block_name])

    def set_warm_up_period(self, warm_up_time: float):
        """Set the warm-up period for the simulation."""
        self.warm_up_period = warm_up_time
        self.env.warm_up_period = warm_up_time

    def safe_delay_time(self, delay_function: Callable[[], float]) -> float:
        """
        Ensure delay times are non-negative.

        Wraps delay functions to replace negative values with 0,
        preventing simulation errors from statistical distributions
        that may generate negative values.

        Args:
            delay_function: Function returning delay time

        Returns:
            Non-negative delay time
        """
        delay = delay_function()
        return max(0.0, delay)

    def run_simulation(self, validate_resources: bool = True,  # NEW parameter
                       until: Optional[float] = None,
                       seed: Optional[int] = None,
                       warm_up_period: float = 0.0,
                       check_stability: bool = False):
        """
        Run the simulation.

        Args:
            until: Simulation end time (None = run until no events)
            seed: Random seed for reproducibility
            warm_up_period: Warm-up period duration
            check_stability: Whether to check system stability before running
        """
        if validate_resources:
            self.validate_resources(raise_on_error=True)

        # Validate stopping condition
        self._validate_stopping_condition(until)

        if seed:
            random.seed(seed)

        # Set warm-up period
        if warm_up_period > 0:
            self.set_warm_up_period(warm_up_period)
            self.env.process(self._warm_up_monitor())

        # Check stability if requested
        if check_stability:
            analyzer = StabilityAnalyzer(self)
            self.stability_result = analyzer.check_system_stability()

            if self.stability_result >= 1.0:
                print("✅ Sistema estavel detectado, executando simulacao completa...")
            else:
                print("🚨 Sistema instavel detectado! Executando mesmo assim...")

        # NEW: Print trace header
        if self.verbose and self.event_tracer:
            self.event_tracer.print_header()

        # Start all CREATE blocks
        for create_block in self.create_blocks:
            create_block.start_generation()

        # Run simulation
        self.env.run(until=until)

        # NEW: Print trace footer
        if self.verbose and self.event_tracer:
            self.event_tracer.print_footer()

    def _validate_stopping_condition(self, until: Optional[float]):
        """Validate that simulation has a stopping condition."""
        has_time_limit = until is not None
        has_entity_limit = any(
            hasattr(cb, 'max_arrivals') and cb.max_arrivals is not None
            for cb in self.create_blocks
        )

        if not has_time_limit and not has_entity_limit:
            print("\n" + "=" * 70)
            print("ERRO CRITICO: SIMULACAO SEM CONDICAO DE PARADA DEFINIDA!")
            print("=" * 70)
            print(
                "A simulacao nao possui criterio de termino e executaria infinitamente.")
            print("\nVoce DEVE especificar pelo menos UMA das seguintes condicoes:")
            print("  1. Tempo de simulacao: run_simulation(until=<tempo>)")
            print("  2. Numero maximo de chegadas: CreateBlock(..., max_arrivals=<n>)")
            print("\nExemplos validos:")
            print("  • model.run_simulation(until=1000)")
            print("  • CreateBlock(..., max_arrivals=500)")
            print("  • Ambos: until=1000 E max_arrivals=500")
            print("\nEXECUCAO ABORTADA para prevenir loop infinito.")
            print("=" * 70)
            sys.exit(1)

        if not has_time_limit and has_entity_limit:
            max_entities = max(
                cb.max_arrivals for cb in self.create_blocks
                if hasattr(cb, 'max_arrivals') and cb.max_arrivals is not None
            )
            print(f"\nAVISO: Simulacao limitada apenas por numero de entidades "
                  f"({max_entities}).")
            print("Tempo de execucao pode ser muito longo se sistema congestionado.")
            print("Recomenda-se tambem definir limite de tempo com until=<valor>\n")

    def _warm_up_monitor(self):
        """Monitor warm-up period completion."""
        if self.warm_up_period > 0:
            yield self.env.timeout(self.warm_up_period)
            self.is_warm_up_complete = True
            self._clear_warm_up_statistics()

    def _clear_warm_up_statistics(self):
        """Clear statistics collected during warm-up."""

        # Reset DisposeBlock counters (keep data for plotting)
        for dispose_block in self.dispose_blocks:
            dispose_block.entities_disposed = 0
            dispose_block.total_system_time = 0.0

        # Reset ProcessBlock stats
        for block in self.blocks.values():
            if isinstance(block, (ProcessBlock, MultiProcessBlock)):
                block.entities_processed = 0
                block.total_delay_time = 0.0
                block.total_queue_time = 0.0

                if isinstance(block, ProcessBlock):
                    block.max_queue_length = 0
                    block.max_in_service = 0
                elif isinstance(block, MultiProcessBlock):
                    for metrics in block.max_metrics.values():
                        metrics['max_queue_length'] = 0
                        metrics['max_in_service'] = 0

    def add_model_variable(self, name: str, initial_value: Any = 0,
                           description: str = "", unit: str = "",
                           calculate_fn: Optional[Callable] = None):
        """Add a custom model variable to track."""
        self.variable_tracker.add_variable(
            name, initial_value, description, unit, calculate_fn
        )

    def update_model_variable(self, name: str, value: Any = None):
        """Update a model variable."""
        self.variable_tracker.update(name, value=value)

    @property
    def entity_count(self) -> int:
        """Total entities disposed (post warm-up)."""
        disposed_sum = sum(
            block.entities_disposed for block in self.dispose_blocks)
        if disposed_sum > 0:
            return disposed_sum
        return sum(block.entities_created for block in self.create_blocks)

    @property
    def overall_throughput(self) -> float:
        """Overall system throughput (entities per time unit)."""
        effective_time = self.env.now - self.warm_up_period
        if effective_time > 0:
            return self.entity_count / effective_time
        return 0

    def get_results(self) -> Dict[str, Any]:
        """
        Get basic simulation results.

        For detailed metrics, use:
        - analytics.metrics.MetricsCollector
        - analytics.reporting.SimulationReporter
        """
        results = {
            'simulation_time': self.env.now,
            'warm_up_period': self.warm_up_period,
            'entity_count': self.entity_count,
            'throughput': self.overall_throughput,
            'blocks': {}
        }

        for block_name, block in self.blocks.items():
            results['blocks'][block_name] = {
                'type': type(block).__name__,
                'statistics': block.statistics
            }

            if hasattr(block, 'entities_processed'):
                results['blocks'][block_name]['entities_processed'] = block.entities_processed
            if hasattr(block, 'entities_created'):
                results['blocks'][block_name]['entities_created'] = block.entities_created
            if hasattr(block, 'entities_disposed'):
                results['blocks'][block_name]['entities_disposed'] = block.entities_disposed
            if hasattr(block, 'decision_counts'):
                results['blocks'][block_name]['decision_counts'] = block.decision_counts

        return results

    def trace_entity(self, entity_id: str):
        """
        Print complete journey of a specific entity.

        Args:
            entity_id: Entity ID to trace (e.g., 'Patient_5')
        """
        if self.event_tracer:
            self.event_tracer.print_entity_journey(entity_id)
        else:
            print("Verbose mode not enabled. Run simulation with verbose=True")

    def trace_entities(self, entity_ids: List[str]):
        """
        Print journeys of multiple entities.

        Args:
            entity_ids: List of entity IDs to trace
        """
        if self.event_tracer:
            for entity_id in entity_ids:
                self.event_tracer.print_entity_journey(entity_id)
                print()  # Blank line between journeys
        else:
            print("Verbose mode not enabled. Run simulation with verbose=True")

    def replay_trace(self, entity_filter: Optional[Set[str]] = None,
                     resource_filter: Optional[Set[str]] = None,
                     event_type_filter: Optional[Set[str]] = None,
                     time_range: Optional[tuple] = None,
                     entity_pattern: Optional[str] = None):
        """
        Replay simulation trace with filters.

        Args:
            entity_filter: Set of specific entity IDs (e.g., {'Patient_0', 'Patient_5'})
            resource_filter: Set of resources (e.g., {'doctors', 'nurses'})
            event_type_filter: Set of event types (e.g., {'queue', 'service_start'})
            time_range: Time window (e.g., (10, 50))
            entity_pattern: Regex pattern for entities (e.g., r'Patient_[0-5]')

        Examples:
            # Trace specific patient
            model.replay_trace(entity_filter={'Patient_1'})

            # Trace first 5 patients
            model.replay_trace(entity_pattern=r'Patient_[0-4]')

            # Trace only doctor interactions
            model.replay_trace(resource_filter={'doctors'})

            # Trace queue and service events
            model.replay_trace(event_type_filter={'queue', 'service_start', 'service_end'})

            # Trace specific time window
            model.replay_trace(time_range=(10, 50))

            # Combine filters
            model.replay_trace(entity_filter={'Patient_1'}, 
                             event_type_filter={'queue', 'service_start'})
        """
        if self.event_tracer:
            self.event_tracer.replay_trace(
                entity_filter=entity_filter,
                resource_filter=resource_filter,
                event_type_filter=event_type_filter,
                time_range=time_range,
                entity_pattern=entity_pattern
            )
        else:
            print("Verbose mode not enabled. Run simulation with verbose=True")

    def print_trace_statistics(self):
        """Print summary statistics of event trace."""
        if self.event_tracer:
            self.event_tracer.print_statistics()
        else:
            print("Verbose mode not enabled. Run simulation with verbose=True")



# ======================================================
# FILE: blocks\dispose_block.py
# ======================================================

# =====================================================================
# FILE: blocks/dispose_block.py
# =====================================================================

# =====================================================================
# FILE: blocks/dispose_block.py
# =====================================================================
class DisposeBlock(BaseBlock):
    """DISPOSE block - removes entities from system and collects statistics."""

    def __init__(self, name: str, env: simpy.Environment, event_logger: EventLogger = None):
        super().__init__(name, env, event_logger)
        self.entities_disposed = 0
        self.total_system_time = 0.0
        self.disposed_entities = []

    def process_entity(self, entity: Entity):
        """Dispose of entity and collect final statistics."""
        entity.route_history.append(self.name)

        # Always collect entity data for plotting, but only count for statistics after warm-up
        system_time = self.env.now - entity.creation_time
        entity.add_attribute("system_time", system_time)
        entity.add_attribute("disposal_time", self.env.now)

        # # NEW: Apply configured attributes (e.g., revenue)
        # self._apply_attributes(entity)

        # ✅ MODIFIED: Capture assigned attributes (e.g., revenue)
        assigned_attrs = self._apply_attributes(entity)

        self.disposed_entities.append(entity)  # Always keep for plotting

        # Only count for official statistics after warm-up period
        if self.env.now >= getattr(self.env, 'warm_up_period', 0):
            self.total_system_time += system_time
            self.entities_disposed += 1

        # # NEW: Trace departure
        # self._trace('departure', entity,
        #            details=f"total_time_in_system={system_time:.2f}")

        # ✅ MODIFIED: Include attributes in departure trace
        details = f"total_time_in_system={system_time:.2f}"

        # Add attribute info if any were assigned
        if assigned_attrs:
            attr_strs = [f"{name}={value:.2f}" if isinstance(value, float) else f"{name}={value}"
                         for name, value in assigned_attrs]
            details += f", Attrib: {', '.join(attr_strs)}"

        self._trace('departure', entity, details=details)

        # Log disposal
        if self.event_logger:
            self.event_logger.log_event(
                case_id=entity.id,
                activity="Discharge",
                timestamp=self.env.now,
                lifecycle='complete',
                system_time=system_time
            )

        # Entity is disposed - no further processing
        yield self.env.timeout(0)

    def get_average_system_time(self):
        """Get average system time for disposed entities."""
        if self.entities_disposed > 0:
            return self.total_system_time / self.entities_disposed
        return 0.0



# ======================================================
# FILE: core\simulation_observer.py
# ======================================================

# =============================================================================
# FILE: core/simulation_observer.py
# =============================================================================
"""
Generic Observer System for Computing Model Variables

DESIGN PRINCIPLES:
1. Keep simulation blocks generic and reusable
2. Separate concerns: blocks handle flow, observers handle metrics
3. Use event-driven architecture (observer pattern)
4. Easy to add/remove observers without touching block code

USAGE:
    observer = SimulationObserver(model)
    observer.on_entity_disposed(block_name='ChamadaBloqueada', 
                                callback=count_lost_calls)
"""


class ObservableEvent(Enum):
    """Types of observable simulation events."""
    ENTITY_CREATED = "entity_created"
    ENTITY_MOVED = "entity_moved"
    ENTITY_DISPOSED = "entity_disposed"
    RESOURCE_SEIZED = "resource_seized"
    RESOURCE_RELEASED = "resource_released"
    DECISION_MADE = "decision_made"
    ACTIVITY_START = "activity_start"
    ACTIVITY_COMPLETE = "activity_complete"


@dataclass
class ObservationRule:
    """Rule for observing specific events."""
    event_type: ObservableEvent
    callback: Callable
    block_filter: Optional[str] = None  # Specific block name
    route_filter: Optional[str] = None  # Specific decision route
    condition: Optional[Callable] = None  # Custom filter function


class SimulationObserver:
    """
    Observes simulation events and updates model variables.

    This class wraps simulation blocks to intercept events WITHOUT
    modifying the original block code.

    Example:
        observer = SimulationObserver(model)

        # Count lost calls when disposed to specific block
        def count_lost_call(entity, block_name, time):
            tracker = model.variable_tracker
            current = tracker.get_current('num_chamadas_perdidas')
            tracker.update('num_chamadas_perdidas', time, current + 1)

        observer.on_entity_disposed(
            block_name='ChamadaBloqueada',
            callback=count_lost_call
        )
    """

    def __init__(self, model):
        """
        Initialize observer.

        Args:
            model: SimulationModel instance
        """
        self.model = model
        self.rules: List[ObservationRule] = []
        self._wrapped_blocks = set()

    def on_entity_created(self, callback: Callable, block_name: Optional[str] = None):
        """
        Observe entity creation events.

        Args:
            callback: Function(entity, block_name, time)
            block_name: Specific CreateBlock to observe (None = all)
        """
        rule = ObservationRule(
            event_type=ObservableEvent.ENTITY_CREATED,
            callback=callback,
            block_filter=block_name
        )
        self.rules.append(rule)
        self._wrap_blocks_if_needed()

    def on_entity_disposed(self, callback: Callable, block_name: Optional[str] = None,
                           condition: Optional[Callable] = None):
        """
        Observe entity disposal events.

        Args:
            callback: Function(entity, block_name, time)
            block_name: Specific DisposeBlock to observe (None = all)
            condition: Function(entity) -> bool to filter entities

        Example:
            # Count only high-priority disposals
            observer.on_entity_disposed(
                callback=count_vip,
                condition=lambda e: e.priority == 0
            )
        """
        rule = ObservationRule(
            event_type=ObservableEvent.ENTITY_DISPOSED,
            callback=callback,
            block_filter=block_name,
            condition=condition
        )
        self.rules.append(rule)
        self._wrap_blocks_if_needed()

    def on_decision_made(self, callback: Callable, block_name: Optional[str] = None,
                         route_name: Optional[str] = None):
        """
        Observe decision routing events.

        Args:
            callback: Function(entity, block_name, route_taken, time)
            block_name: Specific DecideBlock to observe (None = all)
            route_name: Specific route to observe (None = all routes)

        Example:
            # Count emergency route usage
            observer.on_decision_made(
                block_name='TriageDecision',
                route_name='Emergency',
                callback=count_emergency
            )
        """
        rule = ObservationRule(
            event_type=ObservableEvent.DECISION_MADE,
            callback=callback,
            block_filter=block_name,
            route_filter=route_name
        )
        self.rules.append(rule)
        self._wrap_blocks_if_needed()

    def on_activity_complete(self, callback: Callable, block_name: Optional[str] = None):
        """
        Observe activity completion events.

        Args:
            callback: Function(entity, block_name, service_time, time)
            block_name: Specific ProcessBlock to observe (None = all)
        """
        rule = ObservationRule(
            event_type=ObservableEvent.ACTIVITY_COMPLETE,
            callback=callback,
            block_filter=block_name
        )
        self.rules.append(rule)
        self._wrap_blocks_if_needed()

    def _wrap_blocks_if_needed(self):
        """Wrap blocks to intercept events (only once per block)."""

        for block_name, block in self.model.blocks.items():
            if block_name in self._wrapped_blocks:
                continue

            # Wrap CreateBlocks
            if isinstance(block, CreateBlock):
                self._wrap_create_block(block)

            # Wrap DisposeBlocks
            elif isinstance(block, DisposeBlock):
                self._wrap_dispose_block(block)

            # Wrap DecideBlocks
            elif isinstance(block, DecideBlock):
                self._wrap_decide_block(block)

            # Wrap ProcessBlocks
            elif isinstance(block, (ProcessBlock, MultiProcessBlock)):
                self._wrap_process_block(block)

            self._wrapped_blocks.add(block_name)

    def _wrap_create_block(self, block):
        """Wrap CreateBlock to observe entity creation."""
        original_gen = block._generation_process

        def wrapped_generator():
            for item in original_gen():
                # Entity was just created
                if hasattr(block, 'entities_created') and block.entities_created > 0:
                    entity_num = block.entities_created - 1
                    entity_id = f"{block.entity_prefix}_{entity_num}"

                    # Reconstruct entity (we don't have direct access)
                    # This is a limitation - we trigger callbacks based on count
                    self._trigger_event(
                        ObservableEvent.ENTITY_CREATED,
                        block_name=block.name,
                        entity=None,  # We don't have entity object here
                        entity_id=entity_id,
                        time=self.model.env.now
                    )

                yield item

        block._generation_process = wrapped_generator

    def _wrap_dispose_block(self, block):
        """Wrap DisposeBlock to observe entity disposal."""
        original_process = block.process_entity

        def wrapped(entity):
            # Trigger callbacks BEFORE disposal
            self._trigger_event(
                ObservableEvent.ENTITY_DISPOSED,
                block_name=block.name,
                entity=entity,
                time=self.model.env.now
            )

            # Continue normal processing
            yield from original_process(entity)

        block.process_entity = wrapped

    def _wrap_decide_block(self, block):
        """Wrap DecideBlock to observe routing decisions."""
        original_process = block.process_entity

        def wrapped(entity):
            # Store original route history length
            original_history_len = len(entity.route_history)

            # Process normally
            yield from original_process(entity)

            # Detect which route was taken
            decision_attr = f"{block.name}_decision"
            route_taken = entity.get_attribute(decision_attr, None)

            if route_taken:
                self._trigger_event(
                    ObservableEvent.DECISION_MADE,
                    block_name=block.name,
                    entity=entity,
                    route_taken=route_taken,
                    time=self.model.env.now
                )

        block.process_entity = wrapped

    def _wrap_process_block(self, block):
        """Wrap ProcessBlock to observe activity completion."""
        original_log_complete = block.log_complete

        def wrapped_log_complete(entity, resource_name=None):
            # Get service time
            service_time = entity.get_attribute(
                f"{block.name}_service_time", 0)

            # Trigger callbacks
            self._trigger_event(
                ObservableEvent.ACTIVITY_COMPLETE,
                block_name=block.name,
                entity=entity,
                service_time=service_time,
                time=self.model.env.now
            )

            # Continue normal logging
            original_log_complete(entity, resource_name)

        block.log_complete = wrapped_log_complete

    def _trigger_event(self, event_type: ObservableEvent, **kwargs):
        """Trigger all callbacks matching the event."""
        block_name = kwargs.get('block_name')
        entity = kwargs.get('entity')
        time = kwargs.get('time')

        for rule in self.rules:
            # Check event type
            if rule.event_type != event_type:
                continue

            # Check block filter
            if rule.block_filter and rule.block_filter != block_name:
                continue

            # Check route filter (for decisions)
            if event_type == ObservableEvent.DECISION_MADE:
                route_taken = kwargs.get('route_taken')
                if rule.route_filter and rule.route_filter != route_taken:
                    continue

            # Check custom condition
            if rule.condition and entity:
                if not rule.condition(entity):
                    continue

            # Execute callback
            try:
                if event_type == ObservableEvent.ENTITY_CREATED:
                    rule.callback(kwargs.get('entity_id'), block_name, time)
                elif event_type == ObservableEvent.ENTITY_DISPOSED:
                    rule.callback(entity, block_name, time)
                elif event_type == ObservableEvent.DECISION_MADE:
                    rule.callback(entity, block_name,
                                  kwargs.get('route_taken'), time)
                elif event_type == ObservableEvent.ACTIVITY_COMPLETE:
                    rule.callback(entity, block_name,
                                  kwargs.get('service_time'), time)
            except Exception as e:
                print(f"Error in observer callback: {e}")


# # =============================================================================
# # USAGE EXAMPLES
# # =============================================================================
# def example_call_center_with_observer():
#     """Example: Call center with lost call tracking using observer."""

#     from core.simulation_model import SimulationModel
#     from core.entity import EventLogger
#     from blocks.create_block import CreateBlock
#     from blocks.process_block import ProcessBlock
#     from blocks.dispose_block import DisposeBlock
#     from blocks.decide_block import DecideBlock
#     import random

#     # Build model (generic blocks - no modifications)
#     model = SimulationModel()
#     event_logger = EventLogger()

#     # Add model variables
#     model.add_model_variable('num_chamadas_perdidas', 0,
#                             'Número de chamadas perdidas', 'unidades')
#     model.add_model_variable('percentual_chamadas_perdidas', 0,
#                             'Percentual de chamadas perdidas', '%',
#                             calculate_fn=lambda m: (
#                                 m.variable_tracker.get_current('num_chamadas_perdidas') /
#                                 max(1, m.entity_count) * 100
#                             ))

#     # Create resources and blocks (GENERIC - no special logic)
#     troncos = model.add_resource("Troncos", 30, "regular")

#     chegadas = CreateBlock("ChegadasChamadas", model.env,
#                           inter_arrival_time=lambda: random.expovariate(1/15),
#                           entity_prefix="Chamada",
#                           max_arrivals=1000,
#                           event_logger=event_logger)

#     decide = DecideBlock("DecideTronco", model.env,
#                         decision_type="condition_generic",
#                         event_logger=event_logger)

#     atendimento = ProcessBlock("Atendimento", model.env,
#                               resource=troncos,
#                               delay_time=lambda: random.expovariate(1/2),
#                               event_logger=event_logger)
#     atendimento.set_resource_name('Troncos')

#     dispose_atendida = DisposeBlock("ChamadaAtendida", model.env, event_logger)
#     dispose_bloqueada = DisposeBlock("ChamadaBloqueada", model.env, event_logger)

#     # Add blocks
#     for block in [chegadas, decide, atendimento, dispose_atendida, dispose_bloqueada]:
#         model.add_block(block)

#     # Connect flow
#     chegadas.connect_to(decide)
#     atendimento.connect_to(dispose_atendida)

#     # Add routes
#     decide.add_route("Atender", atendimento,
#                     condition_generic=lambda e, ctx: (
#                         ctx['resources']['Troncos'].count < ctx['resources']['Troncos'].capacity
#                     ))
#     decide.add_route("Bloquear", dispose_bloqueada,
#                     condition_generic=lambda e, ctx: (
#                         ctx['resources']['Troncos'].count >= ctx['resources']['Troncos'].capacity
#                     ))

#     # ✅ CREATE OBSERVER (separate from blocks)
#     observer = SimulationObserver(model)

#     # ✅ DEFINE CALLBACK: What to do when call is lost
#     def count_lost_call(entity, block_name, time):
#         """Called when entity disposed to ChamadaBloqueada."""
#         tracker = model.variable_tracker
#         current = tracker.get_current('num_chamadas_perdidas')
#         tracker.update('num_chamadas_perdidas', time, current + 1)
#         tracker.update('percentual_chamadas_perdidas')  # Auto-calculate
#         print(f"[{time:.2f}] Chamada {entity.id} PERDIDA - Total: {current + 1}")

#     # ✅ ATTACH OBSERVER: Monitor specific dispose block
#     observer.on_entity_disposed(
#         block_name='ChamadaBloqueada',
#         callback=count_lost_call
#     )

#     # Run simulation
#     model.run_simulation(until=480, seed=123)

#     # Print results
#     tracker = model.variable_tracker
#     print(f"\n{'='*60}")
#     print(f"RESULTADOS:")
#     print(f"Total de chamadas: {model.entity_count}")
#     print(f"Chamadas perdidas: {tracker.get_final('num_chamadas_perdidas')}")
#     print(f"Percentual perdido: {tracker.get_final('percentual_chamadas_perdidas'):.2f}%")
#     print(f"{'='*60}")

#     return model


# def example_hospital_with_multiple_observers():
#     """Example: Hospital with multiple metric tracking."""

#     from core.simulation_model import SimulationModel

#     model = SimulationModel()

#     # Add multiple variables
#     model.add_model_variable('num_emergency_cases', 0, 'Emergency cases', 'unidades')
#     model.add_model_variable('num_long_waits', 0, 'Long wait times (>30min)', 'unidades')
#     model.add_model_variable('avg_service_time', 0, 'Average service time', 'minutes')

#     # ... build model with generic blocks ...

#     # Create observer
#     observer = SimulationObserver(model)

#     # Observer 1: Count emergency routing
#     def count_emergency(entity, block_name, route_taken, time):
#         if route_taken == 'Emergency':
#             tracker = model.variable_tracker
#             current = tracker.get_current('num_emergency_cases')
#             tracker.update('num_emergency_cases', time, current + 1)

#     observer.on_decision_made(
#         block_name='TriageDecision',
#         callback=count_emergency
#     )

#     # Observer 2: Track long wait times
#     def check_long_wait(entity, block_name, service_time, time):
#         queue_time = entity.get_attribute('queue_time', 0)
#         if queue_time > 30:
#             tracker = model.variable_tracker
#             current = tracker.get_current('num_long_waits')
#             tracker.update('num_long_waits', time, current + 1)

#     observer.on_activity_complete(
#         block_name='Treatment',
#         callback=check_long_wait
#     )

#     # Observer 3: Update rolling average service time
#     def update_avg_service_time(entity, block_name, service_time, time):
#         tracker = model.variable_tracker
#         # Simple exponential moving average
#         current_avg = tracker.get_current('avg_service_time')
#         alpha = 0.1  # Smoothing factor
#         new_avg = alpha * service_time + (1 - alpha) * current_avg
#         tracker.update('avg_service_time', time, new_avg)

#     observer.on_activity_complete(callback=update_avg_service_time)

#     return model, observer


# # =============================================================================
# # INTEGRATION WITH YOUR MODEL
# # =============================================================================
# def your_model_integration_example():
#     """How to add observer to your existing model."""

#     code_example = '''
# # In your build_ex3_model() function:

# def build_ex3_model(final_simulation_time=None, event_logger=None):
#     # ... existing model building code (UNCHANGED) ...

#     model = SimulationModel()

#     # Add variables
#     model.add_model_variable('num_chamadas_perdidas', 0,
#                             'Chamadas perdidas', 'unidades')
#     model.add_model_variable('percentual_chamadas_perdidas', 0,
#                             'Percentual perdidas', '%',
#                             calculate_fn=lambda m: (
#                                 m.variable_tracker.get_current('num_chamadas_perdidas') /
#                                 max(1, m.entity_count) * 100
#                             ))

#     # ... create all blocks (GENERIC - no changes) ...

#     # ✅ ADD: Create observer (AFTER all blocks are added)
#     observer = SimulationObserver(model)

#     # ✅ ADD: Define callback
#     def count_lost_call(entity, block_name, time):
#         tracker = model.variable_tracker
#         current = tracker.get_current('num_chamadas_perdidas')
#         tracker.update('num_chamadas_perdidas', time, current + 1)
#         tracker.update('percentual_chamadas_perdidas')

#     # ✅ ADD: Attach observer
#     observer.on_entity_disposed(
#         block_name='ChamadaBloqueada',
#         callback=count_lost_call
#     )

#     # Store observer in model for later access (optional)
#     model.observer = observer

#     return model
#     '''

#     return code_example


# if __name__ == "__main__":
#     print("="*70)
#     print("SIMULATION OBSERVER SYSTEM")
#     print("="*70)
#     print("\n✅ BENEFITS:")
#     print("  1. Keeps simulation blocks GENERIC and reusable")
#     print("  2. Separates metric computation from simulation logic")
#     print("  3. Easy to add/remove observers without touching blocks")
#     print("  4. Follows observer pattern (event-driven)")
#     print("  5. Can attach multiple observers to same event")

#     print("\n📋 USAGE:")
#     print("  observer = SimulationObserver(model)")
#     print("  observer.on_entity_disposed(block_name='LostSales', callback=count_loss)")

#     print("\n🎯 SUPPORTED EVENTS:")
#     print("  - on_entity_created()")
#     print("  - on_entity_disposed()")
#     print("  - on_decision_made()")
#     print("  - on_activity_complete()")

#     print("\n" + "="*70)

#     # Run example
#     print("\nRunning call center example...")
#     model = example_call_center_with_observer()



# ======================================================
# FILE: blocks\create_block.py
# ======================================================

# =====================================================================
# FILE: blocks/create_block.py
# =====================================================================

# =====================================================================
# FILE: blocks/create_block.py
# =====================================================================
class CreateBlock(BaseBlock):
    """CREATE block - generates entities into the system."""

    def __init__(self, name: str, env: simpy.Environment,
                 inter_arrival_time: Callable[[], float],
                 entity_prefix: str = "Entity",
                 max_arrivals: Optional[int] = None,
                 first_creation: float = 0.0,
                 priority_generator: Optional[Callable[[], int]] = None,
                 event_logger: EventLogger = None):
        # Call parent class init FIRST with event_logger
        super().__init__(name, env, event_logger)
        # NOW we can safely set other attributes
        self.inter_arrival_time = inter_arrival_time
        self.entity_prefix = entity_prefix
        self.max_arrivals = max_arrivals
        self.first_creation = first_creation
        self.entities_created = 1
        self.priority_generator = priority_generator

    def start_generation(self):
        """Start the entity generation process."""
        return self.env.process(self._generation_process())

    def _generation_process(self):
        """Internal process for generating entities."""
        if self.first_creation > 0:
            yield self.env.timeout(self.first_creation)

        while True:
            if self.max_arrivals and self.entities_created > self.max_arrivals:
                break

            entity = Entity(
                id=f"{self.entity_prefix}_{self.entities_created}",
                creation_time=self.env.now,
                data={},
                route_history=[],
                priority=self.priority_generator() if self.priority_generator else 0
            )

            self.entities_created += 1
            entity.route_history.append(self.name)

            # # ✅ ADD THIS LINE: Apply configured attributes to the entity
            # self._apply_attributes(entity)

            # # NEW: Trace entity generation
            # self._trace('arrival', entity, details=f"entity created, priority={entity.priority}")

            # ✅ MODIFIED: Capture assigned attributes at creation
            assigned_attrs = self._apply_attributes(entity)

            # ✅ MODIFIED: Include initial attributes in trace
            details = f"entity created, priority={entity.priority}"

            if assigned_attrs:
                attr_strs = []
                for name, value in assigned_attrs:
                    if isinstance(value, float):
                        attr_strs.append(f"{name}={value:.2f}")
                    else:
                        attr_strs.append(f"{name}={value}")
                details += f", Attrib: {', '.join(attr_strs)}"

            self._trace('generate', entity, details=details)

            # Log creation as an event
            if self.event_logger:
                self.event_logger.log_event(
                    case_id=entity.id,
                    activity="Arrival",
                    timestamp=self.env.now,
                    lifecycle='complete',
                    priority=entity.priority
                )

            if self.next_block:
                self.env.process(self.next_block.process_entity(entity))

            yield self.env.timeout(self.inter_arrival_time())

    def process_entity(self, entity: Entity):
        """CREATE blocks don't process incoming entities."""
        raise NotImplementedError(
            "CREATE blocks generate entities, they don't process them")



# ======================================================
# FILE: analytics\metrics.py
# ======================================================

# =====================================================================
# FILE: analytics/metrics.py
# =====================================================================

# =====================================================================
# FILE: analytics/metrics.py
# =====================================================================
class MetricsCollector:
    """Collects and calculates metrics from a completed simulation."""

    def __init__(self, model):
        """
        Initialize metrics collector.

        Args:
            model: SimulationModel instance with completed simulation
        """
        self.model = model

    def get_entity_metrics_summary(self) -> Dict[str, Any]:
        """
        Calculate entity-level metrics (time in system, by activity).

        Returns:
            Dictionary containing system time and per-activity metrics
        """
        if not self.model.dispose_blocks:
            return {'tempo_medio_sistema': 0, 'atividades': {}}

        # Collect only post-warm-up disposed entities
        post_warmup_entities = [
            e for dispose_block in self.model.dispose_blocks
            for e in dispose_block.disposed_entities
            if e.get_attribute('disposal_time', 0) >= self.model.warm_up_period
        ]

        if not post_warmup_entities:
            return {'tempo_medio_sistema': 0, 'atividades': {}}

        # Calculate system time
        system_times = [entity.get_attribute('system_time', 0)
                        for entity in post_warmup_entities]

        # Group metrics by activity
        activity_queue_times = {}
        activity_service_times = {}
        activity_system_times = {}

        for entity in post_warmup_entities:
            for key, value in entity.data.items():
                # Skip None or nan values
                if value is None or (isinstance(value, float) and math.isnan(value)):
                    continue

                if key.endswith('_queue_time'):
                    activity_name = key.replace('_queue_time', '')
                    if activity_name not in activity_queue_times:
                        activity_queue_times[activity_name] = []
                    activity_queue_times[activity_name].append(value)

                elif key.endswith('_service_time'):
                    activity_name = key.replace('_service_time', '')
                    if activity_name not in activity_service_times:
                        activity_service_times[activity_name] = []
                    activity_service_times[activity_name].append(value)

        # Calculate system time for each activity
        all_activities = set(list(activity_queue_times.keys()) +
                             list(activity_service_times.keys()))

        for activity_name in all_activities:
            queue_times = activity_queue_times.get(activity_name, [])
            service_times = activity_service_times.get(activity_name, [])

            activity_system_times[activity_name] = []
            min_length = min(len(queue_times), len(service_times))

            for i in range(min_length):
                system_time = queue_times[i] + service_times[i]
                activity_system_times[activity_name].append(system_time)

        # Build summary
        summary = {
            'tempo_medio_sistema': statistics.mean(system_times) if system_times else 0,
            'atividades': {}
        }

        for activity_name in all_activities:
            qt = activity_queue_times.get(activity_name, [])
            st = activity_service_times.get(activity_name, [])
            sys_t = activity_system_times.get(activity_name, [])

            summary['atividades'][activity_name] = {
                'tempo_medio_fila': statistics.mean(qt) if len(qt) > 0 else 0,
                'tempo_medio_atendimento': statistics.mean(st) if len(st) > 0 else 0,
                'tempo_medio_sistema': statistics.mean(sys_t) if len(sys_t) > 0 else 0
            }

        return summary

    def get_resource_metrics_summary(self) -> Dict[str, Any]:
        """
        Calculate resource-level metrics (utilization, queue lengths).

        Returns:
            Dictionary mapping resource names to their metrics
        """

        summary = {}

        # Group ProcessBlocks by resource
        resource_blocks = self._group_blocks_by_resource()

        for resource_name, blocks in resource_blocks.items():
            if resource_name in self.model.resources:
                resource = self.model.resources[resource_name]
                resource_obj = resource

                # Combine data from all blocks using this resource
                combined_data = []
                max_queue_length = 0
                max_in_service = 0

                for block in blocks:
                    if isinstance(block, ProcessBlock):
                        combined_data.extend(block.resource_data)
                        max_queue_length = max(
                            max_queue_length, block.max_queue_length)
                        max_in_service = max(
                            max_in_service, block.max_in_service)
                    elif isinstance(block, MultiProcessBlock):
                        if resource_obj in block.resource_data:
                            combined_data.extend(
                                block.resource_data[resource_obj])
                            metrics = block.max_metrics[resource_obj]
                            max_queue_length = max(max_queue_length,
                                                   metrics['max_queue_length'])
                            max_in_service = max(max_in_service,
                                                 metrics['max_in_service'])

                # Deduplicate data points by time
                combined_data = self._deduplicate_resource_data(combined_data)

                # Calculate metrics
                if combined_data:
                    avg_queue = self._calculate_time_weighted_avg(
                        combined_data, lambda x: x[2])
                    avg_in_service = self._calculate_time_weighted_avg(
                        combined_data, lambda x: x[1])
                    utilization = (avg_in_service / resource.capacity
                                   if resource.capacity > 0 else 0)

                    busy_time, idle_time = self._calculate_busy_idle_time(
                        combined_data, resource)
                else:
                    avg_queue = 0
                    avg_in_service = 0
                    utilization = 0
                    busy_time = 0
                    idle_time = self.model.env.now - self.model.warm_up_period

                effective_time = self.model.env.now - self.model.warm_up_period

                summary[resource_name] = {
                    'numero_medio_fila': avg_queue,
                    'numero_medio_atendimento': avg_in_service,
                    'numero_medio_sistema': avg_queue + avg_in_service,
                    'taxa_utilizacao': utilization,
                    'maximo_fila': max_queue_length,
                    'maximo_atendimento': max_in_service,
                    'maximo_sistema': max_queue_length + max_in_service,
                    'tempo_ocupado': busy_time,
                    'tempo_ocioso': idle_time,
                    'percentual_ocupacao': ((busy_time / effective_time * 100)
                                            if effective_time > 0 else 0),
                    'percentual_ociosidade': ((idle_time / effective_time * 100)
                                              if effective_time > 0 else 0)
                }

        return summary

    def _group_blocks_by_resource(self) -> Dict[str, List]:
        """Group ProcessBlocks by the resources they use."""

        resource_blocks = {}

        for block in self.model.blocks.values():
            if isinstance(block, ProcessBlock):
                resource_name = self._find_resource_name(block.resource)
                if resource_name:
                    if resource_name not in resource_blocks:
                        resource_blocks[resource_name] = []
                    resource_blocks[resource_name].append(block)

            elif isinstance(block, MultiProcessBlock):
                for resource in block.resource_requirements.keys():
                    resource_name = self._find_resource_name(resource)
                    if resource_name:
                        if resource_name not in resource_blocks:
                            resource_blocks[resource_name] = []
                        resource_blocks[resource_name].append(block)

        return resource_blocks

    def _find_resource_name(self, resource_obj) -> str:
        """Find resource name from resource object."""
        for res_name, res in self.model.resources.items():
            if res == resource_obj:
                return res_name
        return None

    def _deduplicate_resource_data(self, data: List[Tuple]) -> List[Tuple]:
        """Deduplicate resource data points by timestamp."""
        if not data:
            return []

        data.sort(key=lambda x: x[0])

        unique_data = []
        for timestamp, group in groupby(data, key=lambda x: x[0]):
            group_list = list(group)
            unique_data.append(group_list[-1])  # Keep last state at timestamp

        return unique_data

    def _calculate_time_weighted_avg(self, data: List[Tuple],
                                     extractor: Callable) -> float:
        """Calculate time-weighted average from resource data."""
        if not data:
            return 0

        data.sort(key=lambda x: x[0])
        effective_time = self.model.env.now - self.model.warm_up_period

        if effective_time <= 0:
            return 0

        area = 0
        prev_time = self.model.warm_up_period

        # Find initial value at warm-up boundary
        pre_warmup_data = [point for point in data
                           if point[0] <= self.model.warm_up_period]
        post_warmup_data = [point for point in data
                            if point[0] > self.model.warm_up_period]

        if pre_warmup_data:
            prev_value = extractor(pre_warmup_data[-1])
        else:
            prev_value = 0

        # Process all post-warmup data points
        for point in post_warmup_data:
            time = point[0]
            area += prev_value * (time - prev_time)
            prev_time = time
            prev_value = extractor(point)

        # Add final interval
        area += prev_value * (self.model.env.now - prev_time)

        return area / effective_time if effective_time > 0 else 0

    def _calculate_busy_idle_time(self, data: List[Tuple],
                                  resource) -> Tuple[float, float]:
        """Calculate busy and idle time for a resource."""
        busy_time = 0
        idle_time = 0
        prev_time = self.model.warm_up_period
        prev_count = 0

        post_warmup_data = [p for p in data if p[0]
                            >= self.model.warm_up_period]

        if post_warmup_data:
            prev_count = post_warmup_data[0][1]
            prev_time = post_warmup_data[0][0]

            for time, count, qlen in post_warmup_data[1:]:
                time_interval = time - prev_time
                if prev_count > 0:
                    busy_time += time_interval
                else:
                    idle_time += time_interval
                prev_time = time
                prev_count = count

            final_interval = self.model.env.now - prev_time
            if prev_count > 0:
                busy_time += final_interval
            else:
                idle_time += final_interval
        else:
            idle_time = self.model.env.now - self.model.warm_up_period

        return busy_time, idle_time



# ======================================================
# FILE: analytics\wip_metrics.py
# ======================================================

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

    # def _build_wip_timeline(self) -> List[Tuple[float, int]]:
    #     """
    #     Build WIP timeline from entity creation and disposal events.

    #     Returns:
    #         List of (time, wip_count) tuples
    #     """
    #     events = []

    #     # Add creation events (+1 to WIP)
    #     for create_block in self.model.create_blocks:
    #         # Entities are created at specific times based on inter-arrival
    #         # We need to reconstruct this from disposed entities
    #         pass

    #     # Add disposal events (-1 from WIP)
    #     for dispose_block in self.model.dispose_blocks:
    #         for entity in dispose_block.disposed_entities:
    #             creation_time = entity.creation_time
    #             disposal_time = entity.get_attribute('disposal_time', self.model.env.now)

    #             events.append((creation_time, +1))  # Entity enters system
    #             events.append((disposal_time, -1))  # Entity exits system

    #     # Sort events by time
    #     events.sort(key=lambda x: x[0])

    #     # Build timeline
    #     timeline = []
    #     current_wip = 0

    #     for time, change in events:
    #         current_wip += change
    #         timeline.append((time, current_wip))

    #     return timeline

    def _build_wip_timeline(self) -> List[Tuple[float, int]]:
        """
        Build WIP timeline from entity creation and disposal events.

        Returns:
            List of (time, wip_count) tuples
        """
        # Get event_logger
        event_logger = None
        for block in self.model.blocks.values():
            if hasattr(block, 'event_logger') and block.event_logger is not None:
                event_logger = block.event_logger
                break

        events = []
        if event_logger is None:
            # Fall back to disposed entities
            total_disposed = sum(
                b.entities_disposed for b in self.model.dispose_blocks)
            if total_disposed == 0:
                total_created = sum(
                    c.entities_created for c in self.model.create_blocks)
                timeline = [(0.0, 0)]
                if total_created > 0:
                    timeline.append((self.model.env.now, total_created))
                return timeline
            else:
                for dispose_block in self.model.dispose_blocks:
                    for entity in dispose_block.disposed_entities:
                        creation_time = entity.creation_time
                        disposal_time = entity.get_attribute(
                            'disposal_time', self.model.env.now)
                        events.append((creation_time, +1))
                        events.append((disposal_time, -1))
        else:
            # Use event log
            df = event_logger.get_dataframe()
            grouped = df[df['activity'].isin(
                ['Arrival', 'Discharge'])].groupby('case_id')
            for case_id, case_df in grouped:
                arrival_row = case_df[case_df['activity'] == 'Arrival']
                discharge_row = case_df[case_df['activity'] == 'Discharge']
                if not arrival_row.empty:
                    arrival_time = arrival_row['timestamp'].values[0]
                    events.append((arrival_time, +1))
                    if not discharge_row.empty:
                        discharge_time = discharge_row['timestamp'].values[0]
                        events.append((discharge_time, -1))

        # Sort events
        events.sort(key=lambda x: (x[0], x[1]))

        # Build timeline
        timeline = []
        current_wip = 0
        for time, change in events:
            current_wip += change
            timeline.append((time, current_wip))

        # Add final point if needed
        now = self.model.env.now
        if timeline and timeline[-1][0] < now:
            timeline.append((now, current_wip))
        elif not timeline:
            timeline = [(0.0, 0), (now, 0)]

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

    # def get_system_time_summary(self) -> Dict[str, Any]:
    #     """
    #     Calculate total time in system statistics.

    #     Returns:
    #         Dictionary with system time metrics
    #     """
    #     if not self.model.dispose_blocks:
    #         return self._empty_system_time_summary()

    #     # Get post-warm-up entities
    #     post_warmup_entities = [
    #         e for dispose_block in self.model.dispose_blocks
    #         for e in dispose_block.disposed_entities
    #         if e.get_attribute('disposal_time', 0) >= self.model.warm_up_period
    #     ]

    #     if not post_warmup_entities:
    #         return self._empty_system_time_summary()

    #     # Calculate system times
    #     system_times = [e.get_attribute('system_time', 0) for e in post_warmup_entities]

    #     return {
    #         'average_system_time': np.mean(system_times),
    #         'std_system_time': np.std(system_times),
    #         'min_system_time': np.min(system_times),
    #         'max_system_time': np.max(system_times),
    #         'median_system_time': np.median(system_times),
    #         'num_entities': len(system_times)
    #     }

    def get_system_time_summary(self) -> Dict[str, Any]:
        """
        Calculate total time in system statistics.

        Returns:
            Dictionary with system time metrics
        """
        if not self.model.dispose_blocks:
            return self._empty_system_time_summary()

        # Calculate total disposed entities
        total_disposed = sum(len(dispose_block.disposed_entities)
                             for dispose_block in self.model.dispose_blocks)

        if total_disposed > 0:
            # Original logic for when there are disposed entities
            post_warmup_entities = [
                e for dispose_block in self.model.dispose_blocks
                for e in dispose_block.disposed_entities
                if e.get_attribute('disposal_time', 0) >= self.model.warm_up_period
            ]

            if not post_warmup_entities:
                return self._empty_system_time_summary()

            system_times = [e.get_attribute('system_time', 0)
                            for e in post_warmup_entities]
        else:
            # Find event_logger
            event_logger = None
            for block in self.model.blocks.values():
                if hasattr(block, 'event_logger') and block.event_logger is not None:
                    event_logger = block.event_logger
                    break

            if event_logger is None:
                return self._empty_system_time_summary()

            # Use event log to get earliest timestamp per case_id as entry time
            df = event_logger.get_dataframe()

            if df.empty:
                return self._empty_system_time_summary()

            grouped = df.groupby('case_id')['timestamp']
            min_times = grouped.min()

            post_warmup_min_times = min_times[min_times >=
                                              self.model.warm_up_period]

            if post_warmup_min_times.empty:
                return self._empty_system_time_summary()

            now = self.model.env.now
            system_times = [now - t for t in post_warmup_min_times]

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

    # def plot_wip_over_time(self):
    #     """Plot WIP evolution over time."""
    #     wip_summary = self.get_wip_summary()
    #     timeline = wip_summary['wip_timeline']

    #     if not timeline:
    #         print("No WIP data available to plot.")
    #         return

    #     # --- START MODIFICATION ---
    #     final_time = self.model.env.now
    #     # 1. Ensure the timeline extends to the end of the simulation for plotting
    #     if timeline[-1][0] < final_time:
    #         # Append a point at the final time with the final WIP count
    #         final_wip_count = timeline[-1][1]
    #         timeline.append((final_time, final_wip_count))
    #     # --- END MODIFICATION ---

    #     times = [t for t, _ in timeline]
    #     wips = [w for _, w in timeline]

    #     fig, ax = plt.subplots(figsize=(12, 6))

    #     # Plot as step function
    #     ax.step(times, wips, where='post', linewidth=2, color='steelblue', label='WIP')

    #     # Add average line
    #     ax.axhline(y=wip_summary['average_wip'], color='red', linestyle='--',
    #               linewidth=2, label=f"Average WIP: {wip_summary['average_wip']:.2f}")

    #     # Mark warm-up period
    #     if self.model.warm_up_period > 0:
    #         ax.axvline(x=self.model.warm_up_period, color='orange', linestyle='--',
    #                   linewidth=2, label=f"Warm-up end (t={self.model.warm_up_period})")
    #         ax.axvspan(0, self.model.warm_up_period, alpha=0.2, color='orange')

    #     ax.set_xlabel('Simulation Time', fontsize=12, fontweight='bold')
    #     ax.set_ylabel('Work in Process (WIP)', fontsize=12, fontweight='bold')
    #     ax.set_title('Work in Process Over Time', fontsize=14, fontweight='bold')
    #     ax.legend(loc='best', framealpha=0.9)
    #     ax.grid(True, alpha=0.3)

    #     plt.tight_layout()
    #     plt.show()

    def plot_wip_over_time(self):
        """Plot WIP evolution over time."""
        wip_summary = self.get_wip_summary()
        timeline = wip_summary['wip_timeline']

        if not timeline:
            print("No WIP data available to plot.")
            return

        times = [t for t, _ in timeline]
        wips = [w for _, w in timeline]

        _fig, ax = plt.subplots(figsize=(12, 6))

        # Plot as step function
        ax.step(times, wips, where='post', linewidth=2,
                color='steelblue', label='WIP')

        # Add average line
        ax.axhline(y=wip_summary['average_wip'], color='red', linestyle='--',
                   linewidth=2, label=f"Average WIP: {wip_summary['average_wip']:.2f}")

        # Mark warm-up period
        if self.model.warm_up_period > 0:
            ax.axvline(x=self.model.warm_up_period, color='orange', linestyle='--',
                       linewidth=2, label=f"Warm-up end (t={self.model.warm_up_period})")
            ax.axvspan(0, self.model.warm_up_period, alpha=0.2, color='orange')

        # ✅ NEW: Annotate final WIP if > 0
        final_wip = wip_summary['final_wip']
        if final_wip >= 0:
            ax.annotate(
                f'Final WIP: {final_wip}\n(entities still in system)',
                xy=(self.model.env.now, final_wip),
                xytext=(self.model.env.now * 0.8, final_wip * 1.2),
                arrowprops=dict(arrowstyle='->', color='red', lw=2),
                fontsize=10,
                bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.7)
            )

        ax.set_xlabel('Simulation Time', fontsize=12, fontweight='bold')
        ax.set_ylabel('Work in Process (WIP)', fontsize=12, fontweight='bold')
        ax.set_title('Work in Process Over Time',
                     fontsize=14, fontweight='bold')
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

        system_times = [e.get_attribute('system_time', 0)
                        for e in post_warmup_entities]

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

        # Histogram
        ax1.hist(system_times, bins=30, color='skyblue',
                 edgecolor='black', alpha=0.7)
        ax1.axvline(x=np.mean(system_times), color='red', linestyle='--',
                    linewidth=2, label=f'Mean: {np.mean(system_times):.2f}')
        ax1.axvline(x=np.median(system_times), color='green', linestyle='--',
                    linewidth=2, label=f'Median: {np.median(system_times):.2f}')
        ax1.set_xlabel('Total Time in System', fontsize=11, fontweight='bold')
        ax1.set_ylabel('Frequency', fontsize=11, fontweight='bold')
        ax1.set_title('System Time Distribution',
                      fontsize=12, fontweight='bold')
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



# ======================================================
# FILE: analytics\reporting.py
# ======================================================

# =====================================================================
# FILE: analytics/reporting.py
# =====================================================================

# =====================================================================
# FILE: analytics/reporting.py
# =====================================================================
class SimulationReporter:
    """Generates formatted reports from simulation results."""

    def __init__(self, model):
        self.model = model
        self.metrics = MetricsCollector(model)
        self.wip_tracker = None  # NEW: Lazy loaded
        self.HOURS = 60  # Time conversion (base: minutes)
        self.DAYS = 1440
        self.YEARS = 525600

    def _get_wip_tracker(self):
        """Lazy load WIP tracker."""
        if self.wip_tracker is None:
            self.wip_tracker = WIPTracker(self.model)
        return self.wip_tracker

    def _print_wip_metrics(self):
        """Print WIP and system time metrics."""
        wip_tracker = self._get_wip_tracker()

        # WIP metrics
        wip_summary = wip_tracker.get_wip_summary()
        print("\nWORK IN PROCESS (WIP) METRICS:")
        print(f"  Average WIP: {wip_summary['average_wip']:.2f} entities")
        print(f"  Maximum WIP: {wip_summary['max_wip']} entities")
        print(f"  Current WIP: {wip_summary['final_wip']} entities")

        # System time metrics
        system_time_summary = wip_tracker.get_system_time_summary()
        print("\nTOTAL TIME IN SYSTEM:")
        print(
            f"  Average: {system_time_summary['average_system_time']:.2f} time units")
        print(f"  Std Dev: {system_time_summary['std_system_time']:.2f}")
        print(f"  Min: {system_time_summary['min_system_time']:.2f}")
        print(f"  Max: {system_time_summary['max_system_time']:.2f}")
        print(f"  Median: {system_time_summary['median_system_time']:.2f}")
        print(f"  Based on: {system_time_summary['num_entities']} entities")

        # Little's Law verification
        self._verify_littles_law(wip_summary, system_time_summary)

    def _verify_littles_law(self, wip_summary: Dict, system_time_summary: Dict):
        """
        Verify Little's Law: L = λ × W
        Where:
        - L = Average number in system (WIP)
        - λ = Arrival rate (throughput)
        - W = Average time in system
        """
        avg_wip = wip_summary['average_wip']
        avg_system_time = system_time_summary['average_system_time']
        throughput = self.model.overall_throughput

        if throughput > 0 and avg_system_time > 0:
            print("\nLITTLE'S LAW VERIFICATION:")
            print(f"  L (Avg WIP): {avg_wip:.2f}")
            print(
                f"  lambda (Throughput): {throughput:.4f} entities/time unit")
            print(f"  W (Avg Time): {avg_system_time:.2f} time units")

            # Calculate expected WIP using Little's Law
            expected_wip = throughput * avg_system_time
            print(f"  Expected WIP (lambda * W): {expected_wip:.2f}")

            # Calculate percentage difference
            if avg_wip > 0:
                diff_percent = abs(avg_wip - expected_wip) / avg_wip * 100
                print(f"  Difference: {diff_percent:.1f}%")

                if diff_percent < 5:
                    print("  Status: Excellent match (Little's Law verified)")
                elif diff_percent < 10:
                    print("  Status: Good match")
                else:
                    print("  Status: Significant difference (check warm-up period)")

    def print_results(self):
        """Print comprehensive simulation results INCLUDING WIP."""
        print("=" * 60)
        duration_hours = self.model.env.now / self.HOURS
        print(
            f"📊 RESULTADOS DA SIMULACAO (⏳ Duracao: {duration_hours:.0f} horas)")

        if self.model.warm_up_period > 0:
            effective_time = self.model.env.now - self.model.warm_up_period
            print(f"WARM-UP: {self.model.warm_up_period/self.HOURS:.0f} horas | "
                  f"PERIODO DE ESTATISTICAS: {effective_time/self.HOURS:.0f} horas")
        print("=" * 60)

        self._print_stability_results()
        self._print_system_metrics()
        self._print_wip_metrics()  # NEW: Add WIP metrics here
        # self._print_activity_metrics()
        # self._print_resource_metrics()
        # self._print_entity_counts()
        # self._print_block_statistics()
        # self.print_financial_summary() # Print financial balance sheet

    def _print_stability_results(self):
        """Print stability analysis if available."""
        if self.model.stability_result is not None:
            print(
                f"\nINDICE DE ESTABILIDADE: {self.model.stability_result:.2f}")
            if self.model.stability_result > 1.2:
                print("STATUS: Sistema SUPER dimensionado")
            elif self.model.stability_result > 1.05:
                print("STATUS: Sistema estavel")
            elif self.model.stability_result > 0.95:
                print("STATUS: Sistema NO LIMITE")
            elif self.model.stability_result > 0.8:
                print("STATUS: Sistema INSTAVEL")
            else:
                print("STATUS: COLAPSO IMINENTE")

    def _print_system_metrics(self):
        """Print overall system metrics."""
        entity_summary = self.metrics.get_entity_metrics_summary()
        system_time = entity_summary.get('tempo_medio_sistema', 0)

        print(
            f"\n⏰ Tempo medio no sistema: {system_time/self.HOURS:.2f} horas")
        print(f"👥 Total de entidades processadas: {self.model.entity_count}")
        print(f"⚙️  Throughput: {self.model.overall_throughput*self.HOURS:.2f} "
              f"entidades/hora")
        print(f"📋 Recursos ativos: {list(self.model.resources.keys())}")

        if self.model.warm_up_period > 0:
            print(f"\nNOTA: Estatisticas baseadas apenas no periodo pos warm-up")
            print(f"   (t > {self.model.warm_up_period/self.HOURS:.1f} horas)")

    def _print_activity_metrics(self):
        """Print per-activity metrics."""
        entity_summary = self.metrics.get_entity_metrics_summary()
        activities = entity_summary.get('atividades', {})

        if activities:
            print("\n📈 METRICAS DAS ENTIDADES POR ATIVIDADE:")
            for activity_name, metrics in activities.items():
                print(f"  {activity_name}:")
                print(f"    Tempo medio em fila: "
                      f"{metrics['tempo_medio_fila']:.2f}")
                print(f"    Tempo medio de atendimento: "
                      f"{metrics['tempo_medio_atendimento']:.2f}")
                print(f"    Tempo medio no sistema: "
                      f"{metrics['tempo_medio_sistema']:.2f}")

    def _print_resource_metrics(self):
        """Print per-resource metrics with analysis."""

        validator = ResourceValidator(self.model)
        validator.print_resource_summary()

        resource_summary = self.metrics.get_resource_metrics_summary()

        if resource_summary:
            print("\n📈 METRICAS POR RECURSO:")
            for resource_name, metrics in resource_summary.items():
                capacity = self.model.resources[resource_name].capacity
                util = metrics['taxa_utilizacao']

                print(f"  {resource_name} (capacidade: {capacity}):")
                print(f"    Taxa de utilizacao: {util:.2f}")
                print(f"    Tempo ocupado: {metrics['tempo_ocupado']:.2f} "
                      f"({metrics['percentual_ocupacao']:.1f}%)")
                print(f"    Tempo ocioso: {metrics['tempo_ocioso']:.2f} "
                      f"({metrics['percentual_ociosidade']:.1f}%)")
                print(f"    Maximo em fila: {metrics['maximo_fila']}")
                print(
                    f"    Maximo em atendimento: {metrics['maximo_atendimento']}")
                print(f"    Numero medio em fila: "
                      f"{metrics['numero_medio_fila']:.2f}")
                print(f"    Numero medio em atendimento: "
                      f"{metrics['numero_medio_atendimento']:.2f}")

                # Analysis
                print(f"    Analise (💡): ", end="")
                if util > 0.85:
                    print(f"Sistema sobrecarregado ({util:.1%})! "
                          f"Considere aumentar capacidade.")
                elif util < 0.25:
                    print(f"Sistema ocioso ({util:.1%})! "
                          f"Considere ajustar capacidade.")
                else:
                    print("Sistema operando dentro dos parametros esperados.")
                print()

    def _print_entity_counts(self):
        """Print entity creation and disposal counts."""
        total_created = sum(block.entities_created
                            for block in self.model.create_blocks)
        total_disposed = sum(
            len([e for e in block.disposed_entities
                 if e.get_attribute('disposal_time', 0) >=
                 self.model.warm_up_period])
            for block in self.model.dispose_blocks
        )

        print(f"\nEntidades criadas: {total_created}")
        print(f"Entidades que sairam: {total_disposed}")
        print(f"Entidades no sistema: {total_created - total_disposed}")

    def _print_block_statistics(self):
        """Print statistics for individual blocks."""
        print("\nESTATISTICAS DOS BLOCOS:")
        for block_name, block in self.model.blocks.items():
            print(f"\n{block_name} ({type(block).__name__}):")

            if hasattr(block, 'entities_processed'):
                print(f"  Entidades processadas: {block.entities_processed}")
                if block.entities_processed > 0:
                    avg_delay = block.total_delay_time / block.entities_processed
                    avg_queue = block.total_queue_time / block.entities_processed
                    print(f"  Tempo medio em atendimento: {avg_delay:.2f}")
                    print(f"  Tempo medio em fila: {avg_queue:.2f}")

            if hasattr(block, 'decision_counts'):
                print(f"  Numero de decisoes: {block.decision_counts}")



# ======================================================
# FILE: analytics\plotting.py
# ======================================================

# =====================================================================
# FILE: analytics/plotting.py
# =====================================================================
# from blocks.process_block import ProcessBlock, MultiProcessBlock


# =====================================================================
# FILE: analytics/plotting.py
# =====================================================================
class SimulationPlotter:
    """Creates visualizations from simulation results."""

    def __init__(self, model):
        self.model = model
        self.metrics = None  # Lazy loaded
        self.wip_tracker = None  # NEW

    def _get_wip_tracker(self):
        """Lazy load WIP tracker."""
        if self.wip_tracker is None:
            self.wip_tracker = WIPTracker(self.model)
        return self.wip_tracker

    def plot_wip_over_time(self):
        """Plot WIP evolution over time."""
        wip_tracker = self._get_wip_tracker()
        wip_tracker.plot_wip_over_time()

    def plot_system_time_distribution(self):
        """Plot distribution of total time in system."""
        wip_tracker = self._get_wip_tracker()
        wip_tracker.plot_system_time_distribution()

    def _get_metrics(self):
        """Lazy load metrics collector."""
        if self.metrics is None:
            self.metrics = MetricsCollector(self.model)
        return self.metrics

    def plot_resource_use_over_time(self, show_warm_up: bool = True,
                                    resource: Optional[str] = None,
                                    moving_average_window: int = 50):
        """
        Plot resource utilization over time for warm-up analysis.

        Args:
            show_warm_up: Mark warm-up period visually
            resource: Specific resource to plot (None = all)
            moving_average_window: Window size for smoothing
        """
        # from blocks.process_block import ProcessBlock, MultiProcessBlock

        # Group ProcessBlocks by resource
        resource_blocks = self._group_blocks_by_resource()

        if not resource_blocks:
            print("Nenhum ProcessBlock encontrado para plotar")
            return

        # Filter for specific resource if requested
        if resource:
            if resource in resource_blocks:
                resource_blocks = {resource: resource_blocks[resource]}
            else:
                print(f"Recurso '{resource}' nao encontrado")
                return

        # Create subplots
        num_resources = len(resource_blocks)
        fig, axes = plt.subplots(num_resources, 1,
                                 figsize=(12, 4 * num_resources))
        if num_resources == 1:
            axes = [axes]

        fig.suptitle('Uso de Recursos (determine o tempo ideal de Warm-up)',
                     fontsize=14, fontweight='bold')

        for idx, (resource_name, blocks) in enumerate(resource_blocks.items()):
            ax = axes[idx] if num_resources > 1 else axes[0]
            self._plot_single_resource(ax, resource_name, blocks,
                                       show_warm_up, moving_average_window)

        axes[-1].set_xlabel('Tempo de Simulacao')
        plt.tight_layout()
        plt.show()

    def _plot_single_resource(self, ax, resource_name: str, blocks: List,
                              show_warm_up: bool, moving_avg_window: int):
        """Plot utilization for a single resource."""

        # Combine and deduplicate data
        all_data = []
        seen_timestamps = set()

        for block in blocks:
            if isinstance(block, ProcessBlock):
                for data_point in block.resource_data:
                    timestamp = data_point[0]
                    if timestamp not in seen_timestamps:
                        all_data.append(data_point)
                        seen_timestamps.add(timestamp)
            elif isinstance(block, MultiProcessBlock):
                resource_obj = self.model.resources[resource_name]
                if resource_obj in block.resource_data:
                    for data_point in block.resource_data[resource_obj]:
                        timestamp = data_point[0]
                        if timestamp not in seen_timestamps:
                            all_data.append(data_point)
                            seen_timestamps.add(timestamp)

        if not all_data:
            ax.text(0.5, 0.5, 'Sem dados disponiveis',
                    ha='center', va='center', transform=ax.transAxes)
            ax.set_title(f'{resource_name} (capacidade: '
                         f'{self.model.resources[resource_name].capacity})')
            return

        # Sort and filter data
        all_data.sort(key=lambda x: x[0])

        max_time = (self.model.env.now if self.model.env.now > 0
                    else max(point[0] for point in all_data))

        all_data = [point for point in all_data if point[0] <= max_time]

        if not all_data:
            ax.text(0.5, 0.5, 'Dados filtrados estao vazios',
                    ha='center', va='center', transform=ax.transAxes)
            return

        # Extract time and utilization with step function
        times, utilizations = self._create_step_function(
            all_data, resource_name, max_time)

        # print(f"Times: {times}")
        # print(f"Utilizations: {utilizations}")

        # Plot utilization
        ax.plot(times, utilizations, drawstyle='steps-post',
                alpha=0.7, color='lightblue', linewidth=1.5,
                label='Utilizacao')

        # ✅ NEW: Plot cumulative average (dark green)
        if len(utilizations) >= 2:
            times_array = np.array(times)
            utils_array = np.array(utilizations)

            # Calculate cumulative average
            cumulative_avg = np.cumsum(
                utils_array) / np.arange(1, len(utils_array) + 1)

            ax.plot(times_array, cumulative_avg, color='darkgreen',
                    linewidth=2.5, label='Média Cumulativa (Warm-up)',
                    alpha=0.9, linestyle='-')

        # Plot moving average (dark blue - existing)
        if len(utilizations) >= moving_avg_window:
            times_array = np.array(times)
            utils_array = np.array(utilizations)
            moving_avg = np.convolve(utils_array,
                                     np.ones(moving_avg_window) /
                                     moving_avg_window,
                                     mode='valid')
            moving_avg_times = times_array[moving_avg_window-1:]
            ax.plot(moving_avg_times, moving_avg, color='darkblue',
                    linewidth=2, label=f'Media movel ({moving_avg_window} pontos)',
                    alpha=0.8)

        # Mark warm-up period
        if show_warm_up and self.model.warm_up_period > 0:
            ax.axvline(x=self.model.warm_up_period, color='red',
                       linestyle='--', linewidth=2,
                       label=f'Fim do Warm-up (t={self.model.warm_up_period})')
            ax.axvspan(0, self.model.warm_up_period, alpha=0.2,
                       color='red', label='Periodo de Warm-up')

        # Formatting
        capacity = self.model.resources[resource_name].capacity
        ax.set_title(f'{resource_name} (capacidade: {capacity})')
        ax.set_ylabel('Utilizacao (%)')
        ax.set_ylim(0, 105)
        ax.set_xlim(0, max_time)
        ax.grid(True, alpha=0.3)
        # Smaller font for more labels
        ax.legend(loc='upper right', fontsize=9)

        # Add utilization bands
        ax.axhline(y=85, color='orange', linestyle=':', alpha=0.7,
                   label='85% (Limite recomendado)')
        ax.axhline(y=100, color='red', linestyle=':', alpha=0.7)

    def _create_step_function(self, data: List, resource_name: str,
                              max_time: float) -> tuple:
        """Create step function for resource utilization."""
        times = []
        utilizations = []
        capacity = self.model.resources[resource_name].capacity

        for i, point in enumerate(data):
            current_time = point[0]
            current_util = point[1] / capacity * 100

            times.append(current_time)
            utilizations.append(current_util)

            # Add point before next state change
            if i < len(data) - 1:
                next_time = data[i + 1][0]
                if next_time > current_time:
                    times.append(next_time - 0.0001)
                    utilizations.append(current_util)

        # Extend to end of simulation
        if times and times[-1] < max_time:
            times.append(max_time)
            utilizations.append(utilizations[-1])

        return times, utilizations

    def _group_blocks_by_resource(self) -> dict:
        """Group process blocks by resource."""

        resource_blocks = {}

        for block in self.model.blocks.values():
            if isinstance(block, ProcessBlock):
                resource_name = self._find_resource_name(block.resource)
                if resource_name:
                    if resource_name not in resource_blocks:
                        resource_blocks[resource_name] = []
                    resource_blocks[resource_name].append(block)

            elif isinstance(block, MultiProcessBlock):
                for res in block.resource_requirements.keys():
                    resource_name = self._find_resource_name(res)
                    if resource_name:
                        if resource_name not in resource_blocks:
                            resource_blocks[resource_name] = []
                        resource_blocks[resource_name].append(block)

        return resource_blocks

    def _find_resource_name(self, resource_obj) -> str:
        """Find resource name from object."""
        for name, res in self.model.resources.items():
            if res == resource_obj:
                return name
        return None

    def plot_activity_metrics(self):
        """Create stacked bar chart for queue + service time by activity."""
        metrics = self._get_metrics()
        entity_summary = metrics.get_entity_metrics_summary()
        activities_data = entity_summary.get('atividades', {})

        if not activities_data:
            print("No activity data available to plot.")
            return

        # Extract data
        activity_names = list(activities_data.keys())
        queue_times = [activities_data[name]['tempo_medio_fila']
                       for name in activity_names]
        service_times = [activities_data[name]['tempo_medio_atendimento']
                         for name in activity_names]

        # Create figure
        fig, ax = plt.subplots(figsize=(12, 8))

        bar_width = 0.6
        x_pos = np.arange(len(activity_names))

        # Stacked bars
        bars1 = ax.bar(x_pos, queue_times, bar_width,
                       label='Tempo medio em fila', color='lightcoral', alpha=0.8)
        bars2 = ax.bar(x_pos, service_times, bar_width,
                       bottom=queue_times, label='Tempo medio de atendimento',
                       color='lightblue', alpha=0.8)

        # Add labels
        for i, (qt, st) in enumerate(zip(queue_times, service_times)):
            total = qt + st

            if qt > 0.5:
                ax.text(i, qt/2, f'{qt:.1f}', ha='center', va='center',
                        fontweight='bold', color='darkred')
            if st > 0.5:
                ax.text(i, qt + st/2, f'{st:.1f}', ha='center', va='center',
                        fontweight='bold', color='darkblue')

            max_total = max(queue_times[j] + service_times[j]
                            for j in range(len(activity_names)))
            ax.text(i, total + max_total * 0.02, f'{total:.1f}',
                    ha='center', va='bottom', fontweight='bold', fontsize=11)

        # Formatting
        ax.set_xlabel('Atividades', fontsize=12, fontweight='bold')
        ax.set_ylabel('Tempo (minutos)', fontsize=12, fontweight='bold')
        ax.set_title('Metricas das Entidades por Atividade\n'
                     '(Tempo medio em fila + Tempo medio de atendimento)',
                     fontsize=14, fontweight='bold', pad=20)
        ax.set_xticks(x_pos)
        ax.set_xticklabels(activity_names, rotation=45, ha='right')
        ax.legend(loc='upper right', framealpha=0.9)
        ax.grid(axis='y', alpha=0.3, linestyle='--')
        ax.set_axisbelow(True)

        plt.tight_layout()

        self._print_activity_efficiency_analysis(activities_data)

        plt.show()

    def _print_activity_efficiency_analysis(self, activities_data: dict):
        """Print efficiency analysis for activities."""
        print("\nANALISE DE EFICIENCIA POR ATIVIDADE:")
        print("=" * 45)

        for name, data in activities_data.items():
            qt = data['tempo_medio_fila']
            st = data['tempo_medio_atendimento']
            total = qt + st

            if total > 0:
                queue_pct = (qt / total) * 100
                service_pct = (st / total) * 100

                print(f"{name}:")
                print(f"  Tempo total: {total:.1f} min")
                print(f"  Fila: {qt:.1f} min ({queue_pct:.1f}%)")
                print(f"  Atendimento: {st:.1f} min ({service_pct:.1f}%)")

                if queue_pct > 60:
                    print(
                        f"  🚨 ALERTA: {queue_pct:.1f}% do tempo e gasto em fila!")
                elif queue_pct > 30:
                    print(
                        f"  ⚠️  ATENCAO: {queue_pct:.1f}% do tempo e gasto em fila")
                else:
                    print(
                        f"  ✅ Eficiente: apenas {queue_pct:.1f}% do tempo em fila")
                print()

    def plot_resources_utilization(self):
        """Create bar chart showing utilization rate per resource."""
        metrics = self._get_metrics()
        resource_summary = metrics.get_resource_metrics_summary()

        if not resource_summary:
            print("No resource data available to plot.")
            return

        # Extract data
        resource_names = list(resource_summary.keys())
        utilization_rates = [resource_summary[name]['taxa_utilizacao'] * 100
                             for name in resource_names]
        capacities = [self.model.resources[name].capacity
                      for name in resource_names]

        # Create figure
        fig, ax = plt.subplots(figsize=(12, 8))

        bar_width = 0.6
        x_pos = np.arange(len(resource_names))

        # Color by utilization level
        colors = []
        for util in utilization_rates:
            if util >= 85:
                colors.append('darkred')
            elif util >= 70:
                colors.append('orange')
            elif util >= 50:
                colors.append('gold')
            elif util >= 25:
                colors.append('lightgreen')
            else:
                colors.append('lightblue')

        # Create bars
        bars = ax.bar(x_pos, utilization_rates, bar_width,
                      color=colors, alpha=0.8, edgecolor='black', linewidth=1)

        # Add labels
        for i, (util, cap) in enumerate(zip(utilization_rates, capacities)):
            ax.text(i, util + max(utilization_rates) * 0.02, f'{util:.1f}%',
                    ha='center', va='bottom', fontweight='bold', fontsize=11)
            if util > 15:
                ax.text(i, util/2, f'Cap: {cap}', ha='center', va='center',
                        fontweight='bold',
                        color='white' if util > 50 else 'black')

        # Formatting
        ax.set_xlabel('Recursos', fontsize=12, fontweight='bold')
        ax.set_ylabel('Taxa de Utilizacao (%)', fontsize=12, fontweight='bold')
        ax.set_title('Taxa de Utilizacao por Recurso',
                     fontsize=14, fontweight='bold', pad=20)
        ax.set_xticks(x_pos)
        ax.set_xticklabels(resource_names, rotation=45, ha='right')
        ax.set_ylim(0, max(105, max(utilization_rates) * 1.1))

        # Reference lines
        ax.axhline(y=85, color='red', linestyle='--', alpha=0.7,
                   label='85% (Limite critico)')
        ax.axhline(y=70, color='orange', linestyle='--', alpha=0.5,
                   label='70% (Utilizacao alta)')
        ax.axhline(y=25, color='blue', linestyle='--', alpha=0.3,
                   label='25% (Subutilizacao)')

        ax.legend(loc='upper right', framealpha=0.9)
        ax.grid(axis='y', alpha=0.3, linestyle='--')
        ax.set_axisbelow(True)

        plt.tight_layout()

        self._print_resource_utilization_analysis(resource_summary)

        plt.show()

    def _print_resource_utilization_analysis(self, resource_summary: dict):
        """Print detailed resource utilization analysis."""
        print("\nANALISE DE UTILIZACAO DE RECURSOS:")
        print("=" * 42)

        for name, metrics in resource_summary.items():
            util = metrics['taxa_utilizacao'] * 100
            cap = self.model.resources[name].capacity

            print(f"{name} (Capacidade: {cap}):")
            print(f"  Taxa de utilizacao: {util:.1f}%")

            if util >= 90:
                print(f"  🚨 CRITICO: Recurso extremamente sobrecarregado!")
                print(f"  💡 Recomendacao: Aumentar capacidade urgentemente")
            elif util >= 85:
                print(f"  🔥 ALERTA: Recurso sobrecarregado")
                print(f"  💡 Recomendacao: Considerar aumentar capacidade")
            elif util >= 70:
                print(f"  ⚠️  ATENCAO: Utilizacao alta, monitorar")
            elif util >= 50:
                print(f"  ✅ BOM: Utilizacao moderada e eficiente")
            elif util >= 25:
                print(f"  ℹ️  BAIXA: Utilizacao abaixo do ideal")
            else:
                print(f"  ⚪ MUITO BAIXA: Recurso subutilizado")
            print()



# ======================================================
# FILE: config\simulation_config.py
# ======================================================

# =====================================================================
# FILE: config/simulation_config.py
# =====================================================================


@dataclass
class SimulationConfig:
    """Configuration for simulation run."""
    duration: float
    warm_up_period: float = 0.0
    seed: Optional[int] = None
    check_stability: bool = False

    def validate(self):
        """Validate configuration."""
        if self.duration <= 0:
            raise ValueError("Duration must be positive")
        if self.warm_up_period < 0:
            raise ValueError("Warm-up period cannot be negative")
        if self.warm_up_period >= self.duration:
            raise ValueError("Warm-up period must be less than duration")



# ======================================================
# FILE: generate_all_code.py
# ======================================================

# ======================================================
# CONFIGURATION
# ======================================================

EXCLUDED_DIRS = {
    "tests",
    "scripts",
    "venv",
    "site",
    "script",
    "ref",
    "examples",
    "docs",
    "distfit",
    "dca",
    ".github",
}

EXCLUDED_FILES = {
    "all_blocks.py",
    "all_blocks_bkp.py",
    "decide_time_conditions.py",
}

OUTPUT_FILE = "all_code.py"


# ======================================================
# FILE COLLECTION
# ======================================================

def is_excluded(path: Path) -> bool:
    if path.name in EXCLUDED_FILES:
        return True
    return any(part in EXCLUDED_DIRS for part in path.parts)


def collect_python_files(root: Path) -> List[Path]:
    files = []
    for path in root.rglob("*.py"):
        if not is_excluded(path):
            files.append(path)
    return sorted(files)


# ======================================================
# DEPENDENCY ANALYSIS
# ======================================================

def module_name(root: Path, file: Path) -> str:
    rel = file.relative_to(root).with_suffix("")
    return ".".join(rel.parts)


def extract_dependencies(tree: ast.AST) -> Set[str]:
    deps = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                deps.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                deps.add(node.module.split(".")[0])
    return deps


def build_dependency_graph(
    root: Path, files: List[Path]
) -> Dict[Path, Set[Path]]:
    module_map = {module_name(root, f): f for f in files}
    graph: Dict[Path, Set[Path]] = {f: set() for f in files}

    for file in files:
        tree = ast.parse(file.read_text(encoding="utf-8"))
        deps = extract_dependencies(tree)

        for dep in deps:
            for mod, mod_file in module_map.items():
                if mod.startswith(dep):
                    graph[file].add(mod_file)

    return graph


def topological_sort(graph: Dict[Path, Set[Path]]) -> List[Path]:
    visited = {}
    result = []

    def visit(node: Path):
        if node in visited:
            return
        visited[node] = True
        for dep in graph[node]:
            if dep != node:
                visit(dep)
        result.append(node)

    for node in graph:
        visit(node)

    return list(dict.fromkeys(result))


# ======================================================
# IMPORT HANDLING
# ======================================================

def extract_imports(tree: ast.AST) -> Set[str]:
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                imports.add(
                    f"import {a.name}" +
                    (f" as {a.asname}" if a.asname else "")
                )
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            names = []
            for a in node.names:
                names.append(
                    a.name + (f" as {a.asname}" if a.asname else "")
                )
            imports.add(f"from {module} import {', '.join(names)}")
    return imports


def strip_imports(source: str) -> str:
    lines = source.splitlines()
    return "\n".join(
        line for line in lines
        if not line.strip().startswith(("import ", "from "))
    ).strip()


# ======================================================
# PEP8 FORMATTING
# ======================================================

def format_pep8(code: str) -> str:
    try:
        return autopep8.fix_code(code)
    except ImportError:
        return code


# ======================================================
# MAIN GENERATOR
# ======================================================

def generate_all_code(project_root: str):
    root = Path(project_root).resolve()
    files = collect_python_files(root)

    dep_graph = build_dependency_graph(root, files)
    ordered_files = topological_sort(dep_graph)

    all_imports: Set[str] = set()
    code_sections = []

    for file in ordered_files:
        source = file.read_text(encoding="utf-8")
        tree = ast.parse(source)

        all_imports |= extract_imports(tree)

        cleaned = strip_imports(source)
        cleaned = format_pep8(cleaned)

        if cleaned:
            code_sections.append(
                f"\n\n# ======================================================\n"
                f"# FILE: {file.relative_to(root)}\n"
                f"# ======================================================\n\n"
                f"{cleaned}"
            )

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("# ======================================================\n")
        f.write("# AUTO-GENERATED FILE — DESK PROJECT\n")
        f.write("# Dependency-aware | PEP8 formatted\n")
        f.write("# DO NOT EDIT MANUALLY\n")
        f.write("# ======================================================\n\n")

        for imp in sorted(all_imports):
            f.write(imp + "\n")

        f.write("\n\n")
        f.write("\n".join(code_sections))

    print(
        f"✔ all_code.py generated ({len(ordered_files)} files, dependency-ordered)")


# ======================================================
# ENTRY POINT
# ======================================================

if __name__ == "__main__":
    generate_all_code(".")



# ======================================================
# FILE: stats\factorial.py
# ======================================================

# =====================================================================
# FILE: statistics/factorial.py
# =====================================================================
"""
Factorial experimental design framework for simulation studies.

This module provides tools for:
- Designing full factorial experiments with multiple factors
- Running experiments with multiple replications per configuration
- Analyzing main effects and interaction effects
- Visualizing experimental results
"""


@dataclass
class FactorLevel:
    """
    Represents a factor and its levels for factorial analysis.

    Attributes:
        factor_name: Short name for the factor (e.g., 'arrival_rate')
        parameter_path: Path to parameter in model (for documentation)
        levels: List of values to test for this factor
        description: Human-readable description of the factor
    """
    factor_name: str
    parameter_path: str
    levels: List[Any]
    description: str = ""


class FactorialExperiment:
    """
    Framework for conducting factorial experiments on simulation models.

    This class implements a full factorial design where all combinations
    of factor levels are tested with multiple replications.
    """

    def __init__(self, simulation_function: Callable, base_seed: int = 12345):
        """
        Initialize factorial experiment framework.

        Args:
            simulation_function: Function that creates and runs simulation model.
                                Must accept factor parameters as kwargs and return model.
            base_seed: Base random seed for reproducibility
        """
        self.simulation_function = simulation_function
        self.base_seed = base_seed
        self.factors: List[FactorLevel] = []
        self.results: List[Dict[str, Any]] = []
        self.results_df: Optional[pd.DataFrame] = None

    def add_factor(self, factor_name: str, parameter_path: str,
                   levels: List[Any], description: str = ""):
        """
        Add a factor to the experimental design.

        Args:
            factor_name: Name of the factor (e.g., "arrival_rate")
            parameter_path: Path to parameter in model (for documentation)
            levels: List of values to test
            description: Human-readable description
        """
        factor = FactorLevel(
            factor_name=factor_name,
            parameter_path=parameter_path,
            levels=levels,
            description=description
        )
        self.factors.append(factor)
        print(f"✅ Fator adicionado: {factor_name} ({len(levels)} niveis)")

    def run_factorial_experiment(self, n_replications: int = 1,
                                 simulation_time: Optional[float] = None,
                                 warm_up_period: float = 0.0,
                                 verbose: bool = True):
        """
        Run full factorial experiment with all combinations of factor levels.

        Args:
            n_replications: Number of replications per combination
            simulation_time: Duration of each simulation run
            warm_up_period: Warm-up period for statistics collection
            verbose: Print progress messages
        """
        if not self.factors:
            print("❌ Nenhum fator definido! Use add_factor() primeiro.")
            return

        # Generate all combinations
        factor_levels = [factor.levels for factor in self.factors]
        combinations = list(itertools.product(*factor_levels))
        total_runs = len(combinations) * n_replications

        self._print_experiment_header(combinations, n_replications, total_runs)

        self.results = []
        start_time = time.time()
        run_count = 0

        # Run all combinations
        for combo_idx, combination in enumerate(combinations):
            # Create factor configuration
            config = {
                self.factors[i].factor_name: combination[i]
                for i in range(len(self.factors))
            }

            if verbose:
                print(
                    f"\n📊 Configuração {combo_idx + 1}/{len(combinations)}: {config}")

            # Run replications for this combination
            for rep in range(n_replications):
                run_count += 1
                seed = self.base_seed + combo_idx * 1000 + rep

                if verbose and n_replications > 1:
                    print(
                        f"  Replicacao {rep + 1}/{n_replications} (seed: {seed})")

                try:
                    # Run simulation with current configuration
                    model = self._run_simulation_with_config(
                        config, seed, simulation_time, warm_up_period
                    )

                    # Extract results
                    result = self._extract_results(
                        model, config, combo_idx, rep)
                    self.results.append(result)

                    if verbose and run_count % 10 == 0:
                        self._print_progress(start_time, run_count, total_runs)

                except Exception as e:
                    print(f"  ❌ Erro na execução: {e}")
                    continue

        self._print_completion_summary(start_time, total_runs)

        # Convert to DataFrame
        self.results_df = pd.DataFrame(self.results)
        print(f"📊 {len(self.results)} resultados coletados")

    def _print_experiment_header(self, combinations: List, n_replications: int,
                                 total_runs: int):
        """Print experiment setup information."""
        print("\n🔬 EXPERIMENTO FATORIAL")
        print("=" * 60)
        print(f"Fatores: {len(self.factors)}")
        for factor in self.factors:
            print(f"  - {factor.factor_name}: {len(factor.levels)} niveis")
        print(f"Combinacoes: {len(combinations)}")
        print(f"Replicacoes por combinacao: {n_replications}")
        print(f"Total de execucoes: {total_runs}")
        print("=" * 60)

    def _print_progress(self, start_time: float, run_count: int, total_runs: int):
        """Print progress update."""
        elapsed = time.time() - start_time
        avg_time = elapsed / run_count
        remaining = (total_runs - run_count) * avg_time
        print(f"  Progresso: {run_count}/{total_runs} | "
              f"Tempo restante: {remaining/60:.1f} min")

    def _print_completion_summary(self, start_time: float, total_runs: int):
        """Print experiment completion summary."""
        total_time = time.time() - start_time
        print(f"\n✅ EXPERIMENTO CONCLUÍDO em {total_time/60:.1f} minutos")
        print(
            f"⏱️  Tempo médio por execução: {total_time/total_runs:.1f} segundos")

    def _run_simulation_with_config(self, config: Dict, seed: int,
                                    simulation_time: Optional[float],
                                    warm_up_period: float):
        """Run simulation with specific factor configuration."""
        # Build kwargs from configuration
        kwargs = {
            'seed': seed,
            'return_model': True
        }

        if simulation_time is not None:
            kwargs['until'] = simulation_time
        if warm_up_period > 0:
            kwargs['warm_up_period'] = warm_up_period

        # Add factor values to kwargs
        kwargs.update(config)

        # Run simulation
        model = self.simulation_function(**kwargs)
        return model

    def _extract_results(self, model, config: Dict, combo_idx: int,
                         rep: int) -> Dict[str, Any]:
        """
        Extract KPIs from simulation model.

        Args:
            model: Completed simulation model
            config: Factor configuration for this run
            combo_idx: Combination index
            rep: Replication number

        Returns:
            Dictionary of results including factors and KPIs
        """

        result = {
            'combination_id': combo_idx,
            'replication': rep,
            **config  # Include factor values
        }

        # System-level metrics
        result['simulation_time'] = model.env.now
        result['warm_up_period'] = model.warm_up_period
        result['entities_processed'] = model.entity_count
        result['throughput'] = model.overall_throughput

        ###############################################################
        # Import here to avoid circular dependencies
        ###############################################################
        # Entity metrics: Compute metrics using MetricsCollector
        metrics_collector = MetricsCollector(model)
        entity_summary = metrics_collector.get_entity_metrics_summary()
        result['system_time_avg'] = entity_summary.get(
            'tempo_medio_sistema', 0)

        # Activity metrics
        for activity_name, metrics in entity_summary.get('atividades', {}).items():
            result[f'{activity_name}_queue_time'] = metrics.get(
                'tempo_medio_fila', 0)
            result[f'{activity_name}_service_time'] = metrics.get(
                'tempo_medio_atendimento', 0)

        # Resource metrics
        resource_summary = metrics_collector.get_resource_metrics_summary()
        for resource_name, metrics in resource_summary.items():
            result[f'{resource_name}_utilization'] = metrics['taxa_utilizacao']
            result[f'{resource_name}_avg_queue'] = metrics['numero_medio_fila']
            result[f'{resource_name}_max_queue'] = metrics['maximo_fila']

        return result

    def get_aggregated_results(self) -> Optional[pd.DataFrame]:
        """
        Aggregate results by factor combination (average over replications).

        Returns:
            DataFrame with mean and std for each metric by factor combination
        """
        if self.results_df is None:
            print("❌ Execute o experimento primeiro!")
            return None

        # Group by factor values
        factor_names = [f.factor_name for f in self.factors]

        # Aggregate numeric columns
        numeric_cols = self.results_df.select_dtypes(
            include=[np.number]).columns
        exclude_cols = ['combination_id', 'replication',
                        'simulation_time', 'warm_up_period']
        agg_cols = [col for col in numeric_cols if col not in exclude_cols]

        aggregated = self.results_df.groupby(factor_names)[agg_cols].agg(
            ['mean', 'std']
        ).reset_index()

        return aggregated

    def plot_correlation_matrix(self):
        """Plot correlation matrix of key metrics with compact legend."""
        if self.results_df is None:
            print("❌ Execute o experimento primeiro!")
            return

        # Filter columns and create labels
        selected_cols, col_labels = self._prepare_correlation_data()

        if not selected_cols:
            print("❌ Nenhuma coluna relevante encontrada!")
            return

        # Calculate correlation
        filtered_df = self.results_df[selected_cols]
        corr_matrix = filtered_df.corr()

        # Create short labels
        short_labels = [col_labels[col] for col in filtered_df.columns]

        # Plot
        fig, ax = plt.subplots(figsize=(16, 10))

        sns.heatmap(corr_matrix, annot=True, fmt='.2f', cmap='coolwarm',
                    center=0, square=True, linewidths=0.5,
                    xticklabels=short_labels, yticklabels=short_labels,
                    ax=ax, cbar_kws={'label': 'Correlacao'})

        ax.set_title('Matriz de Correlacao (Metricas Principais)',
                     fontsize=14, fontweight='bold', pad=15)

        # Create and position legend
        legend_text = self._create_correlation_legend(filtered_df, col_labels)
        fig.text(0.75, 0.5, legend_text,
                 fontsize=9,
                 verticalalignment='center',
                 bbox=dict(boxstyle='round', facecolor='wheat',
                           alpha=0.9, pad=0.8),
                 family='monospace')

        plt.subplots_adjust(left=0.1, right=0.75)
        plt.show()

        print(
            f"\nMatriz de correlacao gerada com {len(selected_cols)} variaveis")

        return corr_matrix

    def _prepare_correlation_data(self) -> Tuple[List[str], Dict[str, str]]:
        """Prepare data for correlation matrix."""
        selected_cols = []
        col_labels = {}
        label_counter = 1

        factor_names = [f.factor_name for f in self.factors]

        # Add factor columns
        for col in self.results_df.columns:
            if any(col.startswith(fname) for fname in factor_names):
                selected_cols.append(col)
                col_labels[col] = f"F{label_counter}"
                label_counter += 1

        # Add activity metrics
        metric_counter = 1
        for col in self.results_df.columns:
            if 'queue_time' in col or 'service_time' in col:
                selected_cols.append(col)
                label = f"Q{metric_counter}" if 'queue_time' in col else f"S{metric_counter}"
                col_labels[col] = label
                metric_counter += 1

        # Add resource utilization
        util_counter = 1
        for col in self.results_df.columns:
            if '_utilization' in col:
                selected_cols.append(col)
                col_labels[col] = f"U{util_counter}"
                util_counter += 1

        return selected_cols, col_labels

    def _create_correlation_legend(self, filtered_df: pd.DataFrame,
                                   col_labels: Dict[str, str]) -> str:
        """Create legend text for correlation plot."""
        factor_names = [f.factor_name for f in self.factors]
        legend_lines = ["LEGENDA:", "", "Fatores:"]

        for col in filtered_df.columns:
            if any(col.startswith(fname) for fname in factor_names):
                legend_lines.append(f"  {col_labels[col]}: {col}")

        legend_lines.append("")
        legend_lines.append("Atividades:")
        for col in filtered_df.columns:
            if 'queue_time' in col or 'service_time' in col:
                short_name = col.replace(
                    '_queue_time', '').replace('_service_time', '')
                metric_type = 'Fila' if 'queue' in col else 'Atend'
                legend_lines.append(
                    f"  {col_labels[col]}: {short_name} ({metric_type})")

        legend_lines.append("")
        legend_lines.append("Recursos:")
        for col in filtered_df.columns:
            if '_utilization' in col:
                resource_name = col.replace('_utilization', '')
                legend_lines.append(
                    f"  {col_labels[col]}: {resource_name} (Util)")

        return "\n".join(legend_lines)

    def plot_main_effects(self, response_variable: str):
        """
        Plot main effects for each factor on a response variable.

        Args:
            response_variable: Name of the response variable to plot
        """
        if self.results_df is None:
            print("❌ Execute o experimento primeiro!")
            return

        if response_variable not in self.results_df.columns:
            print(f"❌ Variável '{response_variable}' não encontrada!")
            return

        n_factors = len(self.factors)
        fig, axes = plt.subplots(1, n_factors, figsize=(5*n_factors, 4))
        if n_factors == 1:
            axes = [axes]

        for idx, factor in enumerate(self.factors):
            ax = axes[idx]

            # Group by factor level and calculate mean response
            grouped = self.results_df.groupby(factor.factor_name)[response_variable].agg(
                ['mean', 'std']
            )

            # Plot
            x_pos = range(len(grouped))
            ax.errorbar(x_pos, grouped['mean'], yerr=grouped['std'],
                        marker='o', markersize=8, capsize=5, linewidth=2)

            ax.set_xlabel(factor.factor_name, fontsize=11, fontweight='bold')
            ax.set_ylabel(response_variable, fontsize=11, fontweight='bold')
            ax.set_title(f'Efeito de {factor.factor_name}', fontsize=12)
            ax.set_xticks(x_pos)
            ax.set_xticklabels(grouped.index, rotation=45)
            ax.grid(True, alpha=0.3)

        plt.suptitle(f'Efeitos Principais em {response_variable}',
                     fontsize=14, fontweight='bold')
        plt.tight_layout()
        plt.show()

    def plot_interaction_effects(self, response_variable: str,
                                 factor1_name: str, factor2_name: str):
        """
        Plot interaction effects between two factors.

        Args:
            response_variable: Response variable to analyze
            factor1_name: First factor name
            factor2_name: Second factor name
        """
        if self.results_df is None:
            print("❌ Execute o experimento primeiro!")
            return

        if response_variable not in self.results_df.columns:
            print(f"❌ Variável '{response_variable}' não encontrada!")
            return

        # Group by both factors
        grouped = self.results_df.groupby(
            [factor1_name, factor2_name]
        )[response_variable].mean().reset_index()

        # Pivot for plotting
        pivot = grouped.pivot(index=factor1_name, columns=factor2_name,
                              values=response_variable)

        # Plot
        fig, ax = plt.subplots(figsize=(10, 6))

        for col in pivot.columns:
            ax.plot(pivot.index, pivot[col], marker='o', markersize=8,
                    linewidth=2, label=f'{factor2_name}={col}')

        ax.set_xlabel(factor1_name, fontsize=12, fontweight='bold')
        ax.set_ylabel(response_variable, fontsize=12, fontweight='bold')
        ax.set_title(f'Interacao entre {factor1_name} e {factor2_name}',
                     fontsize=14, fontweight='bold')
        ax.legend(title=factor2_name, framealpha=0.9)
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.show()

    def print_summary(self):
        """Print comprehensive summary of factorial analysis."""
        if self.results_df is None:
            print("❌ Execute o experimento primeiro!")
            return

        print("\n" + "=" * 70)
        print("📊 RESUMO DA ANÁLISE FATORIAL")
        print("=" * 70)

        self._print_factor_summary()
        self._print_best_worst_configurations()
        self._print_descriptive_statistics()
        self._print_general_analysis()

    def _print_factor_summary(self):
        """Print summary of factors tested."""
        print("\n🔬 FATORES TESTADOS:")
        for factor in self.factors:
            print(f"  - {factor.factor_name}: {factor.levels}")
            if factor.description:
                print(f"    {factor.description}")

    def _print_best_worst_configurations(self):
        """Print best and worst configurations for key metrics."""
        factor_names = [f.factor_name for f in self.factors]

        # Find key metrics
        activity_metrics = [col for col in self.results_df.columns
                            if 'queue_time' in col or 'service_time' in col]
        utilization_metrics = [col for col in self.results_df.columns
                               if '_utilization' in col]

        sample_metrics = []
        if activity_metrics:
            sample_metrics.append(activity_metrics[0])
        if utilization_metrics:
            sample_metrics.append(utilization_metrics[0])

        for metric in sample_metrics[:3]:
            print(f"\n  {metric}:")

            # Find best and worst
            if 'time' in metric.lower():
                best_idx = self.results_df[metric].idxmin()
                worst_idx = self.results_df[metric].idxmax()
            elif 'utilization' in metric.lower():
                best_idx = (self.results_df[metric] - 0.75).abs().idxmin()
                worst_idx = self.results_df[metric].idxmax()
            else:
                best_idx = self.results_df[metric].idxmax()
                worst_idx = self.results_df[metric].idxmin()

            best_row = self.results_df.loc[best_idx]
            worst_row = self.results_df.loc[worst_idx]

            best_config = {fname: best_row[fname] for fname in factor_names}
            worst_config = {fname: worst_row[fname] for fname in factor_names}

            best_val = best_row[metric]
            worst_val = worst_row[metric]

            if 'utilization' in metric:
                print(f"    Melhor: {best_config} -> {best_val*100:.1f}%")
                print(f"    Pior: {worst_config} -> {worst_val*100:.1f}%")
            else:
                print(f"    Melhor: {best_config} -> {best_val:.2f}")
                print(f"    Pior: {worst_config} -> {worst_val:.2f}")

    def _print_descriptive_statistics(self):
        """Print descriptive statistics for key metrics."""
        print("\n📈 ESTATÍSTICAS DESCRITIVAS (Métricas Principais):")
        print("-" * 70)

        # Activity times
        print("\n🕐 TEMPOS DE ATIVIDADES:")
        activity_cols = [col for col in self.results_df.columns
                         if 'queue_time' in col or 'service_time' in col]
        if activity_cols:
            activity_df = self.results_df[activity_cols]
            print(activity_df.describe().T[[
                  'mean', 'std', 'min', 'max']].to_string())

        # Resource utilization
        print("\n🏭 UTILIZAÇÃO DE RECURSOS:")
        util_cols = [
            col for col in self.results_df.columns if '_utilization' in col]
        if util_cols:
            util_df = self.results_df[util_cols]
            util_display = util_df.describe(
            ).T[['mean', 'std', 'min', 'max']] * 100
            print(util_display.to_string())
            print("(valores em %)")

    def _print_general_analysis(self):
        """Print general analysis summary."""
        print("\n💡 ANÁLISE GERAL:")
        n_combinations = len(self.results_df['combination_id'].unique())
        n_reps = len(self.results_df[self.results_df['combination_id'] == 0])
        print(f"   Total de configurações testadas: {n_combinations}")
        print(f"   Replicações por configuração: {n_reps}")
        print(f"   Total de execuções: {len(self.results_df)}")

    def export_results(self, filename: str = "factorial_results.csv",
                       export_filtered: bool = False):
        """
        Export results to CSV.

        Args:
            filename: Output filename
            export_filtered: If True, export only key metrics; if False, export all
        """
        if self.results_df is None:
            print("❌ Execute o experimento primeiro!")
            return

        if export_filtered:
            export_df = self._get_filtered_results()
            print(f"📁 Resultados FILTRADOS exportados para {filename}")
            print(f"   Colunas exportadas: {len(export_df.columns)}")
        else:
            export_df = self.results_df
            print(f"📁 Resultados COMPLETOS exportados para {filename}")
            print(f"   Colunas exportadas: {len(export_df.columns)}")

        export_df.to_csv(filename, index=False)
        print(f"   Total de linhas: {len(export_df)}")

    def _get_filtered_results(self) -> pd.DataFrame:
        """Get filtered DataFrame with only key metrics."""
        factor_names = [f.factor_name for f in self.factors]
        key_cols = ['combination_id', 'replication']

        # Add factors
        for col in self.results_df.columns:
            if any(col.startswith(fname) for fname in factor_names):
                key_cols.append(col)

        # Add activity metrics
        for col in self.results_df.columns:
            if 'queue_time' in col or 'service_time' in col:
                key_cols.append(col)

        # Add resource utilization
        for col in self.results_df.columns:
            if '_utilization' in col:
                key_cols.append(col)

        return self.results_df[key_cols]



# ======================================================
# FILE: stats\replication.py
# ======================================================

# =====================================================================
# FILE: statistics/replication.py
# =====================================================================
"""
Replication framework for running multiple simulation runs with statistical analysis.

This module provides the ReplicationFramework class for:
- Running multiple independent simulation replications
- Collecting KPIs across replications
- Computing confidence intervals
- Generating statistical reports and visualizations
"""


# =====================================================================
# FILE: statistics/replication.py
# =====================================================================
class ReplicationFramework:
    """
    Framework for running multiple simulation replications with statistical analysis.

    The framework follows the method of independent replications for steady-state
    simulation analysis, computing confidence intervals using the t-distribution.
    """

    def __init__(self, simulation_function: Callable, n_replications: int = 30):
        """
        Initialize replication framework.

        Args:
            simulation_function: Function that creates, runs, and returns a simulation model.
                                Should accept seed parameter and return a model instance.
            n_replications: Number of replications to run (default 30 for CLT applicability)
        """
        self.simulation_function = simulation_function
        self.n_replications = n_replications
        self.replication_results: List[Dict[str, Any]] = []
        self.summary_statistics: Dict[str, Dict[str, float]] = {}

    def run_replications(self, base_seed: int = 12345, **simulation_kwargs):
        """
        Run multiple simulation replications with different random seeds.

        Args:
            base_seed: Base seed for reproducibility
            **simulation_kwargs: Additional arguments to pass to simulation function
        """
        print(f"EXECUTANDO {self.n_replications} REPLICACOES...")
        print("=" * 50)

        start_time = time.time()

        for replication in range(self.n_replications):
            # Set unique seed for each replication
            replication_seed = base_seed + replication * 1000

            print(
                f"Replicacao {replication + 1}/{self.n_replications} (seed: {replication_seed})")

            # Run simulation
            model = self.simulation_function(
                seed=replication_seed, **simulation_kwargs)

            # Extract KPIs from this replication
            kpis = self._extract_kpis(model, replication)
            self.replication_results.append(kpis)

            # Progress indicator
            if (replication + 1) % 5 == 0 or replication + 1 == self.n_replications:
                elapsed = time.time() - start_time
                avg_time = elapsed / (replication + 1)
                remaining = (self.n_replications - replication - 1) * avg_time
                print(f"  Progresso: {replication + 1}/{self.n_replications} | "
                      f"Tempo restante estimado: {remaining/60:.1f} min")

        total_time = time.time() - start_time
        print(f"\nREPLICACOES CONCLUIDAS em {total_time/60:.1f} minutos")
        print(
            f"Tempo medio por replicacao: {total_time/self.n_replications:.1f} segundos")

        # Calculate summary statistics
        self._calculate_summary_statistics()

        # Print results
        self.print_statistical_summary()

        # Plot confidence intervals
        self.plot_confidence_intervals()

        # Export results
        self.export_results()

    def _extract_kpis(self, model, replication_id: int) -> Dict[str, Any]:
        """
        Extract key performance indicators from a simulation model.

        Args:
            model: Completed simulation model instance
            replication_id: Replication number (for tracking)

        Returns:
            Dictionary of KPIs for this replication
        """
        # Import here to avoid circular dependencies

        metrics_collector = MetricsCollector(model)
        financial_analyzer = FinancialAnalyzer(model)  # NEW
        wip_tracker = WIPTracker(model)  # NEW

        kpis = {
            'replication_id': replication_id,
            'simulation_time': model.env.now,
            'warm_up_period': model.warm_up_period,
            'entities_processed': model.entity_count,
            'overall_throughput': model.overall_throughput
        }

        # Entity metrics
        entity_summary = metrics_collector.get_entity_metrics_summary()
        system_time = entity_summary.get('tempo_medio_sistema', 0)
        kpis['system_time_avg'] = 0 if (
            system_time is None or math.isnan(system_time)) else system_time

        # NEW: WIP metrics
        wip_summary = wip_tracker.get_wip_summary()
        kpis['average_wip'] = wip_summary['average_wip']
        kpis['max_wip'] = wip_summary['max_wip']
        kpis['final_wip'] = wip_summary['final_wip']

        # NEW: System time metrics
        system_time_summary = wip_tracker.get_system_time_summary()
        kpis['system_time_avg_detailed'] = system_time_summary['average_system_time']
        kpis['system_time_std'] = system_time_summary['std_system_time']
        kpis['system_time_min'] = system_time_summary['min_system_time']
        kpis['system_time_max'] = system_time_summary['max_system_time']

        # Activity metrics - Handle None and nan values
        activities = entity_summary.get('atividades', {})
        for activity_name, activity_metrics in activities.items():
            queue_time = activity_metrics.get('tempo_medio_fila', 0) or 0
            service_time = activity_metrics.get(
                'tempo_medio_atendimento', 0) or 0
            activity_system_time = activity_metrics.get(
                'tempo_medio_sistema', 0) or 0

            # Replace nan with 0
            kpis[f'{activity_name}_queue_time'] = 0 if math.isnan(
                queue_time) else queue_time
            kpis[f'{activity_name}_service_time'] = 0 if math.isnan(
                service_time) else service_time
            kpis[f'{activity_name}_system_time'] = 0 if math.isnan(
                activity_system_time) else activity_system_time

        # Resource metrics
        resource_summary = metrics_collector.get_resource_metrics_summary()
        for resource_name, resource_metrics in resource_summary.items():
            kpis[f'{resource_name}_utilization'] = resource_metrics['taxa_utilizacao']
            kpis[f'{resource_name}_avg_queue'] = resource_metrics['numero_medio_fila']
            kpis[f'{resource_name}_avg_in_service'] = resource_metrics['numero_medio_atendimento']
            kpis[f'{resource_name}_max_queue'] = resource_metrics['maximo_fila']

        # Decision routing metrics (if applicable)
        for block_name, block in model.blocks.items():
            if hasattr(block, 'decision_counts'):
                total_decisions = sum(block.decision_counts.values())
                for route_name, count in block.decision_counts.items():
                    percentage = (count / total_decisions *
                                  100) if total_decisions > 0 else 0
                    kpis[f'{block_name}_{route_name}_percentage'] = percentage

        # NEW: Add financial metrics
        financial_summary = financial_analyzer.get_financial_summary()
        kpis['total_revenue'] = financial_summary['total_revenue']
        kpis['total_costs'] = financial_summary['total_costs']
        kpis['net_profit'] = financial_summary['net_profit']
        kpis['avg_revenue_per_entity'] = financial_summary['avg_revenue_per_entity']
        kpis['avg_cost_per_entity'] = financial_summary['avg_cost_per_entity']
        kpis['avg_profit_per_entity'] = financial_summary['avg_profit_per_entity']

        # Add costs by activity
        for activity, cost in financial_summary['costs_by_activity'].items():
            kpis[f'{activity}_total_cost'] = cost

        return kpis

    def _calculate_summary_statistics(self):
        """
        Calculate summary statistics with 95% confidence intervals.

        Uses t-distribution for confidence intervals to account for
        finite sample size and unknown population variance.
        """
        if not self.replication_results:
            print("Nenhum resultado de replicacao disponivel!")
            return

        # Convert to DataFrame for easier manipulation
        df = pd.DataFrame(self.replication_results)
        numeric_columns = df.select_dtypes(include=[np.number]).columns

        self.summary_statistics = {}

        for column in numeric_columns:
            if column in ['replication_id', 'simulation_time', 'warm_up_period']:
                continue

            values = df[column].values
            valid_values = values[~np.isnan(values)]
            n = len(valid_values)

            if n == 0:
                self.summary_statistics[column] = {
                    'mean': np.nan,
                    'std': np.nan,
                    'sem': np.nan,
                    'ci_lower': np.nan,
                    'ci_upper': np.nan,
                    'half_width': np.nan,
                    'relative_precision': np.nan,
                    'n_replications': 0,
                    'min': np.nan,
                    'max': np.nan
                }
                continue

            mean = np.mean(valid_values)
            min_val = np.min(valid_values)
            max_val = np.max(valid_values)

            if n > 1:
                std = np.std(valid_values, ddof=1)  # Sample standard deviation
                sem = std / np.sqrt(n)  # Standard error of the mean

                # 95% Confidence Interval using t-distribution
                confidence_level = 0.95
                alpha = 1 - confidence_level
                t_critical = stats.t.ppf(1 - alpha/2, df=n-1)

                half_width = t_critical * sem
                ci_lower = mean - half_width
                ci_upper = mean + half_width

                # Relative precision (half-width of CI as percentage of mean)
                relative_precision = (
                    half_width / abs(mean) * 100) if mean != 0 else 0
            else:
                std = np.nan
                sem = np.nan
                ci_lower = np.nan
                ci_upper = np.nan
                half_width = np.nan
                relative_precision = np.nan

            self.summary_statistics[column] = {
                'mean': mean,
                'std': std,
                'sem': sem,
                'ci_lower': ci_lower,
                'ci_upper': ci_upper,
                'half_width': half_width,
                'relative_precision': relative_precision,
                'n_replications': n,
                'min': min_val,
                'max': max_val
            }

    def print_statistical_summary(self):
        """Print comprehensive statistical summary with confidence intervals."""
        if not self.summary_statistics:
            print("Estatisticas nao calculadas. Execute run_replications() primeiro.")
            return

        print("=" * 80)
        print(f"RESULTADOS ESTATISTICOS ({self.n_replications} REPLICACOES)")
        print("=" * 80)

        # System-level metrics
        self._print_section_metrics(
            title="METRICAS DO SISTEMA",
            metrics=[
                ('system_time_avg', 'Tempo medio no sistema'),
                ('entities_processed', 'Entidades processadas'),
                ('overall_throughput', 'Throughput (entidades/min)')
            ]
        )

        # Activity metrics
        activity_metrics = [k for k in self.summary_statistics.keys()
                            if any(suffix in k for suffix in ['_queue_time', '_service_time', '_system_time'])]

        if activity_metrics:
            print("\nMETRICAS DAS ATIVIDADES:")
            print("-" * 40)
            for metric_key in sorted(activity_metrics):
                stats_data = self.summary_statistics[metric_key]
                metric_name = metric_key.replace('_', ' ').title()
                self._print_metric_statistics(metric_name, stats_data)

        # Resource utilization metrics
        utilization_metrics = [k for k in self.summary_statistics.keys()
                               if '_utilization' in k]

        if utilization_metrics:
            print("\nUTILIZACAO DE RECURSOS:")
            print("-" * 40)
            for metric_key in sorted(utilization_metrics):
                stats_data = self.summary_statistics[metric_key]
                resource_name = metric_key.replace('_utilization', '')
                metric_name = f"Taxa de utilizacao - {resource_name}"
                # Convert to percentage for display
                stats_pct = self._convert_to_percentage(stats_data)
                self._print_metric_statistics(metric_name, stats_pct, unit='%')

        # Precision analysis
        self._print_precision_analysis()

        print(f"\nNumero de replicacoes: {self.n_replications}")
        print(f"Nivel de confianca: 95%")
        print(f"Recomendacao: {self._get_replication_recommendation()}")

    def _print_section_metrics(self, title: str, metrics: List[tuple]):
        """Print a section of metrics."""
        print(f"\n{title}:")
        print("-" * 40)
        for metric_key, metric_name in metrics:
            if metric_key in self.summary_statistics:
                stats_data = self.summary_statistics[metric_key]
                self._print_metric_statistics(metric_name, stats_data)

    def _convert_to_percentage(self, stats_data: Dict) -> Dict:
        """Convert statistics to percentage scale."""
        stats_pct = stats_data.copy()
        for key in ['mean', 'ci_lower', 'ci_upper', 'std', 'min', 'max', 'half_width']:
            if key in stats_pct and not np.isnan(stats_pct[key]):
                stats_pct[key] = stats_pct[key] * 100
        return stats_pct

    def _print_metric_statistics(self, metric_name: str, stats_data: Dict, unit: str = ""):
        """Print statistics for a single metric, handling NaN."""
        def format_val(val):
            return f"{val:.2f}" if not np.isnan(val) else "N/A"

        mean = stats_data['mean']
        half_width = stats_data['half_width']
        ci_lower = stats_data['ci_lower']
        ci_upper = stats_data['ci_upper']
        precision = stats_data['relative_precision']
        std = stats_data['std']
        min_val = stats_data['min']
        max_val = stats_data['max']

        print(f"{metric_name}:")
        print(
            f"  Media: {format_val(mean)}{unit} +/- {format_val(half_width)}")
        print(
            f"  IC 95%: [{format_val(ci_lower)}, {format_val(ci_upper)}]{unit}")
        print(f"  Precisao: +/-{format_val(precision)}%")
        print(f"  Desvio padrao: {format_val(std)}")
        print(
            f"  Min-Max: [{format_val(min_val)}, {format_val(max_val)}]{unit}")
        print()

    def _print_precision_analysis(self):
        """Print precision analysis summary."""
        print("\nANALISE DE PRECISAO:")
        print("-" * 40)

        high_precision = []
        medium_precision = []
        low_precision = []

        for metric_key, stats_data in self.summary_statistics.items():
            if metric_key in ['replication_id']:
                continue
            precision = stats_data['relative_precision']
            if np.isnan(precision):
                continue

            if precision <= 5:
                high_precision.append((metric_key, precision))
            elif precision <= 10:
                medium_precision.append((metric_key, precision))
            else:
                low_precision.append((metric_key, precision))

        print(f"Alta precisao (<=5%): {len(high_precision)} metricas")
        print(f"Media precisao (5-10%): {len(medium_precision)} metricas")
        print(f"Baixa precisao (>10%): {len(low_precision)} metricas")

        if low_precision:
            print("\nMetricas com baixa precisao (considere mais replicacoes):")
            for metric, precision in sorted(low_precision, key=lambda x: x[1], reverse=True):
                print(f"  {metric}: {precision:.1f}%")

    def _get_replication_recommendation(self) -> str:
        """Provide recommendation for number of replications."""
        if not self.summary_statistics:
            return "Execute analise estatistica primeiro"

        valid_precisions = [stats_data['relative_precision']
                            for stats_data in self.summary_statistics.values()
                            if not np.isnan(stats_data['relative_precision'])]

        if not valid_precisions:
            return "Dados insuficientes para recomendacao"

        avg_precision = np.mean(valid_precisions)

        if avg_precision <= 5:
            return "Precisao excelente - numero adequado de replicacoes"
        elif avg_precision <= 10:
            return "Precisao boa - considere mais replicacoes para metricas criticas"
        elif avg_precision <= 20:
            return "Precisao moderada - recomenda-se dobrar o numero de replicacoes"
        else:
            return "Precisao baixa - aumente significativamente o numero de replicacoes"

    def plot_confidence_intervals(self, metrics_to_plot: Optional[List[str]] = None):
        """
        Plot confidence intervals for resource utilization metrics.

        Args:
            metrics_to_plot: List of specific metrics to plot (None = all utilization metrics)
        """
        if not self.summary_statistics:
            print("Estatisticas nao calculadas.")
            return

        # Get only resource utilization metrics
        utilization_metrics = [k for k in self.summary_statistics.keys()
                               if '_utilization' in k]

        if not utilization_metrics:
            print("Nenhuma metrica de utilizacao de recursos encontrada.")
            return

        # Filter available metrics
        available_metrics = [
            m for m in utilization_metrics if m in self.summary_statistics]

        if not available_metrics:
            print("Nenhuma metrica de utilizacao disponivel para plotar.")
            return

        # Create figure
        _fig, ax = plt.subplots(figsize=(10, 6))

        y_pos = np.arange(len(available_metrics))
        means = []
        half_widths = []
        labels = []

        # Define color palette
        colors = plt.cm.Set3(np.linspace(0, 1, len(available_metrics)))

        for metric in available_metrics:
            stats_data = self.summary_statistics[metric]

            # Convert to percentages
            mean_pct = stats_data['mean'] * 100
            half_width_pct = stats_data['half_width'] * 100

            means.append(mean_pct)
            half_widths.append(half_width_pct)

            # Clean up label - extract resource name
            resource_name = metric.replace(
                '_utilization', '').replace('_', ' ').title()
            labels.append(resource_name)

        # Create horizontal bar plot
        ax.barh(y_pos, means, xerr=half_widths, capsize=8,
                color=colors, edgecolor='black', linewidth=1, alpha=0.8)

        # Add value labels on bars
        for i, (mean, half_width) in enumerate(zip(means, half_widths)):
            label_text = f'{mean:.1f}% +/- {half_width:.1f}%'

            # Position label inside or outside bar based on bar width
            if mean > 15:
                ax.text(mean/2, i, label_text,
                        ha='center', va='center', fontweight='bold',
                        fontsize=9, color='black')
            else:
                ax.text(mean + half_width + 2, i, label_text,
                        ha='left', va='center', fontweight='bold',
                        fontsize=9, color='black')

        # Customize the plot
        ax.set_yticks(y_pos)
        ax.set_yticklabels(labels, fontsize=11)
        ax.set_xlabel('Taxa de Utilizacao (%)', fontsize=12, fontweight='bold')
        ax.set_title(f'Utilizacao de Recursos - Intervalos de Confianca 95%\n'
                     f'({self.n_replications} replicacoes)',
                     fontsize=14, fontweight='bold', pad=20)

        # Set x-axis from 0% to 100%
        ax.set_xlim(0, 100)

        # Add reference lines
        ax.axvline(x=85, color='red', linestyle='--', alpha=0.7, linewidth=1,
                   label='85% (Limite Critico)')
        ax.axvline(x=70, color='orange', linestyle='--', alpha=0.5, linewidth=1,
                   label='70% (Alta Utilizacao)')
        ax.axvline(x=50, color='green', linestyle='--', alpha=0.5, linewidth=1,
                   label='50% (Utilizacao Moderada)')
        ax.axvline(x=25, color='blue', linestyle='--', alpha=0.3, linewidth=1,
                   label='25% (Baixa Utilizacao)')

        # Add grid
        ax.grid(axis='x', alpha=0.3, linestyle='-')
        ax.set_axisbelow(True)

        # Add legend
        ax.legend(loc='lower right', framealpha=0.9, fontsize=9)

        plt.tight_layout()
        plt.show()

        # Print detailed resource analysis
        self._print_resource_analysis(available_metrics)

    def _print_resource_analysis(self, metrics: List[str]):
        """Print detailed resource utilization analysis."""
        print("\nANALISE DETALHADA DA UTILIZACAO DE RECURSOS:")
        print("=" * 55)

        for metric in metrics:
            stats_data = self.summary_statistics[metric]
            mean_util = stats_data['mean'] * 100
            half_width = stats_data['half_width'] * 100
            ci_lower = stats_data['ci_lower'] * 100
            ci_upper = stats_data['ci_upper'] * 100
            precision = stats_data['relative_precision']

            resource_name = metric.replace(
                '_utilization', '').replace('_', ' ').title()

            print(f"\n{resource_name}:")
            print(
                f"  Utilizacao media: {mean_util:.1f}% +/- {half_width:.1f}%")
            print(f"  IC 95%: [{ci_lower:.1f}%, {ci_upper:.1f}%]")
            print(f"  Precisao relativa: +/-{precision:.1f}%")

            # Recommendations based on utilization level
            if mean_util >= 90:
                print("  RECOMENDACAO: Recurso extremamente sobrecarregado!")
                print("     Aumentar capacidade urgentemente")
            elif mean_util >= 85:
                print("  RECOMENDACAO: Recurso sobrecarregado")
                print("     Considerar aumentar capacidade")
            elif mean_util >= 70:
                print("  RECOMENDACAO: Utilizacao alta")
                print("     Monitorar e avaliar necessidade de recursos adicionais")
            elif mean_util >= 50:
                print("  RECOMENDACAO: Utilizacao moderada e eficiente")
                print("     Nivel ideal para maioria dos sistemas")
            elif mean_util >= 25:
                print("  RECOMENDACAO: Utilizacao abaixo do ideal")
                print("     Avaliar redimensionamento ou redistribuicao")
            else:
                print("  RECOMENDACAO: Recurso subutilizado")
                print("     Considerar reducao de capacidade")

    def get_results_dataframe(self) -> pd.DataFrame:
        """
        Return results as a pandas DataFrame for further analysis.

        Returns:
            DataFrame with one row per replication
        """
        df = pd.DataFrame(self.replication_results)
        # print(df.columns)
        df.drop(['replication_id', 'simulation_time',
                 'warm_up_period', 'overall_throughput'], axis=1, inplace=True)
        # return pd.DataFrame(self.replication_results)
        return df

    def export_results(self, filename: str = "framework_results.csv"):
        """
        Export results to CSV file.

        Args:
            filename: Output CSV filename
        """
        df = self.get_results_dataframe()
        df.to_csv(filename, index=False)
        print(f"Resultados exportados para {filename}")



# ======================================================
# FILE: utils\helpers.py
# ======================================================

# =====================================================================
# FILE: utils/helpers.py
# =====================================================================


def safe_delay_time(delay_function: Callable[[], float]) -> float:
    """
    Ensure delay times are non-negative.

    Standalone helper function for delay time validation.

    Args:
        delay_function: Function returning delay time

    Returns:
        Non-negative delay time
    """
    delay = delay_function()
    return max(0.0, delay)



# ======================================================
# FILE: visualization\interface.py
# ======================================================

# =============================================================================
# FILE: visualization/generic_visualizer.py
# =============================================================================
"""
Generic real-time visualization interface for simulation models.

FIXES:
1. Connectors now properly exit/enter blocks from outside (not inside)
2. Entities flow smoothly along connector paths
3. Queue statistics now match visual queue counts

(USER FIX) 4. Play/Step buttons now correctly drive the simulation and animation
           incrementally, instead of running to completion.
"""


# =============================================================================
# Event System for Communication Between Simulation and GUI
# =============================================================================
@dataclass
class VisualizationEvent:
    """Event sent from simulation to GUI."""
    event_type: str  # 'entity_created', 'entity_moved', 'entity_disposed', 'stats_update'
    timestamp: float
    data: Dict[str, Any]


class EventQueue:
    """Thread-safe queue for passing events from simulation to GUI."""

    def __init__(self):
        self.queue = queue.Queue()

    def put(self, event: VisualizationEvent):
        """Add event to queue."""
        self.queue.put(event)

    def get_all(self) -> List[VisualizationEvent]:
        """Get all pending events."""
        events = []
        while not self.queue.empty():
            try:
                events.append(self.queue.get_nowait())
            except queue.Empty:
                break
        return events


# =============================================================================
# Model Inspector - Extracts Structure from Simulation Model
# =============================================================================
class ModelInspector:
    """Extracts structural information from simulation model."""

    @staticmethod
    def extract_structure(model) -> Dict[str, Any]:
        """
        Extract block information and connections from model.

        Returns:
            Dictionary with:
            - blocks: List of block names and types
            - connections: List of (from_block, to_block) tuples
            - resources: Dictionary of resource names and capacities
        """

        structure = {
            'blocks': {},
            'connections': [],
            'resources': {}
        }

        # Extract blocks
        for name, block in model.blocks.items():
            block_info = {
                'name': name,
                'type': type(block).__name__,
                'is_source': isinstance(block, CreateBlock),
                'is_sink': isinstance(block, DisposeBlock),
                'is_decision': isinstance(block, DecideBlock),
                'is_process': isinstance(block, (ProcessBlock, MultiProcessBlock))
            }
            structure['blocks'][name] = block_info

        # Extract connections (regular)
        for name, block in model.blocks.items():
            if block.next_block:
                structure['connections'].append((name, block.next_block.name))

        # Extract decision routes
        for name, block in model.blocks.items():
            if isinstance(block, DecideBlock):
                for route_name, route_info in block.routes.items():
                    target_block = route_info['block']
                    structure['connections'].append((name, target_block.name))

        # Extract resources
        for res_name, resource in model.resources.items():
            structure['resources'][res_name] = {
                'capacity': resource.capacity,
                'type': type(resource).__name__
            }

        return structure


# =============================================================================
# Auto-Layout Generator
# =============================================================================
class AutoLayout:
    """Automatically generates layout positions for blocks."""

    @staticmethod
    def generate(structure: Dict[str, Any],
                 canvas_width: int = 1000,
                 canvas_height: int = 600) -> Dict[str, Tuple[int, int]]:
        """
        Generate automatic layout using hierarchical approach.

        Args:
            structure: Model structure from ModelInspector
            canvas_width: Canvas width
            canvas_height: Canvas height

        Returns:
            Dictionary mapping block names to (x, y) coordinates
        """
        blocks = structure['blocks']
        connections = structure['connections']

        # Build adjacency list
        graph = {name: [] for name in blocks.keys()}
        for from_block, to_block in connections:
            graph[from_block].append(to_block)

        # Find source nodes (CreateBlocks)
        sources = [name for name, info in blocks.items() if info['is_source']]

        # Perform topological sort to get levels
        levels = AutoLayout._assign_levels(graph, sources)

        # Calculate positions
        positions = AutoLayout._calculate_positions(
            levels, canvas_width, canvas_height
        )

        return positions

    @staticmethod
    def _assign_levels(graph: Dict[str, List[str]],
                       sources: List[str]) -> Dict[str, int]:
        """Assign level (depth) to each node using BFS."""
        levels = {}
        visited = set()
        queue_bfs = [(source, 0) for source in sources]

        while queue_bfs:
            node, level = queue_bfs.pop(0)

            if node in visited:
                continue

            visited.add(node)
            levels[node] = level

            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    queue_bfs.append((neighbor, level + 1))

        # Assign level 0 to any unvisited nodes (disconnected)
        for node in graph.keys():
            if node not in levels:
                levels[node] = 0

        return levels

    @staticmethod
    def _calculate_positions(levels: Dict[str, int],
                             width: int, height: int) -> Dict[str, Tuple[int, int]]:
        """Calculate (x, y) positions based on levels."""
        # Group nodes by level
        level_groups = {}
        max_level = max(levels.values()) if levels else 0

        for node, level in levels.items():
            if level not in level_groups:
                level_groups[level] = []
            level_groups[level].append(node)

        positions = {}
        margin_x = 100
        margin_y = 80
        usable_width = width - 2 * margin_x
        usable_height = height - 2 * margin_y

        # Calculate spacing
        level_spacing = usable_width / \
            (max_level + 1) if max_level > 0 else usable_width

        for level, nodes in level_groups.items():
            x = margin_x + level * level_spacing

            # Vertical spacing within level
            n_nodes = len(nodes)
            if n_nodes == 1:
                y_positions = [height // 2]
            else:
                node_spacing = usable_height / (n_nodes - 1)
                y_positions = [margin_y + i *
                               node_spacing for i in range(n_nodes)]

            for node, y in zip(nodes, y_positions):
                positions[node] = (int(x), int(y))

        return positions


# =============================================================================
# Main Visualization GUI
# =============================================================================
class SimulationVisualizer:
    """
    Generic real-time visualization for simulation models.

    Usage:
        visualizer = SimulationVisualizer(model_builder)
        visualizer.run()  # Starts GUI in main thread
    """

    def __init__(self, model_builder,
                 canvas_width: int = 1000,
                 canvas_height: int = 600,
                 custom_positions: Optional[Dict[str, Tuple[int, int]]] = None):
        """
        Initialize visualizer.

        Args:
            model_builder: Function that returns a new model instance
            canvas_width: Canvas width in pixels
            canvas_height: Canvas height in pixels
            custom_positions: Optional manual positions for blocks
        """
        self.model_builder = model_builder
        self.model = self.model_builder()
        self.canvas_width = canvas_width
        self.canvas_height = canvas_height

        # Extract model structure and generate layout
        self.structure = ModelInspector.extract_structure(self.model)
        if custom_positions:
            self.positions = custom_positions
        else:
            self.positions = AutoLayout.generate(
                self.structure, canvas_width, canvas_height
            )

        # Event queue
        self.event_queue = EventQueue()

        # Instrument model
        self.instrument = VisualizationInstrument(self.model, self.event_queue)

        # GUI state
        self.root = None
        self.canvas = None
        self.entities_on_canvas = {}  # entity_id -> (circle, text)
        self.block_widgets = {}  # block_name -> widget_ids
        self.stats_labels = {}

        # Visualization state
        self.connection_paths = {}  # (from, to) -> [(x, y), ...]
        self.queue_areas = {}       # block_name -> (x1, y1, x2, y2)
        self.block_centers = {}     # block_name -> (x, y)
        self.entity_queue_slots = {}  # block_name -> [entity_id, ...]
        self.service_areas = {}     # block_name -> (x1, y1, x2, y2)
        self.entity_service_slots = {}  # block_name -> [entity_id, ...]
        self.resource_to_blocks_map = {}  # Maps res_name -> [block_name]

        # Map resources to blocks
        for res_name, res_obj in self.model.resources.items():
            self.resource_to_blocks_map[res_name] = []
            for block_name, block in self.model.blocks.items():
                if isinstance(block, ProcessBlock) and block.resource == res_obj:
                    self.resource_to_blocks_map[res_name].append(block_name)
                elif isinstance(block, MultiProcessBlock) and res_obj in block.resource_requirements:
                    self.resource_to_blocks_map[res_name].append(block_name)

        # Statistics tracking
        self.stats = {
            'total_created': 0,
            'total_disposed': 0,
            'current_wip': 0,
            'simulation_time': 0.0
        }

        # Animation settings
        self.animation_speed = 0.02  # seconds per step
        self.steps_per_move = 20

        # Playback control
        self.is_paused = True
        self.is_running = False
        self.speed_multiplier = 1.0

        # Control widgets
        self.play_button = None
        self.speed_label = None
        self.progress_bar = None
        self.step_pause_timer = None

        # (1) ADD: Simulation time limit (will be set by run())
        self._simulation_time_limit = float('inf')

    def setup_gui(self):
        """Setup tkinter GUI components."""
        self.root = tk.Tk()
        self.root.title("Simulation Visualizer")

        # Main container
        container = ttk.Frame(self.root)
        container.pack(fill=tk.BOTH, expand=True)

        # Control panel
        control_frame = ttk.Frame(container, relief=tk.RAISED, borderwidth=2)
        control_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        self._create_control_panel(control_frame)

        # Main content
        main_frame = ttk.Frame(container)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Canvas
        # self.canvas = ZoomableCanvas(
        self.canvas = tk.Canvas(
            main_frame,
            width=self.canvas_width,
            height=self.canvas_height,
            bg="white"
        )
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Stats panel
        stats_frame = ttk.Frame(main_frame, width=240)
        stats_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)
        stats_frame.pack_propagate(False)

        ttk.Label(stats_frame, text="Statistics",
                  font=("Arial", 12, "bold")).pack(pady=10)

        self._create_stats_panel(stats_frame)

        # Draw initial structure
        self._draw_blocks()
        self._draw_connections()

        # Setup shortcuts
        self._setup_keyboard_shortcuts()

        # Add legend
        self._draw_legend()

        # (3) MODIFY: Start event processing AND simulation tick
        self.root.after(50, self._process_events)
        self.root.after(50, self._simulation_tick)  # (1) ADD

    def _create_control_panel(self, parent):
        """Create playback control panel."""
        # Title
        title_label = ttk.Label(parent, text="▶ Simulation Controls",
                                font=("Arial", 11, "bold"))
        title_label.pack(side=tk.LEFT, padx=10)

        # Play/Pause button
        self.play_button = ttk.Button(
            parent, text="▶ Play",
            command=self._toggle_play_pause,
            width=10
        )
        self.play_button.pack(side=tk.LEFT, padx=5)

        # Reset button
        ttk.Button(
            parent, text="⟲ Reset",
            command=self._reset_simulation,
            width=10
        ).pack(side=tk.LEFT, padx=5)

        # Step forward button
        ttk.Button(
            parent, text="⏭ Step",
            command=self._step_forward,
            width=8
        ).pack(side=tk.LEFT, padx=5)

        # Speed controls
        ttk.Separator(parent, orient=tk.VERTICAL).pack(
            side=tk.LEFT, fill=tk.Y, padx=10
        )

        ttk.Label(parent, text="Speed:", font=("Arial", 10)).pack(
            side=tk.LEFT, padx=5
        )

        # Speed preset buttons
        speed_frame = ttk.Frame(parent)
        speed_frame.pack(side=tk.LEFT)

        speeds = [
            ("0.25x", 0.25),
            ("0.5x", 0.5),
            ("1x", 1.0),
            ("2x", 2.0),
            ("5x", 5.0),
            ("10x", 10.0),
            ("MAX", 50.0)
        ]

        for label, speed in speeds:
            btn = ttk.Button(
                speed_frame, text=label,
                command=lambda s=speed: self._set_speed(s),
                width=6
            )
            btn.pack(side=tk.LEFT, padx=2)

        # Current speed display
        ttk.Separator(parent, orient=tk.VERTICAL).pack(
            side=tk.LEFT, fill=tk.Y, padx=10
        )

        self.speed_label = ttk.Label(
            parent, text="Current: 1.0x",
            font=("Arial", 10, "bold"),
            foreground="blue"
        )
        self.speed_label.pack(side=tk.LEFT, padx=5)

        # Progress indicator
        ttk.Separator(parent, orient=tk.VERTICAL).pack(
            side=tk.LEFT, fill=tk.Y, padx=10
        )

        status_frame = ttk.Frame(parent)
        status_frame.pack(side=tk.LEFT, padx=5)

        ttk.Label(status_frame, text="Status:",
                  font=("Arial", 9)).pack(anchor=tk.W)

        self.status_label = ttk.Label(
            status_frame, text="Ready",
            font=("Arial", 9, "bold"),
            foreground="green"
        )
        self.status_label.pack(anchor=tk.W)

        # Keyboard shortcuts hint
        ttk.Separator(parent, orient=tk.VERTICAL).pack(
            side=tk.LEFT, fill=tk.Y, padx=10
        )

        ttk.Label(parent, text="⌨ Space=Play/Pause  R=Reset",
                  font=("Arial", 8), foreground="gray").pack(side=tk.LEFT, padx=5)

    def _create_stats_panel(self, parent):
        """Create statistics display panel."""
        # General stats
        ttk.Label(parent, text="Simulation Time:",
                  font=("Arial", 10)).pack(anchor=tk.W)
        self.stats_labels['simulation_time'] = ttk.Label(
            parent, text="0.0", font=("Arial", 10))
        self.stats_labels['simulation_time'].pack(anchor=tk.W)

        ttk.Label(parent, text="Entities Created:",
                  font=("Arial", 10)).pack(anchor=tk.W)
        self.stats_labels['total_created'] = ttk.Label(
            parent, text="0", font=("Arial", 10))
        self.stats_labels['total_created'].pack(anchor=tk.W)

        ttk.Label(parent, text="Entities Disposed:",
                  font=("Arial", 10)).pack(anchor=tk.W)
        self.stats_labels['total_disposed'] = ttk.Label(
            parent, text="0", font=("Arial", 10))
        self.stats_labels['total_disposed'].pack(anchor=tk.W)

        ttk.Label(parent, text="Current WIP:",
                  font=("Arial", 10)).pack(anchor=tk.W)
        self.stats_labels['current_wip'] = ttk.Label(
            parent, text="0", font=("Arial", 10))
        self.stats_labels['current_wip'].pack(anchor=tk.W)

        # Resources section
        ttk.Separator(parent, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        ttk.Label(parent, text="Resources", font=(
            "Arial", 10, "bold")).pack(anchor=tk.W)

        # for res_name in sorted(self.structure['resources'].keys()):
        #     res_frame = ttk.Frame(parent)
        #     res_frame.pack(fill=tk.X, pady=2)
        #     ttk.Label(res_frame, text=f"{res_name}:", width=10).pack(side=tk.LEFT)
        #     ttk.Label(res_frame, text="Util:").pack(side=tk.LEFT, padx=2)
        #     util_key = f"{res_name}_util"
        #     self.stats_labels[util_key] = ttk.Label(res_frame, text="0.00%", width=8)
        #     self.stats_labels[util_key].pack(side=tk.LEFT)
        #     ttk.Label(res_frame, text="Queue:").pack(side=tk.LEFT, padx=2)
        #     queue_key = f"{res_name}_queue"
        #     self.stats_labels[queue_key] = ttk.Label(res_frame, text="0", width=5)
        #     self.stats_labels[queue_key].pack(side=tk.LEFT)
        for res_name in sorted(self.structure['resources'].keys()):
            resource = self.model.resources[res_name]
            capacity = resource.capacity  # <-- directly from simpy.Resource

            res_frame = ttk.Frame(parent)
            res_frame.pack(fill=tk.X, pady=2)

            # Shows "4 doctors:" or "2 nurses:"
            ttk.Label(res_frame, text=f"{capacity} {res_name}:", width=14).pack(
                side=tk.LEFT)

            ttk.Label(res_frame, text="Util:").pack(side=tk.LEFT, padx=2)
            util_key = f"{res_name}_util"
            self.stats_labels[util_key] = ttk.Label(
                res_frame, text="0.00%", width=8)
            self.stats_labels[util_key].pack(side=tk.LEFT)

            ttk.Label(res_frame, text="Queue:").pack(side=tk.LEFT, padx=2)
            queue_key = f"{res_name}_queue"
            self.stats_labels[queue_key] = ttk.Label(
                res_frame, text="0", width=5)
            self.stats_labels[queue_key].pack(side=tk.LEFT)

    def _draw_blocks(self):
        """Draw all blocks on canvas."""
        block_width = 120
        block_height = 40
        for name, (x, y) in self.positions.items():
            info = self.structure['blocks'][name]
            if info['is_source']:
                color = "lightgreen"
            elif info['is_sink']:
                color = "lightpink"
            elif info['is_decision']:
                color = "lightyellow"
            else:
                color = "lightblue"
            x1 = x - block_width / 2
            y1 = y - block_height / 2
            x2 = x + block_width / 2
            y2 = y + block_height / 2

            # rect = self.canvas.create_rectangle(x1, y1, x2, y2, fill=color)
            # text = self.canvas.create_text(x, y, text=name, width=block_width - 10, justify=tk.CENTER)
            # self.block_widgets[name] = (rect, text)
            # self.block_centers[name] = (x, y)

            # Draw diamond for DECIDE blocks
            if info['is_decision']:
                diamond_points = [
                    x, y - 35,     # top
                    x + 60, y,     # right
                    x, y + 35,     # bottom
                    x - 60, y      # left
                ]
                shape = self.canvas.create_polygon(
                    diamond_points, fill=color, outline="black", width=2
                )
                text = self.canvas.create_text(
                    x, y, text=name, font=("Arial", 9, "bold"))
                self.block_widgets[name] = (shape, text)
                self.block_centers[name] = (x, y)

            # Default rectangle for others
            else:
                rect = self.canvas.create_rectangle(x1, y1, x2, y2, fill=color)
                text = self.canvas.create_text(
                    x, y, text=name, width=block_width - 10, justify=tk.CENTER)
                self.block_widgets[name] = (rect, text)
                self.block_centers[name] = (x, y)

            if info['is_process']:
                # Queue area above
                q_y1 = y1 - block_height
                q_y2 = y1
                self.queue_areas[name] = (x1, q_y1, x2, q_y2)
                self.canvas.create_rectangle(
                    self.queue_areas[name], dash=(2, 2), fill="white")
                self.entity_queue_slots.setdefault(name, [])
                # Service area
                self.service_areas[name] = (x1, y1, x2, y2)
                self.entity_service_slots.setdefault(name, [])

    def _draw_connections(self):
        """Draw connections between blocks with correct arrow direction."""
        for from_name, to_name in self.structure['connections']:
            from_pos = self.positions[from_name]
            to_pos = self.positions[to_name]
            x1 = from_pos[0] + 60  # right side
            y1 = from_pos[1]
            x2 = to_pos[0] - 60  # left side
            y2 = to_pos[1]
            # Draw line with arrow at the end (-->)
            self.canvas.create_line(x1, y1, x2, y2, arrow=tk.LAST, width=2)
            # Path for animation
            path = []
            num_points = 20
            for i in range(num_points + 1):
                t = i / num_points
                px = x1 + t * (x2 - x1)
                py = y1 + t * (y2 - y1)
                path.append((px, py))
            self.connection_paths[(from_name, to_name)] = path

    def _draw_legend(self):
        """Draw legend for block types."""
        legend_x = self.canvas_width - 160
        legend_y = 10
        self.canvas.create_rectangle(
            legend_x, legend_y, legend_x + 150, legend_y + 110, fill="lightgray", outline="black")
        self.canvas.create_text(
            legend_x + 75, legend_y + 10, text="Block Types", font=("Arial", 10, "bold"))
        items = [
            ("CREATE (Source)", "lightgreen"),
            ("DISPOSE (Sink)", "lightpink"),
            # ("DECIDE (Decision)", "lightyellow"),
            ("DECIDE (Decision) ◆", "lightyellow"),
            ("PROCESS (Activity)", "lightblue")
        ]
        dy = 25
        for text, color in items:
            self.canvas.create_rectangle(
                legend_x + 10, legend_y + dy, legend_x + 30, legend_y + dy + 15, fill=color)
            self.canvas.create_text(
                legend_x + 40, legend_y + dy + 7.5, text=text, anchor=tk.W)
            dy += 20

    def _process_events(self):
        """Process pending visualization events."""
        events = self.event_queue.get_all()
        for event in events:
            if event.event_type == 'entity_created':
                self._handle_entity_created(event)
            elif event.event_type == 'entity_moved':
                self._handle_entity_moved(event)
            elif event.event_type == 'entity_disposed':
                self._handle_entity_disposed(event)
            elif event.event_type == 'stats_update':
                self._handle_stats_update(event)

        # (3) MODIFY: Reschedule itself
        self.root.after(50, self._process_events)

    def _handle_entity_created(self, event):
        """Handle entity creation event."""
        data = event.data
        entity_id = data['entity_id']
        entity_number = data['entity_number']
        block_name = data['block_name']
        x, y = self.block_centers[block_name]
        circle = self.canvas.create_oval(x-12, y-12, x+12, y+12, fill="red")
        text = self.canvas.create_text(
            x, y-1, text=str(entity_number), fill="white", font=("Arial", 8, "bold"))
        self.entities_on_canvas[entity_id] = (circle, text)
        self.stats['total_created'] += 1
        self.stats['current_wip'] += 1
        self._update_stats_display()

    def _handle_entity_moved(self, event):
        """Handle entity moved event."""
        data = event.data
        entity_id = data['entity_id']
        from_block = data['from_block']
        to_block = data['to_block']
        state = data['state']
        if entity_id not in self.entities_on_canvas:
            return
        circle, text = self.entities_on_canvas[entity_id]
        self._animate_move_along_path(
            entity_id, circle, text, from_block, to_block, state)

    def _handle_entity_disposed(self, event):
        """Handle entity disposed event."""
        entity_id = event.data['entity_id']
        if entity_id in self.entities_on_canvas:
            circle, text = self.entities_on_canvas[entity_id]
            self.canvas.delete(circle)
            self.canvas.delete(text)
            del self.entities_on_canvas[entity_id]
        self.stats['total_disposed'] += 1
        self.stats['current_wip'] -= 1
        self._update_stats_display()

    # (2) REMOVE: The old simulation thread function
    # def _start_simulation_thread(self): ...

    # (1) ADD: New function to initialize SimPy generators
    def _initialize_simulation(self):
        """Initializes the SimPy generators."""
        try:
            for block in self.model.blocks.values():
                if isinstance(block, CreateBlock):
                    self.model.env.process(block._generation_process())
            self.is_running = True  # Mark as "ready to run"
            self.is_paused = True  # Start paused
        except Exception as e:
            messagebox.showerror("Initialization Error", str(e))
            self.is_running = False

    # (1) ADD: New function to drive the simulation from the GUI thread
    def _simulation_tick(self):
        """Advances the simulation by one step or time interval."""

        # 1. Check if simulation is running and not paused
        if not self.is_running or self.is_paused:
            # If paused or stopped, just check again later
            self.root.after(100, self._simulation_tick)  # Check again in 100ms
            return

        # 2. Check if simulation is complete
        # (Compare against sim time limit OR check if events are exhausted)
        next_event_time = self.model.env.peek()
        is_complete = (self.model.env.now >= self._simulation_time_limit) or \
                      (next_event_time == float('inf'))

        if is_complete:
            self.is_running = False
            self.is_paused = True
            self.play_button.config(text="▶ Play")
            self.status_label.config(text="Completed", foreground="green")
            # Keep the loop alive but inactive
            self.root.after(100, self._simulation_tick)
            return

        # 3. Determine how far to run
        # self.animation_speed is 'seconds per step' (e.g., 0.02)
        # self.speed_multiplier is (e.g., 1.0, 2.0, 10.0)

        # The 'delay_ms' for the GUI update is based on animation_speed
        delay_ms = max(1, int(self.animation_speed * 1000))

        # How much *simulation time* should pass per tick?
        # Let's define a 'tick_duration' in sim time.
        # This should be proportional to the speed multiplier.
        # Let's say 1 tick = 0.1 sim time units at 1x speed.
        sim_step = 0.1 * self.speed_multiplier

        # If speed is MAX (50.0), run for a larger chunk.
        if self.speed_multiplier >= 50.0:
            sim_step = 5.0 * self.speed_multiplier  # Run much faster
            delay_ms = 1  # Update GUI as fast as possible

        run_until = self.model.env.now + sim_step

        # Don't run past the end time
        run_until = min(run_until, self._simulation_time_limit)

        # ... but also don't run past the next scheduled event if we are running slowly
        if self.speed_multiplier < 5.0:
            run_until = min(run_until, next_event_time + 0.00001)

        # 4. Run the simulation for that interval
        try:
            self.model.env.run(until=run_until)
        except Exception as e:
            # Catch simulation errors
            messagebox.showerror("Simulation Error", str(e))
            self.is_running = False
            self.is_paused = True
            self.status_label.config(text="Error", foreground="red")
            return

        # 5. Reschedule the next tick
        # The delay_ms controls the *visual* refresh rate.
        self.root.after(delay_ms, self._simulation_tick)

    def _setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts for controls."""
        self.root.bind('<space>', lambda e: self._toggle_play_pause())
        self.root.bind('r', lambda e: self._reset_simulation())
        self.root.bind('R', lambda e: self._reset_simulation())
        self.root.bind('1', lambda e: self._set_speed(1.0))
        self.root.bind('2', lambda e: self._set_speed(2.0))
        self.root.bind('5', lambda e: self._set_speed(5.0))
        self.root.bind('0', lambda e: self._set_speed(0.5))
        self.root.bind('<Right>', lambda e: self._step_forward())

    # (3) MODIFY: Step button logic
    def _step_forward(self):
        """Advance simulation by one event."""
        if self.step_pause_timer:
            self.root.after_cancel(self.step_pause_timer)
            self.step_pause_timer = None

        # Ensure we are paused
        if not self.is_paused:
            self.is_paused = True
            self.play_button.config(text="▶ Play")

        # Check if simulation is over
        next_event_time = self.model.env.peek()
        is_complete = (not self.is_running) or \
                      (self.model.env.now >= self._simulation_time_limit) or \
                      (next_event_time == float('inf'))

        if is_complete:
            self.is_running = False
            self.status_label.config(text="Completed", foreground="green")
            return

        # Set status
        self.status_label.config(text="Stepping...", foreground="blue")

        # Run one simulation step
        try:
            # Run until just after the next event
            run_until = min(next_event_time + 0.00001,
                            self._simulation_time_limit)
            self.model.env.run(until=run_until)

            # Schedule a status update back to 'Paused'
            self.step_pause_timer = self.root.after(
                100, self._auto_pause_after_step)

        except Exception as e:
            messagebox.showerror("Simulation Error", str(e))
            self.is_running = False
            self.status_label.config(text="Error", foreground="red")

    # (3) MODIFY: Play/Pause button logic
    def _toggle_play_pause(self):
        """Toggle between play and pause."""
        if self.step_pause_timer:
            self.root.after_cancel(self.step_pause_timer)
            self.step_pause_timer = None

        # If simulation is finished, pressing Play should Reset
        next_event_time = self.model.env.peek()
        is_complete = (not self.is_running) or \
                      (self.model.env.now >= self._simulation_time_limit) or \
                      (next_event_time == float('inf'))

        if is_complete and not self.is_paused:  # If already finished, pause it
            self.is_paused = True
        elif is_complete and self.is_paused:  # If finished and paused, reset
            self._reset_simulation()
            # After reset, we want to start playing
            self.is_paused = False
            self.is_running = True
            self.play_button.config(text="⏸ Pause")
            self.status_label.config(text="Running", foreground="green")
            return

        # Standard toggle
        self.is_paused = not self.is_paused

        if self.is_paused:
            self.play_button.config(text="▶ Play")
            self.status_label.config(text="Paused", foreground="orange")
        else:
            self.play_button.config(text="⏸ Pause")
            self.status_label.config(text="Running", foreground="green")

            if not self.is_running:
                # This will be true on the very first play click
                self.is_running = True

    def _set_speed(self, multiplier: float):
        """Set simulation speed multiplier."""
        self.speed_multiplier = multiplier

        # (3) MODIFY: Adjust animation speed based on multiplier
        # A higher multiplier should make the animation *faster* (smaller delay)
        base_animation_speed = 0.02  # seconds per step
        self.animation_speed = base_animation_speed / \
            (multiplier**0.5)  # Use sqrt for less extreme speedup

        if multiplier >= 50.0:
            self.animation_speed = 0.0  # Max speed = no animation delay

        self.speed_label.config(text=f"Current: {multiplier}x")

        if multiplier >= 5:
            self.speed_label.config(foreground="red")
        elif multiplier >= 2:
            self.speed_label.config(foreground="orange")
        else:
            self.speed_label.config(foreground="blue")

    # (3) MODIFY: Reset logic
    def _reset_simulation(self):
        """Reset simulation to initial state."""
        # Clear entities
        for entity_id, (circle, text) in list(self.entities_on_canvas.items()):
            self.canvas.delete(circle)
            self.canvas.delete(text)

        self.entities_on_canvas.clear()

        # (1) ADD: Clear queue/service slots
        self.entity_queue_slots.clear()
        self.entity_service_slots.clear()

        # Reset stats
        self.stats = {
            'total_created': 0,
            'total_disposed': 0,
            'current_wip': 0,
            'simulation_time': 0.0
        }
        # (1) ADD: Clear derived stats
        for key in list(self.stats_labels.keys()):
            if key.endswith('_util'):
                self.stats_labels[key].config(text="0.00%")
            elif key.endswith('_queue'):
                self.stats_labels[key].config(text="0")

        self._update_stats_display()

        # Rebuild model
        self.model = self.model_builder()
        self.instrument = VisualizationInstrument(self.model, self.event_queue)

        # Re-extract structure (original code was missing this, but it's not
        # strictly necessary if structure is identical, but good practice)
        self.structure = ModelInspector.extract_structure(self.model)
        if hasattr(self, 'custom_positions') and self.custom_positions:
            self.positions = self.custom_positions
        else:
            self.positions = AutoLayout.generate(
                self.structure, self.canvas_width, self.canvas_height
            )

        # Redraw
        self.canvas.delete("all")
        self._draw_blocks()
        self._draw_connections()
        self._draw_legend()

        # (1) ADD: Re-initialize the SimPy generators
        self._initialize_simulation()

        # (1) ADD: Reset playback state
        self.is_paused = True
        self.is_running = True  # It's "running" in the sense that it's ready
        self.play_button.config(text="▶ Play")
        self.status_label.config(text="Ready", foreground="green")

        if self.step_pause_timer:
            self.root.after_cancel(self.step_pause_timer)
            self.step_pause_timer = None

    def _handle_stats_update(self, event):
        """Handle statistics update event."""
        self.stats['simulation_time'] = event.data.get('time', 0)

        # Update resource utilization (NOT queue - we calculate that visually)
        for key, value in event.data.items():
            if key.endswith('_util'):
                self.stats[key] = value

        self._update_stats_display()

    def _animate_move_along_path(self, entity_id, circle, text, from_block, to_block, state):
        """
        Animate entity movement along a pre-defined path.
        FIX: Entities now follow connector paths smoothly.
        """

        # Remove from previous position before animating
        if from_block:
            if from_block in self.entity_queue_slots and entity_id in self.entity_queue_slots[from_block]:
                self.entity_queue_slots[from_block].remove(entity_id)
                self._reposition_queue(from_block)
            if from_block in self.entity_service_slots and entity_id in self.entity_service_slots[from_block]:
                self.entity_service_slots[from_block].remove(entity_id)
                self._reposition_service(from_block)

        # Case 1: Move from queue to service (within same block)
        if from_block == to_block and state == 'service':
            target_x, target_y = self.block_centers[to_block]
            self._animate_segment(entity_id, circle, text, [
                                  (target_x, target_y)], 0, to_block, state)
            return

        # Case 2: Move between different blocks
        path_segments = self.connection_paths.get((from_block, to_block))

        if not path_segments:
            # No predefined path - snap to target
            target_x, target_y = (0, 0)
            if state == 'queue' and to_block in self.queue_areas:
                if entity_id not in self.entity_queue_slots[to_block]:
                    self.entity_queue_slots[to_block].append(entity_id)
                self._reposition_queue(to_block)
                return
            else:
                target_x, target_y = self.block_centers[to_block]

            self.canvas.moveto(circle, target_x - 12, target_y - 12)
            self.canvas.moveto(text, target_x, target_y - 1)
            return

        # Start recursive animation along the path
        self._animate_segment(entity_id, circle, text,
                              path_segments, 0, to_block, state)

    def _animate_segment(self, entity_id, circle, text, path_segments, index, final_block, final_state):
        """
        Recursively animates one segment of a path.
        FIX: Smooth animation along connector paths.
        """
        if index >= len(path_segments):
            # Animation complete, place entity
            if final_state == 'queue' and final_block in self.queue_areas:
                if entity_id not in self.entity_queue_slots[final_block]:
                    self.entity_queue_slots[final_block].append(entity_id)
                self._reposition_queue(final_block)
            elif final_state == 'service' and final_block in self.service_areas:
                if entity_id not in self.entity_service_slots[final_block]:
                    self.entity_service_slots[final_block].append(entity_id)
                self._reposition_service(final_block)
            else:
                if entity_id not in self.entity_service_slots.get(final_block, []):
                    self.entity_service_slots.setdefault(
                        final_block, []).append(entity_id)
                self._reposition_service(final_block)
            return

        # Get current position
        try:
            x1, y1, x2, y2 = self.canvas.coords(circle)
            current_x = (x1 + x2) / 2
            current_y = (y1 + y2) / 2
        except:
            return

        target_x, target_y = path_segments[index]

        dx = target_x - current_x
        dy = target_y - current_y

        steps_to_move = max(1, int(self.steps_per_move / len(path_segments)))

        # (3) MODIFY: Handle "MAX" speed (no animation)
        if self.speed_multiplier >= 50.0:
            steps_to_move = 1

        step_dx = dx / steps_to_move
        step_dy = dy / steps_to_move

        def animation_loop(step):
            if step >= steps_to_move:
                # Segment complete, move to next
                self._animate_segment(
                    entity_id, circle, text, path_segments, index + 1, final_block, final_state)
                return

            try:
                self.canvas.move(circle, step_dx, step_dy)
                self.canvas.move(text, step_dx, step_dy)
                # (3) MODIFY: Only call canvas.update() if at max speed
                if self.speed_multiplier >= 50.0:
                    self.canvas.update()
            except tk.TclError:
                return

            delay_ms = max(1, int(self.animation_speed * 1000))

            # (3) MODIFY: At MAX speed, don't use root.after, just loop
            if self.speed_multiplier >= 50.0:
                animation_loop(step + 1)
            else:
                self.root.after(delay_ms, lambda: animation_loop(step + 1))

        animation_loop(0)

    def _reposition_queue(self, block_name):
        """Repositions all entities in a block's queue area."""
        if block_name not in self.queue_areas:
            return

        q_area = self.queue_areas[block_name]
        queue = self.entity_queue_slots.get(block_name, [])

        slot_width = 24
        max_in_row = int((q_area[2] - q_area[0]) / slot_width)

        for i, entity_id in enumerate(queue):
            if entity_id not in self.entities_on_canvas:
                continue

            circle, text = self.entities_on_canvas[entity_id]

            x = q_area[0] + (i % max_in_row * slot_width) + (slot_width / 2)
            y = (q_area[1] + q_area[3]) / 2

            try:
                self.canvas.moveto(circle, x - 12, y - 12)
                self.canvas.moveto(text, x, y - 1)
            except tk.TclError:
                continue
        # ADD at the END of the method:
        self._update_stats_display()  # Force immediate update

    def _reposition_service(self, block_name):
        """Repositions all entities in a block's service area."""
        if block_name not in self.service_areas:
            if block_name not in self.block_centers:
                return
            target_x, target_y = self.block_centers[block_name]
            service_list = self.entity_service_slots.get(block_name, [])
            for entity_id in service_list:
                if entity_id in self.entities_on_canvas:
                    circle, text = self.entities_on_canvas[entity_id]
                    try:
                        self.canvas.moveto(
                            circle, target_x - 12, target_y - 12)
                        self.canvas.moveto(text, target_x, target_y - 1)
                    except tk.TclError:
                        pass
            self._update_stats_display()  # Force immediate update
            return

        s_area = self.service_areas[block_name]
        service_list = self.entity_service_slots.get(block_name, [])

        slot_width = 24
        max_in_row = int((s_area[2] - s_area[0]) / slot_width)
        if max_in_row == 0:
            max_in_row = 1

        for i, entity_id in enumerate(service_list):
            if entity_id not in self.entities_on_canvas:
                continue

            circle, text = self.entities_on_canvas[entity_id]

            x = s_area[0] + (i % max_in_row * slot_width) + (slot_width / 2)
            y = (s_area[1] + s_area[3]) / 2

            try:
                self.canvas.moveto(circle, x - 12, y - 12)
                self.canvas.moveto(text, x, y - 1)
            except tk.TclError:
                continue
        # ADD at the END of the method:
        self._update_stats_display()  # Force immediate update

    def _update_stats_display(self):
        """
        Update statistics labels.
        FIX: Queue counts now reflect VISUAL queue (not SimPy's internal queue).
        """
        for key, label in self.stats_labels.items():
            if key in self.stats:
                value = self.stats[key]

                if key == 'simulation_time':
                    label.config(text=f"{value:.1f}")
                elif key.endswith('_util'):
                    label.config(text=f"{value:.2f}%")
                else:
                    label.config(text=str(int(value)))

            # FIX: Calculate queue count from VISUAL queues
            elif key.endswith('_queue'):
                res_name = key.replace('_queue', '')
                blocks_for_this_resource = self.resource_to_blocks_map.get(
                    res_name, [])

                # Sum lengths of visual queues for all blocks using this resource
                total_queue_count = 0
                for block_name in blocks_for_this_resource:
                    total_queue_count += len(
                        self.entity_queue_slots.get(block_name, []))

                label.config(text=str(total_queue_count))

            # ADD debugging (temporary):
            elif key.endswith('_queue'):
                res_name = key.replace('_queue', '')
                blocks_for_this_resource = self.resource_to_blocks_map.get(
                    res_name, [])

                total_queue_count = 0
                for block_name in blocks_for_this_resource:
                    queue_len = len(
                        self.entity_queue_slots.get(block_name, []))
                    total_queue_count += queue_len
                    # DEBUG: Print to console
                    if queue_len > 0:
                        # (3) MODIFY: Comment out debug print
                        # print(f"[DEBUG] {res_name} @ {block_name}: {queue_len} in queue")
                        pass

                label.config(text=str(total_queue_count))

    def _auto_pause_after_step(self):
        """Called by timer to re-pause after a step."""
        self.is_paused = True
        self.play_button.config(text="▶ Play")
        self.status_label.config(text="Paused", foreground="orange")
        self.step_pause_timer = None

    # (3) MODIFY: Run method
    def run(self):
        """Start the visualizer (blocks until window closed)."""

        print("=" * 120)
        print(
            f"{'Time':<8} | {'Event':<22}  | {'Entity':<15} | {'Resource':<30} | {'Details':<50}")
        print("-" * 120)

        self.setup_gui()
        self._initialize_simulation()  # (1) ADD: Initialize generators
        self.root.mainloop()


# =============================================================================
# Instrumentation for Simulation Model
# =============================================================================
class VisualizationInstrument:
    """
    Instruments a simulation model to send events to visualizer.
    """

    def __init__(self, model, event_queue: EventQueue):
        self.model = model
        self.event_queue = event_queue
        self.entity_counter = 0
        self.entity_locations = {}

        self._instrument_blocks()

    def _instrument_blocks(self):
        """Wrap block methods to send visualization events."""

        for name, block in self.model.blocks.items():
            original_process = block.process_entity

            if isinstance(block, CreateBlock):
                original_gen = block._generation_process
                block._generation_process = self._wrap_create_generator(
                    original_gen, block
                )
            elif isinstance(block, DisposeBlock):
                block.process_entity = self._wrap_dispose(
                    original_process, block)
            elif isinstance(block, (ProcessBlock, MultiProcessBlock)):
                # block.process_entity = self._wrap_process(original_process, block)
                # ✅ NEW: Special handling for ProcessBlocks
                block.process_entity = self._wrap_process_with_resource_check(
                    original_process, block
                )
                original_log_start = block.log_start
                block.log_start = self._wrap_log_start(
                    original_log_start, block.name)
            else:
                block.process_entity = self._wrap_process(
                    original_process, block)

            original_log_complete = block.log_complete
            block.log_complete = self._wrap_log_complete(
                original_log_complete, block.name)

    # ✅ NEW METHOD: Resource-aware process wrapping
    def _wrap_process_with_resource_check(self, original_func, block):
        """
        Wrap ProcessBlock with resource availability checking.

        Logic:
        - If resource has available capacity -> go directly to 'service'
        - If resource is full -> go to 'queue' first, then 'service' when seized
        """

        def wrapped(entity):
            entity_id = self._get_entity_id(entity)
            from_block, old_state = self.entity_locations.get(
                entity_id, (None, 'service'))

            # ✅ CHECK: Determine if entity should queue or go directly to service
            should_queue = False

            if isinstance(block, ProcessBlock) and block.resource:
                # Check if resource is at full capacity
                resource = block.resource
                units_needed = getattr(block, 'resource_units', 1)
                available_capacity = resource.capacity - resource.count

                should_queue = (available_capacity < units_needed)

            elif isinstance(block, MultiProcessBlock):
                # Check if ALL required resources are available
                all_available = True
                for resource, units_needed in block.resource_requirements.items():
                    available_capacity = resource.capacity - resource.count
                    if available_capacity < units_needed:
                        all_available = False
                        break

                should_queue = not all_available

            # ✅ SET STATE: Based on resource availability
            new_state = 'queue' if should_queue else 'service'

            self.entity_locations[entity_id] = (block.name, new_state)

            # Send movement event
            self.event_queue.put(VisualizationEvent(
                event_type='entity_moved',
                timestamp=self.model.env.now,
                data={
                    'entity_id': entity_id,
                    'from_block': from_block,
                    'to_block': block.name,
                    'state': new_state
                }
            ))

            self._send_stats_update()

            # Small timeout for GUI update
            yield self.model.env.timeout(0.001)
            yield from original_func(entity)

        return wrapped

    def _wrap_create_generator(self, original_gen_func, block):
        """Wrap CreateBlock generator to track entity creation."""
        def new_wrapped_generator():
            for item in original_gen_func():
                # ✅ Changed > 0 to > 1
                if hasattr(block, 'entities_created') and block.entities_created > 1:
                    entity_num = block.entities_created - 1  # This is AFTER increment
                    # ✅ FIX: Remove -1
                    entity_id = f"{block.entity_prefix}_{entity_num}"

                    if entity_id not in self.entity_locations:
                        self.event_queue.put(VisualizationEvent(
                            event_type='entity_created',
                            timestamp=self.model.env.now,
                            data={
                                'entity_id': entity_id,
                                'entity_number': entity_num,
                                'block_name': block.name
                            }
                        ))
                        self.entity_locations[entity_id] = (
                            block.name, 'service')
                        self._send_stats_update()

                yield item

        return new_wrapped_generator

    def _wrap_process(self, original_func, block):
        """Wrap block processing to track movements."""
        def wrapped(entity):
            entity_id = self._get_entity_id(entity)

            from_block, old_state = self.entity_locations.get(
                entity_id, (None, 'service'))

            is_process = hasattr(block, 'resource') or hasattr(
                block, 'resource_requirements')
            new_state = 'queue' if is_process else 'service'

            self.entity_locations[entity_id] = (block.name, new_state)

            self.event_queue.put(VisualizationEvent(
                event_type='entity_moved',
                timestamp=self.model.env.now,
                data={
                    'entity_id': entity_id,
                    'from_block': from_block,
                    'to_block': block.name,
                    'state': new_state
                }
            ))

            if new_state == 'queue':
                self._send_stats_update()

            # (3) MODIFY: Add a small timeout to allow GUI to update
            # This helps visualization feel more "real-time"
            yield self.model.env.timeout(0.001)
            yield from original_func(entity)

        return wrapped

    def _wrap_log_start(self, original_log_start, block_name):
        """
        Wrap log_start to move entity from queue to service.

        ✅ FIXED: This is called when resource is actually SEIZED.
        If entity was in queue, it now moves to service.
        """
        def wrapped(entity, resource_name=None):
            original_log_start(entity, resource_name)

            entity_id = self._get_entity_id(entity)
            current_block, current_state = self.entity_locations.get(
                entity_id, (block_name, 'queue')
            )

            # ✅ ONLY send event if entity was actually in queue
            if current_state == 'queue':
                self.entity_locations[entity_id] = (block_name, 'service')

                self.event_queue.put(VisualizationEvent(
                    event_type='entity_moved',
                    timestamp=self.model.env.now,
                    data={
                        'entity_id': entity_id,
                        'from_block': block_name,
                        'to_block': block_name,
                        'state': 'service'
                    }
                ))
                self._send_stats_update()

        return wrapped

    def _wrap_log_complete(self, original_log_complete, block_name):
        """Wrap log_complete to mark entity as ready to move."""
        def wrapped(entity, resource_name=None):
            original_log_complete(entity, resource_name)

            entity_id = self._get_entity_id(entity)
            self.entity_locations[entity_id] = (block_name, 'complete')
        return wrapped

    def _wrap_dispose(self, original_func, block):
        """Wrap DisposeBlock to track disposal."""
        def wrapped(entity):
            entity_id = self._get_entity_id(entity)
            from_block, old_state = self.entity_locations.get(
                entity_id, (None, 'service'))

            self.event_queue.put(VisualizationEvent(
                event_type='entity_moved',
                timestamp=self.model.env.now,
                data={
                    'entity_id': entity_id,
                    'from_block': from_block,
                    'to_block': block.name,
                    'state': 'service'
                }
            ))

            # (3) MODIFY: Add a small timeout
            yield self.model.env.timeout(0.001)
            yield from original_func(entity)

            self.event_queue.put(VisualizationEvent(
                event_type='entity_disposed',
                timestamp=self.model.env.now,
                data={'entity_id': entity_id, 'block_name': block.name}
            ))

            if entity_id in self.entity_locations:
                del self.entity_locations[entity_id]
            self._send_stats_update()

        return wrapped

    def _get_entity_id(self, entity) -> str:
        # (3) MODIFY: Use the entity.id attribute directly
        return entity.id

    def _send_stats_update(self):
        """Send statistics update event."""
        stats_data = {'time': self.model.env.now}

        if hasattr(self.model, 'resources'):
            for res_name, resource in self.model.resources.items():
                try:
                    # Get blocks using this resource
                    blocks_using_resource = []
                    for block_name, block in self.model.blocks.items():
                        if isinstance(block, ProcessBlock) and block.resource == resource:
                            blocks_using_resource.append(block_name)
                        elif isinstance(block, MultiProcessBlock) and resource in block.resource_requirements:
                            blocks_using_resource.append(block_name)

                    # This will be set by the GUI later, just use SimPy's count for now
                    if resource.capacity > 0:
                        utilization = (resource.count /
                                       resource.capacity) * 100
                    else:
                        utilization = 0.0
                    stats_data[f"{res_name}_util"] = utilization
                except Exception as e:
                    stats_data[f"{res_name}_util"] = 0.0

        self.event_queue.put(VisualizationEvent(
            event_type='stats_update',
            timestamp=self.model.env.now,
            data=stats_data
        ))


# =============================================================================
# Enables Zooming Canvas
# =============================================================================
class ZoomableCanvas(tk.Canvas):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        # Bind mouse wheel to zoom
        self.bind("<MouseWheel>", self._zoom)          # Windows
        self.bind("<Button-4>", self._zoom)            # Linux scroll up
        self.bind("<Button-5>", self._zoom)            # Linux scroll down

        # Optional: Middle mouse button for dragging (panning)
        self.bind("<ButtonPress-2>", self._start_pan)
        self.bind("<B2-Motion>", self._do_pan)

        self.pan_start = None

    def _zoom(self, event):
        # Determine zoom factor: scroll up = zoom in, scroll down = zoom out
        if event.delta > 0 or event.num == 4:
            factor = 1.1
        else:
            factor = 0.9

        # Zoom everything on the canvas
        self.scale("all", event.x, event.y, factor, factor)
        self.configure(scrollregion=self.bbox("all"))

    def _start_pan(self, event):
        self.pan_start = (event.x, event.y)

    def _do_pan(self, event):
        dx = event.x - self.pan_start[0]
        dy = event.y - self.pan_start[1]
        self.pan_start = (event.x, event.y)
        self.move("all", dx, dy)

# =============================================================================
# Example Usage
# =============================================================================


def run_visualization(model_builder, simulation_time: float = 100):
    """
    Run simulation with visualization.

    Args:
        model_builder: Function that returns a new simulation model instance
        simulation_time: Total simulation time to run
    """
    visualizer = SimulationVisualizer(model_builder)
    visualizer._simulation_time_limit = simulation_time
    visualizer.run()


if __name__ == "__main__":
    print("=" * 70)
    print("🎮 FIXED SIMULATION VISUALIZER")
    print("=" * 70)

    print("\n✅ FIXES APPLIED:")
    print("  1. Connectors now exit/enter blocks from OUTSIDE")
    print("  2. Entities flow smoothly along connector paths")
    print("  3. Queue statistics match visual queue counts")
    print("  4. (NEW) Play/Step buttons now drive simulation incrementally")

    print("\n📊 USAGE:")
    print("  from interface import run_visualization")
    print("  from all_blocks import build_hospital_model")
    print()
    print("  run_visualization(build_hospital_model, simulation_time=500)")

    print("\n" + "=" * 70)
