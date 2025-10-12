#Key 
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

from typing import Optional
import simpy


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
    print(">>> ERRO DE VALIVAÇÃO DE RECURSOS!")
    # pass


class ResourceValidator:
    """
    Validates resource configurations in simulation models.
    
    Performs comprehensive checks to catch configuration errors before
    simulation runtime, providing clear error messages for fixes.
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
        from blocks.process_block import ProcessBlock, MultiProcessBlock
        
        for block_name, block in self.model.blocks.items():
            if isinstance(block, ProcessBlock):
                self._validate_single_resource_block(block_name, block)
            elif isinstance(block, MultiProcessBlock):
                self._validate_multi_resource_block_units(block_name, block)
    
    def _validate_single_resource_block(self, block_name: str, block):
        """Validate ProcessBlock resource configuration."""
        resource = block.resource
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
        from blocks.process_block import ProcessBlock, MultiProcessBlock
        
        registered_resources = set(self.model.resources.values())
        
        for block_name, block in self.model.blocks.items():
            if isinstance(block, ProcessBlock):
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
        from blocks.process_block import ProcessBlock, MultiProcessBlock
        
        for block_name, block in self.model.blocks.items():
            if isinstance(block, (ProcessBlock, MultiProcessBlock)):
                resources = []
                
                if isinstance(block, ProcessBlock):
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
        from blocks.process_block import MultiProcessBlock
        
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
        from blocks.process_block import MultiProcessBlock
        
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
        from blocks.create_block import CreateBlock
        
        for block in self.model.blocks.values():
            if isinstance(block, CreateBlock):
                if block.priority_generator is not None:
                    return True
        return False
    
    def _find_resource_name(self, resource_obj) -> Optional[str]:
        """Find resource name from resource object."""
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
        from blocks.process_block import ProcessBlock, MultiProcessBlock
        
        print("\n" + "=" * 70)
        print("RESOURCE CONFIGURATION SUMMARY")
        print("=" * 70)
        
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
                    if block.resource == resource:
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
                    print(f"    - {block_name}: {units} units ({pct:.0f}% of capacity)")
                
                print(f"  Maximum single allocation: {total_max_usage} units "
                      f"({total_max_usage/capacity*100:.0f}% of capacity)")
            else:
                print(f"  WARNING: Resource not used by any block!")
        
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