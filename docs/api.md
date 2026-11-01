# API — foundation

Only these routes currently exist:

| Method | Route | Behavior |
|---|---|---|
| GET | `/api/v1/health/live` | 200 if the API process can respond |
| GET | `/api/v1/health/ready` | 200 if dependencies/schema are ready, otherwise 503 |
| GET | `/metrics` | Internal Prometheus scrape |
| GET | `/api/docs` | Development OpenAPI UI |
| GET | `/api/openapi.json` | Development OpenAPI schema |

```sh
curl http://localhost:8000/api/v1/health/live
```

Response: `{"status":"ok","dependencies":{}}`.

Readiness returns named booleans, for example
`{"status":"not_ready","dependencies":{"postgresql":false,"redis":true,"qdrant":true}}`.
This is an illustrative response, not a measured deployment result. The database
check requires the current Alembic revision, not merely a successful TCP connection.

Errors follow `{"error":{"code":"http_404","message":"Request could not be completed","request_id":"..."}}`.
Every handled request gets a server-generated `X-Request-ID`; incoming values are not
trusted. Validation responses do not echo raw inputs. Unexpected exceptions return
generic 500 responses and log only an error category.

The planned auth/document/search/chat/evaluation/admin API is listed in the
implementation plan; those routes are not stubbed with success responses.
