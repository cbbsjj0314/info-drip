<!--
PR 본문은 한국어로 작성한다.

빠르게 훑어볼 수 있게 짧게 쓴다.
긴 문단보다 짧은 bullet을 선호한다.
구체적이고 명확하게 쓴다.
쓸데없이 길게 쓰지 않는다.
추상적인 표현보다 구현 사실을 먼저 적는다.
효과를 과장하는 표현보다 실제 변경 사항을 먼저 적는다.

객체명 / endpoint / route / table / model / schema / view / API / command / module / class / function / config key / filename은 번역하지 않고 실제 코드 표기를 유지한다.

docs-only PR이면 Validation / Checks section은 남기고 `- Not run (docs-only change)`라고 적는다.

PR title guidance:
PR 전체를 한 줄로 요약하는 짧고 읽기 쉬운 제목으로 쓴다.
개별 commit 메시지보다 한 단계 위에서 작업 결과나 범위를 설명한다.

Good examples:
- Bootstrap InfoDrip repository
- Add backend FastAPI skeleton
- Add document upload API
- Add highlight creation API
- Add OpenAI-compatible LLM provider interface
- Add explanation generation API
- Add iPad PDF reader skeleton
- Document local agent workflow

Avoid:
- feat: update stuff
- fix: misc changes
- WIP
- update docs
- big cleanup
-->

## Ticket

<!--
Ticket 기반 review에 필요한 최소 정보를 적는다.
Human Gate Required가 Yes라면 이유를 Risks / Notes에 남긴다.
-->

- Ticket ID:
- Risk Level: Low / Medium / High
- Human Gate Required: Yes / No

---

## Summary

<!--
이 PR이 무엇을 바꾸는지 1~3개 bullet로 요약한다.
가능하면 입력과 출력, 또는 사용자 흐름이 보이게 쓴다.
-->

-

---

## Changes

<!--
실제 변경 파일, endpoint, table, model, UI flow, prompt schema 등이 보이게 쓴다.
-->

-

---

## Acceptance Criteria

<!--
Ticket의 acceptance criteria를 어떻게 만족했는지 짧게 적는다.
-->

-

---

## Out of scope / Deferred

<!--
리뷰어가 기대할 수 있지만 이번 PR에서 의도적으로 제외한 작업이 있을 때만 남긴다.
없으면 이 section은 삭제한다.
-->

-

---

## Validation / Checks

<!--
기본은 `command: result` 한 줄 형식으로 쓴다.
merge 전 GitHub Actions check 결과를 확인하고, 실패한 check가 있으면 원인이나 후속 조치를 적는다.

Backend code 변경 예:
- `backend/scripts/check.sh`: passed
- GitHub Actions backend CI: passed

Docs-only 변경 예:
- Not run (docs-only change)

iPad 변경 예:
- Xcode build: passed
- Manual QA on iPad: passed
또는
- Xcode build: not run, current environment does not support Xcode validation
-->

-

---

## Manual QA

<!--
physical iPad smoke나 사람이 직접 확인해야 하는 항목을 적는다.
없으면 `None` 또는 `Not run`으로 남긴다.
-->

-

---

## Risks / Notes

<!--
Summary, Changes, Out of scope / Deferred, Validation / Checks에 이미 적은 내용을 반복하지 않는다.
리뷰어가 알아야 할 caveat, assumption, local 확인 사항이 있을 때만 남긴다.
없으면 이 section은 삭제한다.
-->

-
