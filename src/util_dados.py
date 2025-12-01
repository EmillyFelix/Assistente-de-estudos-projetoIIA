
import json
import csv
from pathlib import Path
from typing import List, Dict, Optional
import pandas as pd
from datetime import datetime

PASTA_BASE = Path(__file__).resolve().parents[1]
PASTA_DADOS = PASTA_BASE / "dados"
ARQ_QUESTOES = PASTA_DADOS / "questoes.json"
PASTA_HISTORICO = PASTA_DADOS / "historico"

PASTA_HISTORICO.mkdir(parents=True, exist_ok=True)

def carregar_questoes() -> List[Dict]:
    with open(ARQ_QUESTOES, "r", encoding="utf-8") as f:
        return json.load(f)

def filtrar_questoes(questoes: List[Dict], tema: Optional[str] = None, dificuldade: Optional[str] = None) -> List[Dict]:
    lista = questoes
    if tema:
        lista = [q for q in lista if q["tema"].lower() == tema.lower()]
    if dificuldade:
        lista = [q for q in lista if q["dificuldade"].lower() == dificuldade.lower()]
    return lista

def caminho_historico(aluno_id: str) -> Path:
    seguro = "".join(ch for ch in aluno_id if ch.isalnum() or ch in ("-", "_")).strip()
    return PASTA_HISTORICO / f"{seguro}.csv"

def registrar_resposta(aluno_id: str, pergunta_id: int, acertou: bool, tema: str, dificuldade: str, tempo_segundos: float) -> None:
    caminho = caminho_historico(aluno_id)
    novo = not caminho.exists()
    with open(caminho, "a", newline="", encoding="utf-8") as f:
        escritor = csv.writer(f)
        if novo:
            escritor.writerow(["momento","aluno_id","pergunta_id","acertou","tema","dificuldade","tempo_segundos"])
        escritor.writerow([datetime.now().isoformat(timespec="seconds"), aluno_id, pergunta_id, int(acertou), tema, dificuldade, round(tempo_segundos, 3)])

def carregar_historico(aluno_id: str) -> pd.DataFrame:
    caminho = caminho_historico(aluno_id)
    if not caminho.exists():
        return pd.DataFrame(columns=["momento","aluno_id","pergunta_id","acertou","tema","dificuldade","tempo_segundos"])
    return pd.read_csv(caminho)

def comparar_resposta(resposta_usuario: str, resposta_correta: str) -> bool:
    a = (resposta_usuario or "").strip().upper()[:1]
    b = (resposta_correta or "").strip().upper()[:1]
    return a == b

def calcular_desempenho(aluno_id: str) -> pd.DataFrame:
    df = carregar_historico(aluno_id)
    if df.empty:
        return pd.DataFrame(columns=["tema","acertos","erros","taxa_acerto","total","tempo_medio_segundos"])
    agrup = df.groupby("tema").agg(
        acertos=("acertou","sum"),
        total=("acertou","count"),
        tempo_medio_segundos=("tempo_segundos","mean")
    ).reset_index()
    agrup["erros"] = agrup["total"] - agrup["acertos"]
    agrup["taxa_acerto"] = agrup["acertos"] / agrup["total"]
    colunas = ["tema","acertos","erros","taxa_acerto","total","tempo_medio_segundos"]
    return agrup[colunas].sort_values(by="taxa_acerto")

def calcular_metricas_agente(
    aluno_id: str,
    tempo_limite_segundos: float = 60.0,
    peso_p1: float = 0.4,
    peso_p2: float = 0.2,
    peso_p3: float = 0.2,
    peso_p4: float = 0.2,
    clareza: float = 1.0,
    adaptacao: float = 1.0,
) -> Dict[str, float]:
    """Calcula as métricas globais de desempenho do agente (P1..P4 e D).

    P1 – Precisão da avaliação: taxa de acerto global do aluno.
    P2 – Eficiência de tempo: 1 - (tempo médio / tempo_limite), limitado a [0,1].
    P3 – Clareza: nota qualitativa informada pelo usuário (0–1).
    P4 – Adaptação: nota qualitativa informada pelo usuário (0–1).

    D = 0.4*P1 + 0.2*P2 + 0.2*P3 + 0.2*P4
    """
    df = carregar_historico(aluno_id)
    if df.empty:
        p1 = 0.0
        tempo_medio = 0.0
    else:
        total = len(df)
        acertos = int(df["acertou"].sum())
        p1 = acertos / total if total > 0 else 0.0
        tempo_medio = float(df["tempo_segundos"].mean())

    if tempo_limite_segundos > 0:
        razao = tempo_medio / tempo_limite_segundos
        p2 = 1.0 - razao
    else:
        p2 = 0.0

    # Garante que fiquem no intervalo [0,1]
    p2 = max(0.0, min(1.0, p2))
    p3 = max(0.0, min(1.0, clareza))
    p4 = max(0.0, min(1.0, adaptacao))

    d = peso_p1 * p1 + peso_p2 * p2 + peso_p3 * p3 + peso_p4 * p4

    return {
        "P1": p1,
        "P2": p2,
        "P3": p3,
        "P4": p4,
        "D": d,
        "taxa_acerto_global": p1,
        "tempo_medio_segundos": tempo_medio,
    }
