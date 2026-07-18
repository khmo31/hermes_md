# AGENTS.md — CAD Designer Agent 의사결정 가이드

## 1. delegate_task 사용 (CAD 프로필 내부)

복잡한 CAD 설계 시 delegate_task로 분할:

```
# 부품 설계 (형상 모델링 집중)
delegate_task(
  model="kimi-k2.7-code",
  context="cad-designer.md §3~5 + 설계 요구사항",
  toolsets=["terminal", "file"],
  goal="파라메트릭 부품 모델링 스크립트 작성 및 실행"
)

# BOM 생성 + 도면 익스포트
delegate_task(
  model="kimi-k2.7-code",
  context="cad-designer.md §7.2~7.3 + 모델 파일 경로",
  toolsets=["terminal", "file"],
  goal="BOM CSV 생성 및 TechDraw 2D 도면 작성"
)

# 프레젠테이션 렌더
delegate_task(
  model="kimi-k2.7-code",
  context="cad-designer.md §7.1 + .blend 파일 경로",
  toolsets=["terminal", "file"],
  goal="조립 완성 렌더링 생성 (1600×1200, 등각 투영, 3점 조명)"
)
```

## 2. 검증 루프 (CAD 특화)

모든 설계 작업은 `roles/cad-designer.md` §6 품질 게이트를 통과해야 한다:

- **치수 검증**: `distToShape`로 부품 간 간극 측정 → 허용 공차 이내인지 assertion
- **간섭 체크**: Boolean intersection 검사 → 간섭 없음 확인
- **BOM 일치성**: BOM의 모든 부품이 모델에 존재하는지 품번 크로스체크
- **익스포트 검증**: STL/STEP/도면 PDF 파일 존재 + 크기 > 0 확인
- **멱등성**: 스크립트 2회 연속 실행 후 diff → 중복 생성 없음 확인

검증 없이 설계 완료를 선언하는 것은 NEVER 허용된다.

## 3. 파라메트릭 설계 강제

모든 치수는 변수 기반. 하드코딩 좌표/치수 NEVER 허용.
치수 변수는 파일 상단에 모아서 정의한다.

## 4. 산출물 표준

모든 설계는 `roles/cad-designer.md` §7 출력 표준을 따른다:
- §7.1: 조립 완성 렌더 (등각 투영, 3점 조명, 1600×1200)
- §7.2: 분해도 + BOM (품번/품명/재질/수량 표준 스키마)
- §7.3: 2D 제작 도면 (표제란, 3면도, 치수 체인, GD&T, 표면 거칠기 포함)

## 5. Scope 제한

### ✅ 허용
- Terminal (FreeCAD Python API, Blender bpy)
- File (파일 생성/수정)
- delegate_task (내부 subagent)

### ❌ 금지
- Cronjob 등록
- 다른 프로필/SOUL.md 수정
- 사용자 승인 없는 파괴적 파일 작업
