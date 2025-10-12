# =====================================================================
# FILE: analytics/plotting.py
# =====================================================================
import matplotlib.pyplot as plt
import numpy as np
from typing import Optional, List
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
            from analytics.wip_metrics import WIPTracker
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
            from analytics.metrics import MetricsCollector
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
        from blocks.process_block import ProcessBlock, MultiProcessBlock
        
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
        
        # Plot moving average
        if len(utilizations) >= moving_avg_window:
            times_array = np.array(times)
            utils_array = np.array(utilizations)
            moving_avg = np.convolve(utils_array, 
                                    np.ones(moving_avg_window)/moving_avg_window,
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
        ax.legend(loc='upper right')
        
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
        from blocks.process_block import ProcessBlock, MultiProcessBlock
        
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
                    print(f"  🚨 ALERTA: {queue_pct:.1f}% do tempo e gasto em fila!")
                elif queue_pct > 30:
                    print(f"  ⚠️  ATENCAO: {queue_pct:.1f}% do tempo e gasto em fila")
                else:
                    print(f"  ✅ Eficiente: apenas {queue_pct:.1f}% do tempo em fila")
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
                print(f"  ℹ️ BAIXA: Utilizacao abaixo do ideal")
            else:
                print(f"  ⚪ MUITO BAIXA: Recurso subutilizado")
            print()

                