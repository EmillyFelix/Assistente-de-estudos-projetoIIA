
import argparse
import matplotlib.pyplot as plt
from .util_dados import calcular_desempenho, PASTA_BASE

def main():
    parser = argparse.ArgumentParser(description="Relatório de desempenho por tema")
    parser.add_argument("--aluno-id", required=True)
    args = parser.parse_args()

    desempenho = calcular_desempenho(args.aluno_id)
    if desempenho.empty:
        print("Sem histórico para este aluno.")
        return

    print("\nDesempenho por tema:")
    print(desempenho.to_string(index=False, formatters={
        "taxa_acerto": "{:.2f}".format,
        "tempo_medio_segundos": "{:.2f}".format
    }))

    pasta_rel = PASTA_BASE / "relatorios"
    pasta_rel.mkdir(exist_ok=True, parents=True)
    caminho_fig = pasta_rel / f"desempenho_{args.aluno_id}.png"

    plt.figure()
    plt.bar(desempenho["tema"], desempenho["taxa_acerto"])
    plt.title(f"Taxa de acerto por tema — {args.aluno_id}")
    plt.xlabel("Tema")
    plt.ylabel("Taxa de acerto")
    plt.ylim(0, 1)
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    plt.savefig(caminho_fig, dpi=150)
    print(f"\nFigura salva em: {caminho_fig}")

if __name__ == "__main__":
    main()
