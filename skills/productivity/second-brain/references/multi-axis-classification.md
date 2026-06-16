# Multi-Axis Classification — Decision Tree & Schema

## Quick Reference

```yaml
---
type: decision|topic|guide|project|skill    # 필수
domain: trading|ai-ml|devops|smarthome|hermes|toeic|discord|notion|general  # 필수
status: draft|stable|deprecated            # 필수
source: session|research|external          # 자동
tags: [tag1, tag2]                         # 선택
session: session_id                        # 자동 (source=session만)
date: YYYY-MM-DD
---
```

## Type Decision Tree

1. 기술 선택/아키텍처 결정/트레이드오프 → `decision`
2. 단계별 지침/설정 방법 → `guide`
3. 특정 프로젝트 진행/작업 추적 → `project`
4. 반복 가능한 패턴/자동화 → `skill`
5. 그 외 모든 개념/학습/조사 → `topic`

## Domain Decision Tree

| Domain | Keywords | Exclusions |
|--------|----------|------------|
| `trading` | KIS API, 자동매매, 주식, 백테스팅, 포트폴리오 | 일반 금융 이론 → ai-ml |
| `ai-ml` | LLM, RAG, 임베딩, DSPy, 프롬프트, 파인튜닝 | Hermes 설정 → hermes |
| `devops` | Docker, K8s, CI/CD, 서버, nginx, 배포, 네트워크 | HA Docker → smarthome |
| `smarthome` | Home Assistant, MQTT, OpenHue, IoT, HA 자동화 | MQTT 프로토콜 → devops |
| `hermes` | delegate_task, cron, SOUL, AGENTS, 스킬, profile | LLM 일반 → ai-ml |
| `toeic` | TOEIC, 토익, LC, RC, Part 5/6/7 | 일반 영어 → general |
| `discord` | 디스코드, 채널, 길드, 봇 토큰, webhook | — |
| `notion` | Notion API, 페이지, 데이터베이스, ntn CLI | — |
| `general` | 위 모든 domain에 속하지 않는 경우 | 사용률 20% 초과 시 domain 재검토 |

## Status Lifecycle

```
draft ──(7일 경과 + 2회 PASS)──▶ stable ──(정보 노후화)──▶ deprecated
  │                                    │
  └──(90일 방치)──▶ deprecated         └── superseded_by 링크
```

## Search Patterns

```bash
# Multi-axis layered search
grep -rl "domain: trading" 10_Wiki/ | xargs grep -l "type: decision" | xargs grep -l "status: stable"

# Legacy folder fallback
grep -ril "쿼리" 10_Wiki/Decisions/ 10_Wiki/Topics/ 10_Wiki/Projects/
```
