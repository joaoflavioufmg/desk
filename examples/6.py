# =====================================================================
# FILE: ex6_comentado.py
# Disciplina: EPD899 — Simulação de Sistemas Logísticos
# Prof: João Flávio F. Almeida <joao.flavio@dep.ufmg.br>
#
# Sistema de Docas (Matérias-primas A e B)
# Implementado com DESK (Discrete Event Simulation Kit)
#
# DESK é um framework de simulação de eventos discretos construído
# sobre o SimPy. Ele organiza o modelo em "blocos" reutilizáveis
# (CREATE, PROCESS, DECIDE, DISPOSE), semelhante a ferramentas
# comerciais como Arena ou AnyLogic.
#
# Fluxo do sistema:
#   Chegada → Recepção (porteiro, prio alta)
#       → [30%] Doca A  (descarga normal 30±6 min)
#       → [70%] Doca B1 ou B2 (menor fila, triangular 30-50 moda 38)
#   → Liberação (funcionário, normal 7±2 min)
#   → Vistoria  (porteiro, prio baixa)
#   → Saída
# =====================================================================

import random
import sys

# --- Imports do DESK ---
# Módulo de experimento fatorial: varia parâmetros e analisa efeitos
from desk.stats.factorial import FactorialExperiment
# Módulo de replicações: executa N rodadas independentes e calcula IC
from desk.stats.replication import ReplicationFramework
# Núcleo do modelo: gerencia o ambiente SimPy e os blocos
from desk.core.simulation_model import SimulationModel
# Registrador de eventos: grava cada evento da simulação em log
from desk.core.entity import EventLogger
# Bloco CREATE: gera entidades (chegadas) no sistema
from desk.blocks.create_block import CreateBlock
# Bloco PROCESS: representa uma atividade com recurso e tempo de serviço
from desk.blocks.process_block import ProcessBlock
# Bloco DECIDE: roteia entidades por condição ou probabilidade
from desk.blocks.decide_block import DecideBlock
# Bloco DISPOSE: remove entidades do sistema (saída)
from desk.blocks.dispose_block import DisposeBlock
# Módulo de relatórios: imprime métricas ao final da simulação
from desk.analytics.reporting import SimulationReporter
# Módulo de gráficos: plota utilização, WIP, tempo no sistema etc.
from desk.analytics.plotting import SimulationPlotter
# Coleta e exporta métricas brutas (tempo no sistema, utilização etc.)
from desk.analytics.metrics import MetricsCollector
# Verifica estabilidade do sistema: ρ < 1 para todos os recursos
from desk.validation.stability import StabilityAnalyzer
# Detecta automaticamente o período de aquecimento (warm-up)
from desk.validation.warmup import WarmUpAnalyzer
# Configuração centralizada da simulação (duração, aquecimento, semente)
from desk.config.simulation_config import SimulationConfig
# Interface visual: animação em tempo real da simulação
from desk.visualization.interface import run_visualization


# ####################################################################################
# Projeto: Empresa de transporte
# Autor: João Flávio F. ALmeida <joao.flavio@dep.ufmg.br>
# Implementação: Alunos da disciplina EPD733 - Simulação de sistema logísticos - PPGEP-UFMG
# Uma empresa usa matérias-primas do tipo A e B (MPA,MPB), que são transportadas por caminhões, 
# de mesma capacidade, que chegam à empresa segundo uma distribuição exponencial com média 
# de 25 minutos. Sabe-se que 30% desses caminhões trazem MPA e o restante, do tipo MPB. 
# Ao chegarem à empresa os caminhões têm sua carga checada por um funcionário da portaria, 
# que preenche um formulário e encaminha o caminhão para uma das docas de descarga, 
# atividade que possui duração exponencialmente distribuída com média de 5 minutos. 
# Existe 1 doca (Doca A) para descarga de caminhões que transportam MPA e 2 docas 
# para aqueles que transportam MPB (Doca B1 e Doca B2). 
# O tempo de descarga dos caminhões que transportam MPA segue uma distribuição normal 
# com média de 30 minutos e desvio padrão de 6 minutos. O tempo de descarga dos caminhões 
# que transportam MPB segue uma distribuição triangular com moda de 38, mínimo de 30 e 
# máximo de 50 minutos. Os caminhões com MPB são encaminhados para a doca que tiver 
# menor fila (B1 ou B2). Após a descarga, os caminhões seguem para outro setor da empresa 
# onde entregam as notas fiscais e os recibos de descarga. 
# Neste setor, os caminhões são atendidos por um funcionário, que preenche um formulário 
# de liberação do veículo. O tempo gasto pelo funcionário para realização deste serviço 
# segue uma distribuição normal com média de 7 minutos e desvio padrão de 2 minutos.
# Após receberem o formulário de liberação, os caminhões se dirigem à portaria da empresa, 
# onde o mesmo funcionário que os recebeu faz uma vistoria de segurança nos caminhões 
# e os libera em seguida. O tempo gasto nesta vistoria é exponencialmente distribuído 
# com média de 4 minutos. O funcionário da portaria prioriza o atendimento de chegada 
# de caminhões em relação à vistoria de saída. Construa o DCA para este sistema.
# ####################################################################################

# desk-sim -m src/6.py --mode visualization
# desk-sim -m src/6.py --mode single
# desk-sim -m src/6.py --mode replications
# desk-sim -m src/6.py --mode factorial


# =====================================================================
# DISTRIBUIÇÕES DE TEMPO
# =====================================================================
# Função que retorna o tempo amostrado de acordo com o tipo de evento.
# Cada chave do dicionário corresponde a uma etapa do fluxo.
# Unidade base: minutos.
def distribuicao(tipo):
    return {
        # Intervalo entre chegadas: exponencial com média 25 min
        'chegada':    random.expovariate(1 / 25),
        # Tempo de recepção na portaria: exponencial com média 5 min
        'recepcao':   random.expovariate(1 / 5),
        # Tempo de descarga tipo A: normal com média 30 min e DP 6 min
        # max(0,...) evita valores negativos
        'descarga_A': max(0, random.gauss(30, 6)),
        # Tempo de descarga tipo B: triangular(mínimo=30, máximo=50, moda=38)
        'descarga_B': random.triangular(30, 50, 38),
        # Tempo de liberação pelo funcionário: normal média 7 min DP 2 min
        'liberacao':  max(0, random.gauss(7, 2)),
        # Tempo de vistoria de saída: exponencial com média 4 min
        'vistoria':   random.expovariate(1 / 4),
    }.get(tipo, 0.0)


# =====================================================================
# CONSTRUÇÃO DO MODELO
# =====================================================================
# Esta função monta toda a estrutura do modelo de simulação:
# recursos, blocos e conexões entre eles.
# É chamada a cada replicação para garantir estado limpo.
#
# Parâmetros:
#   final_simulation_time: duração total da simulação (minutos)
#   event_logger: objeto que registra todos os eventos
#   verbose: se True, imprime cada evento no console
#   entity/resource/event_type/time_range filters: filtros para o log
def build_model(final_simulation_time=None, event_logger=None, verbose=False,
                entity_filter=None, resource_filter=None,
                event_type_filter=None, time_range=None):

    # Cria o modelo DESK, que internamente cria um ambiente SimPy
    model = SimulationModel(
        verbose=verbose,
        entity_filter=entity_filter,
        resource_filter=resource_filter,
        event_type_filter=event_type_filter,
        time_range=time_range,
    )

    # ------------------------------------------------------------------
    # RECURSOS
    # ------------------------------------------------------------------
    # model.add_resource(nome, capacidade, tipo)
    #   - capacidade: número de servidores paralelos
    #   - tipo "priority": usa PriorityResource do SimPy, onde entidades
    #     com menor número de prioridade são atendidas primeiro.
    #     Aqui: chegadas (prio=0) têm preferência sobre vistoria (prio=1)
    #   - sem tipo (padrão): Resource comum, atendimento FIFO
    # ------------------------------------------------------------------

    # Porteiro: 1 servidor com fila de prioridade
    # (recebe chegadas e faz vistoria de saída, priorizando chegadas)
    porteiro    = model.add_resource("Porteiro",    1, "priority")

    # Funcionário: 1 servidor FIFO para liberação de documentos
    funcionario = model.add_resource("Funcionario", 1)

    # Doca A: 1 vaga para descarga de matéria-prima tipo A
    doca_A      = model.add_resource("Doca_A",      1)

    # Doca B1 e B2: 2 docas para matéria-prima tipo B
    doca_B1     = model.add_resource("Doca_B1",     1)
    doca_B2     = model.add_resource("Doca_B2",     1)

    # ------------------------------------------------------------------
    # BLOCO 1 — CHEGADA (CREATE)
    # ------------------------------------------------------------------
    # CreateBlock gera entidades ("caminhões") continuamente.
    # Cada entidade criada dispara o processo de simulação.
    #
    #   inter_arrival_time: função que retorna o intervalo entre chegadas
    #   entity_prefix: prefixo do nome das entidades (ex: "Caminhao_1")
    #   max_arrivals: None = sem limite de chegadas
    #   first_creation: tempo da primeira chegada (0 = imediata)
    #   priority_generator: define a prioridade inicial da entidade.
    #     lambda: 0 → todas as chegadas entram com prioridade 0 (alta),
    #     garantindo preferência sobre vistoria de saída (prio=1)
    #     no porteiro.
    # ------------------------------------------------------------------
    chegada = CreateBlock(
        "Chegada", model.env,
        inter_arrival_time=lambda: distribuicao('chegada'),
        entity_prefix="Caminhao",
        max_arrivals=None,
        first_creation=0.0,
        priority_generator=lambda: 0,   # alta prioridade no porteiro
        event_logger=event_logger,
    )

    # ------------------------------------------------------------------
    # BLOCO 2 — RECEPÇÃO (PROCESS)
    # ------------------------------------------------------------------
    # ProcessBlock representa uma atividade com:
    #   - Fila de espera (Seize)
    #   - Ocupação do recurso e serviço (Delay)
    #   - Liberação do recurso (Release)
    #
    # O porteiro recebe o caminhão, verifica a carga e
    # preenche o formulário de encaminhamento.
    # resource_units=1: cada atendimento ocupa 1 servidor do porteiro.
    # set_resource_name: vincula o nome do recurso ao bloco para
    # fins de relatório e rastreamento.
    # ------------------------------------------------------------------
    recepcao = ProcessBlock(
        "Recepcao", model.env,
        resource=porteiro,
        delay_time=lambda: distribuicao('recepcao'),
        resource_units=1,
        event_logger=event_logger,
    )
    recepcao.set_resource_name('Porteiro')

    # ------------------------------------------------------------------
    # BLOCO 3 — DECISÃO: TIPO DE CARGA (DECIDE)
    # ------------------------------------------------------------------
    # DecideBlock roteia entidades para diferentes caminhos.
    # decision_type="condition": avalia funções booleanas em ordem.
    # A primeira condição verdadeira define o destino da entidade.
    #
    # As rotas são definidas abaixo com add_route().
    # ------------------------------------------------------------------
    decide_tipo = DecideBlock(
        "Decide_Tipo_Carga", model.env,
        decision_type="condition",
        event_logger=event_logger,
    )

    # ------------------------------------------------------------------
    # BLOCO 4a — DESCARGA DOCA A (PROCESS)
    # ------------------------------------------------------------------
    # Caminhões com carga tipo A (30% das chegadas) são descarregados
    # na Doca A. Tempo segue distribuição normal (média 30, DP 6 min).
    # ------------------------------------------------------------------
    descarga_a = ProcessBlock(
        "Descarga_A", model.env,
        resource=doca_A,
        delay_time=lambda: distribuicao('descarga_A'),
        resource_units=1,
        event_logger=event_logger,
    )
    descarga_a.set_resource_name('Doca_A')

    # ------------------------------------------------------------------
    # BLOCO 4b — DECISÃO: DOCA B1 OU B2 (DECIDE)
    # ------------------------------------------------------------------
    # Caminhões tipo B são encaminhados para a doca com menor fila.
    # Acessa len(doca_B1.queue) e len(doca_B2.queue) diretamente,
    # pois o objeto de recurso do DESK expõe o atributo .queue
    # (herdado do SimPy).
    # ------------------------------------------------------------------
    decide_doca_B = DecideBlock(
        "Decide_Doca_B", model.env,
        decision_type="condition",
        event_logger=event_logger,
    )

    # ------------------------------------------------------------------
    # BLOCO 4c — DESCARGA DOCA B1 (PROCESS)
    # ------------------------------------------------------------------
    # Uma das duas docas para carga tipo B.
    # Tempo de descarga: triangular(mínimo=30, máximo=50, moda=38).
    # ------------------------------------------------------------------
    descarga_b1 = ProcessBlock(
        "Descarga_B1", model.env,
        resource=doca_B1,
        delay_time=lambda: distribuicao('descarga_B'),
        resource_units=1,
        event_logger=event_logger,
    )
    descarga_b1.set_resource_name('Doca_B1')

    # ------------------------------------------------------------------
    # BLOCO 4d — DESCARGA DOCA B2 (PROCESS)
    # ------------------------------------------------------------------
    # Segunda doca para carga tipo B. Mesma distribuição que B1.
    # ------------------------------------------------------------------
    descarga_b2 = ProcessBlock(
        "Descarga_B2", model.env,
        resource=doca_B2,
        delay_time=lambda: distribuicao('descarga_B'),
        resource_units=1,
        event_logger=event_logger,
    )
    descarga_b2.set_resource_name('Doca_B2')

    # ------------------------------------------------------------------
    # BLOCO 5 — LIBERAÇÃO (PROCESS)
    # ------------------------------------------------------------------
    # Após a descarga, o caminhão vai ao setor administrativo onde
    # um funcionário preenche o formulário de liberação do veículo.
    # Tempo: normal (média 7 min, DP 2 min).
    #
    # assign_attributes(priority=lambda: 1):
    #   Após a liberação, a prioridade da entidade é atualizada para 1.
    #   Isso faz com que, ao chegar na fila do porteiro para vistoria,
    #   o caminhão aguarde atrás de qualquer nova chegada (prio=0),
    #   reproduzindo a regra do problema original: "o porteiro prioriza
    #   o atendimento de chegadas sobre a vistoria de saída".
    # ------------------------------------------------------------------
    liberacao = ProcessBlock(
        "Liberacao", model.env,
        resource=funcionario,
        delay_time=lambda: distribuicao('liberacao'),
        resource_units=1,
        event_logger=event_logger,
    )
    liberacao.set_resource_name('Funcionario')
    # Rebaixa prioridade para 1 antes de ir à vistoria
    liberacao.assign_attributes(priority=lambda: 1)

    # ------------------------------------------------------------------
    # BLOCO 6 — VISTORIA (PROCESS)
    # ------------------------------------------------------------------
    # O porteiro (mesmo recurso da recepção) faz a vistoria de saída.
    # Por causa da prioridade 1 atribuída na liberação, este caminhão
    # espera na fila atrás de qualquer chegada nova (prio=0).
    # Tempo: exponencial com média 4 min.
    # ------------------------------------------------------------------
    vistoria = ProcessBlock(
        "Vistoria", model.env,
        resource=porteiro,
        delay_time=lambda: distribuicao('vistoria'),
        resource_units=1,
        event_logger=event_logger,
    )
    vistoria.set_resource_name('Porteiro')

    # ------------------------------------------------------------------
    # BLOCO 7 — SAÍDA (DISPOSE)
    # ------------------------------------------------------------------
    # DisposeBlock encerra o ciclo da entidade no sistema.
    # O DESK usa este bloco para contabilizar saídas e calcular
    # métricas como tempo no sistema (TS) e WIP.
    # ------------------------------------------------------------------
    saida = DisposeBlock("Saida", model.env, event_logger=event_logger)

    # ------------------------------------------------------------------
    # REGISTRO DOS BLOCOS NO MODELO
    # ------------------------------------------------------------------
    # Todos os blocos precisam ser registrados para que o DESK os
    # monitore, colete métricas e os inclua nos relatórios.
    # ------------------------------------------------------------------
    for bloco in [
        chegada, recepcao, decide_tipo,
        descarga_a, decide_doca_B, descarga_b1, descarga_b2,
        liberacao, vistoria, saida,
    ]:
        model.add_block(bloco)

    # ------------------------------------------------------------------
    # CONEXÃO DO FLUXO (ACD — Activity Cycle Diagram)
    # ------------------------------------------------------------------
    # connect_to() define o próximo bloco no fluxo padrão.
    # add_route() define rotas condicionais nos blocos DECIDE.
    # ------------------------------------------------------------------

    # Fluxo principal: chegada → recepção → decisão de tipo
    chegada.connect_to(recepcao)
    recepcao.connect_to(decide_tipo)

    # Roteamento por tipo de carga:
    #   30% dos caminhões têm carga A → vão para Doca A
    #   70% restantes têm carga B → vão para decisão de doca B
    # As rotas são avaliadas em ordem; a primeira verdadeira vence.
    decide_tipo.add_route(
        "Carga_A", descarga_a,
        condition=lambda entity: random.random() <= 0.30,
    )
    decide_tipo.add_route(
        "Carga_B", decide_doca_B,
        condition=lambda entity: True,   # todos os demais (70%)
    )

    # Roteamento para doca B com menor fila:
    # .queue retorna a lista de requisições aguardando no recurso.
    # len(.queue) é o tamanho da fila naquele instante.
    decide_doca_B.add_route(
        "Doca_B1", descarga_b1,
        condition=lambda entity: len(doca_B1.queue) <= len(doca_B2.queue),
    )
    decide_doca_B.add_route(
        "Doca_B2", descarga_b2,
        condition=lambda entity: len(doca_B1.queue) > len(doca_B2.queue),
    )

    # Convergência: ambas as docas (A, B1, B2) levam à liberação,
    # que leva à vistoria, que leva à saída.
    descarga_a.connect_to(liberacao)
    descarga_b1.connect_to(liberacao)
    descarga_b2.connect_to(liberacao)
    liberacao.connect_to(vistoria)
    vistoria.connect_to(saida)

    return model


# =====================================================================
# WRAPPER PARA REPLICAÇÕES
# =====================================================================
# O ReplicationFramework chama esta função N vezes, cada vez com uma
# semente diferente, garantindo independência estatística entre as
# replicações. Retorna o modelo após a simulação para coleta de métricas.
def simulation_wrapper(seed=None, until=None, warm_up_period=None):
    event_logger = EventLogger()
    # Cria um modelo novo (estado limpo) a cada replicação
    model = build_model(until, event_logger, verbose=False)
    model.run_simulation(
        validate_resources=False,
        until=until,
        seed=seed,
        warm_up_period=warm_up_period,
    )
    return model


# =====================================================================
# REPLICAÇÕES
# =====================================================================
# Executa 5 replicações independentes com diferentes sementes.
# Ao final, calcula médias e intervalos de confiança (IC 95%) para
# todas as métricas coletadas (TS, TF, utilização dos recursos etc.).
def run_replications():
    DIAS = 1440   # 1 dia = 1440 minutos

    framework = ReplicationFramework(
        simulation_function=simulation_wrapper,
        n_replications=5,         # número de replicações
    )
    framework.run_replications(
        base_seed=1,              # semente base (cada rep. usa base_seed + i)
        until=365 * DIAS,         # duração: 1 ano (525.600 min)
        warm_up_period=30 * DIAS, # aquecimento: 30 dias (43.200 min)
    )

    # Exporta resultados para DataFrame e imprime estatísticas descritivas
    df = framework.get_results_dataframe()
    print(df.describe())


# =====================================================================
# ANÁLISE FATORIAL
# =====================================================================
# Executa um experimento fatorial variando dois fatores:
#   - Capacidade da Doca A (1 ou 2 docas)
#   - Número de porteiros (1 ou 2)
# Permite identificar qual fator mais impacta o desempenho do sistema.
def factorial_analysis():
    DIAS = 1440

    def wrapper_fatorial(seed=None, until=None, warm_up_period=0, **kwargs):
        event_logger = EventLogger()
        model = build_model(until, event_logger, verbose=False)
        model.run_simulation(
            validate_resources=False,
            until=until,
            seed=seed,
            warm_up_period=warm_up_period,
        )
        return model

    factorial = FactorialExperiment(
        simulation_function=wrapper_fatorial,
        base_seed=1,
    )

    # Fator 1: capacidade da Doca A (1 ou 2 servidores)
    factorial.add_factor(
        factor_name='cap_doca_A',
        parameter_path='Resource.Doca_A.capacity',
        levels=[1, 2],
        description='Capacidade da Doca A',
    )

    # Fator 2: número de porteiros (1 ou 2 servidores)
    factorial.add_factor(
        factor_name='cap_porteiro',
        parameter_path='Resource.Porteiro.capacity',
        levels=[1, 2],
        description='Número de porteiros',
    )

    # Executa todas as combinações (2x2 = 4 cenários) × 5 replicações
    factorial.run_factorial_experiment(
        n_replications=5,
        simulation_time=365 * DIAS,
        warm_up_period=30 * DIAS,
        verbose=False,
    )

    # Imprime resumo e gera gráficos de efeitos principais e interação
    factorial.print_summary()
    factorial.plot_main_effects('system_time_avg')
    factorial.plot_interaction_effects('system_time_avg', 'cap_doca_A', 'cap_porteiro')
    return factorial


# =====================================================================
# REPLICAÇÃO ÚNICA (SINGLE)
# =====================================================================
# Executa uma única replicação completa com verbose=True,
# imprime todos os relatórios e gera os mesmos gráficos do exemplo
# hospital.py fornecido pelo DESK.
def main():
    DIAS = 1440
    event_logger = EventLogger()

    # SimulationConfig centraliza os parâmetros da simulação
    # e valida inconsistências (ex: aquecimento > duração)
    config = SimulationConfig(
        duration=365 * DIAS,        # 1 ano de simulação
        warm_up_period=30 * DIAS,   # 30 dias de aquecimento (descartados)
        seed=1,                     # semente para reprodutibilidade
        check_stability=True,       # verifica se ρ < 1 para todos recursos
    )
    config.validate()

    # Constrói o modelo (cria recursos, blocos e conexões)
    model = build_model(config.duration, event_logger, verbose=False)

    # ── Verificação de estabilidade ANTES de rodar ──────────────────
    # StabilityAnalyzer verifica se a taxa de utilização ρ < 1
    # para cada recurso. Se ρ >= 1, o sistema nunca esvazia (instável).
    print("\nVerificando estabilidade do sistema...")
    stability_analyzer = StabilityAnalyzer(model)
    stability = stability_analyzer.check_system_stability()
    model.stability_result = stability   # guarda resultado no modelo

    # ── Execução da simulação ───────────────────────────────────────
    print("\nRodando simulação...")
    model.run_simulation(
        validate_resources=True,         # valida capacidade dos recursos
        until=config.duration,
        seed=config.seed,
        warm_up_period=config.warm_up_period,
    )

    # ── Fase de análise ─────────────────────────────────────────────

    # --- 1. Relatórios textuais ---
    reporter = SimulationReporter(model)
    reporter.print_results()             # resumo geral (TS, throughput, WIP)
    reporter._print_activity_metrics()  # métricas por atividade (fila, serviço, total)
    reporter._print_resource_metrics()  # utilização de cada recurso
    reporter._print_entity_counts()     # chegadas, saídas, WIP final
    reporter._print_block_statistics()  # estatísticas detalhadas por bloco

    # --- 2. Análise de warm-up (período de aquecimento) ---
    # WarmUpAnalyzer detecta automaticamente até quando o sistema
    # ainda está em transiente (não atingiu regime permanente).
    # Útil para calibrar o tempo de aquecimento em futuras rodadas.
    print("\nAnalisando período de aquecimento...")
    warmup_analyzer = WarmUpAnalyzer(model)
    warmup_analyzer.analyze_warm_up_period()

    # --- 3. Gráficos ---
    plotter = SimulationPlotter(model)

    # Utilização de cada recurso ao longo do tempo
    # show_warm_up=True: marca a região de aquecimento no gráfico
    # moving_average_window=50: suaviza a curva com média móvel de 50 pontos
    print("\nGerando gráficos de utilização por recurso...")
    plotter.plot_resource_use_over_time(
        show_warm_up=True, resource='Porteiro',    moving_average_window=50)
    plotter.plot_resource_use_over_time(
        show_warm_up=True, resource='Funcionario', moving_average_window=50)
    plotter.plot_resource_use_over_time(
        show_warm_up=True, resource='Doca_A',      moving_average_window=50)
    plotter.plot_resource_use_over_time(
        show_warm_up=True, resource='Doca_B1',     moving_average_window=50)
    plotter.plot_resource_use_over_time(
        show_warm_up=True, resource='Doca_B2',     moving_average_window=50)

    # WIP (Work In Process) ao longo do tempo
    # Mostra quantas entidades estão no sistema em cada instante
    plotter.plot_wip_over_time()

    # Distribuição do tempo total no sistema (histograma por entidade)
    plotter.plot_system_time_distribution()

    # Métricas por atividade (barras: fila, serviço, total por bloco)
    print("\nGerando gráficos de métricas por atividade...")
    reporter._print_activity_metrics()
    plotter.plot_activity_metrics()

    # Resumo de utilização de todos os recursos (barras side-by-side)
    print("\nGerando resumo de utilização dos recursos...")
    plotter.plot_resources_utilization()
    reporter._print_resource_metrics()

    # --- 4. Exportação do log de eventos ---
    # Salva cada evento (chegada, início/fim de serviço, saída) em CSV.
    # O arquivo pode ser usado para análise externa ou animação no R
    # via processanimateR (integração BupaR do DESK).
    print("\nExportando log de eventos...")
    df = event_logger.export_to_csv("results/docas_event_log.csv")
    print(f"\nPrimeiros 10 eventos:")
    print(df.head(10))

    # --- 5. Acesso direto às métricas brutas ---
    # MetricsCollector permite acessar os dados numéricos diretamente
    # sem depender da saída textual dos reporters.
    metrics = MetricsCollector(model)
    entity_metrics   = metrics.get_entity_metrics_summary()
    resource_metrics = metrics.get_resource_metrics_summary()

    print(f"\nTempo médio no sistema: {entity_metrics['tempo_medio_sistema']:.2f} min")
    print(f"Semente usada: {config.seed}")

    return model, event_logger



# =====================================================================
# SIMULATION KIT — ENTRYPOINTS DO DESK CLI
# =====================================================================
# O comando desk-sim chama automaticamente estas funções conforme
# o modo escolhido:
#   --mode single       → run_single_replication()
#   --mode replications → run_replications_cli()
#   --mode factorial    → run_factorial_cli()
#   --mode visualization→ run_visualization_cli()
# =====================================================================
def run_single_replication():
    return main()

def run_replications_cli():
    run_replications()

def run_factorial_cli():
    return factorial_analysis()

def run_visualization_cli(simulation_time=500):
    return run_visualization(build_model, simulation_time=simulation_time)