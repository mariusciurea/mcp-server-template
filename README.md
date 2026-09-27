# MCP Router Template

Template profesional de server MCP în Python, construit cu **FastAPI** și **fastapi-mcp**.
Expune 3 tool-uri dummy pentru gestionarea unor routere de rețea, protejate cu
autentificare JWT și rate limiting. Nu folosește bază de date — inventarul de
routere e citit dintr-un fișier JSON.

## Structură

```
src/
├── service.py            # entrypoint: FastAPI app + auth + rate limit + MCP mount
├── core/
│   ├── settings.py        # configurare (Pydantic Settings, citită din .env)
│   ├── security.py        # emitere/validare JWT
│   └── rate_limit.py      # limiter (slowapi)
├── data_models/
│   ├── auth.py             # model Token
│   └── devices.py          # modele Pydantic: RouterDevice, CommandRequest, ...
├── tools/
│   ├── list_elements.py    # tool: listează routerele
│   ├── send_command.py     # tool: simulează trimiterea unei comenzi CLI
│   └── router_status.py    # tool: simulează metrici live pentru un router
└── data/
    └── routers.json        # "baza de date" dummy cu routere
```

## Instalare

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
copy .env.example .env        # apoi completează JWT_SECRET_KEY și ADMIN_PASSWORD
```

## Pornire

```bash
python -m src.service
# sau
uvicorn src.service:app --reload
```

Serverul pornește pe `http://127.0.0.1:8000`. Documentația interactivă e la
`/docs`, iar serverul MCP e montat la `/mcp`.

## Autentificare

Nu există bază de date de useri — există un singur cont admin, definit în `.env`.

```bash
curl -X POST http://127.0.0.1:8000/auth/token \
  -d "username=admin&password=<parola-din-.env>"
```

Răspunsul conține un `access_token` JWT, folosit ca `Authorization: Bearer <token>`
pentru orice apel către tool-uri, atât prin REST cât și prin MCP (fastapi-mcp
propagă automat header-ul `Authorization` către tool-uri).

## Rate limiting

Fiecare endpoint (inclusiv `/auth/token`) e limitat conform `RATE_LIMIT` din
`.env` (implicit `10/minute`, per IP). Depășirea limitei întoarce `429`.

## Tool-uri disponibile

| Tool | Metodă | Descriere |
|---|---|---|
| `list_elements` | GET `/tools/routers` | Listează toate routerele din inventar |
| `send_command` | POST `/tools/routers/command` | Simulează rularea unei comenzi CLI pe un router |
| `get_router_status` | GET `/tools/routers/{router_id}/status` | Simulează metrici live (uptime, CPU, memorie) |

Toate sunt endpoint-uri FastAPI normale, protejate cu `Depends(get_current_user)`,
și sunt expuse automat ca tool-uri MCP de `fastapi-mcp` (identificate prin
`operation_id`).

## Notă despre dependențe

`requirements.txt` fixează `mcp<2.0.0` deoarece `fastapi-mcp` 0.4.0 nu e încă
compatibil cu SDK-ul `mcp` 2.x (schimbare de semnătură internă). La un upgrade
de `fastapi-mcp`, verifică dacă restricția mai e necesară.

## Configurare (`.env`)

Vezi [.env.example](.env.example) pentru toate variabilele disponibile
(`JWT_SECRET_KEY`, `JWT_ALGORITHM`, `JWT_EXPIRE_MINUTES`, `ADMIN_USERNAME`,
`ADMIN_PASSWORD`, `RATE_LIMIT`).

## Extindere

- Adaugi un tool nou = o funcție în `tools/`, un model de date în
  `data_models/` (dacă e nevoie) și un endpoint în `service.py` cu
  `operation_id` explicit.
- Pentru conectare reală la routere (SSH/NETCONF), înlocuiește logica dummy
  din `tools/send_command.py` fără să schimbi restul aplicației.
