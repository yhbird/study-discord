import os
import psutil

from sqlalchemy import create_engine, text

from config import POSTGRES_DSN
from exceptions.client_exceptions import DB_CONNECTION_ERROR

from sqlalchemy import Engine, TextClause, Sequence
from typing import Dict, List, Any

# Debug configuration
# 현재 사용중인 메모리 사용량을 MB 단위로 반환 -> 디버그용
def get_memory_usage_mb() -> float:
    """현재 프로세스의 메모리 사용량을 MB 단위로 반환

    Returns:
        float: 현재 프로세스의 메모리 사용량 (MB)
    """
    process = psutil.Process(os.getpid())
    mem = process.memory_info().rss / 1024**2
    return mem


# 서버(guild)내에서 명령어 통계 정보를 반환
def get_command_stats(guild_id: int) -> Dict[str, Any]:
    """서버(guild)내에서 명령어 통계 정보를 반환

    Args:
        guild_id (int): 서버(guild) ID

    Returns:
        dict: 명령어 통계 정보

    Note:
        반환 예시:
        {
            "slowest_command": {
                "command_name": "븜 주식",
                "slowest_elapsed": 1234.5,
                "average_elapsed": 300.0,
                "call_count": 10,
            },
            "fastest_command": {
                "command_name": "븜 도움말",
                "fastest_elapsed": 10.0,
                "average_elapsed": 20.1,
                "call_count": 50,
            },
            "top10_commands": [
                {"command_name": "븜 도움말", "call_count": 50, "average_elapsed": 20.1},
                {"command_name": "븜 주식", "call_count": 30, "average_elapsed": 300.0},
                ...
            ],
        }
    """
    if POSTGRES_DSN == "":
        raise DB_CONNECTION_ERROR("PostgreSQL DSN is not configured.")
    
    psql_engine   : Engine = create_engine(POSTGRES_DSN)

    source_schema : str = "app_service"
    source_table  : str = "discord_command_logs"

    excute_query  : TextClause = text(
        f"""
           select
                command_name_alt 
                , count(*)             as usage_count
                , avg(elapsed_time_ms) as average_elapsed
                , min(elapsed_time_ms) as fastest_elapsed
                , max(elapsed_time_ms) as slowest_elapsed
             from app_service.discord_command_logs
            where guild_id = :p_guild_id
              and command_name_alt is not null
         group by command_name_alt
        """
    )
    
    with psql_engine.connect() as conn:
        rows: Sequence = conn.execute(excute_query, {"p_guild_id": guild_id}).mappings().all()

    # 해당 길드에서 명령어 사용 기록이 없는 경우
    if not rows:
        return {}
    
    # 명령어 사용 통계 정보 가공
    slowest_command_row = max(rows, key=lambda x: x["slowest_elapsed"])
    fastest_command_row = min(rows, key=lambda x: x["fastest_elapsed"])

    slowest_command: Dict[str, str | float | int] = {
        "command_name": str(slowest_command_row["command_name_alt"]),
        "fastest_elapsed": int(slowest_command_row["fastest_elapsed"]),
        "slowest_elapsed": int(slowest_command_row["slowest_elapsed"]),
        "average_elapsed": float(round(slowest_command_row["average_elapsed"], 2)),
        "call_count": int(slowest_command_row["usage_count"]),
    }

    fastest_command: Dict[str, str | float | int] = {
        "command_name": str(fastest_command_row["command_name_alt"]),
        "fastest_elapsed": int(fastest_command_row["fastest_elapsed"]),
        "slowest_elapsed": int(fastest_command_row["slowest_elapsed"]),
        "average_elapsed": float(round(fastest_command_row["average_elapsed"], 2)),
        "call_count": int(fastest_command_row["usage_count"]),
    }

    top10_commands: List[Dict[str, Any]] = sorted(
        rows, key = lambda x: x["usage_count"],
        reverse=True
    )[:10]

    top10_command: List[Dict[str, str | float | int]] = [
        {
            "command_name": str(row["command_name_alt"]),
            "call_count": int(row["usage_count"]),
            "average_elapsed": float(round(row["average_elapsed"], 2)),
        }
        for row in top10_commands
    ]

    return {
        "slowest_command": slowest_command,
        "fastest_command": fastest_command,
        "top10_commands": top10_command,
    }