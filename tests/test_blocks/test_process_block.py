# tests/test_blocks/test_process_block.py
import pytest
import simpy
from blocks.process_block import ProcessBlock
from core.entity import Entity, EventLogger


class TestProcessBlock:
    """Test ProcessBlock functionality."""
    
    def test_process_block_initialization(self):
        """Test ProcessBlock initialization."""
        env = simpy.Environment()
        resource = simpy.Resource(env, capacity=2)
        
        block = ProcessBlock(
            "Service",
            env,
            resource=resource,
            delay_time=lambda: 5.0,
            resource_units=1
        )
        
        assert block.name == "Service"
        assert block.resource == resource
        assert block.resource_units == 1
        assert block.entities_processed == 0
    
    def test_entity_processing(self):
        """Test basic entity processing."""
        env = simpy.Environment()
        resource = simpy.Resource(env, capacity=1)
        
        block = ProcessBlock(
            "Service",
            env,
            resource=resource,
            delay_time=lambda: 3.0
        )
        
        entity = Entity("E1", 0)
        
        def run_test():
            yield from block.process_entity(entity)
        
        env.process(run_test())
        env.run()
        
        assert block.entities_processed == 1
        assert entity.get_attribute("Service_service_time") == 3.0
        assert "Service" in entity.route_history
    
    def test_queue_time_recording(self):
        """Test that queue time is recorded."""
        env = simpy.Environment()
        resource = simpy.Resource(env, capacity=1)
        
        block = ProcessBlock(
            "Service",
            env,
            resource=resource,
            delay_time=lambda: 2.0
        )
        
        entity1 = Entity("E1", 0)
        entity2 = Entity("E2", 0)
        
        def process1():
            yield from block.process_entity(entity1)
        
        def process2():
            yield env.timeout(0.5)  # Start slightly after entity1
            yield from block.process_entity(entity2)
        
        env.process(process1())
        env.process(process2())
        env.run()
        
        # Entity2 should have queue time
        queue_time_e2 = entity2.get_attribute("Service_queue_time")
        assert queue_time_e2 > 0
    
    def test_resource_monitoring(self):
        """Test that resource data is collected."""
        env = simpy.Environment()
        resource = simpy.Resource(env, capacity=2)
        
        block = ProcessBlock(
            "Service",
            env,
            resource=resource,
            delay_time=lambda: 1.0
        )
        
        entity = Entity("E1", 0)
        
        def run_test():
            yield from block.process_entity(entity)
        
        env.process(run_test())
        env.run()
        
        assert len(block.resource_data) > 0
        assert block.max_in_service >= 0
    
    def test_multiple_resource_units(self):
        """Test processing with multiple resource units."""
        env = simpy.Environment()
        resource = simpy.Resource(env, capacity=5)
        
        block = ProcessBlock(
            "Service",
            env,
            resource=resource,
            delay_time=lambda: 1.0,
            resource_units=3
        )
        
        entity = Entity("E1", 0)
        
        def run_test():
            yield from block.process_entity(entity)
        
        env.process(run_test())
        env.run()
        
        assert block.entities_processed == 1
    
    def test_event_logging(self):
        """Test that events are logged."""
        env = simpy.Environment()
        resource = simpy.Resource(env, capacity=1)
        logger = EventLogger()
        
        block = ProcessBlock(
            "Service",
            env,
            resource=resource,
            delay_time=lambda: 2.0,
            event_logger=logger
        )
        block.set_resource_name("ServiceResource")
        
        entity = Entity("E1", 0)
        
        def run_test():
            yield from block.process_entity(entity)
        
        env.process(run_test())
        env.run()
        
        events = logger.get_dataframe()
        assert len(events) == 2  # start and complete
        assert events.iloc[0]["lifecycle"] == "start"
        assert events.iloc[1]["lifecycle"] == "complete"
        assert all(events["resource"] == "ServiceResource")