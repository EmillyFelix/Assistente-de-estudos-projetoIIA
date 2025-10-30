
import src.recomendador as rec
from src.util_dados import registrar_resposta

def test_recomendador(tmp_path, monkeypatch):
    tmp_hist = tmp_path / "historico"
    tmp_hist.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("src.util_dados.PASTA_HISTORICO", tmp_hist)

    aluno = "bob"
    t0 = rec.sugerir_proximo_tema(aluno)
    assert t0 is not None

    registrar_resposta(aluno, 11, False, "Probabilidade", "facil", 1.0)
    registrar_resposta(aluno, 1, True, "Lógica", "facil", 1.0)
    registrar_resposta(aluno, 3, True, "Lógica", "medio", 1.0)

    t1 = rec.sugerir_proximo_tema(aluno)
    assert t1 == "Probabilidade"
