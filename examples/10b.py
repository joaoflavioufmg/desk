# =====================================================================
# FILE: exemplo10b.py
# =====================================================================
# Disciplina: EPD899 - Simulação de Sistemas Logísticos
# Prof: João Flávio F. Almeida <joao.flavio@dep.ufmg.br>
# Implementação DESK — Exemplo 10b: Manutenção (internas + externas)
#
# Sistema:
#   MÁQUINAS INTERNAS (5, ciclo fechado):
#     - Após falha → Estação A (75%) ou B (25%)
#     - Inspeção: 90% retornam à operação, 10% → mesma estação
#
#   MÁQUINAS EXTERNAS (chegada aberta, Gamma(0.96, 7.97) h):
#     - Sempre reparadas na Estação B
#     - Inspeção: 82% liberadas (saem do sistema), 18% → Estação B
#
# Referência SimPy: ex-10b.py (Prof. João Flávio)
#   seed=1 | duração=365 dias | warm-up=30 dias | n_replicacoes=5
#
# Customizações necessárias em relação ao uso padrão do DESK:
#
#   1. MODELO MISTO (fechado + aberto):
#      Dois CreateBlocks independentes:
#        - "Maquinas_Internas": max_arrivals=5, inter=0 (ciclo fechado)
#        - "Maquinas_Externas": max_arrivals=None, inter=Gamma (aberto)
#      Ambos compartilham os recursos Operador_B e Operador_C.
#
#   2. ATRIBUTOS "tipo" e "estacao" como ASSIGN substituto:
#      O DESK não possui bloco ASSIGN nativo. Os atributos são gravados
#      via assign_attributes() no CreateBlock para valor inicial, e
#      sobrescritos via DecideBlock condition (sempre True) antes de
#      cada reparo. "tipo" distingue interna/externa para aplicar a
#      taxa de aprovação correta na inspeção (90% vs 82%) e o destino
#      após aprovação (ciclo vs Dispose). "estacao" determina para onde
#      a máquina reprovada retorna.
#
#   3. INSPEÇÃO COMPARTILHADA COM TAXAS DIFERENTES:
#      Um único ProcessBlock de inspeção atende internas e externas.
#      O DecideBlock "Decide_Inspecao" usa decision_type="condition":
#      a condition "Aprovada" consulta entity.get_attribute("tipo") e
#      sorteia com a taxa correta (90% ou 82%). "Reprovada" é fallback
#      (sempre True se chegou aqui). Isso alinha com o ex-10b.py do
#      professor que usa: if tipo=='interna': sorteio<=0.9 else sorteio<=0.18
#
#   4. DISPOSE DIFERENCIADO após aprovação:
#      Internas aprovadas → voltam à Operacao (ciclo fechado, sem Dispose)
#      Externas aprovadas → DisposeBlock real (saem do sistema)
#      Requer um DecideBlock extra "Decide_Aprovadas_Tipo" para separar
#      os dois fluxos após a aprovação na inspeção.
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

# desk-sim -m examples/10b.py --mode visualization
# desk-sim -m examples/10b.py --mode single
# desk-sim -m examples/10b.py --mode replications
# desk-sim -m examples/10b.py --mode factorial

# =====================================================================
# DISTRIBUIÇÕES — mesmos parâmetros do ex-10b.py do professor
# =====================================================================
def distribuicao(tipo):
    return {
        'chegada':  random.gammavariate(0.96, 7.97) * 60,   # h → min
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
    operador_B = model.add_resource("Operador_B", capacity=1)  # compartilhado
    operador_C = model.add_resource("Operador_C", capacity=1)  # compartilhado

    # -----------------------------------------------------------------
    # BLOCO 1a — CREATE: 5 máquinas internas no t=0
    # -----------------------------------------------------------------
    maquinas_int = CreateBlock(
        "Maquinas_Internas", model.env,
        inter_arrival_time=lambda: 0,
        entity_prefix="MaqInt",
        max_arrivals=5,
        first_creation=0.0,
        event_logger=event_logger
    )
    maquinas_int.assign_attributes(tipo=lambda: "interna", estacao=lambda: None)

    # -----------------------------------------------------------------
    # BLOCO 1b — CREATE: máquinas externas (chegada aberta)
    # -----------------------------------------------------------------
    maquinas_ext = CreateBlock(
        "Maquinas_Externas", model.env,
        inter_arrival_time=lambda: distribuicao('chegada'),
        entity_prefix="MaqExt",
        max_arrivals=None,
        first_creation=0.0,
        event_logger=event_logger
    )
    maquinas_ext.assign_attributes(tipo=lambda: "externa", estacao=lambda: "B")

    # -----------------------------------------------------------------
    # BLOCO 2 — PROCESS: Operação (só máquinas internas)
    # -----------------------------------------------------------------
    operacao = ProcessBlock(
        "Operacao", model.env,
        delay_time=lambda: distribuicao('operacao'),
        resource=None,
        event_logger=event_logger
    )

    # -----------------------------------------------------------------
    # BLOCO 3 — DECIDE: Estação de reparo para internas (A=75%, B=25%)
    # Customização: grava atributo "estacao" via condition (ASSIGN sub.)
    # -----------------------------------------------------------------
    def marca_interna_A(entity):
        entity.add_attribute("estacao", "A")
        return True

    def marca_interna_B(entity):
        entity.add_attribute("estacao", "B")
        return True

    decide_estacao = DecideBlock(
        "Decide_Estacao", model.env,
        decision_type="probability",
        event_logger=event_logger
    )

    apos_decide_A = DecideBlock(
        "Atrib_Interna_A", model.env,
        decision_type="condition",
        event_logger=event_logger
    )

    apos_decide_B = DecideBlock(
        "Atrib_Interna_B", model.env,
        decision_type="condition",
        event_logger=event_logger
    )

    # -----------------------------------------------------------------
    # BLOCO 4 — DECIDE: Atribuir estacao=B para externas (ASSIGN sub.)
    # -----------------------------------------------------------------
    def marca_externa_B(entity):
        entity.add_attribute("estacao", "B")
        return True

    atrib_ext = DecideBlock(
        "Atrib_Externa_B", model.env,
        decision_type="condition",
        event_logger=event_logger
    )

    # -----------------------------------------------------------------
    # BLOCO 5a — PROCESS: Reparo Estação A (só internas)
    # -----------------------------------------------------------------
    reparo_A = ProcessBlock(
        "Manutencao_Estacao_A", model.env,
        delay_time=lambda: distribuicao('mnt_a'),
        resource=operador_A,
        resource_units=1,
        event_logger=event_logger
    )

    # -----------------------------------------------------------------
    # BLOCO 5b — PROCESS: Reparo Estação B (internas + externas)
    # -----------------------------------------------------------------
    reparo_B = ProcessBlock(
        "Manutencao_Estacao_B", model.env,
        delay_time=lambda: distribuicao('mnt_b'),
        resource=operador_B,
        resource_units=1,
        event_logger=event_logger
    )

    # -----------------------------------------------------------------
    # BLOCO 6 — PROCESS: Inspeção Final (compartilhada)
    # -----------------------------------------------------------------
    inspecao = ProcessBlock(
        "Inspecao", model.env,
        delay_time=lambda: distribuicao('inspecao'),
        resource=operador_C,
        resource_units=1,
        event_logger=event_logger
    )

    # -----------------------------------------------------------------
    # BLOCO 7 — DECIDE: Resultado da inspeção com taxa por tipo
    # Customização: decision_type="condition" para aplicar taxas
    # diferentes conforme o tipo da máquina (interna=90%, externa=82%)
    # Alinhado com o professor: interna sorteio<=0.9, externa sorteio>0.18
    # -----------------------------------------------------------------
    def aprovada(entity):
        taxa = 0.90 if entity.get_attribute("tipo") == "interna" else 0.82
        return random.random() < taxa

    def reprovada(entity):
        return True  # fallback — chegou aqui, foi reprovada

    decide_inspecao = DecideBlock(
        "Decide_Inspecao", model.env,
        decision_type="condition",
        event_logger=event_logger
    )

    # -----------------------------------------------------------------
    # BLOCO 8 — DECIDE: Aprovadas — separar interna (ciclo) e externa
    # Customização: bloco extra necessário pois o destino após aprovação
    # é diferente por tipo — não existe no modelo 10a.
    # -----------------------------------------------------------------
    decide_aprovadas = DecideBlock(
        "Decide_Aprovadas_Tipo", model.env,
        decision_type="condition",
        event_logger=event_logger
    )

    # -----------------------------------------------------------------
    # BLOCO 9 — DECIDE: Reprovadas → mesma estação (E ou F do DCA)
    # -----------------------------------------------------------------
    decide_retorno = DecideBlock(
        "Decide_Retorno_Estacao", model.env,
        decision_type="condition",
        event_logger=event_logger
    )

    # -----------------------------------------------------------------
    # BLOCO 10 — DISPOSE: apenas máquinas externas aprovadas saem
    # -----------------------------------------------------------------
    liberada_ext = DisposeBlock(
        "Liberada_Externa", model.env,
        event_logger=event_logger
    )

    # -----------------------------------------------------------------
    # Registrar todos os blocos no modelo
    # -----------------------------------------------------------------
    for bloco in [maquinas_int, maquinas_ext, operacao,
                  decide_estacao, apos_decide_A, apos_decide_B,
                  atrib_ext, reparo_A, reparo_B, inspecao,
                  decide_inspecao, decide_aprovadas,
                  decide_retorno, liberada_ext]:
        model.add_block(bloco)

    # -----------------------------------------------------------------
    # ROTAS
    # -----------------------------------------------------------------

    # Fluxo INTERNO: decide estação por probabilidade
    decide_estacao.add_route("Estacao_A", apos_decide_A, probability=0.75)
    decide_estacao.add_route("Estacao_B", apos_decide_B, probability=0.25)

    # Grava atributo e envia para reparo
    apos_decide_A.add_route("Para_Reparo_A", reparo_A, condition=marca_interna_A)
    apos_decide_B.add_route("Para_Reparo_B", reparo_B, condition=marca_interna_B)

    # Fluxo EXTERNO: grava atributo e envia para reparo B
    atrib_ext.add_route("Para_Reparo_B", reparo_B, condition=marca_externa_B)

    # Resultado da inspeção (condition com taxa por tipo)
    decide_inspecao.add_route("Aprovada",  decide_aprovadas, condition=aprovada)
    decide_inspecao.add_route("Reprovada", decide_retorno,   condition=reprovada)

    # Aprovadas: interna → ciclo, externa → Dispose
    decide_aprovadas.add_route(
        "Ciclo_Interno", operacao,
        condition=lambda e: e.get_attribute("tipo") == "interna"
    )
    decide_aprovadas.add_route(
        "Sai_Externa", liberada_ext,
        condition=lambda e: e.get_attribute("tipo") == "externa"
    )

    # Reprovadas: retornar à mesma estação
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
    # Maquinas_Internas → Operacao → Decide_Estacao
    #                                   ├─[75%]→ Atrib_A → Reparo_A ─┐
    #                                   └─[25%]→ Atrib_B → Reparo_B ─┤
    #                                                                  └→ Inspecao
    # Maquinas_Externas → Atrib_Ext ──────────────→ Reparo_B ─────────┘
    #                                                   Inspecao → Decide_Inspecao
    #                                                                ├─ Aprovada → Decide_Aprovadas
    #                                                                │               ├─ interna → Operacao
    #                                                                │               └─ externa → Dispose
    #                                                                └─ Reprovada → Decide_Retorno
    #                                                                                  ├─ Volta_A → Reparo_A
    #                                                                                  └─ Volta_B → Reparo_B
    # -----------------------------------------------------------------
    maquinas_int.connect_to(operacao)
    operacao.connect_to(decide_estacao)
    maquinas_ext.connect_to(atrib_ext)
    reparo_A.connect_to(inspecao)
    reparo_B.connect_to(inspecao)
    inspecao.connect_to(decide_inspecao)

    return model


# =====================================================================
# MAIN — replicação única
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
# REPLICAÇÕES — 5 replicações igual ao ex-10b.py do professor
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
