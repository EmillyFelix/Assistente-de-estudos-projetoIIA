from typing import Optional
import random

from util_dados import (
    calcular_desempenho,
    carregar_questoes,
    filtrar_questoes,
    calcular_metricas_agente,
)

LIMIAR_BAIXO = 0.50
LIMIAR_ALTO = 0.80

def sugerir_proximo_tema(aluno_id: str) -> Optional[str]:
    """Sugere o próximo tema a ser estudado.

    A lógica considera:
    - Desempenho por tema (taxa de acerto, total de questões, tempo médio)
    - Métrica P4 (adaptação), para ajustar o "estilo" de recomendação

    * Se P4 < 0.5  → modo reforço pesado: sempre recomenda o tema com pior taxa de acerto
    * Se P4 ≥ 0.5 → usa a heurística original em 3 etapas:
        1) temas com taxa < LIMIAR_BAIXO
        2) depois  LIMIAR_BAIXO ≤ taxa < LIMIAR_ALTO
        3) taxa ≥ LIMIAR_ALTO, escolhendo o de menor total e maior tempo
    """
    desempenho = calcular_desempenho(aluno_id)
    if desempenho.empty:
        # sem histórico: recomenda o primeiro tema em ordem alfabética
        temas = sorted({q["tema"] for q in carregar_questoes()})
        return temas[0] if temas else None

    metricas = calcular_metricas_agente(aluno_id)
    p4 = metricas.get("P4", 1.0)

    # ==========================
    #  MODO REFORÇO (P4 < 0.5)
    # ==========================
    if p4 < 0.5:
        # ordena por taxa de acerto crescente (piores temas primeiro)
        candidatos = desempenho.sort_values("taxa_acerto", ascending=True)
        return candidatos.iloc[0]["tema"]

    # ==========================
    #  MODO NORMAL (P4 >= 0.5)
    # ==========================

    # Priorizar temas com taxa < LIMIAR_BAIXO
    candidatos = desempenho[desempenho["taxa_acerto"] < LIMIAR_BAIXO]
    if not candidatos.empty:
        candidatos = candidatos.sort_values("taxa_acerto", ascending=True)
        return candidatos.iloc[0]["tema"]

    # Depois temas com taxa entre LIMIAR_BAIXO e LIMIAR_ALTO
    candidatos = desempenho[
        (desempenho["taxa_acerto"] >= LIMIAR_BAIXO)
        & (desempenho["taxa_acerto"] < LIMIAR_ALTO)
    ]
    if not candidatos.empty:
        candidatos = candidatos.sort_values("taxa_acerto", ascending=True)
        return candidatos.iloc[0]["tema"]

    # temas dominados (>= LIMIAR_ALTO):
    #    escolhe o de menor total mas onde o tempo médio ainda é relativamente alto
    candidatos = desempenho[desempenho["taxa_acerto"] >= LIMIAR_ALTO].copy()
    if not candidatos.empty:
        candidatos = candidatos.sort_values(
            by=["tempo_medio_segundos", "total"],
            ascending=[False, True],  # primeiro quem demora mais, depois quem tem menos questões
        )
        return candidatos.iloc[0]["tema"]

    return None


def escolher_pergunta(tema: Optional[str] = None, dificuldade: Optional[str] = None):
    banco = carregar_questoes()
    banco = filtrar_questoes(banco, tema=tema, dificuldade=dificuldade)
    if not banco:
        return None
    return random.choice(banco)
