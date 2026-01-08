# =====================================================================
# FILE: analytics/reporting.py
# =====================================================================
from desk.analytics.metrics import MetricsCollector
from typing import Dict

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
            from desk.analytics.wip_metrics import WIPTracker
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
        print(f"  Average: {system_time_summary['average_system_time']:.2f} time units")
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
            print(f"  lambda (Throughput): {throughput:.4f} entities/time unit")
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
        print(f"📊 RESULTADOS DA SIMULACAO (⏳ Duracao: {duration_hours:.0f} horas)")
        
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
            print(f"\nINDICE DE ESTABILIDADE: {self.model.stability_result:.2f}")
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
        
        print(f"\n⏰ Tempo medio no sistema: {system_time/self.HOURS:.2f} horas")
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

        from desk.validation.resource_validator import ResourceValidator        
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
                print(f"    Maximo em atendimento: {metrics['maximo_atendimento']}")
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
