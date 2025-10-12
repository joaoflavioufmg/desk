# tests/test_core/test_base_block.py
import pytest
import simpy
from core.base_block import BaseBlock
from core.entity import Entity, EventLogger


class ConcreteBlock(BaseBlock):
    """Concrete implementation for testing abstract BaseBlock."""
    
    def process_entity(self, entity: Entity):
        """Minimal implementation."""
        entity.route_history.append(self.name)
        yield self.env.timeout(0)


class TestBaseBlock:
    """Test BaseBlock abstract class functionality."""
    
    def test_base_block_creation(self):
        """Test creating a concrete block."""
        env = simpy.Environment()
        block = ConcreteBlock("TestBlock", env)
        
        assert block.name == "TestBlock"
        assert block.env == env
        assert block.next_block is None
        assert block.statistics == {}
        assert block.attributes_to_assign == {}
    
    def test_base_block_with_event_logger(self):
        """Test creating block with event logger."""
        env = simpy.Environment()
        logger = EventLogger()
        block = ConcreteBlock("TestBlock", env, event_logger=logger)
        
        assert block.event_logger == logger
    
    def test_connect_to(self):
        """Test connecting blocks."""
        env = simpy.Environment()
        block1 = ConcreteBlock("Block1", env)
        block2 = ConcreteBlock("Block2", env)
        
        block1.connect_to(block2)
        
        assert block1.next_block == block2
    
    def test_assign_attributes_fixed_values(self):
        """Test assigning fixed attribute values."""
        env = simpy.Environment()
        block = ConcreteBlock("TestBlock", env)
        
        block.assign_attributes(
            cost=100,
            category="outpatient",
            priority=1
        )
        
        assert block.attributes_to_assign["cost"] == 100
        assert block.attributes_to_assign["category"] == "outpatient"
        assert block.attributes_to_assign["priority"] == 1
    
    def test_assign_attributes_callable(self):
        """Test assigning callable attribute values."""
        env = simpy.Environment()
        block = ConcreteBlock("TestBlock", env)
        
        block.assign_attributes(
            cost=lambda: 150,
            revenue=lambda: 200
        )
        
        assert callable(block.attributes_to_assign["cost"])
        assert callable(block.attributes_to_assign["revenue"])
    
    def test_apply_attributes_fixed(self):
        """Test applying fixed attributes to entity."""
        env = simpy.Environment()
        block = ConcreteBlock("TestBlock", env)
        entity = Entity("E1", 0)
        
        block.assign_attributes(cost=100, category="urgent")
        block._apply_attributes(entity)
        
        assert entity.get_attribute("TestBlock_cost") == 100
        assert entity.get_attribute("TestBlock_category") == "urgent"
    
    def test_apply_attributes_callable(self):
        """Test applying callable attributes to entity."""
        env = simpy.Environment()
        block = ConcreteBlock("TestBlock", env)
        entity = Entity("E1", 0)
        
        call_count = 0
        def get_cost():
            nonlocal call_count
            call_count += 1
            return 100 + call_count
        
        block.assign_attributes(cost=get_cost)
        
        # Apply twice to verify callable is executed each time
        block._apply_attributes(entity)
        assert entity.get_attribute("TestBlock_cost") == 101
        
        block._apply_attributes(entity)
        assert entity.get_attribute("TestBlock_cost") == 102
    
    def test_update_statistics(self):
        """Test updating block statistics."""
        env = simpy.Environment()
        block = ConcreteBlock("TestBlock", env)
        
        block.update_statistics("processed", 10)
        block.update_statistics("avg_time", 5.5)
        
        assert block.statistics["processed"] == 10
        assert block.statistics["avg_time"] == 5.5
    
    def test_log_start(self):
        """Test logging activity start."""
        env = simpy.Environment()
        logger = EventLogger()
        block = ConcreteBlock("TestBlock", env, event_logger=logger)
        entity = Entity("E1", 0, priority=2)
        
        block.log_start(entity, "Resource1")
        
        assert len(logger.events) == 1
        event = logger.events[0]
        assert event["case_id"] == "E1"
        assert event["activity"] == "TestBlock"
        assert event["lifecycle"] == "start"
        assert event["resource"] == "Resource1"
        assert event["priority"] == 2
    
    def test_log_complete(self):
        """Test logging activity completion."""
        env = simpy.Environment()
        logger = EventLogger()
        block = ConcreteBlock("TestBlock", env, event_logger=logger)
        entity = Entity("E1", 0, priority=1)
        
        block.log_complete(entity, "Resource1")
        
        assert len(logger.events) == 1
        event = logger.events[0]
        assert event["lifecycle"] == "complete"
    
    def test_send_to_next(self):
        """Test sending entity to next block."""
        env = simpy.Environment()
        block1 = ConcreteBlock("Block1", env)
        block2 = ConcreteBlock("Block2", env)
        block1.connect_to(block2)
        
        entity = Entity("E1", 0)
        
        def run_test():
            yield from block1.send_to_next(entity)
        
        env.process(run_test())
        env.run()
        
        assert "Block2" in entity.route_history
    
    def test_send_to_next_no_connection(self):
        """Test sending entity when no next block exists."""
        env = simpy.Environment()
        block = ConcreteBlock("Block1", env)
        entity = Entity("E1", 0)
        
        def run_test():
            yield from block.send_to_next(entity)
        
        env.process(run_test())
        env.run()  # Should complete without error
        
        # Entity should not have any additional route history
        assert len(entity.route_history) == 0