# Código completo consolidado — Sondas de Petróleo (DESK + DCA)

# =====================================================================
# SONDAS DE PETRÓLEO — VISUAL DCA
# =====================================================================

import os
import random

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from desk.core.simulation_model import SimulationModel
from desk.core.entity import EventLogger
from desk.blocks.create_block import CreateBlock
from desk.blocks.process_block import ProcessBlock
from desk.blocks.decide_block import DecideBlock
from desk.analytics.plotting import SimulationPlotter
from desk.config.simulation_config import SimulationConfig
from desk.validation.stability import StabilityAnalyzer
from desk.stats.replication import ReplicationFramework
from desk.visualization.interface import run_visualization


# ####################################################################################
# Projeto: Sondas de Petroleo
# Autor: João Flávio F. ALmeida <joao.flavio@dep.ufmg.br>
# Implementação: Alunos da disciplina EPD733 - Simulação de sistema logísticos - PPGEP-UFMG
# Uma empresa opera 7 sondas de perfuração de petróleo num campo petrolífero no mar.
# As sondas trabalham em operação contínua, interrompendo seu funcionamento apenas para 
# manutenção corretiva. O tempo entre falhas é descrito por uma distribuição normal 
# com média 168 e desvio padrão de 24 horas. A manutenção é feita por uma única equipe 
# e sua duração é exponencialmente distribuída com média de 24 horas. 
# No início da operação a equipe se encontra em uma base em terra. 
# A cada quebra de sonda, a equipe se desloca para o local da sonda, ali permanecendo 
# até o término da manutenção. Ao final da manutenção, se não houver outras sondas 
# quebradas, a equipe retorna à base. Caso haja outra sonda quebrada, a equipe se 
# desloca diretamente para a sonda que estiver há mais tempo aguardando manutenção. 
# Os tempos de deslocamento entre as sondas são descritos por uma distribuição normal 
# com média de 0,9h e desvio padrão de 0,2h. Os tempos de deslocamento entre as sondas 
# e a base em terra também seguem uma distribuição normal com média de 1,2h e desvio 
# padrão de 0,2h. Posto isto, fazer o DCA representativo do sistema.
# ####################################################################################

# desk-sim -m examples/8.py --mode visualization
# desk-sim -m examples/8.py --mode single
# desk-sim -m examples/8.py --mode replications
# desk-sim -m examples/8.py --mode factorial

# =====================================================================
# CONSTANTES
# =====================================================================

HOURS = 60
DAYS = 1440
N_SONDAS = 7

PASTA = os.path.dirname(os.path.abspath(__file__))

# =====================================================================
# DISTRIBUIÇÕES
# =====================================================================

def distribution(tipo):

    return {

        'operacao': max(
            0,
            random.gauss(168 * HOURS, 24 * HOURS)
        ),

        'manutencao': random.expovariate(
            1 / (24 * HOURS)
        ),

        'desloc_terra_mar': max(
            0,
            random.gauss(1.2 * HOURS, 0.2 * HOURS)
        ),

        'desloc_sonda_sonda': max(
            0,
            random.gauss(0.9 * HOURS, 0.2 * HOURS)
        ),

        'desloc_mar_terra': max(
            0,
            random.gauss(1.2 * HOURS, 0.2 * HOURS)
        ),

    }.get(tipo, 0)

# =====================================================================
# UTILIZAÇÃO
# =====================================================================

def calc_utilizacao(df, recurso, duracao_total, warm_up=0):

    df_r = df[
        df["resource"] == recurso
    ].copy()

    starts = df_r[
        df_r["lifecycle"] == "start"
    ].sort_values("timestamp")["timestamp"].values

    completes = df_r[
        df_r["lifecycle"] == "complete"
    ].sort_values("timestamp")["timestamp"].values

    n = min(len(starts), len(completes))

    if n == 0:
        return 0

    tempo_ocupado = 0

    periodo = duracao_total - warm_up

    for s, c in zip(starts[:n], completes[:n]):

        s_clip = max(s, warm_up)

        c_clip = min(c, duracao_total)

        if c_clip > s_clip:
            tempo_ocupado += c_clip - s_clip

    return tempo_ocupado / periodo

# =====================================================================
# BUILD MODEL
# =====================================================================

def build_model(
    final_simulation_time=None,
    event_logger=None,
    verbose=True,
    entity_filter=None,
    resource_filter=None,
    event_type_filter=None,
    time_range=None
):

    model = SimulationModel(
        verbose=verbose,
        entity_filter=entity_filter,
        resource_filter=resource_filter,
        event_type_filter=event_type_filter,
        time_range=time_range,
    )

    estado_equipe = {
        'local': 'terra'
    }

    equipe = model.add_resource(
        "Equipe_Manutencao",
        1,
        "priority"
    )

    # ==============================================================  
    # OPERAÇÃO  
    # ==============================================================  

    operacao = ProcessBlock(
        "Operacao",
        model.env,
        resource=None,
        delay_time=lambda: distribution('operacao'),
        resource_units=0,
        event_logger=event_logger,
    )

    # ==============================================================  
    # DECIDE ORIGEM EQUIPE  
    # ==============================================================  

    decide_local = DecideBlock(
        "Decide_Local_Equipe",
        model.env,
        decision_type="condition",
        event_logger=event_logger,
    )

    def equipe_terra(entity):
        return estado_equipe['local'] == 'terra'

    def equipe_mar(entity):
        return estado_equipe['local'] == 'mar'

    # ==============================================================  
    # DESLOCAMENTO TERRA → MAR  
    # ==============================================================  

    desloc_tm = ProcessBlock(
        "Desloc_Terra_Mar",
        model.env,
        resource=None,
        delay_time=lambda: distribution('desloc_terra_mar'),
        resource_units=0,
        event_logger=event_logger,
    )

    # ==============================================================  
    # DESLOCAMENTO SONDA → SONDA  
    # ==============================================================  

    desloc_ss = ProcessBlock(
        "Desloc_Sonda_Sonda",
        model.env,
        resource=None,
        delay_time=lambda: distribution('desloc_sonda_sonda'),
        resource_units=0,
        event_logger=event_logger,
    )

    # ==============================================================  
    # FILA MANUTENÇÃO  
    # ==============================================================  

    manutencao = ProcessBlock(
        "Manutencao",
        model.env,
        resource=equipe,
        delay_time=lambda: distribution('manutencao'),
        resource_units=1,
        event_logger=event_logger,
    )

    manutencao.set_resource_name(
        "Equipe_Manutencao"
    )

    # ==============================================================  
    # DECIDE PÓS MANUTENÇÃO  
    # ==============================================================  

    decide_saida = DecideBlock(
        "Decide_Saida",
        model.env,
        decision_type="condition",
        event_logger=event_logger,
    )

    def fila_vazia(entity):

        try:
            vazia = len(equipe.queue) == 0
        except:
            vazia = True

        if vazia:
            estado_equipe['local'] = 'terra'
        else:
            estado_equipe['local'] = 'mar'

        return vazia

    def fila_nao_vazia(entity):

        estado_equipe['local'] = 'mar'

        return True

    # ==============================================================  
    # CONEXÕES  
    # ==============================================================  

    for block in [
        operacao,
        decide_local,
        desloc_tm,
        desloc_ss,
        manutencao,
        decide_saida
    ]:

        model.add_block(block)

    operacao.connect_to(decide_local)

    decide_local.add_route(
        "Equipe_Terra",
        desloc_tm,
        condition=equipe_terra
    )

    decide_local.add_route(
        "Equipe_Mar",
        desloc_ss,
        condition=equipe_mar
    )

    desloc_tm.connect_to(manutencao)
    desloc_ss.connect_to(manutencao)
    manutencao.connect_to(decide_saida)

    decide_saida.add_route(
        "Retorna_Base",
        operacao,
        condition=fila_vazia
    )

    decide_saida.add_route(
        "Continua_Offshore",
        operacao,
        condition=fila_nao_vazia
    )

    # ==============================================================  
    # CRIAÇÃO DAS SONDAS  
    # ==============================================================  

    init = CreateBlock(
        "Init_Sondas",
        model.env,
        inter_arrival_time=lambda: 0,
        entity_prefix="Sonda",
        max_arrivals=N_SONDAS,
        first_creation=0,
        priority_generator=lambda: 0,
        event_logger=event_logger,
    )

    model.add_block(init)
    init.connect_to(operacao)

    return model
# =====================================================================
# MAIN
# =====================================================================

def main():

    print("=" * 60)
    print("SONDAS DE PETRÓLEO — VISUAL DCA")
    print("=" * 60)

    event_logger = EventLogger()

    config = SimulationConfig(
        duration=365 * DAYS,
        warm_up_period=30 * DAYS,
        seed=42,
        check_stability=True,
    )

    config.validate()

    model = build_model(
        config.duration,
        event_logger,
        verbose=True
    )

    analyzer = StabilityAnalyzer(model)

    model.stability_result = analyzer.check_system_stability()

    model.run_simulation(
        validate_resources=True,
        until=config.duration,
        seed=config.seed,
        warm_up_period=config.warm_up_period,
    )

    # ==============================================================  
    # EVENT LOG  
    # ==============================================================  

    caminho_log = os.path.join(
        PASTA,
        "sondas_event_log.csv"
    )

    df = event_logger.export_to_csv(caminho_log)

    print(f"\nEvent log salvo:\n{caminho_log}")

    warm = config.warm_up_period

    # ==============================================================  
    # HELPERS MÉTRICAS  
    # ==============================================================  

    def get_timestamps(atividade, lifecycle):

        sub = df[
            (df["activity"] == atividade) &
            (df["lifecycle"] == lifecycle)
        ]

        return {
            sid:
            sub[
                sub["case_id"] == sid
            ]["timestamp"]
            .sort_values()
            .values
            for sid in sub["case_id"].unique()
        }

    def tempo_atividade(atividade):

        starts = get_timestamps(
            atividade,
            "start"
        )

        completes = get_timestamps(
            atividade,
            "complete"
        )

        tempos = []

        for sid, tc in completes.items():

            ts = starts.get(sid, [])

            for t_c in tc:

                if t_c < warm:
                    continue

                cands = ts[ts <= t_c]

                if len(cands) > 0:
                    tempos.append(t_c - cands[-1])

        return pd.Series(tempos)

    def tempo_entre(ativ_a, ativ_b):

        completes_a = get_timestamps(
            ativ_a,
            "complete"
        )

        starts_b = get_timestamps(
            ativ_b,
            "start"
        )

        tempos = []

        for sid, ts_b in starts_b.items():

            tc_a = completes_a.get(sid, [])

            for t_b in ts_b:

                if t_b < warm:
                    continue

                cands = tc_a[tc_a <= t_b]

                if len(cands) > 0:

                    diff = t_b - cands[-1]

                    if diff >= 0:
                        tempos.append(diff)

        return pd.Series(tempos)
        # ==============================================================  
    # MÉTRICAS  
    # ==============================================================  

    periodo = config.duration - warm

    df_manut = df[
        (df["activity"] == "Manutencao") &
        (df["lifecycle"] == "complete") &
        (df["timestamp"] >= warm)
    ]

    n_manut = len(df_manut)

    # Tempo em fila = Operacao.complete → Manutencao.start
    tempo_fila = tempo_entre("Operacao", "Manutencao")

    # Tempo de manutenção
    tempo_manut = tempo_atividade("Manutencao")

    # Tempo de operação (TO)
    tempo_oper = tempo_atividade("Operacao")

    # Tempos de deslocamento
    tempo_desloc_tm = tempo_atividade("Desloc_Terra_Mar")
    tempo_desloc_ss = tempo_atividade("Desloc_Sonda_Sonda")

    tempo_desloc_total = pd.concat([tempo_desloc_tm, tempo_desloc_ss])

    # Tempo total no sistema (TTS)
    tempo_sistema = tempo_oper + tempo_fila + tempo_manut

    # Throughput
    throughput = n_manut / periodo

    # Utilização da equipe
    util = calc_utilizacao(
        df,
        "Equipe_Manutencao",
        config.duration,
        warm_up=warm
    )



    # ==============================================================  
    # LEI DE LITTLE  
    # ==============================================================  

    L_fila = (
        throughput * tempo_fila.mean()
        if len(tempo_fila) > 0
        else 0
    )

    L_manut = (
        throughput * tempo_manut.mean()
        if len(tempo_manut) > 0
        else 0
    )

    L_desloc = (
        throughput * tempo_desloc_total.mean()
        if len(tempo_desloc_total) > 0
        else 0
    )

    L_operando = max(
        0,
        N_SONDAS -
        L_fila -
        L_manut -
        L_desloc
    )

    # ==============================================================  
    # RESULTADOS  
    # ==============================================================  

    print("\n" + "=" * 70)
    print("RESULTADOS — SONDAS DE PETRÓLEO")
    print("=" * 70)

    print(f"\nWarm-up: {warm/HOURS:.1f} h")
    print(f"Período análise: {periodo/HOURS:.1f} h")
    print(f"\nTotal manutenções: {n_manut}")
    print(f"\nThroughput: {throughput * HOURS:.4f} manut/h")
    print(f"Utilização equipe: {util:.2%}")

    if len(tempo_fila) > 0:
        print("\nTEMPO EM FILA")
        print(f"Média: {tempo_fila.mean()/HOURS:.2f} h")
        print(f"Mediana: {tempo_fila.median()/HOURS:.2f} h")
        print(f"Desvio: {tempo_fila.std()/HOURS:.2f} h")

    if len(tempo_manut) > 0:
        print("\nTEMPO MANUTENÇÃO")
        print(f"Média: {tempo_manut.mean()/HOURS:.2f} h")
        print(f"Mediana: {tempo_manut.median()/HOURS:.2f} h")
        print(f"Desvio: {tempo_manut.std()/HOURS:.2f} h")
    if len(tempo_oper) > 0:
        print("\nTEMPO DE OPERAÇÃO (TO)")
        print(f"Média: {tempo_oper.mean()/HOURS:.2f} h")
        print(f"Mediana: {tempo_oper.median()/HOURS:.2f} h")
        print(f"Desvio: {tempo_oper.std()/HOURS:.2f} h")

    if len(tempo_sistema) > 0:
        print("\nTEMPO NO SISTEMA (TTS)")
        print(f"Média: {tempo_sistema.mean()/HOURS:.2f} h")
        print(f"Mediana: {tempo_sistema.median()/HOURS:.2f} h")
        print(f"Desvio: {tempo_sistema.std()/HOURS:.2f} h")

    print("\nLEI DE LITTLE")
    print(f"Operando: {L_operando:.2f}")
    print(f"Fila: {L_fila:.2f}")
    print(f"Deslocamento: {L_desloc:.2f}")
    print(f"Manutenção: {L_manut:.2f}")
    print("=" * 70)
    # ==============================================================  
    # GRÁFICOS  
    # ==============================================================  

    plotter = SimulationPlotter(model)

    print("\nGerando gráficos...")

    plotter.plot_resource_use_over_time(
        show_warm_up=True,
        resource="Equipe_Manutencao",
        moving_average_window=30
    )

    plotter.plot_system_time_distribution()
    plotter.plot_resources_utilization()

    # --------------------------------------------------------------
    # TEMPO EM FILA
    # --------------------------------------------------------------
    if len(tempo_fila) > 0:

        plt.figure(figsize=(8,5))
        plt.hist(tempo_fila / HOURS, bins=30)

        media_fila = (tempo_fila / HOURS).mean()
        mediana_fila = (tempo_fila / HOURS).median()

        plt.axvline(media_fila,   color='red',    linestyle='--', linewidth=1.5)
        plt.axvline(mediana_fila, color='orange', linestyle=':',  linewidth=1.5)

        plt.xlabel("Tempo fila (h)")
        plt.ylabel("Frequência")
        plt.title("Distribuição Tempo em Fila")

    # --------------------------------------------------------------
    # TEMPO TOTAL NO SISTEMA (TTS)
    # --------------------------------------------------------------
    if len(tempo_sistema) > 0:

        plt.figure(figsize=(8,5))
        plt.hist(
            tempo_sistema / HOURS,
            bins=30,
            color="skyblue",
            edgecolor="black"
        )

        media_tts = (tempo_sistema / HOURS).mean()
        mediana_tts = (tempo_sistema / HOURS).median()

        plt.axvline(media_tts,   color='red',    linestyle='--', linewidth=1.5, label=f'Média: {media_tts:.1f} h')
        plt.axvline(mediana_tts, color='orange', linestyle=':',  linewidth=1.5, label=f'Mediana: {mediana_tts:.1f} h')

        plt.xlabel("Tempo total no sistema (h)")
        plt.ylabel("Frequência")
        plt.title("Distribuição do Tempo Total no Sistema (TTS)")
        plt.legend()

    # --------------------------------------------------------------
    # TEMPO DE MANUTENÇÃO
    # --------------------------------------------------------------
    if len(tempo_manut) > 0:

        plt.figure(figsize=(8,5))
        plt.hist(tempo_manut / HOURS, bins=30)

        media_manut = (tempo_manut / HOURS).mean()
        mediana_manut = (tempo_manut / HOURS).median()

        plt.axvline(media_manut,   color='red',    linestyle='--', linewidth=1.5)
        plt.axvline(mediana_manut, color='orange', linestyle=':',  linewidth=1.5)

        plt.xlabel("Tempo manutenção (h)")
        plt.ylabel("Frequência")
        plt.title("Distribuição Tempo Manutenção")
    # --------------------------------------------------------------
    # TEMPO DE OPERAÇÃO (TO)
    # --------------------------------------------------------------
    if len(tempo_oper) > 0:

        plt.figure(figsize=(8,5))
        plt.hist(tempo_oper / HOURS, bins=30, color="lightgreen", edgecolor="black")

        media_oper = (tempo_oper / HOURS).mean()
        mediana_oper = (tempo_oper / HOURS).median()

        plt.axvline(media_oper,   color='red',    linestyle='--', linewidth=1.5, label=f'Média: {media_oper:.1f} h')
        plt.axvline(mediana_oper, color='orange', linestyle=':',  linewidth=1.5, label=f'Mediana: {mediana_oper:.1f} h')

        plt.xlabel("Tempo de operação (h)")
        plt.ylabel("Frequência")
        plt.title("Distribuição do Tempo de Operação (TO)")
        plt.legend()

    # --------------------------------------------------------------
    # DISTRIBUIÇÃO MÉDIA DAS SONDAS
    # --------------------------------------------------------------
    plt.figure(figsize=(8,5))

    labels = ["Operando", "Fila", "Deslocamento", "Manutenção"]
    valores = [L_operando, L_fila, L_desloc, L_manut]

    plt.bar(labels, valores)

    media_sondas = sum(valores) / len(valores)
    plt.axhline(media_sondas, color='red', linestyle='--', linewidth=1.5)

    plt.ylabel("Número médio de sondas")
    plt.title("Distribuição Média das Sondas")

        # --------------------------------------------------------------
    # MOSTRAR TODOS OS GRÁFICOS
    # --------------------------------------------------------------
    plt.show()

    return model


# =====================================================================
# WRAPPER
# =====================================================================

def simulation_wrapper(
    seed=None,
    until=None,
    warm_up_period=None
):

    event_logger = EventLogger()

    model = build_model(
        until,
        event_logger,
        verbose=False
    )

    model.run_simulation(
        validate_resources=False,
        until=until or 365 * DAYS,
        seed=seed,
        warm_up_period=warm_up_period or 30 * DAYS,
    )

    return model


# =====================================================================
# REPLICAÇÕES
# =====================================================================

def run_replications():

    rf = ReplicationFramework(
        simulation_function=simulation_wrapper,
        n_replications=30,
    )

    rf.run_replications(
        base_seed=12345,
        until=365 * DAYS,
        warm_up_period=30 * DAYS,
    )

    print(
        rf.get_results_dataframe().describe()
    )


# =====================================================================
# VISUALIZAÇÃO
# =====================================================================

def run_single_replication():
    return main()


def run_replications_cli():
    run_replications()


def run_visualization_cli(
    simulation_time=525600
):

    return run_visualization(
        build_model,
        simulation_time=simulation_time
    )


# =====================================================================
# MAIN
# =====================================================================

if __name__ == "__main__":
    main()
