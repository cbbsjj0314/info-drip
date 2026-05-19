InfoDrip은 iPad에서 PDF를 읽다가 궁금한 부분을 선택해 설명, 용어 정리, 질문/답변, 퀴즈, 다시 보기 흐름을 사용할 수 있는 local-first PDF reading assistant입니다.

## iPad backend URL 설정

iOS app은 Info.plist의 `INFODRIP_BACKEND_BASE_URL` 값을 backend base URL로 사용한다.

이 값은 Xcode target build setting의 `INFODRIP_BACKEND_BASE_URL`에서 주입된다.

- Simulator 기본값: `http://127.0.0.1:8000`
- 실제 iPad에서 Mac의 local backend를 호출할 때는 Xcode target build setting의 `INFODRIP_BACKEND_BASE_URL` 값을 `http://<Mac LAN IP>:8000` 형식으로 바꾼다.

이 값은 backend URL만 담는다.

LLM API key와 provider secret은 iPad app에 넣지 않고 backend 환경 변수에만 둔다.
