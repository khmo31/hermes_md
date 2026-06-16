Second Brain auto-save ON. Discover knowledge → auto-classify → save to ~/second_brain/10_Wiki/ without asking. Categories: Decisions/Topics/Projects/Guides/Skills. Git commit automatically. Cron: wiki-pipeline daily 21:00 UTC.
§
Knowledge Distillation Pipeline: Hermes 세션 로그 → Owner/Reviewer/Harness → second_brain Wiki. cron(second-brain-wiki-pipeline, 매일 21:00 UTC)에 통합. Owner=flash(초안), Reviewer=v4-pro(팩트체크). 다축 frontmatter(type/domain/status/source/tags) 사용. 메트릭: distillation_metrics.jsonl.
§
Meta-Optimizer: 별도 프로필(~/.hermes/profiles/meta-optimizer/), 자체 SOUL.md/AGENTS.md로 Scope 격리. second_brain pipeline 개선만 담당. 주간 cron(일 22:00 UTC). 모든 변경은 improvement_proposals/ → 사용자 승인 게이트 통과 필수. Meta-Optimizer는 Knowledge Agent의 영역(파이프라인 실행)을 침범하지 않는다.
§
khmo31 지식 관리 철학: 축(axis)+링킹(linking)이 임베딩 기반 RAG보다 우월하다고 보며, 큐레이션된 지식베이스에서는 벡터 검색이 불필요하다고 판단한다. 임베딩은 분류 체계가 없는 생데이터의 차선책이라는 입장. second_brain의 자동화된 축 분류 파이프라인(Owner/Reviewer cron)이 정리 비용을 제로로 만들었기 때문에, 잘 유지되는 축 체계에서는 grep+LLM 검색어 생성으로 충분하다고 본다.
