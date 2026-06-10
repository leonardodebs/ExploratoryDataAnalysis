"""
Testes do projeto1-eda.

Cobrem:
  1. Geração de dados — shape e colunas corretas
  2. Cálculo da taxa de erro — sempre entre 0 e 100
  3. Execução das análises — os 5 gráficos PNG + summary.json são criados
"""

import sys
from pathlib import Path

import pytest

# Adiciona data/ e src/ ao path para importar os módulos do projeto
RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "data"))
sys.path.insert(0, str(RAIZ / "src"))

from generate_data import COLUNAS, gerar_eventos  # noqa: E402
from analysis import calcular_metricas, executar_analises  # noqa: E402

GRAFICOS_ESPERADOS = [
    "q1_top_api_calls.png",
    "q2_atividade_por_hora.png",
    "q3_taxa_erros.png",
    "q4_top_ips_accessdenied.png",
    "q5_heatmap_hora_dia.png",
]


@pytest.fixture(scope="module")
def df_eventos():
    """Dataset sintético compartilhado entre os testes (com colunas derivadas)."""
    df = gerar_eventos(1000)
    df["hora"] = df["timestamp"].dt.hour
    df["dia_semana"] = df["timestamp"].dt.dayofweek
    return df


def test_geracao_shape_e_colunas(df_eventos):
    """A geração deve produzir 1000 linhas com exatamente as colunas esperadas."""
    assert len(df_eventos) == 1000
    assert list(df_eventos.columns[: len(COLUNAS)]) == COLUNAS


def test_geracao_valores_validos(df_eventos):
    """Campos numéricos e categóricos devem respeitar os domínios definidos."""
    assert df_eventos["duration_ms"].between(50, 2000).all()
    assert df_eventos["user_type"].isin(["IAMUser", "AssumedRole", "Root"]).all()
    erros_validos = {"AccessDenied", "NoSuchBucket", "InvalidClientTokenId"}
    assert set(df_eventos["error_code"].dropna().unique()) <= erros_validos


def test_taxa_erro_entre_0_e_100(df_eventos):
    """A taxa de erro calculada deve estar sempre no intervalo [0, 100]."""
    metricas = calcular_metricas(df_eventos)
    assert 0 <= metricas["error_rate_pct"] <= 100


def test_metricas_summary_completas(df_eventos):
    """O summary deve conter todas as chaves do formato especificado."""
    metricas = calcular_metricas(df_eventos)
    chaves = {
        "total_events",
        "error_rate_pct",
        "top_api_call",
        "peak_hour",
        "unique_ips",
        "most_common_error",
    }
    assert set(metricas.keys()) == chaves
    assert metricas["total_events"] == 1000
    assert 0 <= metricas["peak_hour"] <= 23


def test_graficos_e_summary_criados(df_eventos, tmp_path):
    """Após rodar as análises, os 5 PNGs e o summary.json devem existir."""
    executar_analises(df_eventos, tmp_path)

    for nome in GRAFICOS_ESPERADOS:
        arquivo = tmp_path / nome
        assert arquivo.exists(), f"gráfico não encontrado: {nome}"
        assert arquivo.stat().st_size > 0, f"gráfico vazio: {nome}"

    assert (tmp_path / "summary.json").exists()
