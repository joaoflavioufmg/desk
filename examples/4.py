# =====================================================================
# FILE: porto.py
# Modelo DESK corrigido para fidelidade ao SimPy
# =====================================================================

import os
import random
import numpy as np
import math
import matplotlib.pyplot as plt
from scipy import stats as scipy_stats

from desk.core.simulation_model import SimulationModel
from desk.core.entity import EventLogger
from desk.blocks.create_block import CreateBlock
from desk.blocks.process_block import ProcessBlock
from desk.blocks.decide_block import DecideBlock
from desk.blocks.dispose_block import DisposeBlock
from desk.analytics.plotting import SimulationPlotter
from desk.config.simulation_config import SimulationConfig
from desk.stats.replication import ReplicationFramework
from desk.stats.factorial import FactorialExperiment
from desk.visualization.interface import run_visualization

# desk-sim -m examples/4.py --mode visualization
# desk-sim -m examples/4.py --mode single
# desk-sim -m examples/4.py --mode replications
# desk-sim -m examples/4.py --mode factorial

# =====================================================================
# UNIDADES
# =====================================================================

HOURS = 1.0
DAYS = 24.0 * HOURS

# =====================================================================
# TAXAS
# =====================================================================

TAXA_NAVIOS = 1 / (4.39 * DAYS)
TAXA_TRENS = 1 / (7.0 * HOURS)
TAXA_TOTAL = TAXA_NAVIOS + TAXA_TRENS

PASTA = os.path.dirname(os.path.abspath(__file__))

# =====================================================================
# VARIÁVEIS GLOBAIS
# =====================================================================

ESTOQUE_MINERIO = 14700
EXPORTACAO_TOTAL = 0.0

# =====================================================================
# BUILD MODEL
# =====================================================================

def build_model(final_simulation_time=None,
                event_logger=None,
                verbose=True,
                entity_filter=None,
                resource_filter=None,
                event_type_filter=None,
                time_range=None):

    global ESTOQUE_MINERIO
    global EXPORTACAO_TOTAL

    ESTOQUE_MINERIO = 14700
    EXPORTACAO_TOTAL = 0.0

    model = SimulationModel(
        verbose=verbose,
        entity_filter=entity_filter,
        resource_filter=resource_filter,
        event_type_filter=event_type_filter,
        time_range=time_range
    )

    # ================================================================
    # CHEGADAS
    # ================================================================

    def inter_arrival_combinado():
        return random.expovariate(TAXA_TOTAL)

    def tipo_entidade():
        prob_navio = TAXA_NAVIOS / TAXA_TOTAL
        return 1 if random.random() < prob_navio else 2

    # ================================================================
    # NAVIOS
    # ================================================================

    def ship_loading_time():

        global ESTOQUE_MINERIO
        global EXPORTACAO_TOTAL

        sorteio = random.random()

        if sorteio <= 0.75:
            cap_t = 100000

        elif sorteio <= 0.90:
            cap_t = 200000

        else:
            cap_t = 150000

        # taxa nominal
        tempo_base = cap_t / 1200.0

        # ============================================================
        # ESTOQUE SUFICIENTE
        # ============================================================

        if ESTOQUE_MINERIO >= cap_t:

            ESTOQUE_MINERIO -= cap_t
            EXPORTACAO_TOTAL += cap_t

            return tempo_base

        # ============================================================
        # FALTA ESTOQUE
        # ============================================================

        else:

            falta = cap_t - ESTOQUE_MINERIO

            exportado = ESTOQUE_MINERIO

            EXPORTACAO_TOTAL += exportado

            ESTOQUE_MINERIO = 0

            # atraso equivalente SimPy
            tempo_bloqueio = (falta / 8000.0) * 132.39

            return tempo_base + tempo_bloqueio

    # ================================================================
    # TRENS
    # ================================================================

    def train_unloading_time():

        global ESTOQUE_MINERIO

        capacidade_trem = 8000

        # 80 vagões
        tempo_base = sum(
            max(0.0, random.gauss(2.5 / 60.0, 0.3 / 60.0))
            for _ in range(80)
        )

        # ============================================================
        # ESTOQUE ABAIXO LIMITE
        # ============================================================

        if ESTOQUE_MINERIO + capacidade_trem <= 500000:

            ESTOQUE_MINERIO += capacidade_trem

            return tempo_base

        # ============================================================
        # PÁTIO LOTADO
        # ============================================================

        else:

            excesso = (
                ESTOQUE_MINERIO + capacidade_trem
            ) - 500000

            ESTOQUE_MINERIO = 500000

            # aproximação do comportamento do Container.put()
            # do SimPy sem inflar artificialmente o recurso

            tempo_congelamento = (
                (excesso / 8000.0)
                * 132.39
                * 0.25
            )

            return tempo_base + tempo_congelamento

    # =================================================================
    # RECURSOS
    # =================================================================

    pier = model.add_resource("pier", 1, "priority")
    tipper = model.add_resource("tipper", 1, "priority")

    # =================================================================
    # BLOCOS
    # =================================================================

    arrivals = CreateBlock(
        "Chegadas",
        model.env,
        inter_arrival_time=inter_arrival_combinado,
        entity_prefix="Entidade",
        max_arrivals=None,
        first_creation=0.0,
        priority_generator=tipo_entidade,
        event_logger=event_logger
    )

    tipo_check = DecideBlock(
        "Tipo_Entidade",
        model.env,
        decision_type="condition",
        event_logger=event_logger
    )

    loading = ProcessBlock(
        "Carrega_Navio",
        model.env,
        resource=pier,
        delay_time=ship_loading_time,
        resource_units=1,
        event_logger=event_logger
    )

    loading.set_resource_name("pier")

    ship_departs = DisposeBlock(
        "Saida_Mar",
        model.env,
        event_logger=event_logger
    )

    unloading = ProcessBlock(
        "Descarrega_Trem",
        model.env,
        resource=tipper,
        delay_time=train_unloading_time,
        resource_units=1,
        event_logger=event_logger
    )

    unloading.set_resource_name("tipper")

    train_departs = DisposeBlock(
        "Saida_Ferrovia",
        model.env,
        event_logger=event_logger
    )

    # =================================================================
    # REGISTRO
    # =================================================================

    for block in [
        arrivals,
        tipo_check,
        loading,
        ship_departs,
        unloading,
        train_departs
    ]:
        model.add_block(block)

    # =================================================================
    # CONEXÕES
    # =================================================================

    arrivals.connect_to(tipo_check)

    tipo_check.add_route(
        "Navio",
        loading,
        condition=lambda e: e.priority == 1
    )

    tipo_check.add_route(
        "Trem",
        unloading,
        condition=lambda e: e.priority == 2
    )

    loading.connect_to(ship_departs)
    unloading.connect_to(train_departs)

    return model

# =====================================================================
# UTILIZAÇÃO
# =====================================================================

def _calc_utilizacao(df, recurso, warm, duration):

    df_r = df[df["resource"] == recurso].copy()

    starts = df_r[
        df_r["lifecycle"] == "start"
    ].sort_values("timestamp")["timestamp"].values

    completes = df_r[
        df_r["lifecycle"] == "complete"
    ].sort_values("timestamp")["timestamp"].values

    n = min(len(starts), len(completes))

    if n == 0:
        return 0.0

    ocupado = 0.0

    for s, c in zip(starts[:n], completes[:n]):

        s_adj = max(s, warm)
        c_adj = min(c, duration)

        if c_adj > s_adj:
            ocupado += (c_adj - s_adj)

    return ocupado / (duration - warm)

# =====================================================================
# INTERVALO DE CONFIANÇA 95%
# =====================================================================

CONFIANCA = 0.95
PRECISAO  = 0.01   # 1%

def calc_ic(lista):
    """IC 95% via t-Student."""
    n = len(lista)
    if n <= 1:
        return 0.0
    se = scipy_stats.sem(lista)
    return se * scipy_stats.t.ppf((1 + CONFIANCA) / 2.0, n - 1)

def n_ideal(lista):
    """Número mínimo de replicações para precisão relativa de 1%."""
    n = len(lista)
    if n <= 1:
        return None
    media  = np.mean(lista)
    if media == 0:
        return None
    t_val  = scipy_stats.t.ppf((1 + CONFIANCA) / 2.0, n - 1)
    s      = np.std(lista, ddof=1)
    erro   = PRECISAO * abs(media)
    return math.ceil((t_val * s / erro) ** 2)



def main():

    global ESTOQUE_MINERIO
    global EXPORTACAO_TOTAL

    config = SimulationConfig(
        duration= 24.0 * 730 * HOURS,
        warm_up_period= 6000 * HOURS,
        seed=1,
        check_stability=False
    )

    config.validate()

    warm = config.warm_up_period
    periodo = config.duration - warm

    # ================================================================
    # VETORES
    # ================================================================

    reps_NS_nav = []
    reps_NF_nav = []
    reps_NA_nav = []
    reps_TS_nav = []
    reps_TF_nav = []
    reps_TA_nav = []
    reps_USO_P = []

    reps_NS_tre = []
    reps_NF_tre = []
    reps_NA_tre = []
    reps_TS_tre = []
    reps_TF_tre = []
    reps_TA_tre = []
    reps_USO_V = []

    reps_Estoque = []
    reps_Exportacao = []

    # ── Observações individuais (para calc_ic) ──────────────────────
    obs_NS_nav = []; obs_NF_nav = []; obs_NA_nav = []
    obs_TS_nav = []; obs_TF_nav = []; obs_TA_nav = []
    obs_USO_P  = []

    obs_NS_tre = []; obs_NF_tre = []; obs_NA_tre = []
    obs_TS_tre = []; obs_TF_tre = []; obs_TA_tre = []
    obs_USO_V  = []

    obs_Estoque    = []
    obs_Exportacao = []

    n_replications = 5

    # ================================================================
    # LOOP
    # ================================================================

    for r in range(n_replications):

        event_logger = EventLogger()

        model = build_model(
            config.duration,
            event_logger,
            verbose=False
        )

        model.run_simulation(
            validate_resources=True,
            until=config.duration,
            seed=config.seed + r,
            warm_up_period=config.warm_up_period
        )

        log_path = os.path.join(
            PASTA,
            f"porto_event_log_r{r}.csv"
        )

        df = event_logger.export_to_csv(log_path)

        # ============================================================
        # IDs
        # ============================================================

        navios_ids = set(
            df.loc[
                (df["activity"] == "Arrival")
                &
                (df["priority"] == 1.0),
                "case_id"
            ]
        )

        trens_ids = set(
            df.loc[
                (df["activity"] == "Arrival")
                &
                (df["priority"] == 2.0),
                "case_id"
            ]
        )

        # ============================================================
        # FILTRAGEM WARM-UP
        # ============================================================

        df_arr_after = df[
            (df["activity"] == "Arrival")
            &
            (df["timestamp"] >= warm)
        ]

        navios_pos_wu = set(
            df_arr_after[
                df_arr_after["case_id"].isin(navios_ids)
            ]["case_id"]
        )

        trens_pos_wu = set(
            df_arr_after[
                df_arr_after["case_id"].isin(trens_ids)
            ]["case_id"]
        )

        # ============================================================
        # THROUGHPUT
        # ============================================================

        df_dis_nav = df[
            (df["activity"] == "Discharge")
            &
            (df["case_id"].isin(navios_pos_wu))
        ]

        df_dis_tre = df[
            (df["activity"] == "Discharge")
            &
            (df["case_id"].isin(trens_pos_wu))
        ]

        lambda_nav = len(navios_pos_wu) / periodo
        lambda_tre = len(trens_pos_wu) / periodo

        # ============================================================
        # UTILIZAÇÃO
        # ============================================================

        util_pier = _calc_utilizacao(
            df,
            "pier",
            warm,
            config.duration
        )

        util_tipper = _calc_utilizacao(
            df,
            "tipper",
            warm,
            config.duration
        )

        # ============================================================
        # NAVIOS
        # ============================================================

        df_arr_nav = df[
            (df["activity"] == "Arrival")
            &
            (df["case_id"].isin(navios_pos_wu))
        ][["case_id", "timestamp"]].rename(
            columns={"timestamp": "t_arr"}
        )

        df_dis_nav2 = df_dis_nav[
            ["case_id", "timestamp"]
        ].rename(
            columns={"timestamp": "t_dis"}
        )

        st_nav = df_dis_nav2.merge(
            df_arr_nav,
            on="case_id"
        )

        st_nav["TS"] = st_nav["t_dis"] - st_nav["t_arr"]

        ts_nav = st_nav.set_index("case_id")["TS"]

        df_nav = df[df["case_id"].isin(navios_pos_wu)]

        pier_s = df_nav[
            (df_nav["lifecycle"] == "start")
            &
            (df_nav["resource"] == "pier")
        ][["case_id", "timestamp"]].rename(
            columns={"timestamp": "ts"}
        )

        pier_c = df_nav[
            (df_nav["lifecycle"] == "complete")
            &
            (df_nav["resource"] == "pier")
        ][["case_id", "timestamp"]].rename(
            columns={"timestamp": "tc"}
        )

        svc_nav = pier_s.merge(
            pier_c,
            on="case_id"
        )

        svc_nav["TA"] = svc_nav["tc"] - svc_nav["ts"]

        ta_nav = svc_nav.set_index("case_id")["TA"]

        tf_nav = (
            ts_nav - ta_nav.reindex(ts_nav.index)
        ).dropna()

        reps_TS_nav.append(ts_nav.mean())
        reps_TA_nav.append(ta_nav.mean())
        reps_TF_nav.append(tf_nav.mean())

        reps_NS_nav.append(lambda_nav * ts_nav.mean())
        reps_NA_nav.append(lambda_nav * ta_nav.mean())
        reps_NF_nav.append(lambda_nav * tf_nav.mean())

        reps_USO_P.append(util_pier)

        obs_TS_nav.extend(ts_nav.tolist())
        obs_TA_nav.extend(ta_nav.tolist())
        obs_TF_nav.extend(tf_nav.tolist())
        obs_NS_nav.extend((lambda_nav * ts_nav).tolist())
        obs_NA_nav.extend((lambda_nav * ta_nav).tolist())
        obs_NF_nav.extend((lambda_nav * tf_nav).tolist())
        obs_USO_P .extend([util_pier] * max(len(ts_nav), 1))

        # ============================================================
        # TRENS
        # ============================================================

        df_arr_tre = df[
            (df["activity"] == "Arrival")
            &
            (df["case_id"].isin(trens_pos_wu))
        ][["case_id", "timestamp"]].rename(
            columns={"timestamp": "t_arr"}
        )

        df_dis_tre2 = df_dis_tre[
            ["case_id", "timestamp"]
        ].rename(
            columns={"timestamp": "t_dis"}
        )

        # ============================================================
        # TS = tempo no sistema
        # ============================================================

        st_tre = df_dis_tre2.merge(
            df_arr_tre,
            on="case_id",
            how="inner"
        )

        st_tre["TS"] = (
            st_tre["t_dis"] - st_tre["t_arr"]
        )

        ts_tre = st_tre.set_index("case_id")["TS"]

        # ============================================================
        # TA = tempo em atendimento
        # ============================================================

        df_tre = df[
            df["case_id"].isin(trens_pos_wu)
        ].copy()

        tip_s = df_tre[
            (df_tre["lifecycle"] == "start")
            &
            (df_tre["resource"] == "tipper")
        ][["case_id", "timestamp"]].rename(
            columns={"timestamp": "ts"}
        )

        tip_c = df_tre[
            (df_tre["lifecycle"] == "complete")
            &
            (df_tre["resource"] == "tipper")
        ][["case_id", "timestamp"]].rename(
            columns={"timestamp": "tc"}
        )

        svc_tre = tip_s.merge(
            tip_c,
            on="case_id",
            how="inner"
        )

        svc_tre["TA"] = (
            svc_tre["tc"] - svc_tre["ts"]
        )

        ta_tre = svc_tre.set_index("case_id")["TA"]

        # ============================================================
        # ALINHAMENTO SOMENTE DOS TRENS COMPLETOS
        # ============================================================

        common_ids = (
            ts_tre.index
            .intersection(ta_tre.index)
        )

        ts_tre = ts_tre.loc[common_ids]
        ta_tre = ta_tre.loc[common_ids]

        # ============================================================
        # TF = fila
        # ============================================================

        tf_tre = ts_tre - ta_tre

        # ============================================================
        # THROUGHPUT REAL
        # ============================================================

        lambda_tre_real = (
            len(common_ids) / periodo
        )

        # ============================================================
        # TS / TA / TF (médias por replicação)
        # ============================================================

        reps_TS_tre.append(ts_tre.mean())
        reps_TA_tre.append(ta_tre.mean())
        reps_TF_tre.append(tf_tre.mean())

        # ============================================================
        # NS / NA / NF — contagens instantâneas no momento em que o
        # virador é LIBERADO por cada trem (equivalente ao ex-4.py):
        #
        #   NA ≈ 0  : virador acabou de ser liberado; ainda não foi
        #             ocupado pelo próximo trem no instante da coleta.
        #   NS ≈ NF : como NA≈0, todos os trens no sistema estão
        #             na fila (NS = NF).
        #
        # Cálculo:
        #   n_chegados(t)  = trens chegados até t  (TODOS os trens)
        #   n_saidos(t)    = trens saídos  até t   (inclui o trem k
        #                    que acabou de ser liberado, como no ex-4.py)
        #   NS_k = n_chegados(t) - n_saidos(t)
        # ============================================================

        # Dicionários de chegada/saída de TODOS os trens
        # (não só os pós warm-up, para contar o sistema completo)
        arr_all_tre = df[
            (df["activity"] == "Arrival")
            &
            (df["priority"] == 2.0)
        ][["case_id", "timestamp"]].set_index("case_id")["timestamp"]

        dis_all_tre = df[
            (df["activity"] == "Discharge")
            &
            (df["case_id"].isin(trens_ids))
        ][["case_id", "timestamp"]].set_index("case_id")["timestamp"]

        arr_vals = arr_all_tre.values          # array de timestamps de chegada
        dis_dict = dis_all_tre.to_dict()       # {case_id: timestamp_saida}

        # Eventos "tipper complete" dos trens pós warm-up
        tip_complete_wu = df[
            df["case_id"].isin(common_ids)
            &
            (df["resource"] == "tipper")
            &
            (df["lifecycle"] == "complete")
        ].sort_values("timestamp")

        ns_obs, na_obs, nf_obs = [], [], []

        for _, ev in tip_complete_wu.iterrows():

            t   = ev["timestamp"]
            cid = ev["case_id"]

            # Trens chegados até t (inclusive)
            n_chegados = int((arr_vals <= t).sum())

            # Trens saídos até t (inclusive):
            # o trem k acabou de ser liberado — conta como "saído"
            # mesmo que o evento Discharge ainda não tenha ocorrido
            # (replica o comportamento de ex-4.py onde conta_saida
            #  é incrementado antes de calcular numero_sistema)
            t_dis_k = dis_dict.get(cid, float("inf"))
            n_saidos = int((dis_all_tre.values <= t).sum())
            if t_dis_k > t:
                # Discharge do trem k ainda não ocorreu: adiciona 1
                n_saidos += 1

            ns_k = max(0, n_chegados - n_saidos)
            na_k = lambda_tre_real * ta_tre.mean()  # Lei de Little: λ × TA
            nf_k = ns_k  # NA≈0 → NF = NS

            ns_obs.append(ns_k)
            na_obs.append(na_k)
            nf_obs.append(nf_k)

        reps_NS_tre.append(np.mean(ns_obs) if ns_obs else 0.0)
        reps_NA_tre.append(np.mean(na_obs) if na_obs else 0.0)
        reps_NF_tre.append(np.mean(nf_obs) if nf_obs else 0.0)

        reps_USO_V.append(util_tipper)

        obs_TS_tre.extend(ts_tre.tolist())
        obs_TA_tre.extend(ta_tre.tolist())
        obs_TF_tre.extend(tf_tre.tolist())
        obs_NS_tre.extend(ns_obs)
        obs_NA_tre.extend(na_obs)
        obs_NF_tre.extend(nf_obs)
        obs_USO_V .extend([util_tipper] * max(len(ts_tre), 1))

        # ============================================================
        # ESTOQUE / EXPORTAÇÃO
        # ============================================================

        reps_Estoque.append(ESTOQUE_MINERIO)

        # IMPORTANTE:
        # remove warm-up proporcionalmente
        fator = periodo / config.duration

        exportacao_corrigida = (
            EXPORTACAO_TOTAL * fator
        ) / 1_000_000.0

        reps_Exportacao.append(exportacao_corrigida)

        obs_Estoque   .append(ESTOQUE_MINERIO)
        obs_Exportacao.append(exportacao_corrigida)

    # =================================================================
    # MÉDIAS
    # =================================================================

    def media(x):
        return np.mean(x) if x else 0.0

    m_NS_n = media(reps_NS_nav)
    m_NF_n = media(reps_NF_nav)
    m_NA_n = media(reps_NA_nav)
    m_TS_n = media(reps_TS_nav)
    m_TF_n = media(reps_TF_nav)
    m_TA_n = media(reps_TA_nav)
    m_USO_P = media(reps_USO_P)

    m_NS_t = media(reps_NS_tre)
    m_NF_t = media(reps_NF_tre)
    m_NA_t = media(reps_NA_tre)
    m_TS_t = media(reps_TS_tre)
    m_TF_t = media(reps_TF_tre)
    m_TA_t = media(reps_TA_tre)
    m_USO_V = media(reps_USO_V)

    m_Est = media(reps_Estoque)
    m_Exp = media(reps_Exportacao)

    # =================================================================
    # PRINT
    # =================================================================

    # =================================================================
    # PRINT — formato RESPOSTAS SIMPY + DESK com IC 95%
    # =================================================================

    L   = 66
    sep = "=" * L

    print()
    print("RESPOSTAS SIMPY + DESK")
    print("Indicadores de Desempenho do Sistema de Navios")
    print(sep)
    print(f"NS: {np.mean(reps_NS_nav):.2f} \u00B1 {calc_ic(obs_NS_nav):.2f} navios (IC 95%)")
    print(f"NF: {np.mean(reps_NF_nav):.2f} \u00B1 {calc_ic(obs_NF_nav):.2f} navios (IC 95%)")
    print(f"NA: {np.mean(reps_NA_nav):.2f} \u00B1 {calc_ic(obs_NA_nav):.2f} navios (IC 95%)")
    print(f"TS: {np.mean(reps_TS_nav):.2f} \u00B1 {calc_ic(obs_TS_nav):.2f} horas (IC 95%)")
    print(f"TF: {np.mean(reps_TF_nav):.2f} \u00B1 {calc_ic(obs_TF_nav):.2f} horas (IC 95%)")
    print(f"TA: {np.mean(reps_TA_nav):.2f} \u00B1 {calc_ic(obs_TA_nav):.2f} horas (IC 95%)")
    print(f"USO-P:{np.mean(reps_USO_P)*100:.2f}% \u00B1 {calc_ic(obs_USO_P)*100:.2f}%  (IC 95%)")
    print(sep)
    print("Indicadores de Desempenho do Sistema de Trens")
    print(sep)
    print(f"NS: {np.mean(reps_NS_tre):.2f} \u00B1 {calc_ic(obs_NS_tre):.2f} trens (IC 95%)")
    print(f"NF: {np.mean(reps_NF_tre):.2f} \u00B1 {calc_ic(obs_NF_tre):.2f} trens (IC 95%)")
    print(f"NA: {np.mean(reps_NA_tre):.2f} \u00B1 {calc_ic(obs_NA_tre):.2f} trens (IC 95%)")
    print(f"TS: {np.mean(reps_TS_tre):.2f} \u00B1 {calc_ic(obs_TS_tre):.2f} horas (IC 95%)")
    print(f"TF: {np.mean(reps_TF_tre):.2f} \u00B1 {calc_ic(obs_TF_tre):.2f} horas (IC 95%)")
    print(f"TA: {np.mean(reps_TA_tre):.2f} \u00B1 {calc_ic(obs_TA_tre):.2f} horas (IC 95%)")
    print(f"USO-V:{np.mean(reps_USO_V)*100:.2f}% \u00B1 {calc_ic(obs_USO_V)*100:.2f}%  (IC 95%)")
    print(sep)
    print(f"Estoque de minerio: {np.mean(reps_Estoque):.2f} \u00B1 {calc_ic(obs_Estoque):.2f} t (IC 95%)")
    print(f"Exportacao de minerio: {np.mean(reps_Exportacao):.2f} \u00B1 {calc_ic(obs_Exportacao):.2f} Mt (IC 95%)")

    # =================================================================
    # VALIDAÇÃO DO NÚMERO DE REPLICAÇÕES (precisão 1%)
    # =================================================================

    print()
    print(f"{'='*L}")
    print(f"VALIDAÇÃO — Número de Replicações (precisão {PRECISAO*100:.0f}%, IC {CONFIANCA*100:.0f}%)")
    print(f"{'='*L}")
    print(f"  Replicações executadas : {n_replications}")
    for nome, lista in [
        ("TS Navios", obs_TS_nav),
        ("TS Trens",  obs_TS_tre),
        ("USO-P",     obs_USO_P ),
        ("USO-V",     obs_USO_V ),
    ]:
        ni = n_ideal(lista)
        status = "OK" if ni is not None and n_replications >= ni else f"recomendado: {ni}"
        print(f"  {nome:<14}: n* = {ni if ni else 'N/A':<6}  {status}")
    print(f"{'='*L}")

    print(f"\nDuracao total   : {config.duration:.0f} h")
    print(f"Warm-up         : {warm:.0f} h")
    print(f"Periodo analise : {periodo:.0f} h")

    # =================================================================
    # PLOTS
    # =================================================================

    plotter = SimulationPlotter(model)

    def plot_e_salva(nome_arquivo, plot_fn):

        import matplotlib.pyplot as _plt

        caminho = os.path.join(PASTA, nome_arquivo)

        _show_orig = _plt.show

        def _show_e_salva(*args, **kwargs):

            _plt.gcf().savefig(
                caminho,
                dpi=150,
                bbox_inches="tight"
            )

            _plt.show = _show_orig

            _show_orig(*args, **kwargs)

        _plt.show = _show_e_salva

        try:
            plot_fn()

        except:
            pass

        finally:
            _plt.show = _show_orig

    plot_e_salva(
        "porto_pier_uso.png",
        lambda: plotter.plot_resource_use_over_time(
            show_warm_up=True,
            resource="pier",
            moving_average_window=10
        )
    )

    plot_e_salva(
        "porto_tipper_uso.png",
        lambda: plotter.plot_resource_use_over_time(
            show_warm_up=True,
            resource="tipper",
            moving_average_window=20
        )
    )

    plot_e_salva(
        "porto_wip.png",
        lambda: plotter.plot_wip_over_time()
    )

    return model, event_logger

# =====================================================================
# WRAPPER
# =====================================================================

def simulation_wrapper(seed=None,
                       until=None,
                       warm_up_period=None):

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
        warm_up_period=warm_up_period
        if warm_up_period is not None
        else 30 * DAYS
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

    rf.run_replications(
        base_seed=12345,
        until= 730 * DAYS,
        warm_up_period=250 * DAYS
    )

    print(rf.get_results_dataframe().describe())

# =====================================================================
# FATORIAL
# =====================================================================

def factorial_analysis():

    def sim_wrapper(seed=None,
                    until=None,
                    warm_up_period=250*DAYS,
                    verbose=False,
                    **kwargs):

        model = build_model(verbose=False)

        model.run_simulation(
            validate_resources=False,
            until=until,
            seed=seed,
            warm_up_period=warm_up_period
        )

        return model

    factorial = FactorialExperiment(
        simulation_function=sim_wrapper,
        base_seed=12345
    )

    factorial.add_factor(
        factor_name="arrival_rate_ships",
        parameter_path="CreateBlock.inter_arrival_time",
        levels=[3.0 * DAYS, 4.39 * DAYS, 6.0 * DAYS],
        description="Intervalo médio entre navios"
    )

    factorial.add_factor(
        factor_name="pier_capacity",
        parameter_path="Resource.pier.capacity",
        levels=[1, 2],
        description="Número de píers"
    )

    factorial.run_factorial_experiment(
        n_replications=30,
        simulation_time=730 * DAYS,
        warm_up_period=250 * DAYS,
        verbose=True
    )

    factorial.print_summary()

    factorial.plot_main_effects("system_time_avg")

    factorial.export_results()

    return factorial

# =====================================================================
# CLI
# =====================================================================

def run_single_replication():
    return main()

def run_replications_cli():
    run_replications()

def run_factorial_cli():
    return factorial_analysis()

# ======================================================================
# porto_visualization.py
# Animação do DCA — Porto de Embarque de Minério
# Layout fiel ao Diagrama de Ciclo de Atividades (DCA)
# ======================================================================

import random
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.patheffects as pe
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Circle, Arc
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.lines import Line2D
import os

PASTA = os.path.dirname(os.path.abspath(__file__))

# ======================================================================
# PARÂMETROS DA SIMULAÇÃO (espelho do porto)
# ======================================================================
HOURS = 1.0
DAYS  = 24.0

random.seed(42)
np.random.seed(42)

# ======================================================================
# MINI SIMULAÇÃO INTERNA (para gerar eventos reais)
# ======================================================================

def mini_simula(duracao_h=500):
    """Gera lista de eventos (tipo, t_chegada, t_inicio_serv, t_saida)."""
    TAXA_NAVIOS = 1 / (4.39 * DAYS)
    TAXA_TRENS  = 1 / (7.0  * HOURS)

    eventos_navios = []
    eventos_trens  = []

    t = 0.0
    while t < duracao_h:
        t += random.expovariate(TAXA_NAVIOS)
        sorteio = random.random()
        cap = 100000 if sorteio<=.75 else (200000 if sorteio<=.90 else 150000)
        eventos_navios.append((t, cap))

    t = 0.0
    while t < duracao_h:
        t += max(0.1, random.gauss(7.0, 1.07))
        eventos_trens.append(t)

    # Simula filas simples
    nav_events = []
    pier_livre = 0.0
    estoque    = 14700.0
    exportacao = 0.0

    for t_arr, cap in eventos_navios:
        t_ini = max(t_arr, pier_livre)
        # tempo de carga
        unidades = int(cap // 100)
        t_fim    = t_ini + unidades * (100/1200)
        pier_livre = t_fim
        estoque   -= cap
        exportacao += cap
        nav_events.append({
            "t_arr": t_arr,
            "t_ini": t_ini,
            "t_fim": t_fim,
            "cap"  : cap,
            "na_fila": max(0, t_arr < pier_livre - (t_fim - t_ini)),
        })

    tre_events = []
    virador_livre = 0.0
    for t_arr in eventos_trens:
        t_ini = max(t_arr, virador_livre)
        dur   = sum(max(0, random.gauss(2.5/60, 0.3/60)) for _ in range(80))
        t_fim = t_ini + dur
        virador_livre = t_fim
        estoque += 8000
        tre_events.append({
            "t_arr": t_arr,
            "t_ini": t_ini,
            "t_fim": t_fim,
        })

    return nav_events, tre_events


# ======================================================================
# LAYOUT DO DCA
# ======================================================================

# Posições dos nós (x, y) — inspiradas no DCA da imagem
NOS = {
    # ── Fluxo Navios (topo) ──────────────────────────────────────────
    "Mar"          : (0.88, 0.82),
    "Cheg_Navios"  : (0.63, 0.82),
    "Ag_Carregamento": (0.35, 0.72),
    "Pier"         : (0.63, 0.60),
    "Carrega_Navio": (0.63, 0.45),

    # ── Estoque (centro) ─────────────────────────────────────────────
    "Estoque"      : (0.35, 0.45),

    # ── Fluxo Trens (baixo) ──────────────────────────────────────────
    "Cheg_Trens"   : (0.63, 0.18),
    "Ag_Descarga"  : (0.88, 0.30),
    "Virador"      : (0.63, 0.30),
    "Descarrega_V" : (0.63, 0.45),   # mesmo bloco que carrega (compartilha y)
    "Ferrovia"     : (0.35, 0.18),

    # ── Mina/Navio (fonte de minério) ────────────────────────────────
    "Mina_Navio"   : (0.88, 0.45),
}

# Cores por tipo de nó (fiel ao DCA)
COR_NOS = {
    "Mar"            : "#D6EAF8",   # azul claro — entidade permanente navio
    "Pier"           : "#FADBD8",   # vermelho claro — recurso
    "Virador"        : "#FDEBD0",   # laranja claro — recurso
    "Estoque"        : "#D5F5E3",   # verde — estoque
    "Ferrovia"       : "#F9EBEA",   # rosa — origem trem
    "Mina_Navio"     : "#EBF5FB",   # azul pálido
    "Cheg_Navios"    : "#EBF5FB",
    "Cheg_Trens"     : "#EBF5FB",
    "Carrega_Navio"  : "#D6EAF8",
    "Descarrega_V"   : "#FDEBD0",
    "Ag_Carregamento": "#FDFEFE",
    "Ag_Descarga"    : "#FDFEFE",
}

FORMA_NOS = {   # "rect" | "circle" | "queue"
    "Mar"            : "circle",
    "Pier"           : "circle",
    "Virador"        : "circle",
    "Estoque"        : "circle",
    "Ferrovia"       : "circle",
    "Mina_Navio"     : "circle",
    "Cheg_Navios"    : "rect",
    "Cheg_Trens"     : "rect",
    "Carrega_Navio"  : "rect",
    "Descarrega_V"   : "rect",
    "Ag_Carregamento": "queue",
    "Ag_Descarga"    : "queue",
}

LABEL_NOS = {
    "Mar"            : "Mar",
    "Pier"           : "Píer\ndisponível",
    "Virador"        : "Virador\ndisponível",
    "Estoque"        : "Estoque\nde\nMinério",
    "Ferrovia"       : "Ferrovia",
    "Mina_Navio"     : "Mina/\nNavio",
    "Cheg_Navios"    : "Chegada de\nnavios\nExp(4,39d)",
    "Cheg_Trens"     : "Chegada de\ntrens\nN(7h;1,07h)",
    "Carrega_Navio"  : "Carrega\nnavios\nCte(5)min",
    "Descarrega_V"   : "Descarrega\nvagão\nN(2,5;0,3)min",
    "Ag_Carregamento": "Aguarda\nCarregamento\n>P",
    "Ag_Descarga"    : "Aguarda\nDescarga\n>P",
}

# Caminhos das setas: lista de (origem, destino, cor, estilo)
SETAS = [
    # Navios (azul)
    ("Mar",           "Cheg_Navios",    "#2471A3", "-"),
    ("Cheg_Navios",   "Ag_Carregamento","#2471A3", "-"),
    ("Ag_Carregamento","Pier",          "#2471A3", "-"),
    ("Pier",          "Carrega_Navio",  "#C0392B", "-"),   # vermelho = recurso
    ("Carrega_Navio", "Mar",            "#2471A3", "-"),

    # Trens (preto)
    ("Ferrovia",      "Cheg_Trens",     "#2C3E50", "-"),
    ("Cheg_Trens",    "Ag_Descarga",    "#2C3E50", "-"),
    ("Ag_Descarga",   "Virador",        "#2C3E50", "-"),
    ("Virador",       "Descarrega_V",   "#784212", "--"),  # marrom = recurso virador
    ("Descarrega_V",  "Ferrovia",       "#2C3E50", "-"),

    # Minério (marrom tracejado)
    ("Mina_Navio",    "Descarrega_V",   "#784212", "--"),
    ("Descarrega_V",  "Estoque",        "#784212", "--"),
    ("Estoque",       "Carrega_Navio",  "#784212", "--"),
    ("Carrega_Navio", "Mina_Navio",     "#784212", "--"),
]


# ======================================================================
# DESENHA O DIAGRAMA BASE
# ======================================================================

def desenha_diagrama(ax):
    """Desenha nós e setas do DCA fixos no eixo ax."""
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.axis("off")

    R_CIRCLE = 0.055
    W_RECT   = 0.13
    H_RECT   = 0.09

    patch_map = {}   # nome → centro do patch (para setas)

    for nome, (x, y) in NOS.items():
        cor   = COR_NOS.get(nome, "#FDFEFE")
        forma = FORMA_NOS.get(nome, "rect")
        label = LABEL_NOS.get(nome, nome)

        if forma == "circle":
            circ = Circle((x, y), R_CIRCLE, color=cor,
                          ec="#555", lw=1.2, zorder=3)
            ax.add_patch(circ)
            ax.text(x, y, label, ha="center", va="center",
                    fontsize=6.5, fontweight="bold", zorder=4,
                    multialignment="center")
            patch_map[nome] = (x, y)

        elif forma == "rect":
            rect = FancyBboxPatch(
                (x - W_RECT/2, y - H_RECT/2), W_RECT, H_RECT,
                boxstyle="round,pad=0.01", facecolor=cor,
                edgecolor="#555", lw=1.2, zorder=3
            )
            ax.add_patch(rect)
            ax.text(x, y, label, ha="center", va="center",
                    fontsize=6.0, zorder=4, multialignment="center")
            patch_map[nome] = (x, y)

        else:   # queue — retângulo tracejado
            rect = FancyBboxPatch(
                (x - W_RECT/2, y - H_RECT/2), W_RECT, H_RECT,
                boxstyle="round,pad=0.01", facecolor="#FEFEFE",
                edgecolor="#AAA", lw=1.0, linestyle="--", zorder=3
            )
            ax.add_patch(rect)
            ax.text(x, y, label, ha="center", va="center",
                    fontsize=6.0, color="#555", zorder=4,
                    multialignment="center")
            patch_map[nome] = (x, y)

    # Setas
    for (orig, dest, cor, ls) in SETAS:
        if orig not in patch_map or dest not in patch_map:
            continue
        x0, y0 = patch_map[orig]
        x1, y1 = patch_map[dest]

        # Offset para não sobrepor centro do nó
        dx, dy = x1 - x0, y1 - y0
        dist   = max((dx**2 + dy**2)**0.5, 1e-6)
        ox, oy = dx/dist * 0.058, dy/dist * 0.058

        arrowprops = dict(
            arrowstyle="-|>",
            color=cor,
            lw=1.5 if ls == "-" else 1.0,
            linestyle=ls,
            connectionstyle="arc3,rad=0.0",
        )
        ax.annotate("",
            xy    =(x1 - ox, y1 - oy),
            xytext=(x0 + ox, y0 + oy),
            arrowprops=arrowprops, zorder=2
        )

    return patch_map


# ======================================================================
# ENTIDADES ANIMADAS
# ======================================================================

class EntidadeAnimada:
    """Ponto colorido que percorre um caminho de nós."""

    def __init__(self, ax, caminho, cor, t_inicio, t_fim_lista):
        """
        caminho    : lista de nomes de nós pelo qual passa
        t_inicio   : tempo de simulação em que começa a andar
        t_fim_lista: lista de tempos de chegada a cada nó
        """
        self.caminho    = caminho
        self.cor        = cor
        self.t_inicio   = t_inicio
        self.t_fins     = t_fim_lista
        self.dot,       = ax.plot([], [], "o", color=cor,
                                  ms=7, zorder=10,
                                  markeredgecolor="white",
                                  markeredgewidth=0.8)
        self.ativo      = True

    def atualiza(self, t_sim, nos_pos):
        """Posiciona o ponto de acordo com t_sim."""
        if t_sim < self.t_inicio:
            self.dot.set_data([], [])
            return

        if t_sim >= self.t_fins[-1]:
            self.dot.set_data([], [])
            self.ativo = False
            return

        # Determina em qual segmento está
        for i in range(len(self.t_fins) - 1):
            t0 = self.t_inicio if i == 0 else self.t_fins[i-1]
            t1 = self.t_fins[i]
            if t_sim <= t1:
                frac = (t_sim - t0) / max(t1 - t0, 1e-9)
                frac = np.clip(frac, 0, 1)
                x0, y0 = nos_pos[self.caminho[i]]
                x1, y1 = nos_pos[self.caminho[i+1]]
                xp = x0 + frac*(x1 - x0)
                yp = y0 + frac*(y1 - y0)
                self.dot.set_data([xp], [yp])
                return

        self.dot.set_data([], [])


# ======================================================================
# FUNÇÃO PRINCIPAL DE ANIMAÇÃO
# ======================================================================

def run_visualization(build_model_fn=None, simulation_time=1000):
    """
    Gera animação DCA-style do porto.
    Salva em porto_visualization.gif
    """
    print(f"\n  Gerando visualização DCA ({simulation_time:.0f}h = {simulation_time/DAYS:.0f}d) …")

    nav_ev, tre_ev = mini_simula(duracao_h=simulation_time)

    # ── Figura ──────────────────────────────────────────────────────
    fig = plt.figure(figsize=(14, 9))
    fig.patch.set_facecolor("#FAFAFA")

    # Título
    fig.text(0.5, 0.97,
             "Exemplo 4 (DCA): Porto de Embarque de Minério",
             ha="center", va="top", fontsize=13, fontweight="bold")
    fig.text(0.5, 0.935,
             "Simulação de Eventos Discretos — SimPy + DESK",
             ha="center", va="top", fontsize=9, color="#555")

    # Eixo principal (DCA)
    ax = fig.add_axes([0.01, 0.12, 0.70, 0.80])
    nos_pos = desenha_diagrama(ax)

    # Painel lateral
    ax_info = fig.add_axes([0.73, 0.12, 0.25, 0.80])
    ax_info.set_xlim(0, 1); ax_info.set_ylim(0, 1)
    ax_info.axis("off")

    # ── Painel de informações ────────────────────────────────────────
    def painel_titulo(ax_i, txt, y, cor="#2C3E50"):
        ax_i.text(0.05, y, txt, fontsize=9, fontweight="bold",
                  color=cor, transform=ax_i.transAxes)

    # Estoque — barra de nível
    ax_stk = fig.add_axes([0.74, 0.62, 0.22, 0.18])
    ax_stk.set_xlim(0, 1); ax_stk.set_ylim(0, 500)
    ax_stk.set_title("Estoque de Minério (kt)", fontsize=8, pad=3)
    ax_stk.set_xticks([]); ax_stk.set_ylabel("kt", fontsize=7)
    ax_stk.tick_params(axis="y", labelsize=7)
    bar_stk = ax_stk.bar([0.5], [0], width=0.6,
                          color="#27AE60", alpha=0.8, edgecolor="white")

    # Contadores
    ax_cnt = fig.add_axes([0.73, 0.38, 0.26, 0.22])
    ax_cnt.axis("off")
    txt_tempo   = ax_cnt.text(0.05, 0.92, "", fontsize=8, transform=ax_cnt.transAxes)
    txt_nav_arr = ax_cnt.text(0.05, 0.76, "", fontsize=8, transform=ax_cnt.transAxes)
    txt_nav_wip = ax_cnt.text(0.05, 0.62, "", fontsize=8, transform=ax_cnt.transAxes)
    txt_nav_uso = ax_cnt.text(0.05, 0.48, "", fontsize=8, transform=ax_cnt.transAxes,
                               color="#C0392B")
    txt_tre_arr = ax_cnt.text(0.05, 0.34, "", fontsize=8, transform=ax_cnt.transAxes)
    txt_tre_wip = ax_cnt.text(0.05, 0.20, "", fontsize=8, transform=ax_cnt.transAxes)
    txt_uso_v   = ax_cnt.text(0.05, 0.06, "", fontsize=8, transform=ax_cnt.transAxes,
                               color="#784212")

    # Mini-gráfico de utilização do píer
    ax_uso = fig.add_axes([0.74, 0.13, 0.22, 0.18])
    ax_uso.set_xlim(0, simulation_time/DAYS)
    ax_uso.set_ylim(0, 1.05)
    ax_uso.set_title("Utilização do Píer", fontsize=8, pad=3)
    ax_uso.set_xlabel("Dias", fontsize=7); ax_uso.set_ylabel("Uso", fontsize=7)
    ax_uso.tick_params(labelsize=6)
    ax_uso.axhline(0.89, color="red", ls="--", lw=0.8, alpha=0.7,
                   label="ref 89%")
    ax_uso.legend(fontsize=6)
    line_uso, = ax_uso.plot([], [], color="#C0392B", lw=1)

    # ── Legenda ──────────────────────────────────────────────────────
    leg_elem = [
        Line2D([0],[0], marker="o", color="w", markerfacecolor="#2471A3",
               ms=8, label="Navio"),
        Line2D([0],[0], marker="o", color="w", markerfacecolor="#27AE60",
               ms=8, label="Trem"),
        Line2D([0],[0], marker="o", color="w", markerfacecolor="#E67E22",
               ms=8, label="Minério (100t)"),
    ]
    ax.legend(handles=leg_elem, loc="lower left", fontsize=7,
              framealpha=0.9, ncol=3)

    # ── Texto de tempo ───────────────────────────────────────────────
    txt_sim = ax.text(0.01, 0.01, "", transform=ax.transAxes,
                      fontsize=8, color="#555")

    # ── Cria entidades animadas ──────────────────────────────────────
    entidades = []

    # Navios
    caminho_nav = [
        "Mar", "Cheg_Navios", "Ag_Carregamento",
        "Pier", "Carrega_Navio", "Mar"
    ]
    for ev in nav_ev[:60]:   # limita para não sobrecarregar
        t0  = ev["t_arr"]
        ts  = ev["t_ini"]
        tf  = ev["t_fim"]
        dur_seg = (tf - ts) / 5
        t_fins  = [t0+0.1, t0+0.3, ts, ts+0.1, tf, tf+0.2]
        ent = EntidadeAnimada(ax, caminho_nav, "#2471A3", t0, t_fins)
        entidades.append(ent)

    # Trens
    caminho_tre = [
        "Ferrovia", "Cheg_Trens", "Ag_Descarga",
        "Virador", "Descarrega_V", "Ferrovia"
    ]
    for ev in tre_ev[:80]:
        t0 = ev["t_arr"]
        ts = ev["t_ini"]
        tf = ev["t_fim"]
        t_fins = [t0+0.05, t0+0.2, ts, ts+0.05, tf, tf+0.1]
        ent = EntidadeAnimada(ax, caminho_tre, "#27AE60", t0, t_fins)
        entidades.append(ent)

    # ── Pré-computa estoque e utilização ao longo do tempo ──────────
    T_SNAPSHOTS = np.linspace(0, simulation_time, 300)
    estoque_hist = []
    uso_pier_hist = []

    estoque_cur = 14700.0
    t_pier_busy = 0.0

    for t_snap in T_SNAPSHOTS:
        for ev in nav_ev:
            if abs(ev["t_fim"] - t_snap) < (simulation_time/300)/2:
                estoque_cur = max(0, estoque_cur - ev["cap"])
        for ev in tre_ev:
            if abs(ev["t_fim"] - t_snap) < (simulation_time/300)/2:
                estoque_cur = min(500000, estoque_cur + 8000)
        estoque_hist.append(max(0, estoque_cur))

        busy = sum(max(0, min(ev["t_fim"], t_snap) - max(ev["t_ini"], 0))
                   for ev in nav_ev if ev["t_ini"] <= t_snap)
        uso  = busy / max(t_snap, 0.001)
        uso_pier_hist.append(min(uso, 1.0))

    # ── Frames ───────────────────────────────────────────────────────
    N_FRAMES = 120
    t_frames = np.linspace(0, simulation_time, N_FRAMES)

    uso_t_plot  = []
    uso_v_plot  = []

    def update(fi):
        t = t_frames[fi]

        # Entidades
        for ent in entidades:
            if ent.ativo:
                ent.atualiza(t, nos_pos)

        # Estoque
        idx = int(fi * len(estoque_hist) / N_FRAMES)
        idx = min(idx, len(estoque_hist)-1)
        estoq_kt = estoque_hist[idx] / 1000.0
        bar_stk[0].set_height(estoq_kt)
        bar_stk[0].set_color("#27AE60" if estoq_kt > 100 else "#E74C3C")

        # Contadores
        n_arr_nav = sum(1 for ev in nav_ev if ev["t_arr"] <= t)
        n_sai_nav = sum(1 for ev in nav_ev if ev["t_fim"] <= t)
        n_wip_nav = n_arr_nav - n_sai_nav

        n_arr_tre = sum(1 for ev in tre_ev if ev["t_arr"] <= t)
        n_sai_tre = sum(1 for ev in tre_ev if ev["t_fim"] <= t)
        n_wip_tre = n_arr_tre - n_sai_tre

        uso_p = uso_pier_hist[idx]

        busy_v = sum(max(0, min(ev["t_fim"], t) - max(ev["t_ini"], 0))
                     for ev in tre_ev if ev["t_ini"] <= t)
        uso_v  = min(busy_v / max(t, 0.001), 1.0)

        txt_tempo  .set_text(f"Tempo: {t/DAYS:.1f} dias")
        txt_nav_arr.set_text(f"Navios chegados : {n_arr_nav}")
        txt_nav_wip.set_text(f"No sistema (WIP): {n_wip_nav}")
        txt_nav_uso.set_text(f"Uso Pier        : {uso_p*100:.1f}%")
        txt_tre_arr.set_text(f"Trens chegados  : {n_arr_tre}")
        txt_tre_wip.set_text(f"No sistema (WIP): {n_wip_tre}")
        txt_uso_v  .set_text(f"Uso Virador     : {uso_v*100:.1f}%")

        txt_sim.set_text(f"t = {t/DAYS:.1f} dias")

        # Mini-gráfico utilização
        uso_t_plot.append(t/DAYS)
        uso_v_plot.append(uso_p)
        line_uso.set_data(uso_t_plot, uso_v_plot)

        artists = ([ent.dot for ent in entidades]
                   + [bar_stk[0], txt_tempo, txt_nav_arr,
                      txt_nav_wip, txt_nav_uso, txt_tre_arr,
                      txt_tre_wip, txt_uso_v, txt_sim, line_uso])
        return artists

    anim = FuncAnimation(fig, update, frames=N_FRAMES,
                         interval=120, blit=False)

    gif_path = os.path.join(PASTA, "porto_visualization.gif")
    writer   = PillowWriter(fps=10)
    anim.save(gif_path, writer=writer, dpi=100)
    print(f"  Visualização salva: {gif_path}")
    plt.close(fig)
    return gif_path


# # ======================================================================
# # ENTRY POINT
# # ======================================================================

# if __name__ == "__main__":
#     main()
#     run_visualization(simulation_time=720000)