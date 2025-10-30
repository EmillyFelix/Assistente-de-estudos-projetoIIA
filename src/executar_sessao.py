
import argparse
import time
from .util_dados import carregar_questoes, filtrar_questoes, comparar_resposta, registrar_resposta
from .recomendador import sugerir_proximo_tema

def fazer_pergunta(pergunta: dict):
    print("\nTema:", pergunta["tema"], "| Dificuldade:", pergunta["dificuldade"])
    print(pergunta["enunciado"])
    for letra, texto in pergunta["alternativas"].items():
        print(f"  {letra}) {texto}")
    inicio = time.time()
    resposta = input("Sua resposta (A/B/C/D): ").strip().upper()[:1]
    fim = time.time()
    correto = comparar_resposta(resposta, pergunta["resposta_correta"])
    if correto:
        print("✅ Correto!")
    else:
        print(f"❌ Errado — resposta correta: {pergunta['resposta_correta']}")
    return bool(correto), fim - inicio, resposta

def main():
    parser = argparse.ArgumentParser(description="Sessão de estudo (CLI) — Português")
    parser.add_argument("--aluno-id", required=True, help="Identificador do aluno (ex.: ana)")
    parser.add_argument("--num-perguntas", type=int, default=5)
    parser.add_argument("--tema", default=None)
    parser.add_argument("--dificuldade", choices=["facil","medio","dificil"], default=None)
    parser.add_argument("--recomendar-tema", action="store_true", help="Ignora --tema e usa recomendação heurística")
    args = parser.parse_args()

    if args.recomendar_tema:
        tema_sugerido = sugerir_proximo_tema(args.aluno_id)
        if tema_sugerido:
            print(f"(Recomendação): próximo tema sugerido = {tema_sugerido}")
            args.tema = tema_sugerido
        else:
            print("(Recomendação): sem sugestão — seguindo sem filtro de tema.")

    perguntas = filtrar_questoes(carregar_questoes(), tema=args.tema, dificuldade=args.dificuldade)
    if not perguntas:
        print("Não encontrei questões com esses filtros.")
        return

    import random
    random.shuffle(perguntas)
    selecao = perguntas[:args.num_perguntas]

    total_acertos = 0
    for p in selecao:
        ok, tempo, _ = fazer_pergunta(p)
        total_acertos += int(ok)
        registrar_resposta(args.aluno_id, p["id"], bool(ok), p["tema"], p["dificuldade"], tempo)

    print(f"\nResumo: {total_acertos}/{len(selecao)} corretas. Histórico salvo.")

if __name__ == "__main__":
    main()
