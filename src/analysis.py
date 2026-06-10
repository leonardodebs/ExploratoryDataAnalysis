"""
Análise Exploratória de Dados (EDA) de eventos AWS CloudTrail — versão CLI.

Responde 5 perguntas sobre o dataset e salva os resultados como gráficos PNG
(tema escuro) + um summary.json com as métricas-chave.

Uso:
    python src/analysis.py --output reports/
    python src/analysis.py --input data/cloudtrail_sample.csv --output reports/
"""

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # backend sem display — funciona em servidor/CI

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

# Tema escuro para todos os gráficos
plt.style.use("dark_background")
COR_PRINCIPAL = "#4FC3F7"
COR_ALERTA = "#EF5350"

DIAS_SEMANA = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]


def carregar_dados(caminho: Path) -> pd.DataFrame:
    """Carrega o CSV e prepara colunas derivadas de tempo."""
    df = pd.read_csv(caminho, parse_dates=["timestamp"])
    df["hora"] = df["timestamp"].dt.hour
    df["dia_semana"] = df["timestamp"].dt.dayofweek
    return df


def q1_top_api_calls(df: pd.DataFrame, saida: Path) -> pd.Series:
    """Q1: As 10 chamadas de API mais frequentes."""
    top10 = df["event_name"].value_counts().head(10)

    fig, ax = plt.subplots(figsize=(10, 6))
    top10.sort_values().plot.barh(ax=ax, color=COR_PRINCIPAL)
    ax.set_title("Q1 — Top 10 chamadas de API mais frequentes")
    ax.set_xlabel("Número de eventos")
    ax.set_ylabel("")
    fig.tight_layout()
    fig.savefig(saida / "q1_top_api_calls.png", dpi=120)
    plt.close(fig)
    return top10


def q2_atividade_por_hora(df: pd.DataFrame, saida: Path) -> pd.Series:
    """Q2: Distribuição de atividade por hora do dia (gráfico de linha)."""
    por_hora = df.groupby("hora").size().reindex(range(24), fill_value=0)

    fig, ax = plt.subplots(figsize=(10, 5))
    por_hora.plot.line(ax=ax, marker="o", color=COR_PRINCIPAL)
    ax.set_title("Q2 — Atividade por hora do dia")
    ax.set_xlabel("Hora (UTC)")
    ax.set_ylabel("Número de eventos")
    ax.set_xticks(range(0, 24, 2))
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(saida / "q2_atividade_por_hora.png", dpi=120)
    plt.close(fig)
    return por_hora


def q3_taxa_erros(df: pd.DataFrame, saida: Path) -> pd.Series:
    """Q3: Percentual de eventos com erro, detalhado por tipo de erro."""
    por_tipo = df["error_code"].value_counts(dropna=True)

    fig, ax = plt.subplots(figsize=(8, 5))
    cores = [COR_ALERTA, "#FFB74D", "#BA68C8"]
    por_tipo.plot.bar(ax=ax, color=cores[: len(por_tipo)])
    taxa_total = df["error_code"].notna().mean() * 100
    ax.set_title(f"Q3 — Erros por tipo (taxa global: {taxa_total:.1f}%)")
    ax.set_ylabel("Número de eventos")
    ax.tick_params(axis="x", rotation=0)
    fig.tight_layout()
    fig.savefig(saida / "q3_taxa_erros.png", dpi=120)
    plt.close(fig)
    return por_tipo


def q4_top_ips_accessdenied(df: pd.DataFrame, saida: Path) -> pd.Series:
    """Q4: Top 10 IPs de origem com mais erros AccessDenied (gráfico de barras)."""
    negados = df[df["error_code"] == "AccessDenied"]
    top_ips = negados["source_ip"].value_counts().head(10)

    fig, ax = plt.subplots(figsize=(10, 6))
    top_ips.sort_values().plot.barh(ax=ax, color=COR_ALERTA)
    ax.set_title("Q4 — Top 10 IPs com mais AccessDenied")
    ax.set_xlabel("Número de AccessDenied")
    ax.set_ylabel("")
    fig.tight_layout()
    fig.savefig(saida / "q4_top_ips_accessdenied.png", dpi=120)
    plt.close(fig)
    return top_ips


def q5_heatmap_hora_dia(df: pd.DataFrame, saida: Path) -> pd.DataFrame:
    """Q5: Taxa de erro (%) por hora do dia x dia da semana (heatmap)."""
    pivot = (
        df.assign(tem_erro=df["error_code"].notna())
        .pivot_table(index="dia_semana", columns="hora", values="tem_erro", aggfunc="mean")
        .reindex(index=range(7), columns=range(24))
        * 100
    )
    pivot.index = DIAS_SEMANA

    fig, ax = plt.subplots(figsize=(14, 5))
    sns.heatmap(
        pivot,
        ax=ax,
        cmap="rocket",
        cbar_kws={"label": "Taxa de erro (%)"},
        linewidths=0.3,
        linecolor="#222222",
    )
    ax.set_title("Q5 — Taxa de erro (%) por hora x dia da semana")
    ax.set_xlabel("Hora (UTC)")
    ax.set_ylabel("")
    fig.tight_layout()
    fig.savefig(saida / "q5_heatmap_hora_dia.png", dpi=120)
    plt.close(fig)
    return pivot


def calcular_metricas(df: pd.DataFrame) -> dict:
    """Consolida as métricas-chave do dataset no formato do summary.json."""
    erros = df["error_code"].dropna()
    return {
        "total_events": int(len(df)),
        "error_rate_pct": round(float(df["error_code"].notna().mean() * 100), 2),
        "top_api_call": str(df["event_name"].value_counts().idxmax()),
        "peak_hour": int(df.groupby("hora").size().idxmax()),
        "unique_ips": int(df["source_ip"].nunique()),
        "most_common_error": str(erros.value_counts().idxmax()) if len(erros) > 0 else None,
    }


def executar_analises(df: pd.DataFrame, saida: Path) -> dict:
    """Roda as 5 análises, salva os PNGs + summary.json e retorna as métricas."""
    saida = Path(saida)
    saida.mkdir(parents=True, exist_ok=True)

    q1_top_api_calls(df, saida)
    q2_atividade_por_hora(df, saida)
    q3_taxa_erros(df, saida)
    q4_top_ips_accessdenied(df, saida)
    q5_heatmap_hora_dia(df, saida)

    metricas = calcular_metricas(df)
    with open(saida / "summary.json", "w", encoding="utf-8") as f:
        json.dump(metricas, f, indent=2, ensure_ascii=False)
    return metricas


def main() -> None:
    raiz = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description="EDA de eventos CloudTrail")
    parser.add_argument(
        "--input",
        type=Path,
        default=raiz / "data" / "cloudtrail_sample.csv",
        help="CSV de entrada",
    )
    parser.add_argument(
        "--output", type=Path, default=raiz / "reports", help="diretório de saída"
    )
    args = parser.parse_args()

    df = carregar_dados(args.input)
    metricas = executar_analises(df, args.output)

    print(f"✔ Análises concluídas — saída em {args.output}/")
    for chave, valor in metricas.items():
        print(f"  {chave}: {valor}")


if __name__ == "__main__":
    main()
