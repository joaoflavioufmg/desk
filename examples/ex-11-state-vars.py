# =====================================================================
# EXEMPLO COMPLETO: Como integrar variáveis customizadas no modelo
# =====================================================================

# =====================================================================
# PASSO 1: Modificar SimulationModel para incluir o tracker
# =====================================================================
class SimulationModel:
    """Modified to include variable tracking."""
    
    def __init__(self):
        self.env = simpy.Environment()
        self.env.model = self
        self.blocks: Dict[str, 'BaseBlock'] = {}
        self.resources: Dict[str, Union[simpy.Resource, simpy.PriorityResource]] = {}
        self.create_blocks: List['CreateBlock'] = []
        self.dispose_blocks: List['DisposeBlock'] = []
        self.stability_result: Optional[float] = None
        self.warm_up_period: float = 0.0
        self.is_warm_up_complete: bool = False
        
        # ✅ NOVO: Adicionar tracker de variáveis
        self.variable_tracker = ModelVariableTracker(self)
    
    def add_model_variable(self, name: str, initial_value: Any = 0,
                          description: str = "", unit: str = "",
                          calculate_fn: Optional[Callable] = None):
        """
        Add a custom model variable to track.
        
        Example:
            model.add_model_variable(
                'percentual_falhas',
                initial_value=0,
                description='Percentual de falhas no sistema',
                unit='%'
            )
        """
        self.variable_tracker.add_variable(
            name, initial_value, description, unit, calculate_fn
        )
    
    def update_model_variable(self, name: str, value: Any = None):
        """
        Update a model variable.
        
        Example:
            model.update_model_variable('num_falhas', 5)
            model.update_model_variable('percentual_falhas')  # Auto-calculate
        """
        self.variable_tracker.update(name, value=value)


# =====================================================================
# PASSO 2: Exemplo de modelo com variáveis customizadas
# =====================================================================
def build_model_with_custom_variables():
    """Build model with custom variable tracking."""
    
    model = SimulationModel()
    HOURS = 60
    
    # ✅ DEFINIR VARIÁVEIS CUSTOMIZADAS
    
    # Variável 1: Contador simples de falhas
    model.add_model_variable(
        'num_falhas',
        initial_value=0,
        description='Número total de falhas no sistema',
        unit='unidades'
    )
    
    # Variável 2: Percentual calculado automaticamente
    model.add_model_variable(
        'percentual_falhas',
        initial_value=0,
        description='Percentual de entidades que falharam',
        unit='%',
        calculate_fn=lambda m: (
            m.variable_tracker.get_current('num_falhas') / 
            max(1, m.entity_count) * 100
        )
    )
    
    # Variável 3: Taxa de ocupação média
    model.add_model_variable(
        'taxa_ocupacao_media',
        initial_value=0,
        description='Taxa média de ocupação do sistema',
        unit='%'
    )
    
    # Variável 4: Custo acumulado
    model.add_model_variable(
        'custo_total',
        initial_value=0,
        description='Custo total acumulado',
        unit='R$'
    )
    
    # ... criar recursos e blocos ...
    
    rec1 = model.add_resource("Rec1", 2, "regular")
    event_logger = EventLogger()
    
    # CREATE BLOCK
    chegadas = CreateBlock(
        "Chegadas", model.env,
        inter_arrival_time=lambda: random.expovariate(1/10),
        entity_prefix="Cliente",
        max_arrivals=100,
        event_logger=event_logger
    )
    
    # PROCESS BLOCK com lógica de falha
    atendimento = ProcessBlock(
        "Atendimento", model.env,
        resource=rec1,
        delay_time=lambda: random.gauss(6, 1),
        event_logger=event_logger
    )
    atendimento.set_resource_name('Rec1')
    
    # DISPOSE
    dispose = DisposeBlock("Dispose", model.env, event_logger=event_logger)
    
    # Adicionar blocos
    for block in [chegadas, atendimento, dispose]:
        model.add_block(block)
    
    chegadas.connect_to(atendimento)
    atendimento.connect_to(dispose)
    
    return model


# =====================================================================
# PASSO 3: Modificar ProcessBlock para atualizar variáveis
# =====================================================================
class ProcessBlockWithVariables(ProcessBlock):
    """
    ProcessBlock that updates model variables during processing.
    """
    
    def __init__(self, *args, failure_probability: float = 0.1, **kwargs):
        super().__init__(*args, **kwargs)
        self.failure_probability = failure_probability
    
    def process_entity(self, entity: Entity):
        """Process entity and update model variables."""
        entity.route_history.append(self.name)
        
        # ... processo normal de seize/delay/release ...
        if self.resource is None:
            yield from self._process_without_resource(entity)
        else:
            yield from self._process_with_resource_and_variables(entity)
    
    def _process_with_resource_and_variables(self, entity: Entity):
        """Modified process that updates model variables."""
        
        self._monitor_resource()
        
        while True:
            queue_start = self.env.now
            request_priority = (self.activity_priority 
                              if self.activity_priority is not None 
                              else entity.priority)
            
            requests = []
            for _ in range(self.resource_units):
                if isinstance(self.resource, simpy.PreemptiveResource):
                    req = self.resource.request(priority=request_priority, preempt=False)
                elif isinstance(self.resource, simpy.PriorityResource):
                    req = self.resource.request(priority=request_priority)
                else:
                    req = self.resource.request()
                requests.append(req)
            
            acquired = []
            try:
                yield simpy.AllOf(self.env, requests)
                acquired = requests
                
                self._monitor_resource()
                self.log_start(entity, self.resource_name)
                
                queue_time = self.env.now - queue_start
                self.total_queue_time += queue_time
                entity.add_attribute(f"{self.name}_queue_time", queue_time)
                
                # Delay
                if hasattr(self.env, 'model') and hasattr(self.env.model, 'safe_delay_time'):
                    delay = self.env.model.safe_delay_time(self.delay_time)
                else:
                    delay = max(0.0, self.delay_time())
                
                yield self.env.timeout(delay)
                
                # ✅ APÓS O ATENDIMENTO: Verificar se houve falha
                if hasattr(self.env, 'model') and hasattr(self.env.model, 'variable_tracker'):
                    tracker = self.env.model.variable_tracker
                    
                    # Simular falha com probabilidade
                    if random.random() < self.failure_probability:
                        # Incrementar contador de falhas
                        current_failures = tracker.get_current('num_falhas')
                        tracker.update('num_falhas', self.env.now, current_failures + 1)
                        
                        # Marcar entidade como falha
                        entity.add_attribute('falhou', True)
                        
                        # Auto-atualizar percentual
                        tracker.update('percentual_falhas')
                    else:
                        entity.add_attribute('falhou', False)
                    
                    # Atualizar custo total
                    custo_atendimento = delay * 2.5  # R$ 2.50 por minuto
                    current_cost = tracker.get_current('custo_total')
                    tracker.update('custo_total', self.env.now, 
                                 current_cost + custo_atendimento)
                    
                    # Atualizar taxa de ocupação
                    utilization = self.resource.count / self.resource.capacity * 100
                    tracker.update('taxa_ocupacao_media', self.env.now, utilization)
                
                # Continue normal processing
                self.entities_processed += 1
                self.total_delay_time += delay
                entity.add_attribute(f"{self.name}_service_time", delay)
                
                self._apply_attributes(entity)
                self._modify_attributes(entity)
                self.log_complete(entity, self.resource_name)
                
                break
                
            except simpy.Interrupt as interrupt:
                if self.event_logger:
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
                continue
            
            finally:
                for req in acquired:
                    try:
                        self.resource.release(req)
                    except:
                        pass
                self._monitor_resource()
        
        self._monitor_resource()
        self.env.process(self.send_to_next(entity))
        yield self.env.timeout(0)


# =====================================================================
# PASSO 4: Usar no modelo
# =====================================================================
def build_complete_model_with_variables():
    """Complete example with variable tracking."""
    
    model = SimulationModel()
    HOURS = 60
    event_logger = EventLogger()
    
    # Definir variáveis
    model.add_model_variable('num_falhas', 0, 'Número de falhas', 'unidades')
    model.add_model_variable('percentual_falhas', 0, 'Percentual de falhas', '%',
                            calculate_fn=lambda m: (
                                m.variable_tracker.get_current('num_falhas') / 
                                max(1, m.entity_count) * 100
                            ))
    model.add_model_variable('custo_total', 0, 'Custo total', 'R$')
    model.add_model_variable('taxa_ocupacao', 0, 'Taxa de ocupação', '%')
    
    # Criar recursos
    rec1 = model.add_resource("Atendentes", 3, "regular")
    
    # Criar blocos
    chegadas = CreateBlock(
        "Chegadas", model.env,
        inter_arrival_time=lambda: random.expovariate(1/10),
        entity_prefix="Cliente",
        max_arrivals=200,
        event_logger=event_logger
    )
    
    # Usar ProcessBlock modificado
    atendimento = ProcessBlockWithVariables(
        "Atendimento", model.env,
        resource=rec1,
        delay_time=lambda: random.gauss(8, 2),
        failure_probability=0.15,  # 15% de chance de falha
        event_logger=event_logger
    )
    atendimento.set_resource_name('Atendentes')
    
    dispose = DisposeBlock("Dispose", model.env, event_logger=event_logger)
    
    # Adicionar e conectar
    for block in [chegadas, atendimento, dispose]:
        model.add_block(block)
    
    chegadas.connect_to(atendimento)
    atendimento.connect_to(dispose)
    
    return model, event_logger


# =====================================================================
# PASSO 5: Executar e analisar
# =====================================================================
def main_example():
    """Run complete example."""
    
    HOURS = 60
    
    # Build model
    model, event_logger = build_complete_model_with_variables()
    
    # Run simulation
    model.run_simulation(
        until=24*HOURS,
        seed=123,
        warm_up_period=2*HOURS
    )
    
    # Analyze custom variables
    print("\n" + "="*70)
    print("CUSTOM MODEL VARIABLES")
    print("="*70)
    
    tracker = model.variable_tracker
    tracker.print_summary()
    
    # Plot individual variables
    tracker.plot_variable('percentual_falhas')
    tracker.plot_variable('custo_total')
    tracker.plot_variable('taxa_ocupacao')
    
    # Plot all together
    tracker.plot_all_variables()
    
    # Export to CSV
    tracker.export_to_csv('model_variables.csv')
    
    # Access specific values
    print(f"\nPercentual final de falhas: {tracker.get_final('percentual_falhas'):.2f}%")
    print(f"Custo total acumulado: R$ {tracker.get_final('custo_total'):.2f}")
    print(f"Taxa média de ocupação: {tracker.get_average('taxa_ocupacao'):.2f}%")
    
    return model, tracker


# =====================================================================
# EXEMPLO ALTERNATIVO: Atualizar variáveis em qualquer lugar do código
# =====================================================================
def alternative_update_methods():
    """Show different ways to update variables."""
    
    model = SimulationModel()
    tracker = model.variable_tracker
    
    # Método 1: Atualizar manualmente quando algo acontece
    if some_condition:
        current_value = tracker.get_current('num_falhas')
        tracker.update('num_falhas', model.env.now, current_value + 1)
    
    # Método 2: Auto-calcular com função
    tracker.update('percentual_falhas')  # Usa calculate_fn automaticamente
    
    # Método 3: Dentro de um DecideBlock
    class DecideBlockWithTracking(DecideBlock):
        def process_entity(self, entity: Entity):
            entity.route_history.append(self.name)
            
            chosen_route = None
            
            if self.decision_type == "probability":
                chosen_route = self._choose_by_probability()
            elif self.decision_type == "condition":
                chosen_route = self._choose_by_condition(entity)
            else:
                chosen_route = self._choose_by_time_condition()
            
            # ✅ Atualizar variável baseado na decisão
            if chosen_route == 'rota_emergencia':
                if hasattr(self.env, 'model'):
                    tracker = self.env.model.variable_tracker
                    current = tracker.get_current('num_emergencias')
                    tracker.update('num_emergencias', self.env.now, current + 1)
            
            # Continue normal processing
            if chosen_route and chosen_route in self.routes:
                self.decision_counts[chosen_route] += 1
                next_block = self.routes[chosen_route]['block']
                entity.add_attribute(f"{self.name}_decision", chosen_route)
                
                if self.event_logger:
                    self.event_logger.log_event(
                        case_id=entity.id,
                        activity=f"{self.name}_{chosen_route}",
                        timestamp=self.env.now,
                        lifecycle='complete',
                        decision=chosen_route,
                        decision_time=self.env.now
                    )
                
                self.env.process(next_block.process_entity(entity))
                yield self.env.timeout(0)
            else:
                yield self.env.timeout(0)
    
    # Método 4: Dentro de um DisposeBlock
    class DisposeBlockWithTracking(DisposeBlock):
        def process_entity(self, entity: Entity):
            entity.route_history.append(self.name)
            
            system_time = self.env.now - entity.creation_time
            entity.add_attribute("system_time", system_time)
            entity.add_attribute("disposal_time", self.env.now)
            
            self._apply_attributes(entity)
            self.disposed_entities.append(entity)
            
            if self.env.now >= getattr(self.env, 'warm_up_period', 0):
                self.total_system_time += system_time
                self.entities_disposed += 1
            
            # ✅ Atualizar variáveis ao descartar
            if hasattr(self.env, 'model'):
                tracker = self.env.model.variable_tracker
                
                # Contar tipos de saída
                if entity.get_attribute('falhou', False):
                    current = tracker.get_current('num_falhas_descartadas')
                    tracker.update('num_falhas_descartadas', self.env.now, current + 1)
                else:
                    current = tracker.get_current('num_sucessos')
                    tracker.update('num_sucessos', self.env.now, current + 1)
                
                # Atualizar percentuais
                tracker.update('percentual_sucesso')
            
            if self.event_logger:
                self.event_logger.log_event(
                    case_id=entity.id,
                    activity="Discharge",
                    timestamp=self.env.now,
                    lifecycle='complete',
                    system_time=system_time
                )
            
            yield self.env.timeout(0)


# =====================================================================
# INTEGRAÇÃO COM REPLICATION FRAMEWORK
# =====================================================================
def extract_variables_in_replication(model, replication_id: int) -> Dict[str, Any]:
    """
    Extract custom variables for replication analysis.
    
    This should be added to ReplicationFramework._extract_kpis()
    """
    kpis = {
        'replication_id': replication_id,
        # ... outros KPIs existentes ...
    }
    
    # ✅ Adicionar variáveis customizadas
    if hasattr(model, 'variable_tracker'):
        tracker = model.variable_tracker
        
        for var_name, variable in tracker.variables.items():
            # Adicionar valores finais
            kpis[f'{var_name}_final'] = tracker.get_final(var_name)
            
            # Adicionar médias
            kpis[f'{var_name}_avg'] = tracker.get_average(var_name)
            
            # Se for percentual, adicionar ambos
            if variable.unit == '%':
                kpis[f'{var_name}_pct'] = tracker.get_final(var_name)
    
    return kpis


# =====================================================================
# EXEMPLO COMPLETO: Modelo de Produção com Falhas
# =====================================================================
def build_production_model_with_quality_tracking():
    """
    Production model that tracks quality metrics.
    
    Tracks:
    - Number and percentage of defective products
    - Rework rate
    - Quality control pass rate
    - Production costs
    """
    
    model = SimulationModel()
    HOURS = 60
    event_logger = EventLogger()
    
    # ✅ DEFINIR VARIÁVEIS DE QUALIDADE
    model.add_model_variable(
        'num_defeituosos',
        initial_value=0,
        description='Número de produtos defeituosos',
        unit='unidades'
    )
    
    model.add_model_variable(
        'percentual_defeituosos',
        initial_value=0,
        description='Percentual de defeitos na produção',
        unit='%',
        calculate_fn=lambda m: (
            m.variable_tracker.get_current('num_defeituosos') / 
            max(1, sum(cb.entities_created for cb in m.create_blocks)) * 100
        )
    )
    
    model.add_model_variable(
        'num_retrabalho',
        initial_value=0,
        description='Número de produtos enviados para retrabalho',
        unit='unidades'
    )
    
    model.add_model_variable(
        'taxa_retrabalho',
        initial_value=0,
        description='Taxa de retrabalho',
        unit='%',
        calculate_fn=lambda m: (
            m.variable_tracker.get_current('num_retrabalho') /
            max(1, sum(cb.entities_created for cb in m.create_blocks)) * 100
        )
    )
    
    model.add_model_variable(
        'custo_producao_total',
        initial_value=0,
        description='Custo total de produção',
        unit='R$'
    )
    
    model.add_model_variable(
        'custo_retrabalho_total',
        initial_value=0,
        description='Custo total de retrabalho',
        unit='R$'
    )
    
    model.add_model_variable(
        'taxa_aprovacao_qc',
        initial_value=100,
        description='Taxa de aprovação no controle de qualidade',
        unit='%',
        calculate_fn=lambda m: (
            (m.entity_count - m.variable_tracker.get_current('num_defeituosos')) /
            max(1, m.entity_count) * 100
        )
    )
    
    # Criar recursos
    maquinas_producao = model.add_resource("Maquinas", 5, "regular")
    inspetores_qc = model.add_resource("Inspetores_QC", 2, "regular")
    area_retrabalho = model.add_resource("Retrabalho", 3, "regular")
    
    # Criar blocos
    chegada_materias_primas = CreateBlock(
        "ChegadaMateriasPrimas", model.env,
        inter_arrival_time=lambda: random.expovariate(1/5),  # A cada 5 min
        entity_prefix="Produto",
        max_arrivals=500,
        event_logger=event_logger
    )
    
    # Produção (pode gerar defeitos)
    producao = ProcessBlockWithVariables(
        "Producao", model.env,
        resource=maquinas_producao,
        delay_time=lambda: random.gauss(10, 2),
        failure_probability=0.08,  # 8% de defeito
        event_logger=event_logger
    )
    producao.set_resource_name('Maquinas')
    
    # Inspeção de qualidade
    inspecao_qc = ProcessBlock(
        "InspecaoQC", model.env,
        resource=inspetores_qc,
        delay_time=lambda: random.uniform(2, 4),
        event_logger=event_logger
    )
    inspecao_qc.set_resource_name('Inspetores_QC')
    
    # Decisão baseada em qualidade
    decide_qualidade = DecideBlock(
        "DecideQualidade", model.env,
        decision_type="condition",
        event_logger=event_logger
    )
    
    # Retrabalho
    retrabalho = ProcessBlock(
        "Retrabalho", model.env,
        resource=area_retrabalho,
        delay_time=lambda: random.gauss(15, 3),  # Leva mais tempo
        event_logger=event_logger
    )
    retrabalho.set_resource_name('Retrabalho')
    
    # Descarte (produtos defeituosos não recuperáveis)
    descarte_defeituosos = DisposeBlock(
        "DescarteDefeituosos", model.env, 
        event_logger=event_logger
    )
    
    # Saída de produtos aprovados
    saida_produtos = DisposeBlock(
        "SaidaProdutos", model.env,
        event_logger=event_logger
    )
    
    # Adicionar blocos
    for block in [chegada_materias_primas, producao, inspecao_qc,
                  decide_qualidade, retrabalho, descarte_defeituosos,
                  saida_produtos]:
        model.add_block(block)
    
    # Conectar fluxo
    chegada_materias_primas.connect_to(producao)
    producao.connect_to(inspecao_qc)
    inspecao_qc.connect_to(decide_qualidade)
    
    # Lógica de decisão de qualidade
    def produto_aprovado(entity):
        """Produto passou na inspeção."""
        return not entity.get_attribute('falhou', False)
    
    def produto_recuperavel(entity):
        """Produto defeituoso mas pode ser retrabalhado."""
        falhou = entity.get_attribute('falhou', False)
        if not falhou:
            return False
        # 70% dos defeituosos podem ser retrabalhados
        return random.random() < 0.70
    
    def produto_descartavel(entity):
        """Produto defeituoso sem recuperação."""
        falhou = entity.get_attribute('falhou', False)
        if not falhou:
            return False
        # 30% dos defeituosos devem ser descartados
        return random.random() >= 0.70
    
    # Adicionar rotas de decisão
    decide_qualidade.add_route(
        "Aprovado", saida_produtos,
        condition=produto_aprovado
    )
    decide_qualidade.add_route(
        "Retrabalho", retrabalho,
        condition=produto_recuperavel
    )
    decide_qualidade.add_route(
        "Descarte", descarte_defeituosos,
        condition=produto_descartavel
    )
    
    # Retrabalho volta para inspeção
    retrabalho.connect_to(inspecao_qc)
    
    # ✅ ATRIBUIR CUSTOS
    producao.assign_attributes(
        custo_producao=lambda: random.uniform(50, 70)
    )
    retrabalho.assign_attributes(
        custo_retrabalho=lambda: random.uniform(30, 50)
    )
    saida_produtos.assign_attributes(
        valor_venda=lambda: random.uniform(150, 200)
    )
    
    return model, event_logger


# =====================================================================
# MODIFICAR DecideBlock PARA ATUALIZAR VARIÁVEIS
# =====================================================================
class DecideBlockWithQualityTracking(DecideBlock):
    """DecideBlock that updates quality tracking variables."""
    
    def process_entity(self, entity: Entity):
        """Route entity and update quality metrics."""
        entity.route_history.append(self.name)
        
        chosen_route = None
        
        if self.decision_type == "probability":
            chosen_route = self._choose_by_probability()
        elif self.decision_type == "condition":
            chosen_route = self._choose_by_condition(entity)
        elif self.decision_type == "time_condition":
            chosen_route = self._choose_by_time_condition()
        else:
            raise ValueError(f"Invalid decision type: {self.decision_type}")
        
        # ✅ ATUALIZAR VARIÁVEIS BASEADO NA DECISÃO
        if chosen_route and hasattr(self.env, 'model'):
            tracker = self.env.model.variable_tracker
            
            if chosen_route == "Retrabalho":
                # Incrementar contador de retrabalho
                current = tracker.get_current('num_retrabalho')
                tracker.update('num_retrabalho', self.env.now, current + 1)
                tracker.update('taxa_retrabalho')  # Auto-calcular percentual
                
                # Adicionar custo de retrabalho
                custo = entity.get_attribute('custo_retrabalho', 0)
                current_cost = tracker.get_current('custo_retrabalho_total')
                tracker.update('custo_retrabalho_total', self.env.now,
                             current_cost + custo)
            
            elif chosen_route == "Descarte":
                # Contar como defeituoso
                current = tracker.get_current('num_defeituosos')
                tracker.update('num_defeituosos', self.env.now, current + 1)
                tracker.update('percentual_defeituosos')  # Auto-calcular
                tracker.update('taxa_aprovacao_qc')  # Atualizar taxa de aprovação
        
        # Continue normal processing
        if chosen_route and chosen_route in self.routes:
            self.decision_counts[chosen_route] += 1
            next_block = self.routes[chosen_route]['block']
            entity.add_attribute(f"{self.name}_decision", chosen_route)
            
            if self.event_logger:
                self.event_logger.log_event(
                    case_id=entity.id,
                    activity=f"{self.name}_{chosen_route}",
                    timestamp=self.env.now,
                    lifecycle='complete',
                    decision=chosen_route,
                    decision_time=self.env.now
                )
            
            self.env.process(next_block.process_entity(entity))
            yield self.env.timeout(0)
        else:
            yield self.env.timeout(0)


# =====================================================================
# EXECUTAR MODELO DE PRODUÇÃO
# =====================================================================
def run_production_model_example():
    """Run production model with quality tracking."""
    
    HOURS = 60
    
    # Build model
    print("Building production model with quality tracking...")
    model, event_logger = build_production_model_with_quality_tracking()
    
    # Run simulation
    print("Running simulation...")
    model.run_simulation(
        until=48*HOURS,  # 48 horas
        seed=456,
        warm_up_period=8*HOURS  # 8 horas de warm-up
    )
    
    # Analyze results
    print("\n" + "="*70)
    print("QUALITY CONTROL METRICS")
    print("="*70)
    
    tracker = model.variable_tracker
    tracker.print_summary()
    
    # Print detailed quality analysis
    print("\nDETAILED QUALITY ANALYSIS:")
    print("-" * 70)
    
    num_defeituosos = tracker.get_final('num_defeituosos')
    pct_defeituosos = tracker.get_final('percentual_defeituosos')
    num_retrabalho = tracker.get_final('num_retrabalho')
    taxa_retrabalho = tracker.get_final('taxa_retrabalho')
    taxa_aprovacao = tracker.get_final('taxa_aprovacao_qc')
    
    print(f"Total de produtos defeituosos: {num_defeituosos}")
    print(f"Percentual de defeitos: {pct_defeituosos:.2f}%")
    print(f"Produtos enviados para retrabalho: {num_retrabalho}")
    print(f"Taxa de retrabalho: {taxa_retrabalho:.2f}%")
    print(f"Taxa de aprovação no QC: {taxa_aprovacao:.2f}%")
    
    # Financial analysis
    print("\nFINANCIAL ANALYSIS:")
    print("-" * 70)
    custo_producao = tracker.get_final('custo_producao_total')
    custo_retrabalho = tracker.get_final('custo_retrabalho_total')
    custo_total = custo_producao + custo_retrabalho
    
    print(f"Custo de produção: R$ {custo_producao:,.2f}")
    print(f"Custo de retrabalho: R$ {custo_retrabalho:,.2f}")
    print(f"Custo total: R$ {custo_total:,.2f}")
    print(f"Percentual de retrabalho no custo: "
          f"{(custo_retrabalho/custo_total*100):.1f}%")
    
    # Plot variables
    print("\nGenerating plots...")
    tracker.plot_variable('percentual_defeituosos')
    tracker.plot_variable('taxa_retrabalho')
    tracker.plot_variable('taxa_aprovacao_qc')
    tracker.plot_all_variables()
    
    # Export
    tracker.export_to_csv('production_quality_metrics.csv')
    
    return model, tracker


if __name__ == "__main__":
    # Escolha qual exemplo executar:
    
    # Exemplo 1: Modelo simples com variáveis
    # model, tracker = main_example()
    
    # Exemplo 2: Modelo de produção com controle de qualidade
    model, tracker = run_production_model_example()