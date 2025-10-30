
from src.util_dados import carregar_questoes, comparar_resposta, registrar_resposta, carregar_historico, calcular_desempenho, PASTA_HISTORICO
from pathlib import Path

def test_carregar_questoes():
    qs = carregar_questoes()
    assert len(qs) >= 20
    assert {"id","tema","enunciado","alternativas","resposta_correta","dificuldade"} <= set(qs[0].keys())

def test_comparar_resposta():
    assert comparar_resposta("a", "A")
    assert not comparar_resposta("B", "A")

def test_historico_desempenho(tmp_path, monkeypatch):
    tmp_hist = tmp_path / "historico"
    tmp_hist.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("src.util_dados.PASTA_HISTORICO", tmp_hist)

    registrar_resposta("teste", 1, True, "Lógica", "facil", 1.2)
    registrar_resposta("teste", 2, False, "Lógica", "facil", 1.0)
    registrar_resposta("teste", 6, True, "Busca", "facil", 0.8)

    df = carregar_historico("teste")
    assert len(df) == 3

    perf = calcular_desempenho("teste")
    temas = set(perf["tema"])
    assert "Lógica" in temas and "Busca" in temas
    taxas = dict(zip(perf["tema"], perf["taxa_acerto"]))
    assert abs(taxas["Lógica"] - (1/2)) < 1e-9
    assert abs(taxas["Busca"] - 1.0) < 1e-9
