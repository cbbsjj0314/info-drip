InfoDrip은 iPad에서 PDF를 읽다가 궁금한 부분을 선택해 설명, 용어 정리, 질문/답변, 퀴즈, 다시 보기 흐름을 사용할 수 있는 local-first PDF reading assistant입니다.

## iPad backend URL 설정

iOS app은 Info.plist의 `INFODRIP_BACKEND_BASE_URL` 값을 backend base URL로 사용한다.

이 값은 Xcode target build configuration의 `.xcconfig`에서 주입된다.

- Simulator 기본값: `http://127.0.0.1:8000`
- 실제 iPad에서 backend를 호출할 때는 `ios/InfoDrip/Config/Local.xcconfig.example`을 `ios/InfoDrip/Config/Local.xcconfig`로 복사한 뒤 `INFODRIP_BACKEND_BASE_URL` 값을 iPad에서 접근 가능한 backend base URL로 바꾼다.
- `Local.xcconfig`는 개인 개발 환경 파일이므로 Git에 커밋하지 않는다.
- `.xcconfig`에서는 `//`가 comment로 해석되므로 URL은 `http://...` 대신 `http:/$()/...`로 적는다. Build setting으로 확장된 값은 `http://...`가 된다.

실제 iPad에서 접근하려면 backend는 loopback 전용 주소가 아니라 LAN에서 접근 가능한 host로 실행되어야 한다.

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

이 값은 backend URL만 담는다.

LLM API key와 provider secret은 iPad app에 넣지 않고 backend 환경 변수에만 둔다.
