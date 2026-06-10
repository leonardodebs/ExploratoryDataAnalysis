"""
Gerador de dados sintéticos de eventos AWS CloudTrail.

Gera 1000 eventos realistas simulando logs do CloudTrail, com padrões
intencionais embutidos para tornar a análise exploratória interessante:
  - Pico de atividade em horário comercial (~14h)
  - Menos atividade nos finais de semana
  - Alguns IPs "suspeitos" que concentram erros AccessDenied de madrugada
"""

import argparse
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42

# Colunas esperadas no dataset final (usadas também nos testes)
COLUNAS = [
    "event_id",
    "timestamp",
    "event_name",
    "source_ip",
    "aws_region",
    "user_agent",
    "error_code",
    "user_type",
    "duration_ms",
]

# Chamadas de API com pesos: leituras (Describe*) dominam, como em contas reais
EVENT_NAMES = {
    "DescribeInstances": 0.25,
    "DescribeSecurityGroups": 0.15,
    "PutObject": 0.14,
    "AssumeRole": 0.12,
    "GetSecretValue": 0.10,
    "RunInstances": 0.08,
    "StopInstances": 0.06,
    "CreateBucket": 0.04,
    "TerminateInstances": 0.03,
    "DeleteBucket": 0.03,
}

REGIOES = {
    "us-east-1": 0.45,
    "us-west-2": 0.25,
    "sa-east-1": 0.20,
    "eu-west-1": 0.10,
}

USER_AGENTS = [
    "aws-cli/2.15.30 Python/3.11.8 Linux/6.5.0",
    "terraform/1.7.4 aws-sdk-go/1.50.0",
    "boto3/1.34.50 Python/3.12.2 Linux/6.5.0",
    "console.aws.amazon.com",
    "aws-sdk-go/1.50.0 (go1.21; linux; amd64)",
]

USER_TYPES = {
    "IAMUser": 0.55,
    "AssumedRole": 0.42,
    "Root": 0.03,  # uso de Root deve ser raro (e é um achado de segurança!)
}

ERROS_NORMAIS = {
    "AccessDenied": 0.50,
    "NoSuchBucket": 0.30,
    "InvalidClientTokenId": 0.20,
}

# IPs suspeitos: concentram tentativas negadas, simulando credencial vazada
IPS_SUSPEITOS = ["203.0.113.66", "198.51.100.23", "203.0.113.99"]


def _gerar_pool_ips(rng: np.random.Generator, n: int = 30) -> list[str]:
    """Gera um pool de IPs internos/corporativos plausíveis (RFC 5737 e 10.x)."""
    pool = []
    for _ in range(n):
        if rng.random() < 0.6:
            pool.append(f"10.0.{rng.integers(0, 32)}.{rng.integers(1, 255)}")
        else:
            pool.append(f"192.0.2.{rng.integers(1, 255)}")
    return pool


def _sortear_timestamp(rng: np.random.Generator, base: datetime, suspeito: bool) -> datetime:
    """
    Sorteia um timestamp nos últimos 30 dias com padrão diurno:
      - tráfego normal concentrado em horário comercial (pico ~14h)
      - tráfego suspeito concentrado de madrugada (2h-5h)
    """
    if suspeito:
        hora = int(rng.choice([2, 3, 4, 5], p=[0.35, 0.30, 0.20, 0.15]))
    else:
        # Distribuição de horas com pico às 14h (formato de jornada de trabalho)
        horas = np.arange(24)
        pesos = np.exp(-((horas - 14) ** 2) / (2 * 4.0**2)) + 0.08
        pesos /= pesos.sum()
        hora = int(rng.choice(horas, p=pesos))

    # Menos atividade aos finais de semana (sábado=5, domingo=6)
    while True:
        dia_offset = int(rng.integers(0, 30))
        candidato = base - timedelta(days=dia_offset)
        if candidato.weekday() < 5 or rng.random() < 0.35:
            break

    return candidato.replace(
        hour=hora,
        minute=int(rng.integers(0, 60)),
        second=int(rng.integers(0, 60)),
        microsecond=0,
    )


def gerar_eventos(n: int = 1000, seed: int = SEED) -> pd.DataFrame:
    """Gera um DataFrame com `n` eventos sintéticos de CloudTrail."""
    rng = np.random.default_rng(seed)
    base = datetime.now(tz=timezone.utc).replace(microsecond=0)
    pool_ips = _gerar_pool_ips(rng)

    registros = []
    for _ in range(n):
        # ~10% dos eventos vêm dos IPs suspeitos
        suspeito = rng.random() < 0.10
        if suspeito:
            ip = str(rng.choice(IPS_SUSPEITOS, p=[0.5, 0.3, 0.2]))
            # IP suspeito falha quase sempre com AccessDenied
            erro = "AccessDenied" if rng.random() < 0.70 else None
            evento = str(rng.choice(["GetSecretValue", "AssumeRole", "RunInstances"]))
        else:
            ip = str(rng.choice(pool_ips))
            evento = str(rng.choice(list(EVENT_NAMES), p=list(EVENT_NAMES.values())))
            # Tráfego normal falha ~14% das vezes (total fica perto de 20%)
            if rng.random() < 0.145:
                erro = str(rng.choice(list(ERROS_NORMAIS), p=list(ERROS_NORMAIS.values())))
            else:
                erro = None

        registros.append(
            {
                "event_id": str(uuid.UUID(int=int(rng.integers(0, 2**63)))),
                "timestamp": _sortear_timestamp(rng, base, suspeito),
                "event_name": evento,
                "source_ip": ip,
                "aws_region": str(rng.choice(list(REGIOES), p=list(REGIOES.values()))),
                "user_agent": str(rng.choice(USER_AGENTS)),
                "error_code": erro,
                "user_type": str(rng.choice(list(USER_TYPES), p=list(USER_TYPES.values()))),
                "duration_ms": int(rng.integers(50, 2001)),
            }
        )

    df = pd.DataFrame(registros, columns=COLUNAS)
    return df.sort_values("timestamp").reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera eventos sintéticos de CloudTrail")
    parser.add_argument("--rows", type=int, default=1000, help="número de eventos")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).parent / "cloudtrail_sample.csv",
        help="caminho do CSV de saída",
    )
    args = parser.parse_args()

    df = gerar_eventos(args.rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.output, index=False)

    taxa_erro = df["error_code"].notna().mean() * 100
    print(f"✔ {len(df)} eventos gerados em {args.output}")
    print(f"  Taxa de erro: {taxa_erro:.1f}% | IPs únicos: {df['source_ip'].nunique()}")


if __name__ == "__main__":
    main()
