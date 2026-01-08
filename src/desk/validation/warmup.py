# =====================================================================
# FILE: validation/warmup.py
# =====================================================================
import numpy as np
from typing import List, Tuple


# =====================================================================
# FILE: validation/warmup.py
# =====================================================================
class WarmUpAnalyzer:
    """Analyzes warm-up period requirements."""
    
    def __init__(self, model):
        self.model = model
    
    def analyze_warm_up_period(self):
        """Analyze data to suggest adequate warm-up period."""
        from desk.blocks.process_block import ProcessBlock, MultiProcessBlock
        
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
                print(f"   Estabilizacao detectada em: t={stabilization_time:.1f}")
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
        from desk.blocks.process_block import ProcessBlock, MultiProcessBlock
        
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
        from desk.blocks.process_block import ProcessBlock, MultiProcessBlock
        
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