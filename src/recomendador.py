
from typing import Optional
from .util_dados import calcular_desempenho, carregar_questoes, filtrar_questoes
import random

LIMIAR_BAIXO = 0.50
LIMIAR_ALTO = 0.80

def sugerir_proximo_tema(aluno_id: str) -> Optional[str]:
    desempenho = calcular_desempenho(aluno_id)
    if desempenho.empty:
        temas = sorted({q["tema"] for q in carregar_questoes()})
        return temas[0] if temas else None

    # 1) Priorizar temas com taxa < 0.5
    candidatos = desempenho[desempenho["taxa_acerto"] < LIMIAR_BAIXO]
    if not candidatos.empty:
        return candidatos.sort_values("taxa_acerto").iloc[0]["tema"]

    # 2) Depois 0.5–0.8
    candidatos = desempenho[(desempenho["taxa_acerto"] >= LIMIAR_BAIXO) & (desempenho["taxa_acerto"] < LIMIAR_ALTO)]
    if not candidatos.empty:
        return candidatos.sort_values("taxa_acerto").iloc[0]["tema"]

    # 3) Dominados (>= 0.8): escolher o de menor total (revisão leve)
    candidatos = desempenho[desempenho["taxa_acerto"] >= LIMIAR_ALTO].sort_values(["total","tempo_medio_segundos"], ascending=[True, True])
    if not candidatos.empty:
        return candidatos.iloc[0]["tema"]

    return None

def escolher_pergunta(tema: Optional[str] = None, dificuldade: Optional[str] = None):
    banco = carregar_questoes()
    banco = filtrar_questoes(banco, tema=tema, dificuldade=dificuldade)
    if not banco:
        return None
    return random.choice(banco)
