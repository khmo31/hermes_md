OpenCode Notion MCP config 등록 완료. Hermes config에도 Notion MCP 추가 완료. delegate_task subagent 세션에서 Notion 접근 가능. Notion 포트폴리오 문서화는 writer 프로필(qwen3.7-max)이 delegate_task로 처리.
§
Discord: 일반/트레이딩/클로-보고/오픈코드/대화/자기개발(xxxxxxxxxxxxxxxxx369). #자기개발 아침루틴 전용. ⚠️ 텔레그램 올인원 금지 — 채널별 분류 필수. 트레이딩→#트레이딩, 위키→#클로-보고, 루틴→#자기개발. 텔레그램은 긴급만.
§
서버: 192.168.x.x. SmartHome: ~/smarthome/docker-compose (HA:8123, MQTT:1883). 계정 khmo31. 토큰 ~/.homeassistant_token. MCP 등록. OpenHue 설치. manage.sh.
§
Discord 채널 생성 가능 (Bot Token 있음). Guild: xxxxxxxxxxxxxxxxx396. #토익(xxxxxxxxxxxxxxxxx294), #스피킹(xxxxxxxxxxxxxxxxx099) 생성 완료. TOEIC 크론→#토익.
§
멀티프로필 구조: writer(qwen3.7-max, 문서/AI어투), reviewer(v4-pro, 코드리뷰/보안), knowledge(v4-pro, wiki-pipeline/distillation), meta-optimizer(v4-pro, pipeline 개선). default가 단일 진입점, delegate_task로 각 프로필에 위임.
§
hermes_md 레포 (https://github.com/khmo31/hermes_md): Hermes Agent 구조화 설정 파일의 canonical source. SOUL.md, AGENTS.md, profiles/ 포함. 로컬 수정 → cp → commit → push 워크플로우.
§
의사결정 스타일: 모델/설정 변경 시 데이터 기반 접근 선호. "데이터가 결정하게 두는 게 맞다. 미리 최적화할 필요 없다" — 통계적 유의미성 확보 전까지 현상 유지.
