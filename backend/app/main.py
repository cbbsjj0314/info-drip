from fastapi import FastAPI

app = FastAPI(title="InfoDrip Backend")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
