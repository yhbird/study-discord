# study-discord
Python을 활용한 discord 봇기능 생성 및 테스트

## 개요

### python을 활용한 Discord 봇 생성 및 테스트  
파이썬을 `Discord` 라이브러리를 사용해서 디스코드 봇을 개발할 수 있다고 해서 봇을 직접 만들어 사용해 보기 위해 만든 프로젝트

### 목표  
- 메이플스토리 API를 통해 얻은 정보를 Discord에 전달한다.
- 사용자가 요청한 기능을 적절한 명령어를 통해 수행할 수 있도록 한다.
- 다른 사람들이 개발한 Discord 봇을 확인하여 개선점 과 배울 부분들을 알아본다.

## 환경설정
- miniconda를 설치하여 간단한 파이썬 가상환경을 활요한다.
- discord 라이브러리에 호환되는 파이썬 버전을 가상환경으로 설치한다.

### miniconda 설치 (WSL)
```bash
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh
```

### conda 가상환경 생성 (Python 3.11 사용)
```bash
conda create -n discord-bot python=3.11
conda activate discord-bot
```

왜 3.11 버전을 사용할까?

discord.py의 최근 fork 버전으로 `py-cord`, `nextcord`를 사용하고 있다.  
두 라이브러리는 python 3.8 ~ 3.12 버전을 사용할 수 있다.  
그러나 3.12 버전은 일부 미지원 기능이 있을 수도 있기 때문에 3.10 혹은 3.11 버전을 권장함.

개인적인 목적으로 사용하기 위해 개발되기 때문에 우선 3.11 버전으로 작업을 진행할 예정

### python 3.10 과 3.11 비교 표 (Chat GPT으로 검색해서 요약함)

| 항목        | Python 3.10                                 | Python 3.11                                                                  |
| --------- | ------------------------------------------- | ---------------------------------------------------------------------------- |
| 출시일       | 2021년 10월                                   | 2022년 10월                                                                    |
| 성능        | 기존 수준                                       | **최대 10\~60% 성능 향상**                                                         |
| 주요 기능     | - `match-case` (패턴 매칭) <br> - 정확한 에러 메시지 개선 | - **성능 대폭 향상**<br> - `Exception Groups` 및 `except*` 지원<br> - `tomllib` 내장 지원 |
| 안정성       | 더 오랜 기간 테스트되어 안정적                           | 비교적 최신이지만 충분히 안정화됨                                                           |
| 라이브러리 호환성 | 대부분 라이브러리 완벽 호환                             | 최근 라이브러리들은 대부분 지원하지만 일부 보수적인 라이브러리는 3.10까지만 지원 가능성                           |
| LTS 지원    | 2026년 10월까지                                 | 2027년 10월까지                                                                  |

### py-cord 라이브러리 설치
```bash
pip install -U py-cord
python -m discord --version #설치확인
```