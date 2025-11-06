# 📖 API Documentation – Game Statement

## Base URL
```
http://localhost:8000/api
```

---

## 1. Health Check
**Endpoint**
```
GET /health
```

**Response**
```json
{ "status": "healthy" }
```

---

## 2. Realtime Update Statement (Redis only)

Lưu state tạm thời trong Redis khi người chơi thao tác realtime.

**Endpoint**
```
POST /rt-update-game-statement
```

**Request Body**
```json
{
  "user_id": 3,
  "token": "token_active_1234567890abcdef",
  "patch": {
    "coins": 150,
    "itemAmmo": 5,
    "itemShield": 2
  }
}
```

**Response**
```json
{
  "status": "success",
  "message": "realtime updated",
  "version": 2
}
```

📌 Lưu ý:  
- Chỉ update Redis, **chưa ghi xuống DB**.  
- `version` tăng dần mỗi lần update.

---

## 3. Save Statement (flush Redis → DB)

Dùng khi kết thúc màn chơi, hoặc muốn ghi dữ liệu từ Redis xuống DB.

**Endpoint**
```
POST /save-game-statement
```

**Request Body**
```json
{
  "user_id": 3,
  "token": "token_active_1234567890abcdef"
}
```

**Response**
```json
{
  "status": "success",
  "message": "Game statement saved",
  "statement_id": 4
}
```

📌 Lưu ý:  
- Nếu có state trong Redis → lấy state đó để lưu DB.  
- Nếu Redis rỗng → dùng `json_data` từ request (dành cho lần chơi đầu tiên).

---

## 4. Get Statement (từ Redis hoặc DB)

Lấy state hiện tại của user.

**Endpoint**
```
GET /get-game-statement/{user_id}
```

**Example**
```
GET /get-game-statement/3
```

**Response**
```json
{
  "status": "success",
  "source": "redis",
  "statement_id": null,
  "user_id": 3,
  "json_data": {
    "coins": 150,
    "itemAmmo": 5,
    "itemShield": 2
  }
}
```

📌 Field `source` cho biết dữ liệu lấy từ đâu:  
- `"redis"` → state còn nằm trong Redis.  
- `"db"` → lấy từ DB (khi Redis rỗng).  

---

## 5. Admin Flush Realtime (ép Redis → DB ngay)

**Endpoint**
```
POST /admin/flush-realtime/{user_id}
```

**Example**
```
POST /admin/flush-realtime/3
```

**Response**
```json
{
  "status": "success",
  "statement_id": 4
}
```

📌 Dùng cho mục đích admin/debug để ép ghi Redis xuống DB ngay lập tức.

---

## 🚀 Hướng dẫn test bằng Postman

1. Mở Postman, tạo collection `Game Statement API`.  
2. Tạo các request tương ứng với các API trên (copy body JSON từ tài liệu này).  
3. Chạy theo thứ tự:
   - Gọi `rt-update-game-statement` vài lần để update realtime.  
   - Gọi `get-game-statement/{user_id}` → thấy dữ liệu lấy từ Redis.  
   - Gọi `save-game-statement` → dữ liệu được flush xuống DB.  
   - Gọi `get-game-statement/{user_id}` lại → nếu Redis rỗng sẽ thấy `"source": "db"`.  
