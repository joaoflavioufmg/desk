# =====================================================================
# FILE: comercio_eletronico.py
# Exemplo 7 (DCA): Comércio Eletrônico
# =====================================================================
#
# SISTEMA:
#   Pedidos chegam via e-mail: Exp(10 min)
#   Funcionário 1 verifica estoque: N(8; 0,75) min
#     → 20% falta item → encaminha Produção (saída B)
#     → 80% itens ok   → Funcionário 2 verifica crédito
#   Funcionário 2 verifica crédito: T(4, 6, 9) min
#     → 7%  recusado → Escreve Carta: N(3; 0,5) min → saída D
#     → 93% aprovado → encaminha Almoxarifado (saída C)
#
# DCA:
#   Chegada_Pedidos [Exp(10)]
#     → Verifica_Itens [Func1, N(8;0,75)]
#       → [A 80%] Verifica_Credito [Func2, T(4,6,9)]
#                   → [C 93%] Saida_Almoxarifado
#                   → [D  7%] Escreve_Carta [Func2, N(3;0,5)]
#                               → Saida_Recusado
#       → [B 20%] Saida_Producao
#
# RECURSOS:
#   Funcionário 1 (1) — verifica estoque
#   Funcionário 2 (1) — verifica crédito e escreve carta (mesmo recurso)
#
# UNIDADE DE TEMPO BASE: minutos
# =====================================================================

import os
import math
import random
 
import matplotlib.pyplot as plt
 
from desk.core.simulation_model import SimulationModel
from desk.core.entity import EventLogger
from desk.blocks.create_block import CreateBlock
from desk.blocks.process_block import ProcessBlock
from desk.blocks.decide_block import DecideBlock
from desk.blocks.dispose_block import DisposeBlock
from desk.analytics.reporting import SimulationReporter
from desk.analytics.plotting import SimulationPlotter
from desk.config.simulation_config import SimulationConfig
from desk.validation.stability import StabilityAnalyzer
from desk.stats.replication import ReplicationFramework
from desk.stats.factorial import FactorialExperiment
from desk.visualization.interface import run_visualization
 
# ####################################################################################
# Projeto: Comercio eletronico
# Autor: João Flávio F. ALmeida <joao.flavio@dep.ufmg.br>
# Implementação: Alunos da disciplina EPD733 - Simulação de sistema logísticos - PPGEP-UFMG
# Em uma empresa de comércio eletrônico, os pedidos chegam ao setor de vendas via correio eletrônico onde são analisados por um funcionário que verifica se todos os itens do pedido existem no estoque da empresa.
# Caso falte algum item, o pedido é encaminhado ao departamento de produção, saindo do setor de vendas.
# Caso todos os itens estejam disponíveis, o pedido é enviado para um outro funcionário, que entra em 
# contato com a administradora de cartões de crédito para verificar se a compra pode ser debitada no 
# cartão de crédito fornecido pelo cliente.
# Caso exista algum problema com o cartão, o pedido é recusado e o funcionário, antes de verificar 
# o próximo pedido, redige e envia uma mensagem para o cliente informando a recusa da administradora 
# do cartão. Se a administradora do cartão aceitar o débito, o pedido é encaminhado ao almoxarifado, 
# saindo do setor de vendas.
# Os pedidos chegam a intervalos de 10 minutos, seguindo uma distribuição exponencial. 
# O tempo de verificação do estoque segue uma distribuição normal com média de 8 minutos e 
# desvio padrão de 0,75 minutos. O processo de verificação do crédito segue uma distribuição 
# triangular com mínimo de 4, moda de 6 e máximo de 9 minutos. O tempo de redigir e enviar a  
# mensagem para o cliente, quando o pedido é recusado pela administradora de cartões, 
# segue uma distribuição normal com média de 3 minutos e desvio padrão de 0,5 minutos. 
# Sabe-se que historicamente, 20% dos pedidos contém itens em falta e que 7% das 
# transações com cartão são recusadas pela administradora. Construa o DCA para este sistema.
# ####################################################################################

# desk-sim -m src/7.py --mode visualization
# desk-sim -m src/7.py --mode single
# desk-sim -m src/7.py --mode replications
# desk-sim -m src/7.py --mode factorial


HOURS = 60
DAYS  = 1440
 
# Pasta de saída = mesma pasta do script
PASTA = os.path.dirname(os.path.abspath(__file__))
 
 
# =====================================================================
# BUILD MODEL
# =====================================================================
def build_model(final_simulation_time=None, event_logger=None, verbose=False,
                entity_filter=None, resource_filter=None,
                event_type_filter=None, time_range=None):
    """
    Comércio Eletrônico — Exemplo 7 (DCA).
 
    Fluxo:
      Chegada_Pedidos
        → Verifica_Itens [func1]
          → [B 20%] Saida_Producao
          → [A 80%] Verifica_Credito [func2]
                      → [C 93%] Saida_Almoxarifado
                      → [D  7%] Escreve_Carta [func2]
                                  → Saida_Recusado
 
    Nota: Funcionário 2 é o mesmo recurso para Verifica_Credito
    e Escreve_Carta — ao recusar, ele próprio redige a carta
    antes de atender o próximo pedido (recurso retido em sequência).
    """
 
    model = SimulationModel(
        verbose=verbose,
        entity_filter=entity_filter,
        resource_filter=resource_filter,
        event_type_filter=event_type_filter,
        time_range=time_range
    )
 
    # ------------------------------------------------------------------
    # Distribuições (padrão hospital.py — função única)
    # ------------------------------------------------------------------
    def triangular(a, m, b):
        """Triangular(mínimo=a, moda=m, máximo=b) via inversa analítica."""
        u = random.random()
        fc = (m - a) / (b - a)
        if u < fc:
            return a + math.sqrt(u * (b - a) * (m - a))
        else:
            return b - math.sqrt((1 - u) * (b - a) * (b - m))
 
    def distribution(tipo):
        return {
            'arrival'       : random.expovariate(1 / 10),
            'verif_itens'   : max(0.0, random.gauss(8, 0.75)),
            'verif_credito' : triangular(4, 6, 9),
            'escreve_carta' : max(0.0, random.gauss(3, 0.5)),
        }.get(tipo, 0.0)
 
    # ------------------------------------------------------------------
    # Recursos
    # ------------------------------------------------------------------
    func1 = model.add_resource("Funcionario_1", 1, "priority")
    func2 = model.add_resource("Funcionario_2", 1, "priority")
 
    # ------------------------------------------------------------------
    # Blocos
    # ------------------------------------------------------------------
 
    # Chegada de pedidos: Exp(10 min)
    chegada = CreateBlock(
        "Chegada_Pedidos", model.env,
        inter_arrival_time=lambda: distribution('arrival'),
        entity_prefix="Pedido",
        max_arrivals=None,
        first_creation=0.0,
        priority_generator=lambda: 0,
        event_logger=event_logger
    )
 
    # Verifica Itens: N(8; 0,75) min — Funcionário 1
    verif_itens = ProcessBlock(
        "Verifica_Itens", model.env,
        resource=func1,
        delay_time=lambda: distribution('verif_itens'),
        resource_units=1,
        event_logger=event_logger
    )
    verif_itens.set_resource_name("Funcionario_1")
 
    # Desvio A/B: 80% itens ok (A) | 20% falta item (B)
    desvio_estoque = DecideBlock(
        "Desvio_Estoque", model.env,
        decision_type="probability",
        event_logger=event_logger
    )
 
    # Verifica Crédito: T(4, 6, 9) min — Funcionário 2
    verif_credito = ProcessBlock(
        "Verifica_Credito", model.env,
        resource=func2,
        delay_time=lambda: distribution('verif_credito'),
        resource_units=1,
        event_logger=event_logger
    )
    verif_credito.set_resource_name("Funcionario_2")
 
    # Desvio C/D: 93% aprovado (C) | 7% recusado (D)
    desvio_credito = DecideBlock(
        "Desvio_Credito", model.env,
        decision_type="probability",
        event_logger=event_logger
    )
 
    # Escreve Carta: N(3; 0,5) min — mesmo Funcionário 2
    # O Func2 redige a carta antes de liberar o recurso para o próximo pedido
    escreve_carta = ProcessBlock(
        "Escreve_Carta", model.env,
        resource=func2,
        delay_time=lambda: distribution('escreve_carta'),
        resource_units=1,
        event_logger=event_logger
    )
    escreve_carta.set_resource_name("Funcionario_2")
 
    # Saídas
    saida_almoxarifado = DisposeBlock("Saida_Almoxarifado", model.env, event_logger=event_logger)
    saida_producao     = DisposeBlock("Saida_Producao",     model.env, event_logger=event_logger)
    saida_recusado     = DisposeBlock("Saida_Recusado",     model.env, event_logger=event_logger)
 
    # ------------------------------------------------------------------
    # Adiciona blocos ao modelo
    # ------------------------------------------------------------------
    for block in [chegada, verif_itens, desvio_estoque,
                  verif_credito, desvio_credito, escreve_carta,
                  saida_almoxarifado, saida_producao, saida_recusado]:
        model.add_block(block)
 
    # ------------------------------------------------------------------
    # Conexões
    # ------------------------------------------------------------------
    chegada.connect_to(verif_itens)
    verif_itens.connect_to(desvio_estoque)
 
    # CORREÇÃO: 1.00 garante que 100% do fluxo restante (20%) vá para a Produção
    desvio_estoque.add_route("Itens_OK",    verif_credito,    probability=0.80)
    desvio_estoque.add_route("Falta_Item",  saida_producao,   probability=1.00) 
 
    verif_credito.connect_to(desvio_credito)
 
    # CORREÇÃO: 1.00 garante que 100% do fluxo restante (7%) vá para a Carta
    desvio_credito.add_route("Credito_OK",      saida_almoxarifado, probability=0.93)
    desvio_credito.add_route("Credito_Recusado", escreve_carta,     probability=1.00) 
 
    escreve_carta.connect_to(saida_recusado)
 
    return model
 
 
# =====================================================================
# HELPER — utilização de recursos
# =====================================================================
def _calc_utilizacao(df, recurso, duracao_total):
    """Utilização = tempo_ocupado / duracao_total (sobre toda a simulação)."""
    df_r = df[df["resource"] == recurso].copy()
    starts    = df_r[df_r["lifecycle"] == "start"   ].sort_values("timestamp")["timestamp"].values
    completes = df_r[df_r["lifecycle"] == "complete" ].sort_values("timestamp")["timestamp"].values
    n = min(len(starts), len(completes))
    if n == 0:
        return 0.0
    return (completes[:n] - starts[:n]).sum() / duracao_total
 
 
# =====================================================================
# MAIN
# =====================================================================
# =====================================================================
# MAIN (Cálculo Dinâmico Automatizado — Sem Valores Chumbados)
# =====================================================================
def main():
    print("=" * 65)
    print("  MODELO: Comércio Eletrônico — Exemplo 7 (DCA)")
    print("=" * 65)
 
    event_logger = EventLogger()
 
    config = SimulationConfig(
        duration       = 7 * DAYS,    # 1 semana
        warm_up_period = 4 * HOURS,   # 4 horas de aquecimento
        seed           = 42,
        check_stability= True
    )
    config.validate()
 
    model = build_model(config.duration, event_logger, verbose=False)
 
    print("\nVerificando estabilidade...")
    stability_analyzer = StabilityAnalyzer(model)
    model.stability_result = stability_analyzer.check_system_stability()
 
    print("\nRodando simulação...")
    model.run_simulation(
        validate_resources=True,
        until=config.duration,
        seed=config.seed,
        warm_up_period=config.warm_up_period
    )
 
    # ------------------------------------------------------------------
    # Event log
    # ------------------------------------------------------------------
    log_path = os.path.join(PASTA, "comercio_event_log.csv")
    df = event_logger.export_to_csv(log_path)
 
    warm    = config.warm_up_period
    periodo = config.duration - warm
 
    # Pedidos que chegaram após o warm-up
    df_arr_after = df[(df["activity"] == "Arrival") & (df["timestamp"] >= warm)]
    n_pedidos = len(df_arr_after)
 
    # System time de todos os pedidos concluídos após warm-up
    df_dis = df[(df["activity"] == "Discharge") & (df["timestamp"] >= warm)]
    st_all = df_dis["system_time"].dropna()
 
    # Pedidos por destino
    df_after = df[df["timestamp"] >= warm].copy()
 
    visitou_escreve  = set(df_after[df_after["activity"] == "Escreve_Carta" ]["case_id"])
    visitou_credito  = set(df_after[df_after["activity"] == "Verifica_Credito"]["case_id"])
    visitou_itens    = set(df_after[df_after["activity"] == "Verifica_Itens" ]["case_id"])
 
    todos_concluidos = set(df_after[df_after["activity"] == "Discharge"]["case_id"])
 
    ids_recus = todos_concluidos & visitou_escreve
    ids_prod  = todos_concluidos & visitou_itens - visitou_credito
    ids_almox = todos_concluidos & visitou_credito - visitou_escreve
 
    n_almox = len(ids_almox)
    n_prod  = len(ids_prod)
    n_recus = len(ids_recus)
 
    throughput = n_pedidos / periodo   # pedidos/min
 
    util_f1 = _calc_utilizacao(df, "Funcionario_1", config.duration)
    util_f2 = _calc_utilizacao(df, "Funcionario_2", config.duration)
 
    # ------------------------------------------------------------------
    # CÁLCULO DINÂMICO DOS INDICADORES SOLICITADOS (SEM CHUMBAMENTO)
    # ------------------------------------------------------------------
    # 1. TS (Tempo Médio no Sistema) direto do log de Discharge
    mean_TS = st_all.mean() if len(st_all) > 0 else 0.0
 
    # 2. TA (Tempo Médio de Atendimento): extrai a duração real do uso de recursos por caso
    df_res = df_after[df_after["resource"].notna()]
    res_starts = df_res[df_res["lifecycle"] == "start"].set_index(["case_id", "activity"])["timestamp"]
    res_comps  = df_res[df_res["lifecycle"] == "complete"].set_index(["case_id", "activity"])["timestamp"]
    ta_per_case = (res_comps - res_starts).dropna().groupby("case_id").sum()
 
    # Alinha os tempos de atendimento com os casos concluídos
    ts_indexed = df_dis.set_index("case_id")["system_time"]
    ta_aligned = ta_per_case.reindex(ts_indexed.index).fillna(0.0)
    mean_TA = ta_aligned.mean()
 
    # 3. TF (Tempo Médio em Fila): Tempo no Sistema - Tempo em Atendimento
    tf_per_case = ts_indexed - ta_aligned
    mean_TF = max(0.0, tf_per_case.mean())
 
    # 4. Métricas de Volume (NS, NF, NA) via Lei de Little (N = Lambda * T)
    lambda_sys = n_pedidos / periodo
    mean_NS = lambda_sys * mean_TS
    mean_NF = lambda_sys * mean_TF
    mean_NA = lambda_sys * mean_TA
 
    # ------------------------------------------------------------------
    # Resultados
    # ------------------------------------------------------------------
    print("\n" + "=" * 65)
    print("  RESULTADOS — COMÉRCIO ELETRÔNICO")
    print("=" * 65)
    print(f"  Duração total     : {config.duration/HOURS:.0f} h  ({config.duration/DAYS:.1f} dias)")
    print(f"  Warm-up           : {warm/HOURS:.0f} h")
    print(f"  Período de análise: {periodo/HOURS:.0f} h")
    print()
    print(f"  Pedidos chegados (pós warm-up): {n_pedidos}")
    print(f"  Throughput        : {throughput * HOURS:.2f} pedidos/hora")
    print()
    print(f"  DESTINO DOS PEDIDOS:")
    print(f"    Almoxarifado (aprovados) : {n_almox}  ({n_almox/max(n_pedidos,1):.1%})")
    print(f"    Produção (falta item)    : {n_prod}   ({n_prod/max(n_pedidos,1):.1%})")
    print(f"    Recusados (cartão)       : {n_recus}  ({n_recus/max(n_pedidos,1):.1%})")
    print()
    print(f"  TEMPO NO SISTEMA (todos os pedidos):")
    print(f"    Média   : {mean_TS:.2f} min")
    print(f"    Mediana : {st_all.median():.2f} min")
    print(f"    Desvio  : {st_all.std():.2f} min")
    print(f"    Mínimo  : {st_all.min():.2f} min")
    print(f"    Máximo  : {st_all.max():.2f} min")
    print(f"    N       : {len(st_all)} pedidos")
    print()
    print(f"  WIP médio (Lei de Little): {mean_NS:.2f} pedidos")
    print()
    print(f"  UTILIZAÇÃO DOS RECURSOS:")
    print(f"    Funcionário 1 (verif. estoque)          : {util_f1:.1%}")
    print(f"    Funcionário 2 (verif. crédito + carta)  : {util_f2:.1%}")
    print("-" * 65)
    print("  ESTATÍSTICAS COLETADAS DINAMICAMENTE:")
    print("-" * 65)
    print(f"    NS: {mean_NS:.2f} pedidos")
    print(f"    NF: {mean_NF:.2f} pedidos")
    print(f"    NA: {mean_NA:.2f} pedidos")
    print(f"    TS: {mean_TS:.2f} minutos")
    print(f"    TF: {mean_TF:.2f} minutos")
    print(f"    TA: {mean_TA:.2f} minutos")
    print(f"    USO-F1: {util_f1*100:.2f}%")
    print(f"    USO-F2: {util_f2*100:.2f}%")
    print("=" * 65)
 
    # ------------------------------------------------------------------
    # Gráficos — exibe e salva na mesma pasta do script
    # ------------------------------------------------------------------
    plotter = SimulationPlotter(model)
 
    def plot_e_salva(nome_arquivo, plot_fn):
        import matplotlib.pyplot as _plt
        caminho = os.path.join(PASTA, nome_arquivo)
        _show_orig = _plt.show
 
        def _show_e_salva(*args, **kwargs):
            _plt.gcf().savefig(caminho, dpi=150, bbox_inches="tight")
            print(f"  Salvo: {caminho}")
            _plt.show = _show_orig          
            _show_orig(*args, **kwargs)
 
        _plt.show = _show_e_salva
        try:
            plot_fn()
        except:
            pass
        finally:
            _plt.show = _show_orig          
 
    print("\nGerando gráficos...")
 
    plot_e_salva("ce_func1_uso.png",
        lambda: plotter.plot_resource_use_over_time(
            show_warm_up=True, resource="Funcionario_1", moving_average_window=30))
 
    plot_e_salva("ce_func2_uso.png",
        lambda: plotter.plot_resource_use_over_time(
            show_warm_up=True, resource="Funcionario_2", moving_average_window=30))
 
    plot_e_salva("ce_wip.png",
        lambda: plotter.plot_wip_over_time())
 
    plot_e_salva("ce_system_time.png",
        lambda: plotter.plot_system_time_distribution())
 
    plot_e_salva("ce_recursos_resumo.png",
        lambda: plotter.plot_resources_utilization())
 
    return model, event_logger
 
 
# =====================================================================
# WRAPPER
# =====================================================================
def simulation_wrapper(seed=None, until=None, warm_up_period=None):
    event_logger = EventLogger()
    model = build_model(until, event_logger, verbose=False)
    model.run_simulation(
        validate_resources=False,
        until=until or 7 * DAYS,
        seed=seed,
        warm_up_period=warm_up_period if warm_up_period is not None else 4 * HOURS
    )
    return model
 
 
# =====================================================================
# REPLICAÇÕES
# =====================================================================
def run_replications():
    rf = ReplicationFramework(
        simulation_function=simulation_wrapper,
        n_replications=30
    )
    rf.run_replications(base_seed=12345, until=7 * DAYS, warm_up_period=4 * HOURS)
    print(rf.get_results_dataframe().describe())
 
 
# =====================================================================
# ANÁLISE FATORIAL
# =====================================================================
def factorial_analysis():
    def sim_wrapper(seed=None, until=None, warm_up_period=4*HOURS,
                    verbose=False, **kwargs):
        model = build_model(verbose=False)
        model.run_simulation(validate_resources=False, until=until,
                             seed=seed, warm_up_period=warm_up_period)
        return model
 
    factorial = FactorialExperiment(simulation_function=sim_wrapper, base_seed=12345)
 
    factorial.add_factor(
        factor_name="taxa_chegada",
        parameter_path="CreateBlock.inter_arrival_time",
        levels=[8, 10, 12],
        description="Intervalo médio entre pedidos (min)"
    )
    factorial.add_factor(
        factor_name="func1_capacity",
        parameter_path="Resource.Funcionario_1.capacity",
        levels=[1, 2],
        description="Número de Funcionários 1"
    )
 
    factorial.run_factorial_experiment(
        n_replications=5,
        simulation_time=7  * DAYS,
        warm_up_period=4   * HOURS,
        verbose=False
    )
    factorial.print_summary()
    factorial.plot_main_effects("system_time_avg")
    factorial.export_results()
    return factorial
 
 
# =====================================================================
# SIMULATION KIT
# =====================================================================
def run_single_replication():
    return main()
 
def run_replications_cli():
    run_replications()
 
def run_factorial_cli():
    return factorial_analysis()
 
def run_visualization_cli(simulation_time=500):
    return run_visualization(build_model, simulation_time=simulation_time)
 
 
if __name__ == "__main__":
    main()
    run_visualization_cli(simulation_time=500)