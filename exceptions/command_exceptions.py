"""
exceptions/mapper_exceptions.py

Mapper 단계 예외 처리 모듈

???_command.py에서 사용되는 예외 클래스 정의
"""

from __future__ import annotations

from discord.ext import commands
from exceptions.base import CommandBaseException

class InvalidCommandFormat(CommandBaseException):
    """명령어 형식이 올바르지 않을 때 발생하는 오류"""
    pass

class CommandFailure(CommandBaseException):
    """명령어 실행에 실패했을 때 발생하는 오류"""
    pass