# Ticket Template

이 template은 Codex implementation prompt로 쉽게 변환할 수 있는 ticket 형식이다.

Ticket은 scope, acceptance criteria, checks, risk를 정리하는 source이고, agent execution prompt는 이 ticket을 바탕으로 현재 repo 상태와 실행 지시를 덧붙여 작성한다.

---

## Ticket ID

<!-- 예: INFO-001, docs(agent)-001, local ticket id 등 -->


## Title

<!-- 한 줄로 작업 결과를 설명한다. -->


## Goal

<!-- 이 ticket이 달성해야 하는 사용자/프로젝트 목표를 짧게 적는다. -->


## Background / Context

<!-- 관련 spec, 현재 상태, repo 문맥, 이전 결정사항을 적는다. -->


## Scope

<!-- 이번 ticket에서 수정하거나 추가할 범위를 구체적으로 적는다. -->

-


## Out of Scope

<!-- 리뷰어가 기대할 수 있지만 이번 ticket에서 명시적으로 제외할 항목을 적는다. -->

-


## Requirements

<!-- 구현 요구사항을 agent가 확인 가능한 bullet로 적는다. -->

-


## Acceptance Criteria

<!-- PR review 시 완료 여부를 판단할 기준을 적는다. -->

-


## Required Checks

<!-- 변경 유형에 맞는 command 또는 docs reread 기준을 적는다. -->

-


## Manual QA

<!-- physical iPad smoke, local app 확인 등 사람이 확인해야 할 항목을 적는다. 없으면 `None`으로 둔다. -->

-


## Risk Level

<!-- Low / Medium / High 중 하나를 남긴다. -->

Low


## Human Gate Required

<!-- Yes / No 중 하나를 남긴다. Yes라면 이유를 적는다. -->

No


## Suggested Branch Name

<!-- 예: docs/agent-workflow, feat/document-upload, fix/quiz-attempt-save -->


## Suggested PR Title

<!-- PR 전체 변경을 한 줄로 설명한다. -->


## Dependencies / Order

<!-- 먼저 merge되어야 하는 ticket, 후속 ticket, strong dependency가 있으면 적는다. 없으면 `None`으로 둔다. -->

None


## Notes

<!-- agent가 알아야 할 caveat, repo boundary, 참고 문서, deferred 판단을 적는다. -->

-
