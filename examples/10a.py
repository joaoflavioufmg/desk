# =====================================================================
# FILE: exemplo10a.py
# =====================================================================
# Disciplina: EPD899 - Simulação de Sistemas Logísticos
# Prof: João Flávio F. Almeida <joao.flavio@dep.ufmg.br>
# Implementação DESK — Exemplo 10a: Manutenção (somente máquinas internas)
#
# Sistema:
#   5 máquinas internas em ciclo fechado. Após falha, vão para
#   Estação A (75%) ou B (25%). Após reparo, passam por inspeção:
#   90% retornam à operação, 10% voltam para reparo na mesma estação.
#
# Referência SimPy: ex-10a.py (Prof. João Flávio)
#   seed=1 | duração=365 dias | warm-up=30 dias | n_replicacoes=1
#   USO-A: ~45.50% | USO-B: ~12.19% | USO-I: ~22.33%
#
# Customizações necessárias em relação ao uso padrão do DESK:
#
#   1. MODELO FECHADO (ciclo sem Dispose):
#      O DESK não possui um bloco de ciclo nativo. As 5 máquinas são
#      geradas no t=0 via CreateBlock (max_arrivals=5,
#      inter_arrival_time=0). O ciclo fechado é implementado
#      conectando a saída "Aprovada" da inspeção de volta ao bloco
#      "Operacao", sem que haja DisposeBlock para máquinas internas.
#
#   2. ATRIBUTO "estacao" como ASSIGN substituto:
#      O DESK não possui bloco ASSIGN nativo (como no Arena).
#      O atributo é gravado usando assign_attributes() no CreateBlock
#      com valor padrão, e depois sobrescrito via DecideBlock com
#      decision_type="condition" — cada rota grava o valor correto
#      em entity.add_attribute() antes de retornar True.
#      Isso é necessário para que o desvio "E ou F" do DCA (retorno
#      à mesma estação após reprovação) funcione corretamente.
#
#   3. DESVIO CONDICIONAL por atributo (E ou F no DCA):
#      O decide_retorno usa decision_type="condition" com funções
#      que leem entity.get_attribute("estacao") para rotear a máquina
#      reprovada de volta à estação correta (A ou B).
# =====================================================================

import random
import sys

from desk.stats.replication import ReplicationFramework
from desk.core.simulation_model import SimulationModel
from desk.core.entity import EventLogger
from desk.blocks.create_block import CreateBlock
from desk.blocks.process_block import ProcessBlock
from desk.blocks.decide_block import DecideBlock
from desk.blocks.dispose_block import DisposeBlock
from desk.analytics.reporting import SimulationReporter
from desk.analytics.plotting import SimulationPlotter
from desk.validation.warmup import WarmUpAnalyzer
from desk.config.simulation_config import SimulationConfig
from desk.visualization.interface import run_visualization


# ####################################################################################
# Projeto: Manutencao de maquinas internas e externas
# Autor: João Flávio F. ALmeida <joao.flavio@dep.ufmg.br>
# Implementação: Alunos da disciplina EPD733 - Simulação de sistema logísticos - PPGEP-UFMG
# Uma empresa possui uma oficina de manutenção de 5 máquinas que são utilizadas para operação 
# dentro de sua área industrial. Dentro da oficina existem duas estações de reparo, estação A e B. 
# Em cada uma destas estações, existe apenas 1 operador disponível para execução dos trabalhos. 
# A probabilidade de uma máquina necessitar de reparos na estação A é de 75% e na estação B de 25%. 
# Uma máquina, após reparada vai para uma inspeção final, onde existe um único operador que 
# realiza o trabalho. Após a inspeção, 90% das máquinas são liberadas para operação e 
# 10% retornam para nova manutenção. Esta nova manutenção sempre ocorre na mesma estação 
# onde a máquina foi reparada inicialmente. Além da manutenção das máquinas da empresa, 
# esta oficina também está estudando a possibilidade de realizar serviços para terceiros, 
# isto é, manutenção em máquinas de outras empresas. As máquinas externas sempre 
# seriam reparadas na estação B e, após o reparo, também seriam inspecionadas pelo 
# mesmo operador que inspeciona as máquinas internas e seriam liberadas (neste caso a 
# taxa é de 82% dos casos) ou retidas para nova manutenção (18% dos casos). 
# A nova manutenção, neste caso, sempre aconteceria na estação B. Os tempos relacionados 
# a este sistema foram levantados e apresentam as seguintes distribuições: 
# Inspeção: Weibull (31.05, 1.03)min; Reparo Estação A: Exp (88.98)min; 
# Reparo Estação B: Gama (60.48, 1.03)min; Intervalo entre falhas: Gama (10.36, 0.97)h; 
# Intervalo entre chegadas de máquinas externas: Gama (7.97, 0.96)h. 
# De posse dos dados acima, construa 2 DCA's e modelos no DESK: Um DCA somente com máquinas internas, 
# e outro DCA com máquinas internas e externas.
# ####################################################################################

# desk-sim -m examples/10a.py --mode visualization
# desk-sim -m examples/10a.py --mode single
# desk-sim -m examples/10a.py --mode replications
# desk-sim -m examples/10a.py --mode factorial


# =====================================================================
# DISTRIBUIÇÕES — mesmos parâmetros do ex-10a.py do professor
# Atenção: gammavariate(shape, scale) — shape é o primeiro argumento
# O enunciado escreve Gamma(10.36, 0.97) mas o professor usa
# gammavariate(0.97, 10.36), ou seja shape=0.97, scale=10.36.
# =====================================================================
def distribuicao(tipo):
    return {
        'operacao': random.gammavariate(0.97, 10.36) * 60,  # h → min
        'mnt_a':    random.expovariate(1.0 / 88.98),        # min
        'mnt_b':    random.gammavariate(1.03, 60.48),        # min
        'inspecao': random.weibullvariate(31.05, 1.03),      # min
    }.get(tipo, 0.0)


# =====================================================================
# BUILD MODEL
# =====================================================================
def build_model(final_simulation_time=None, event_logger=None, verbose=True,
                entity_filter=None, resource_filter=None,
                event_type_filter=None, time_range=None):

    DAYS = 1440

    if final_simulation_time is None:
        final_simulation_time = 365 * DAYS

    model = SimulationModel(
        verbose=verbose,
        entity_filter=entity_filter,
        resource_filter=resource_filter,
        event_type_filter=event_type_filter,
        time_range=time_range
    )

    # -----------------------------------------------------------------
    # RECURSOS
    # -----------------------------------------------------------------
    operador_A = model.add_resource("Operador_A", capacity=1)
    operador_B = model.add_resource("Operador_B", capacity=1)
    operador_C = model.add_resource("Operador_C", capacity=1)

    # -----------------------------------------------------------------
    # BLOCO 1 — CREATE: gera as 5 máquinas no t=0
    # max_arrivals=5 + inter_arrival_time=0 → todas no instante zero
    # -----------------------------------------------------------------
    maquinas = CreateBlock(
        "Maquinas_Prontas", model.env,
        inter_arrival_time=lambda: 0,
        entity_prefix="Maquina",
        max_arrivals=5,
        first_creation=0.0,
        event_logger=event_logger
    )
    # Atributo inicial (será sobrescrito no decide_estacao)
    maquinas.assign_attributes(estacao=lambda: None)

    # -----------------------------------------------------------------
    # BLOCO 2 — PROCESS: Operação (tempo até a falha, sem recurso)
    # No SimPy do professor, momento_chegada é registrado APÓS a
    # operação — o TS mede só o ciclo de manutenção, não o tempo
    # operando. No DESK isso é equivalente: o CreateBlock cria no t=0
    # e a métrica de TS só começa a contar a partir do primeiro evento
    # pós warm-up.
    # -----------------------------------------------------------------
    operacao = ProcessBlock(
        "Operacao", model.env,
        delay_time=lambda: distribuicao('operacao'),
        resource=None,
        event_logger=event_logger
    )

    # -----------------------------------------------------------------
    # BLOCO 3 — DECIDE: Qual estação? (A=75%, B=25%)
    # Customização: além de rotear, cada rota grava o atributo
    # "estacao" na entidade (substituto do bloco ASSIGN do Arena).
    # -----------------------------------------------------------------
    def vai_para_A(entity):
        entity.add_attribute("estacao", "A")
        return True

    def vai_para_B(entity):
        entity.add_attribute("estacao", "B")
        return True

    decide_estacao = DecideBlock(
        "Decide_Estacao", model.env,
        decision_type="probability",
        event_logger=event_logger
    )

    # -----------------------------------------------------------------
    # BLOCO 4a — PROCESS: Reparo Estação A
    # -----------------------------------------------------------------
    reparo_A = ProcessBlock(
        "Manutencao_Estacao_A", model.env,
        delay_time=lambda: distribuicao('mnt_a'),
        resource=operador_A,
        resource_units=1,
        event_logger=event_logger
    )

    # -----------------------------------------------------------------
    # BLOCO 4b — PROCESS: Reparo Estação B
    # -----------------------------------------------------------------
    reparo_B = ProcessBlock(
        "Manutencao_Estacao_B", model.env,
        delay_time=lambda: distribuicao('mnt_b'),
        resource=operador_B,
        resource_units=1,
        event_logger=event_logger
    )

    # -----------------------------------------------------------------
    # BLOCO 5 — DECIDE: Gravar atributo "estacao" após reparo A
    # Customização: usado como ASSIGN substituto — condition sempre
    # True, mas grava o atributo como efeito colateral antes de rotear
    # para a inspeção.
    # -----------------------------------------------------------------
    def marca_estacao_A(entity):
        entity.add_attribute("estacao", "A")
        return True

    def marca_estacao_B(entity):
        entity.add_attribute("estacao", "B")
        return True

    apos_reparo_A = DecideBlock(
        "Apos_Reparo_A", model.env,
        decision_type="condition",
        event_logger=event_logger
    )

    apos_reparo_B = DecideBlock(
        "Apos_Reparo_B", model.env,
        decision_type="condition",
        event_logger=event_logger
    )

    # -----------------------------------------------------------------
    # BLOCO 6 — PROCESS: Inspeção Final
    # -----------------------------------------------------------------
    inspecao = ProcessBlock(
        "Inspecao", model.env,
        delay_time=lambda: distribuicao('inspecao'),
        resource=operador_C,
        resource_units=1,
        event_logger=event_logger
    )

    # -----------------------------------------------------------------
    # BLOCO 7 — DECIDE: Resultado da inspeção (C=90%, D=10%)
    # -----------------------------------------------------------------
    decide_inspecao = DecideBlock(
        "Decide_Inspecao", model.env,
        decision_type="probability",
        event_logger=event_logger
    )

    # -----------------------------------------------------------------
    # BLOCO 8 — DECIDE: Retorno à mesma estação (E ou F no DCA)
    # Customização: lê entity.get_attribute("estacao") para decidir
    # para qual estação de reparo retornar.
    # -----------------------------------------------------------------
    decide_retorno = DecideBlock(
        "Decide_Retorno_Estacao", model.env,
        decision_type="condition",
        event_logger=event_logger
    )

    # -----------------------------------------------------------------
    # Registrar todos os blocos no modelo
    # -----------------------------------------------------------------
    for bloco in [maquinas, operacao, decide_estacao,
                  reparo_A, reparo_B, apos_reparo_A, apos_reparo_B,
                  inspecao, decide_inspecao, decide_retorno]:
        model.add_block(bloco)

    # -----------------------------------------------------------------
    # ROTAS
    # -----------------------------------------------------------------

    # Decide estação: probabilidade + grava atributo via condition
    decide_estacao.add_route("Estacao_A", apos_reparo_A, probability=0.75)
    decide_estacao.add_route("Estacao_B", apos_reparo_B, probability=0.25)

    # Após decide, grava atributo e envia para o reparo correto
    apos_reparo_A.add_route("Para_Reparo_A", reparo_A, condition=marca_estacao_A)
    apos_reparo_B.add_route("Para_Reparo_B", reparo_B, condition=marca_estacao_B)

    # Resultado da inspeção:
    #   Aprovada (90%) → volta à operação (ciclo fechado)
    #   Reprovada (10%) → retorna à mesma estação
    decide_inspecao.add_route("Aprovada",  operacao,        probability=0.90)
    decide_inspecao.add_route("Reprovada", decide_retorno,  probability=0.10)

    # Retorno à mesma estação (desvio E ou F do DCA)
    decide_retorno.add_route(
        "Volta_A", reparo_A,
        condition=lambda e: e.get_attribute("estacao") == "A"
    )
    decide_retorno.add_route(
        "Volta_B", reparo_B,
        condition=lambda e: e.get_attribute("estacao") == "B"
    )

    # -----------------------------------------------------------------
    # CONEXÕES DE FLUXO
    #
    # Maquinas_Prontas → Operacao → Decide_Estacao
    #                                  ├─[75%]→ Apos_Reparo_A → Reparo_A ─┐
    #                                  └─[25%]→ Apos_Reparo_B → Reparo_B ─┤
    #                                                                       └→ Inspecao
    #                                                                            → Decide_Inspecao
    #                                                                               ├─[90%]→ Operacao (ciclo)
    #                                                                               └─[10%]→ Decide_Retorno
    #                                                                                          ├─ Reparo_A
    #                                                                                          └─ Reparo_B
    # -----------------------------------------------------------------
    maquinas.connect_to(operacao)
    operacao.connect_to(decide_estacao)
    reparo_A.connect_to(inspecao)
    reparo_B.connect_to(inspecao)
    inspecao.connect_to(decide_inspecao)

    return model


# =====================================================================
# MAIN — replicação única (equivalente ao ex-10a.py com n=1)
# =====================================================================
def main():
    DAYS = 1440

    config = SimulationConfig(
        duration=365 * DAYS,
        warm_up_period=30 * DAYS,
        seed=1,
        check_stability=True
    )
    config.validate()

    event_logger = EventLogger()

    model = build_model(
        final_simulation_time=config.duration,
        event_logger=event_logger,
        verbose=False
    )

    model.run_simulation(
        validate_resources=True,
        until=config.duration,
        seed=config.seed,
        warm_up_period=config.warm_up_period
    )

    # Relatório
    reporter = SimulationReporter(model)
    reporter.print_results()
    reporter._print_activity_metrics()
    reporter._print_resource_metrics()
    reporter._print_entity_counts()
    reporter._print_block_statistics()

    # Gráficos
    plotter = SimulationPlotter(model)
    # 1-3: Utilização individual de cada recurso ao longo do tempo
    plotter.plot_resource_use_over_time(
        show_warm_up=True, resource='Operador_A', moving_average_window=50)
    plotter.plot_resource_use_over_time(
        show_warm_up=True, resource='Operador_B', moving_average_window=50)
    plotter.plot_resource_use_over_time(
        show_warm_up=True, resource='Operador_C', moving_average_window=50)
    # 4: Comparação consolidada de todos os recursos
    plotter.plot_resources_utilization()
    # 5: WIP ao longo do tempo
    plotter.plot_wip_over_time()
    # 6: Distribuição do tempo no sistema
    plotter.plot_system_time_distribution()
    # 7: Métricas de atividade por bloco (filas e serviço)
    plotter.plot_activity_metrics()

    # Warm-up
    warmup_analyzer = WarmUpAnalyzer(model)
    warmup_analyzer.analyze_warm_up_period()

    return model, event_logger


# =====================================================================
# REPLICAÇÕES
# =====================================================================
def simulation_wrapper(seed=None, until=None, warm_up_period=None):
    event_logger = EventLogger()
    model = build_model(
        final_simulation_time=until,
        event_logger=event_logger,
        verbose=False
    )
    model.run_simulation(
        validate_resources=False,
        until=until,
        seed=seed,
        warm_up_period=warm_up_period
    )
    return model


def run_replications():
    DAYS = 1440
    replication_framework = ReplicationFramework(
        simulation_function=simulation_wrapper,
        n_replications=30
    )
    replication_framework.run_replications(
        base_seed=1,
        until=365 * DAYS,
        warm_up_period=30 * DAYS
    )
    df = replication_framework.get_results_dataframe()
    print(df.describe())


# =====================================================================
# Simulation Kit entry points
# =====================================================================
def run_single_replication():
    return main()


def run_replications_cli():
    run_replications()


def run_factorial_cli():
    pass


def run_visualization_cli(simulation_time=50000):
    return run_visualization(build_model, simulation_time=simulation_time)
