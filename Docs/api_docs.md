# MoMo SMS Transactions API Documentation

**Version:** 1.0.0  
**Base URL:** `http://127.0.0.1:8000`  

This API provides access to mobile money SMS transaction records. It supports CRUD operations and basic authentication.

---

## Authentication

**Type:** Basic Authentication  

All endpoints require authentication. Use the following credentials:

| Username | Password | Role   |
|----------|----------|--------|
| group4   | member   | admin  |
| alice    | user123  | user   |
| bob      | user123  | user   |

- Admins can read/write all transactions.  
- Users can only read/write their own transactions.

**Unauthorized Response (401)**

```json
{
  "error": "Unauthorized"
}
```
Header Example:

pgsql

Authorization: Basic <base64(username:password)>
Endpoints
1. GET /transactions
Retrieve all transactions.
```

Request Example:

```bash

curl -u alice:user123 http://127.0.0.1:8000/transactions
Response Example (200 OK):
Returns a list of transaction objects with user, message, and category fields.
```
Error Codes:

401 Unauthorized – Invalid credentials

2. GET /transactions/{id}
Retrieve a single transaction by ID.

Request Example:

```bash

curl -u group4:member http://127.0.0.1:8000/transactions/5001
Response Example (200 OK):
Returns the transaction object for the given ID.
```
Error Codes:

401 Unauthorized – Invalid credentials

403 Forbidden – User cannot view this transaction

404 Not Found – Transaction ID does not exist
```
3. POST /transactions
Add a new transaction.

Request Example:

```bash

curl -X POST -u alice:user123 \
-H "Content-Type: application/json" \
-d '{...}' \
http://127.0.0.1:8000/transactions
Response Example (201 Created):
Returns the newly created transaction object.

Error Codes:

401 Unauthorized – Invalid credentials

409 Conflict – Transaction ID already exists

400 Bad Request – Invalid JSON format

4. PUT /transactions/{id}
Update an existing transaction.

Request Example:

```bash

curl -X PUT -u alice:user123 \
-H "Content-Type: application/json" \
-d '{...}' \
http://127.0.0.1:8000/transactions/5002
Response Example (200 OK):
Returns the updated transaction object.

Error Codes:

401 Unauthorized – Invalid credentials

403 Forbidden – User cannot update this transaction

404 Not Found – Transaction ID does not exist

5. DELETE /transactions/{id}
Delete a transaction.

Request Example:

```bash

curl -X DELETE -u alice:user123 http://127.0.0.1:8000/transactions/5002
Response Example (204 No Content):
Returns a status message confirming deletion.

Error Codes:

401 Unauthorized – Invalid credentials

403 Forbidden – User cannot delete this transaction

404 Not Found – Transaction ID does not exist

6. GET /dsa/benchmark
Benchmark search efficiency (linear vs dictionary) for the first 20 transactions.

Request Example:

```bash

curl -u group4:member http://127.0.0.1:8000/dsa/benchmark
Response Example (200 OK):
Returns a JSON object with linear_search_ms and dictionary_lookup_ms.

Notes: Dictionary lookup is faster due to O(1) access time vs O(n) for linear search.

Notes on Authentication & Security
Basic Auth is easy to implement but insecure over plain HTTP. Passwords are base64-encoded, not encrypted.

Stronger alternatives:

JWT (JSON Web Tokens) – Tokens with expiration, no need to send passwords every request.

OAuth2 – Token-based access control, supports scopes and third-party apps.
