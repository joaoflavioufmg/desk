# =====================================================================
# FILE: oficina.py
# Exemplo 9 (ACD): Oficina de Reparos Automotivos
# =====================================================================
#
# SISTEMA:
#   - Carros chegam Exp(2h)
#   - Triagem: N(0,17h; 0,02h) | 1 funcionário
#   - Roteamento:
#       45% → Mecânica          [2 equipes, Exp(3,8h)]
#       25% → Elétrica          [1 equipe,  Exp(2,5h)]
#       18% → Lanternagem       [1 equipe,  Exp(5,0h)]
#       12% → Mecânica + Lanternagem (menor fila primeiro,
#              depois o outro serviço com prioridade alta)
#
# MODELAGEM (blocos desk):
#   Chegada → Triagem [func] → Decide_Tipo →
#       A (25%): Aguarda_Eletrica  → Manutencao_Eletrica  → Saida
#       B (45%): Aguarda_Mecanica  → Manutencao_Mecanica  → Saida
#       C (18%): Aguarda_Lantern   → Lanternagem           → Saida
#       D (12%): Decide_MenorFila  →
#                   E: Aguarda_Mecanica  → Manutencao_Mecanica  → Aguarda_Lantern → Lanternagem → Saida
#                   F: Aguarda_Lantern   → Lanternagem           → Aguarda_Mecanica → Manutencao_Mecanica → Saida
#
# ATRIBUTOS usados para controlar o fluxo dos 12%:
#   entity.priority  — sobe para 2 após o 1º serviço (fila com prioridade)
#   entity.servicos  — conta quantos serviços já foram feitos (0→1→2)
#
# UNIDADE DE TEMPO BASE: horas
# =====================================================================
import os
import random

import matplotlib.pyplot as plt

from desk.core.simulation_model import SimulationModel
from desk.core.entity import EventLogger
from desk.blocks.create_block import CreateBlock
from desk.blocks.process_block import ProcessBlock
from desk.blocks.decide_block import DecideBlock
from desk.blocks.dispose_block import DisposeBlock
from desk.analytics.plotting import SimulationPlotter
from desk.analytics.reporting import SimulationReporter
from desk.config.simulation_config import SimulationConfig
from desk.validation.stability import StabilityAnalyzer
from desk.stats.replication import ReplicationFramework
from desk.stats.factorial import FactorialExperiment
from desk.visualization.interface import run_visualization


# desk-sim -m examples/9.py --mode visualization
# desk-sim -m examples/9.py --mode single
# desk-sim -m examples/9.py --mode replications
# desk-sim -m examples/9.py --mode factorial


# -----------------------------------------------------------------------
# Constantes de tempo
# -----------------------------------------------------------------------
HOURS = 1          # unidade base = horas (sem conversão)
DAYS  = 24         # 1 dia = 24 horas

PASTA = os.path.dirname(os.path.abspath(__file__))

# Probabilidades de roteamento
P_ELETRICA    = 0.25
P_MECANICA    = 0.45
P_LANTERNAGEM = 0.18
P_AMBOS       = 0.12    # mecânica + lanternagem


# =====================================================================
# BUILD MODEL
# =====================================================================
def build_model(final_simulation_time=None, event_logger=None, verbose=True,
                entity_filter=None, resource_filter=None,
                event_type_filter=None, time_range=None):

    model = SimulationModel(
        verbose=verbose,
        entity_filter=entity_filter,
        resource_filter=resource_filter,
        event_type_filter=event_type_filter,
        time_range=time_range
    )

    # ------------------------------------------------------------------
    # Distribuições de tempo de serviço
    # ------------------------------------------------------------------
    def chegada_inter():
        return random.expovariate(1 / 2.0)          # Exp(2h)

    def triagem_time():
        return max(0.0, random.gauss(0.17, 0.02))   # N(0,17h; 0,02h)

    def mecanica_time():
        return random.expovariate(1 / 3.8)          # Exp(3,8h)

    def eletrica_time():
        return random.expovariate(1 / 2.5)          # Exp(2,5h)

    def lanternagem_time():
        return random.expovariate(1 / 5.0)          # Exp(5,0h)

    # ------------------------------------------------------------------
    # Recursos
    # ------------------------------------------------------------------
    func       = model.add_resource("funcionario",  1, "priority")
    eq_mec     = model.add_resource("eq_mecanica",  2, "priority")
    eq_elet    = model.add_resource("eq_eletrica",  1, "priority")
    eq_lant    = model.add_resource("eq_lantern",   1, "priority")

    # ------------------------------------------------------------------
    # Bloco de chegadas
    # ------------------------------------------------------------------
    chegadas = CreateBlock(
        "Chegada_Carros", model.env,
        inter_arrival_time=chegada_inter,
        entity_prefix="Carro",
        max_arrivals=None,
        first_creation=0.0,
        event_logger=event_logger
    )

    # ------------------------------------------------------------------
    # Triagem (1 funcionário)
    # ------------------------------------------------------------------
    triagem = ProcessBlock(
        "Triagem", model.env,
        resource=func,
        delay_time=triagem_time,
        resource_units=1,
        event_logger=event_logger
    )
    triagem.set_resource_name("funcionario")

    # ------------------------------------------------------------------
    # Decisão: tipo de serviço (A=25% elét | B=45% mec | C=18% lant | D=12% ambos)
    # ------------------------------------------------------------------
    decide_tipo = DecideBlock(
        "Decide_Tipo", model.env,
        decision_type="condition",
        event_logger=event_logger
    )

    # ------------------------------------------------------------------
    # Manutenção Elétrica
    # ------------------------------------------------------------------
    manut_elet = ProcessBlock(
        "Manutencao_Eletrica", model.env,
        resource=eq_elet,
        delay_time=eletrica_time,
        resource_units=1,
        event_logger=event_logger
    )
    manut_elet.set_resource_name("eq_eletrica")

    # ------------------------------------------------------------------
    # Manutenção Mecânica  (usada por B e pelos 12%)
    # ------------------------------------------------------------------
    manut_mec = ProcessBlock(
        "Manutencao_Mecanica", model.env,
        resource=eq_mec,
        delay_time=mecanica_time,
        resource_units=1,
        event_logger=event_logger
    )
    manut_mec.set_resource_name("eq_mecanica")

    # ------------------------------------------------------------------
    # Lanternagem  (usada por C e pelos 12%)
    # ------------------------------------------------------------------
    lanternagem = ProcessBlock(
        "Lanternagem", model.env,
        resource=eq_lant,
        delay_time=lanternagem_time,
        resource_units=1,
        event_logger=event_logger
    )
    lanternagem.set_resource_name("eq_lantern")

    # ------------------------------------------------------------------
    # Saída
    # ------------------------------------------------------------------
    saida = DisposeBlock("Saida_Rua", model.env, event_logger=event_logger)

    # ------------------------------------------------------------------
    # Decisão de menor fila (para os 12%)
    # Compara tamanho da fila de mecânica vs lanternagem
    # ------------------------------------------------------------------
    decide_menor_fila = DecideBlock(
        "Decide_MenorFila", model.env,
        decision_type="condition",
        event_logger=event_logger
    )

    # ------------------------------------------------------------------
    # Decisão pós-1º serviço (para os 12%):
    # se veio de mecânica → vai para lanternagem
    # se veio de lanternagem → vai para mecânica
    # ------------------------------------------------------------------
    decide_segundo = DecideBlock(
        "Decide_Segundo_Servico", model.env,
        decision_type="condition",
        event_logger=event_logger
    )

    # ------------------------------------------------------------------
    # Registra blocos no modelo
    # ------------------------------------------------------------------
    for bloco in [chegadas, triagem, decide_tipo,
                  manut_elet, manut_mec, lanternagem,
                  decide_menor_fila, decide_segundo, saida]:
        model.add_block(bloco)

    # ------------------------------------------------------------------
    # Conexões
    # ------------------------------------------------------------------
    chegadas.connect_to(triagem)

    triagem.connect_to(decide_tipo)

    # Após triagem: inicializa atributos e roteia
    # Usamos lambda para setar atributos durante a avaliação da condição.
    # Ordem das rotas importa: desk avalia na ordem de adição.

    def init_e_eletrica(e):
        e.priority = 1
        e.servicos = 1
        e.tipo = "eletrica"
        return random.random() < P_ELETRICA

    def init_e_mecanica(e):
        # só chega aqui se não for elétrica (prob acumulada considerada)
        e.priority = 1
        e.servicos = 1
        e.tipo = "mecanica"
        return random.random() < (P_MECANICA / (1 - P_ELETRICA))

    def init_e_lanternagem(e):
        e.priority = 1
        e.servicos = 1
        e.tipo = "lanternagem"
        return random.random() < (P_LANTERNAGEM / (1 - P_ELETRICA - P_MECANICA))

    def init_e_ambos(e):
        e.priority = 1
        e.servicos = 0   # ainda não fez nenhum dos dois
        e.tipo = "ambos"
        return True      # catch-all (12%)

    decide_tipo.add_route("Eletrica",    manut_elet,        condition=init_e_eletrica)
    decide_tipo.add_route("Mecanica",    manut_mec,         condition=init_e_mecanica)
    decide_tipo.add_route("Lanternagem", lanternagem,       condition=init_e_lanternagem)
    decide_tipo.add_route("Ambos",       decide_menor_fila, condition=init_e_ambos)

    # Saídas simples (elétrica, mecânica pura, lanternagem pura)
    manut_elet.connect_to(decide_segundo)
    manut_mec.connect_to(decide_segundo)
    lanternagem.connect_to(decide_segundo)

    # Decide_Segundo_Servico:
    #   - se tipo != ambos → saída
    #   - se tipo == ambos e servicos == 1 (já fez um) → saída
    #   - se tipo == ambos e servicos == 0 → foi pela 1ª vez → encaminha para 2º serviço

    def vai_para_lanternagem_depois(e):
        """12% que fez mecânica primeiro → lanternagem com prioridade"""
        if e.tipo == "ambos" and e.servicos == 0:
            # acabou de sair da mecânica (rota E → mec → aqui)
            e.servicos = 1
            e.priority = 2   # prioridade alta na próxima fila
            return True
        return False

    def vai_para_mecanica_depois(e):
        """12% que fez lanternagem primeiro → mecânica com prioridade"""
        if e.tipo == "ambos" and e.servicos == 0:
            # acabou de sair da lanternagem (rota F → lant → aqui)
            e.servicos = 1
            e.priority = 2
            return True
        return False

    # Precisamos saber qual serviço o carro "ambos" fez primeiro.
    # Usamos um atributo auxiliar: e.primeiro_servico
    # Ajustamos as funções de roteamento de decide_menor_fila para setar isso.

    def rota_mec_primeiro(e):
        """Menor fila → mecânica; marca que fez mecânica primeiro"""
        fila_mec  = eq_mec.queue_length  if hasattr(eq_mec,  "queue_length") else 0
        fila_lant = eq_lant.queue_length if hasattr(eq_lant, "queue_length") else 0
        # usa queue do SimPy via resource interno
        try:
            fila_mec  = len(eq_mec._resource.queue)
        except Exception:
            fila_mec = 0
        try:
            fila_lant = len(eq_lant._resource.queue)
        except Exception:
            fila_lant = 0
        if fila_mec <= fila_lant:
            e.primeiro_servico = "mecanica"
            return True
        return False

    def rota_lant_primeiro(e):
        """Senão → lanternagem; marca que fez lanternagem primeiro"""
        e.primeiro_servico = "lanternagem"
        return True  # catch-all

    decide_menor_fila.add_route("MecPrimeiro",  manut_mec,  condition=rota_mec_primeiro)
    decide_menor_fila.add_route("LantPrimeiro", lanternagem, condition=rota_lant_primeiro)

    # Decide_Segundo_Servico — avaliado após QUALQUER ProcessBlock
    def vai_sair(e):
        """Tipos simples (ou 12% que já fez os 2 serviços) → saída"""
        if e.tipo != "ambos":
            return True
        if e.servicos == 1:
            return True   # já completou os 2 serviços
        return False

    def ambos_para_lant(e):
        """12% que acabou de fazer mecânica → lanternagem"""
        if e.tipo == "ambos" and e.servicos == 0 and e.primeiro_servico == "mecanica":
            e.servicos = 1
            e.priority = 2
            return True
        return False

    def ambos_para_mec(e):
        """12% que acabou de fazer lanternagem → mecânica"""
        if e.tipo == "ambos" and e.servicos == 0 and e.primeiro_servico == "lanternagem":
            e.servicos = 1
            e.priority = 2
            return True
        return False

    decide_segundo.add_route("Saida",     saida,      condition=vai_sair)
    decide_segundo.add_route("ParaLant",  lanternagem, condition=ambos_para_lant)
    decide_segundo.add_route("ParaMec",   manut_mec,  condition=ambos_para_mec)

    return model


# =====================================================================
# HELPER — utilização por tempo ocupado
# =====================================================================
def _calc_utilizacao(df, recurso, duracao_total):
    df_r = df[df["resource"] == recurso].copy()
    starts    = df_r[df_r["lifecycle"] == "start"   ].sort_values("timestamp")["timestamp"].values
    completes = df_r[df_r["lifecycle"] == "complete" ].sort_values("timestamp")["timestamp"].values
    n = min(len(starts), len(completes))
    if n == 0:
        return 0.0
    ocupado = (completes[:n] - starts[:n]).sum()
    return ocupado / duracao_total


# =====================================================================
# MAIN
# =====================================================================
def main():
    print("=" * 65)
    print("  MODELO: Oficina de Reparos — Exemplo 9 (ACD/DCA)")
    print("=" * 65)

    event_logger = EventLogger()

    config = SimulationConfig(
        duration        = 52 * 5 * 8,   # ~1 ano de operação (52 sem × 5 dias × 8h)
        warm_up_period  = 5  * 8,        # 1 semana de warm-up
        seed            = 42,
        check_stability = True
    )
    config.validate()

    model = build_model(config.duration, event_logger, verbose=True)

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
    # Exporta e processa o event log
    # ------------------------------------------------------------------
    log_path = os.path.join(PASTA, "oficina_event_log.csv")
    df = event_logger.export_to_csv(log_path)

    warm    = config.warm_up_period
    periodo = config.duration - warm

    # IDs por tipo (baseado no atributo 'tipo' registrado no Arrival)
    ids_elet  = set(df.loc[(df["activity"] == "Arrival") & (df["priority"] == 1.0), "case_id"])

    # System time — todos os carros que saíram após warm-up
    df_dis = df[(df["activity"] == "Discharge") & (df["timestamp"] >= warm)].copy()
    st_all = df_dis["system_time"].dropna()

    # Contagem geral
    df_arr = df[(df["activity"] == "Arrival") & (df["timestamp"] >= warm)]
    n_total = len(df_arr)

    throughput = n_total / periodo   # carros/hora

    # WIP (Lei de Little)
    wip = throughput * st_all.mean() if len(st_all) > 0 else 0

    # Utilização dos recursos
    util_func = _calc_utilizacao(df, "funcionario", config.duration)
    util_mec  = _calc_utilizacao(df, "eq_mecanica", config.duration)
    util_elet = _calc_utilizacao(df, "eq_eletrica", config.duration)
    util_lant = _calc_utilizacao(df, "eq_lantern",  config.duration)

    # ------------------------------------------------------------------
    # Resultados
    # ------------------------------------------------------------------
    print("\n" + "=" * 65)
    print("  RESULTADOS — OFICINA DE REPAROS")
    print("=" * 65)
    print(f"  Duração total     : {config.duration:.0f} h")
    print(f"  Warm-up           : {warm:.0f} h")
    print(f"  Período de análise: {periodo:.0f} h")
    print()
    print(f"  Carros chegados (pós warm-up): {n_total}")
    print(f"  Throughput        : {throughput:.4f} carros/hora")
    print()
    print(f"  TEMPO NO SISTEMA — TODOS OS CARROS:")
    print(f"    Média   : {st_all.mean():.3f} h")
    print(f"    Mediana : {st_all.median():.3f} h")
    print(f"    Desvio  : {st_all.std():.3f} h")
    print(f"    Mínimo  : {st_all.min():.3f} h")
    print(f"    Máximo  : {st_all.max():.3f} h")
    print(f"    N       : {len(st_all)} carros")
    print()
    print(f"  WIP médio (Lei de Little): {wip:.2f} carros")
    print()
    print(f"  UTILIZAÇÃO DOS RECURSOS (sobre duração total):")
    print(f"    Funcionário (triagem)  : {util_func:.1%}")
    print(f"    Eq. Mecânica (2 equip.): {util_mec:.1%}  (por equipe)")
    print(f"    Eq. Elétrica (1 equip.): {util_elet:.1%}")
    print(f"    Eq. Lanternagem (1 eq.): {util_lant:.1%}")
    print("=" * 65)

    # ------------------------------------------------------------------
    # Relatório automático desk — validação V&V
    # ------------------------------------------------------------------
    print("\n--- Relatório automático desk (SimulationReporter) ---")
    reporter = SimulationReporter(model)
    reporter.print_results()
    reporter._print_activity_metrics()
    reporter._print_resource_metrics()
    reporter._print_entity_counts()
    reporter._print_block_statistics()

    # ------------------------------------------------------------------
    # Gráficos
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
        finally:
            _plt.show = _show_orig

    print("\nGerando gráficos...")

    plot_e_salva("oficina_func_uso.png",
        lambda: plotter.plot_resource_use_over_time(
            show_warm_up=True, resource="funcionario", moving_average_window=10))

    plot_e_salva("oficina_mecanica_uso.png",
        lambda: plotter.plot_resource_use_over_time(
            show_warm_up=True, resource="eq_mecanica", moving_average_window=10))

    plot_e_salva("oficina_eletrica_uso.png",
        lambda: plotter.plot_resource_use_over_time(
            show_warm_up=True, resource="eq_eletrica", moving_average_window=10))

    plot_e_salva("oficina_lantern_uso.png",
        lambda: plotter.plot_resource_use_over_time(
            show_warm_up=True, resource="eq_lantern", moving_average_window=10))

    plot_e_salva("oficina_wip.png",
        lambda: plotter.plot_wip_over_time())

    plot_e_salva("oficina_recursos_resumo.png",
        lambda: plotter.plot_resources_utilization())

    # Gráfico manual — system time
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle("Tempo no Sistema — Todos os Carros", fontsize=14)

    axes[0].hist(st_all, bins=40, color="steelblue", edgecolor="white", alpha=0.8)
    axes[0].axvline(st_all.mean(),   color="red",   linestyle="--",
                    label=f"Média: {st_all.mean():.2f} h")
    axes[0].axvline(st_all.median(), color="green", linestyle="--",
                    label=f"Mediana: {st_all.median():.2f} h")
    axes[0].set_xlabel("Tempo no sistema (h)")
    axes[0].set_ylabel("Frequência")
    axes[0].set_title("Distribuição")
    axes[0].legend()

    axes[1].boxplot(st_all)
    axes[1].set_ylabel("Tempo no sistema (h)")
    axes[1].set_title("Box Plot")

    plt.tight_layout()
    caminho_st = os.path.join(PASTA, "oficina_system_time.png")
    plt.savefig(caminho_st, dpi=150, bbox_inches="tight")
    print(f"  Salvo: {caminho_st}")

    return model, event_logger


# =====================================================================
# WRAPPER para replicações
# =====================================================================
def simulation_wrapper(seed=None, until=None, warm_up_period=None):
    event_logger = EventLogger()
    model = build_model(until, event_logger, verbose=False)
    dur = until or (52 * 5 * 8)
    model.run_simulation(
        validate_resources=False,
        until=dur,
        seed=seed,
        warm_up_period=warm_up_period if warm_up_period is not None else (5 * 8)
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
    rf.run_replications(base_seed=12345, until=(52 * 5 * 8), warm_up_period=(5 * 8))
    print(rf.get_results_dataframe().describe())


# =====================================================================
# ANÁLISE FATORIAL
# =====================================================================
def factorial_analysis():
    """
    Fatores testados:
      - taxa de chegada (intervalo médio entre carros): 1h | 2h | 3h
      - capacidade da equipe mecânica: 1 | 2 | 3 equipes
    """

    def sim_wrapper(seed=None, until=None, warm_up_period=None,
                    verbose=False, **kwargs):
        event_logger = EventLogger()
        model = build_model(until, event_logger, verbose=False)
        dur = until or (52 * 5 * 8)
        model.run_simulation(
            validate_resources=False,
            until=dur,
            seed=seed,
            warm_up_period=warm_up_period if warm_up_period is not None else (5 * 8)
        )
        return model

    factorial = FactorialExperiment(
        simulation_function=sim_wrapper,
        base_seed=12345
    )

    factorial.add_factor(
        factor_name="arrival_rate",
        parameter_path="CreateBlock.inter_arrival_time",
        levels=[1.0, 2.0, 3.0],
        description="Intervalo médio entre chegadas (h)"
    )

    factorial.add_factor(
        factor_name="eq_mecanica_capacity",
        parameter_path="Resource.eq_mecanica.capacity",
        levels=[1, 2, 3],
        description="Número de equipes mecânicas"
    )

    factorial.run_factorial_experiment(
        n_replications=5,
        simulation_time=52 * 5 * 8,
        warm_up_period=5 * 8,
        verbose=True
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

def run_visualization_cli(simulation_time=200):
    return run_visualization(build_model, simulation_time=simulation_time)


if __name__ == "__main__":
    main()
    run_visualization_cli(simulation_time=200)
    
