## MoMo SMS Transactions API (Plain Python http.server)

### Quickstart
1. Place `modified_sms_v2 (1).xml` and `data_dsa.py` in the project directory.
2. Run:
   - Windows PowerShell:
     ```
     python .\api_server.py
     ```
   - Output shows the count loaded and server address `http://127.0.0.1:8000`.

### Auth
- HTTP Basic
- Users:
  - group4 / member (role: admin)
  - alice / user123 (role: user)
  - bob / user123 (role: user)

Admin has full access. Users only see and modify their own transactions (`owner == username`).

### Endpoints
- GET `/transactions`
  - 200: list (admin: all; user: only own)
  - 401 unauthorized

- GET `/transactions/{id}`
  - 200: single record (if permitted)
  - 403 forbidden (not owner)
  - 404 not found
  - 401 unauthorized

- POST `/transactions`
  - Body JSON: `type, amount, sender, receiver, timestamp, owner(optional for admin)`
  - User role: `owner` forced to username
  - 201 created, 409 id exists, 400 invalid JSON, 401 unauthorized

- PUT `/transactions/{id}`
  - Update fields (ID fixed). Users cannot change `owner`.
  - 200 ok, 403/404/400/401

- DELETE `/transactions/{id}`
  - 204 deleted, 403/404/401

- GET `/dsa/benchmark`
  - Sample performance of linear list scan vs dict lookup.

### Testing (PowerShell)
- GET all (admin):
```
curl.exe -u admin:admin123 http://127.0.0.1:8000/transactions
```

- Unauthorized:
```
curl.exe http://127.0.0.1:8000/transactions
```

- POST (user alice):
```
curl.exe -u alice:user123 -H "Content-Type: application/json" `
  -d "{\"type\":\"transfer\",\"amount\":\"100.00\",\"sender\":\"alice\",\"receiver\":\"shop\",\"timestamp\":\"2025-09-30T10:00:00Z\"}" `
  http://127.0.0.1:8000/transactions
```

- PUT (admin):
```
curl.exe -u admin:admin123 -X PUT -H "Content-Type: application/json" `
  -d "{\"amount\":\"250.00\"}" `
  http://127.0.0.1:8000/transactions/1
```

- DELETE (admin):
```
curl.exe -u admin:admin123 -X DELETE http://127.0.0.1:8000/transactions/1
```

- DSA benchmark:
```
curl.exe -u admin:admin123 http://127.0.0.1:8000/dsa/benchmark