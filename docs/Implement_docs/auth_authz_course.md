# Khóa học Auth / AuthZ — dự án Pinterest soft-live

Đọc **tuần tự**. Mỗi module: **là gì → vì sao cần → công thức → code trong repo → nối với module trước/sau → tự kiểm**.

**Mục tiêu cuối khóa:** kể lại được ống nước auth/authz của project không nhìn tài liệu; mở một route bất kỳ và chỉ ra từng lớp; phân biệt 401 / 403 / 500 (kể cả case jmco).

**Cách học:** đừng nhảy. Module 6 trở đi giả định bạn đã hiểu hash, JWT, cookie, CSRF.

---

## Mục lục

| Module | Chủ đề | Bạn sẽ hiểu |
|--------|--------|-------------|
| 0 | Bản đồ | Ba đoạn ống A/B/C |
| 1 | Identity & credential | AuthN ≠ AuthZ |
| 2 | Password hash | Credential lâu dài |
| 3 | JWT | Credential ngắn hạn |
| 4 | Cookie | Cách browser giữ JWT |
| 5 | CSRF | Bảo vệ khi cookie tự gửi |
| 6 | Login E2E | Ráp A+B lần đầu + `/me` |
| 7 | Dependency `user_id` | Cổng AuthN mỗi request |
| 8 | Refresh / logout / Redis | Gia hạn & cắt session |
| 9 | Google & URL token | Nhánh AuthN khác |
| 10 | RBAC roles | AuthZ lớp 1 |
| 11 | account_kind / org | AuthZ lớp 2 |
| 12 | Ownership & domain | AuthZ lớp 3 |
| 13 | Cheatsheet | Ghép toàn hệ |

**File code mở kèm:**

| File | Việc |
|------|------|
| `app/postgresql/models.py` | `UsersOrm`, `UserRolesOrm` |
| `app/api/rest/utils.py` | hash, JWT create/decode |
| `app/api/rest/security.py` | Set-Cookie |
| `app/api/rest/dependencies.py` | `user_id`, optional, `require_roles` |
| `app/api/rest/users/routes.py` | login, refresh, logout, `/me` |
| `app/middlewares.py` | CSRF |
| `app/redis/redis_revoke_tokens.py` | denylist |
| `app/api/rest/roles.py` | RBAC |
| `app/api/rest/role_gates.py` | personal vs org |
| `app/api/rest/ownership.py` | resource owner |
| `app/api/rest/job_market/helpers.py` | `resolve_account_kind` |
| `vuejs/src/main.js` | credentials + CSRF header |
| `vuejs/src/api/sessionRefresh.js` | refresh interceptor |
| `vuejs/src/App.vue` | `resolveSession` |

---

# Module 0 — Bản đồ khóa học

## 0.1 Vấn đề thực tế

App không thể hỏi password mỗi lần like pin. Cần:

1. Lần đầu: chứng minh “tôi là user X” (password / Google).
2. Các lần sau: mang theo bằng chứng ngắn hạn (token trong cookie).
3. Khi đã biết là X: quyết định X có được xóa pin Y, sửa JD Z, bán hàng… không.

## 0.2 Ba đoạn ống (nhớ hình này suốt khóa)

```
[A] Chứng minh danh tính lần đầu
    password / Google
         ↓
[B] Giữ danh tính giữa các request
    JWT trong HttpOnly cookie
    + CSRF + refresh + Redis revoke
         ↓
[C] Quyết định được làm gì
    roles → account_kind (org?) → ownership
```

- **A + B = AuthN (Authentication)** — *bạn là ai?* → ra `user_id` hoặc 401.
- **C = AuthZ (Authorization)** — *bạn được làm gì?* → 200 hoặc 403 (đôi khi 404).

## 0.3 Case thật (neo xuyên khóa)

Seed `jmco_*`:

1. Password drift → 401 `password dont match` → gãy đoạn **A**.
2. Reset pass → login 200, set cookie → **A+B server OK**.
3. `/me` 500 vì email `@…local` fail `EmailStr` → **không** phải AuthN fail; FE `resolveSession` catch → UI tưởng chưa login.

Học xong Module 6 bạn phải giải thích được case này bằng đúng thuật ngữ.

---

# Module 1 — Identity, credential, AuthN / AuthZ

## 1.1 Identity — *là gì?*

**Identity** = câu trả lời “request này thuộc về ai?” trong hệ thống.

Trong project, identity ổn định là **`users.id`** (số nguyên). Username chỉ là cách *tìm* user lúc login; sau khi đã login, JWT mang `user_id`, không mang username (username có thể đổi sau này).

```python
# app/postgresql/models.py — UsersOrm (rút cột liên quan auth)
id: Mapped[int] = mapped_column(primary_key=True)
username: Mapped[str] = mapped_column(String(200), unique=True)
hashed_password: Mapped[str | None] = mapped_column(String(200), default=None)
google_id: Mapped[str | None] = mapped_column(String(200), default=None)
email: Mapped[str | None] = mapped_column(String(200), default=None)
verified: Mapped[bool | None] = mapped_column(Boolean, default=False)
```

**Lưu ý:** `email` và `verified` là thông tin hồ sơ / xác minh hộp thư — **không** phải thứ login password đang kiểm. Login không đọc email để quyết định đúng/sai mật khẩu.

## 1.2 Credential — *là gì?*

**Credential** = bằng chứng client đưa ra để *chứng minh* identity. Khác identity: credential là “chìa”, identity là “chủ nhà”.

| Thời điểm | Credential trong app | Ý nghĩa |
|-----------|----------------------|---------|
| Login lần đầu | `password` trong body POST, hoặc Google OAuth | Chứng minh lâu dài |
| Mọi API sau | Cookie `access_token` (JWT) | “Server đã xác nhận tôi là user X, còn hạn” |
| Khi access hết hạn | Cookie `refresh_token` (JWT) | Xin access mới, không hỏi lại password |

Cùng `user_id=42` có thể được chứng minh bằng password hôm nay và bằng JWT ngày mai — hai credential khác nhau, một identity.

## 1.3 AuthN vs AuthZ — *vì sao tách?*

Nếu gộp một khái niệm “login”, bạn sẽ không phân được:

| | Câu hỏi | Khi fail |
|---|---------|----------|
| **AuthN** | Credential có đúng không? → gắn được `user_id`? | Thường **401** |
| **AuthZ** | `user_id` đó có được làm hành động X trên tài nguyên Y? | Thường **403** |

Ví dụ trong đầu:

- Sai password → AuthN fail (`password dont match`).
- Đúng password, không phải chủ pin → AuthN OK, AuthZ fail (`not pin owner`).
- Đúng password, `/me` crash vì email DB xấu → AuthN OK, **không phải AuthZ** — lỗi serialize response.

## 1.4 Principal

Sau AuthN, handler không hỏi lại password. Nó làm việc với **principal** = `user_id` lấy từ JWT. Mọi AuthZ so với principal đó.

**Tự kiểm M1:** Email có phải credential login không? Vì sao?

---

# Module 2 — Mật khẩu (credential lâu dài — đoạn A)

## 2.1 Vì sao không lưu plaintext?

DB bị lộ → attacker đăng nhập mọi account. Vì vậy chỉ lưu **hash một chiều**: từ hash khó suy ngược password; lúc login so khớp bằng hàm `verify`.

## 2.2 Các thành phần nhỏ

| Thuật ngữ | Là gì |
|-----------|--------|
| **Plaintext** | Chuỗi user gõ. Chỉ sống trong body request; không ghi DB, không log. |
| **Hash** | Kết quả `f(password)`. Bcrypt dùng trong app (qua passlib). |
| **Salt** | Muối ngẫu nhiên trộn trước khi hash. Hai user cùng password vẫn khác hash; chống rainbow table. **bcrypt tự sinh & nhúng salt trong chuỗi `hashed_password`** → không cần cột `salt` riêng. |
| **verify(plain, hashed)** | Hash lại plain với tham số trong `hashed`, so khớp an toàn → `true`/`false`. |

## 2.3 Code trong project

```python
# app/api/rest/utils.py
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)
```

**Công thức:**

```
register:  users.hashed_password = hash_password(plain)
login:     ok = verify_password(plain, users.hashed_password)
```

`hashed_password` có thể `NULL` — user chỉ login Google, không có password.

## 2.4 Chỗ AuthN password thật sự xảy ra

```python
# app/api/rest/users/routes.py — login_user
user = await db.scalar(select(UsersOrm).where(UsersOrm.username == user_in.username))
if not user:
    raise HTTPException(status_code=401, detail="user not found")
if not user_in.password or not verify_password(user_in.password, user.hashed_password):
    raise HTTPException(status_code=401, detail="password dont match")
# ← tới đây: AuthN password thành công. Chưa có session.
# Bước tiếp (Module 3–4): phát JWT + Set-Cookie.
```

**Nối tiếp:** Module 2 chỉ trả lời “password đúng”. Module 3–4 trả lời “giữ identity mà không hỏi password lại”.

**Tự kiểm M2:** Hai user cùng `SeedCoPass123!` — vì sao `hashed_password` trong DB khác nhau?

---

# Module 3 — JWT (credential ngắn hạn — nền của đoạn B)

## 3.1 JWT *là gì?*

**JSON Web Token** = chuỗi ba phần nối bằng dấu chấm:

```
header . payload . signature
```

1. **Header** — metadata thuật toán (vd HS256).
2. **Payload (claims)** — JSON. *Encode* base64, **không mã hóa**: ai cầm token đều đọc được claims. Vì vậy **không** nhét password / secret vào payload.
3. **Signature** — `HMAC(JWT_SECRET_KEY, header + "." + payload)`. Đổi 1 bit payload → chữ ký sai → server reject. Chứng minh: token do server phát, chưa bị sửa.

## 3.2 Vì sao cần JWT sau password?

Password chỉ kiểm một lần. JWT là giấy xác nhận tạm: “Server đã verify password (hoặc Google); người cầm giấy này là `user_id=42` đến lúc `exp`.”

## 3.3 Hai loại token trong project

```python
# app/api/rest/utils.py
def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode |= {"exp": expire, "sub": "access"}
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def create_refresh_token(data: dict) -> str:
    ...
    to_encode |= {"exp": expire, "sub": "refresh"}  # TTL dài hơn
```

Sau login, gọi với `{"user_id": user.id}` → payload thực tế:

```json
{ "user_id": 42, "sub": "access",  "exp": "<utc>" }
{ "user_id": 42, "sub": "refresh", "exp": "<utc dài hơn>" }
```

| Claim | Nghĩa **trong app này** |
|-------|-------------------------|
| `user_id` | Identity |
| `sub` | `"access"` hoặc `"refresh"` — **phân loại token**, không phải user id kiểu chuẩn OIDC |
| `exp` | Hết hạn. Sau `exp`, chữ ký còn đúng vẫn reject |

Config: `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_MINUTES` (`app/config.py`).

**Thiết kế quan trọng:** dùng refresh làm access → decode có thể OK nhưng `sub != "access"` → 401 `Invalid token` (xem Module 7).

## 3.4 Decode cứng vs mềm

```python
def encode_token(token: str) -> dict:
    # hết hạn → HTTP 403 "Token has expired"   ← FE dùng để refresh
    # sai chữ ký / hỏng → HTTP 401 "Invalid token"

def jwt_decode_soft(token: str) -> dict | None:
    # fail → None; không ném HTTP (guest / optional)
```

**Tên hàm `encode_token` trong repo thực ra là decode** — đọc code theo hành vi, đừng theo tên.

**Nối tiếp:** JWT chỉ là chuỗi. Module 4 giải thích *browser giữ và gửi chuỗi đó thế nào*.

**Tự kiểm M3:** Đưa refresh token vào cookie `access_token` → API hard-auth trả gì, vì sao?

---

# Module 4 — Cookie (cách đoạn B được vận chuyển)

## 4.1 Cookie *là gì?*

**Cookie** = mẩu dữ liệu browser lưu theo host/path/flags và **tự gắn** vào request phù hợp (`Cookie` header). Server set bằng `Set-Cookie`.

## 4.2 Vì sao không để JWT trong localStorage?

XSS (script độc trên trang) đọc được `localStorage` → đánh cắp access token → giả danh user.  
`HttpOnly` cookie → JavaScript **không** đọc được `document.cookie` cho auth token → giảm mặt tấn công đó.

## 4.3 Code set cookie auth

```python
# app/api/rest/security.py
def set_auth_cookie(response: Response, key: str, value: str) -> None:
    response.set_cookie(
        key=key,
        value=value,
        httponly=True,
        secure=cookie_secure(),  # True khi không DEV_MODE (HTTPS)
        samesite="lax",
        path="/",
        # không set domain → host-only
    )
```

| Flag | Nghĩa |
|------|--------|
| **HttpOnly** | JS không đọc — dùng cho `access_token`, `refresh_token` |
| **Secure** | Chỉ gửi qua HTTPS (prod) |
| **SameSite=Lax** | Hạn chế cookie đi theo cross-site POST cổ điển; vẫn gửi khi click link top-level GET |
| **Path=/** | Mọi path trên host |
| **(no Domain)** | Chỉ đúng hostname đã set |

`csrf_token` set bằng `set_csrf_cookie`: **HttpOnly=False** vì FE *phải* đọc để gắn header (Module 5).

## 4.4 FE phải xin phép gửi cookie

```javascript
// vuejs/src/main.js
axios.defaults.withCredentials = true
```

Không dòng này: login vẫn trả `Set-Cookie`, nhưng request `/me` sau **không** mang cookie → 401 mãi — trông như “login không được” dù password đúng.

## 4.5 JSON `access_token` trong body login

`login_user` vẫn `return {"access_token", "refresh_token"}`. Đó là legacy; **session thật là cookie HttpOnly**. FE hiện hydrate bằng `/me` + cookie, không dựa localStorage JWT.

**Nối tiếp:** Cookie tự gửi → rủi ro CSRF → Module 5.

**Tự kiểm M4:** FE có *cần* lưu JWT vào localStorage không? Vì sao?

---

# Module 5 — CSRF (bảo vệ mutate khi đã có cookie)

## 5.1 CSRF *là gì?*

**Cross-Site Request Forgery:** site độc hại khiến *browser của user đã login* tự gửi request thay đổi dữ liệu (POST/PATCH/…) tới API của bạn. Vì cookie **tự đi theo**, server có thể tưởng user cố ý.

SameSite=Lax giảm nhiều case, nhưng app vẫn thêm lớp **double-submit** cho chắc.

## 5.2 Double-submit *là gì?*

1. Server đặt cookie `csrf_token` ngẫu nhiên (**không** HttpOnly → JS đọc được).
2. FE copy giá trị đó vào header `X-CSRF-Token`.
3. Middleware so: cookie === header (`secrets.compare_digest`).

Attacker trên domain khác **không đọc được** cookie của `monitest.top` (same-origin policy) → không giả đúng header khớp cookie.

## 5.3 Khi nào middleware enforce?

```python
# app/middlewares.py (logic rút gọn)
STATE_CHANGING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
CSRF_EXEMPT_PATHS = {
    "/users/login",
    "/users/register",
    "/marketplace/webhooks/sepay",
}

# Nếu: method mutate
#  VÀ có cookie access_token
#  VÀ path không exempt
#  VÀ (thiếu cookie/header CSRF hoặc không khớp)
# → 403 "CSRF validation failed"
```

**Vì sao login/register exempt?** Lúc đó chưa có (hoặc chưa tin) session access — user đang *xin* session.  
**Vì sao SePay exempt?** Webhook máy-máy, auth bằng HMAC, không dùng cookie user.

## 5.4 FE gắn header

```javascript
// vuejs/src/main.js — request interceptor
if (['post', 'put', 'patch', 'delete'].includes(method)) {
  let csrfToken = readCookie('csrf_token')
  if (!csrfToken) {
    const response = await axios.get('/api/users/csrf', { withCredentials: true })
    csrfToken = response.data.csrf_token
  }
  config.headers['X-CSRF-Token'] = csrfToken
}
```

GET `/users/me` **không** cần CSRF (không phải mutate).

**Nối tiếp:** Đủ viên gạch A+B. Module 6 ráp thành một lần login thật từ form → Pinia.

**Tự kiểm M5:** GET `/users/me` có cần CSRF không? POST `/users/logout` có không?

---

# Module 6 — Luồng Login hoàn chỉnh (ráp đoạn A + B lần đầu)

Đây là module “nối ống”. Đọc chậm từng bước.

## 6.1 Toàn cảnh 11 bước

```
[1] User gõ username + password trên FE
[2] POST /users/login  (CSRF exempt)
[3] Server tìm user theo username
[4] verify_password → AuthN password
[5] create_access_token + create_refresh_token
[6] Set-Cookie: access, refresh (HttpOnly), csrf (readable)
[7] Response JSON vẫn trả 2 token (legacy)
[8] FE gọi GET /users/me  (browser tự gửi access cookie)
[9] get_current_user_id  (cổng AuthN ngắn hạn — Module 7)
[10] Build UserOut (+ account_kind, EmailStr)
[11] Pinia markAuthenticated (+ thường /me/roles)
```

- Bước **3–6** = AuthN server + phát session.  
- Bước **8–11** = **hydrate** UI. Thiếu bước này, cookie có thể đã có nhưng UI vẫn “chưa login”.

## 6.2 Server sau khi password đúng

```python
# users/routes.py
access_token = create_access_token({"user_id": user.id})
refresh_token = create_refresh_token({"user_id": user.id})
set_auth_cookie(response, "access_token", access_token)
set_auth_cookie(response, "refresh_token", refresh_token)
set_csrf_cookie(response)
return {"access_token": access_token, "refresh_token": refresh_token}
```

Tới đây server đã tin bạn là `user.id`. FE chưa chắc đã “thấy” session cho đến khi `/me` thành công.

## 6.3 FE hydrate

```javascript
// vuejs/src/App.vue
async function login(token) {
  resetSessionExpiredFlag()
  access_token.value = token   // biến FE; session thật vẫn là cookie
  await resolveSession()
}

async function resolveSession() {
  try {
    const { data } = await axios.get('/api/users/me', { withCredentials: true })
    userStore.setUserId(data.id)
    userStore.setUsername(data.username)
    userStore.markAuthenticated()
    ...
  } catch {
    userStore.clearAuth()
    // → UI coi như chưa login
  }
}
```

App boot cũng gọi `resolveSession()` — nếu cookie còn hạn, vào lại trang vẫn login.

## 6.4 `/me` phía server — chỗ dễ nhầm

`/me` **không** kiểm password. Nó:

1. AuthN bằng cookie JWT → `user_id`.
2. Load `UsersOrm`.
3. `_user_out`: gắn `account_kind` / `company_id`, validate thành `UserOut` (có `email: EmailStr`).

Nếu email trong DB là `jmco_05@seed.jobmarket.local`, Pydantic reject `.local` → **500**. Cookie JWT **vẫn còn**. FE `catch` → tưởng AuthN fail.

## 6.5 Bảng gỡ lỗi (thuộc lòng)

| Hiện tượng | Đoạn gãy |
|------------|----------|
| 401 `password dont match` | Module 2 — AuthN password |
| Login 200 nhưng `/me` 401 | Cookie không gửi (`withCredentials` / domain / Secure) |
| Login 200, `/me` 500, UI chưa login | AuthN OK — vỡ `UserOut` (email…) |
| UI tắt modal, không toast, chưa login | FE không surface lỗi login / `resolveSession` catch |

**Tự kiểm M6:** Đánh dấu bước nào trong 11 bước là AuthN thuần; bước nào chỉ hydrate UI.

---

# Module 7 — Cổng AuthN mỗi request (`dependencies.py`)

## 7.1 Vì sao cần dependency?

Sau login, mỗi API “cần đăng nhập” không tự đọc password. Chúng nhờ FastAPI **Depends** chạy cổng AuthN trước handler: thành công → inject `user_id`; fail → 401/403, không vào business logic.

## 7.2 Hard auth — từng điều kiện

```python
# app/api/rest/dependencies.py
async def get_token(request: Request):
    token = request.cookies.get("access_token", None)
    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return token

async def get_current_user_id(token: Annotated[str, Depends(get_token)]):
    if await is_token_revoked(token):
        raise HTTPException(status_code=401, detail="Token is revoked")
    data = encode_token(token)           # 403 nếu expired
    if data.get("sub") != "access":
        raise HTTPException(status_code=401, detail="Invalid token")
    return data["user_id"]

user_id = Annotated[int, Depends(get_current_user_id)]
```

Đọc như checklist:

1. Có cookie `access_token`?
2. Token có trong Redis denylist không? (Module 8)
3. Chữ ký + `exp` OK?
4. `sub == "access"`?
5. → trả `user_id` cho handler.

Handler viết `async def foo(user_id: user_id, ...)` là đang yêu cầu hard auth.

## 7.3 Soft auth — guest

```python
async def get_optional_user_id(request: Request) -> int | None:
    # thiếu / revoked / decode fail → None, không bao giờ 401
```

Dùng khi “có user thì personalize, không có thì vẫn trả nội dung”: home feed, một số đọc JM công khai, preview watermark.

## 7.4 Pipeline một request đã login (ráp Module 4+5+7+8)

```
Browser gửi Cookie
  → [nếu POST/PATCH/…] CSRF middleware          (M5)
  → get_token                                    (M7)
  → is_token_revoked                             (M8)
  → encode_token (chữ ký + exp)                  (M3)
  → sub == "access"
  → handler: roles / org / ownership             (M10–12)
```

**Tự kiểm M7:** `403 Token has expired` đến từ CSRF middleware hay từ `encode_token`?

---

# Module 8 — Refresh, Logout, Redis revoke

## 8.1 Vì sao hai token?

- **Access ngắn:** lộ (nếu lộ) thì cửa sổ lạm dụng nhỏ.
- **Refresh dài hơn:** chỉ endpoint refresh dùng; xin access mới mà không hỏi password.

## 8.2 Access hết hạn — FE nối lại

`encode_token` ném **403** `"Token has expired"`. Interceptor FE nhận diện → gọi refresh → retry request gốc một lần:

```javascript
// vuejs/src/api/sessionRefresh.js
function isExpiredTokenError(error) {
  return status === 403 && /token has expired/i.test(detail)
}
// refreshAccessToken() = GET /api/users/refresh_token với credentials
// rồi client(config) retry với _retry = true
```

```python
# users/routes.py — get_new_access_token
refresh_token = request.cookies.get("refresh_token", None)
if not refresh_token: 401
if await is_token_revoked(refresh_token): 401
data = encode_token(refresh_token)   # phải là JWT refresh còn hạn
access_token = create_access_token({"user_id": data["user_id"]})
set_auth_cookie(response, "access_token", access_token)
set_csrf_cookie(response)
```

Refresh cũng fail → `notifySessionExpired` → FE clear UI (session chết hẳn).

## 8.3 Revoke — JWT không tự “xóa” trên server

JWT **stateless**: server không giữ bảng session. Chỉ xóa cookie phía browser thì **bản copy** token (nếu ai đó giữ) vẫn dùng được đến `exp`.

**Denylist Redis:** lúc logout, ghi nguyên chuỗi token vào Redis với TTL ≈ thời gian còn lại. Mọi hard auth gọi `is_token_revoked` trước.

```python
# app/redis/redis_revoke_tokens.py
async def revoke_token(token: str, ex: int) -> None:
    await redis_connection.set(name=token, value="1", ex=ex * 60)

async def is_token_revoked(token: str) -> bool:
    return await redis_connection.exists(token) > 0
```

**Logout đầy đủ** = (1) Redis revoke access + refresh (2) clear 3 cookies (3) FE Pinia `clearAuth`.

Xóa cookie tay trên DevTools ≠ logout đầy đủ về mặt server.

**Tự kiểm M8:** Khác nhau giữa xóa cookie DevTools và `POST /users/logout`?

---

# Module 9 — Google OAuth & URL token (nhánh phụ đoạn A)

## 9.1 Google

Flow khác password nhưng **cùng điểm đến đoạn B**:

`users_google_auth/routes.py`: redirect Google → callback → tìm/tạo user theo `google_id` → `ensure_default_roles` → set **cùng** 3 cookies → redirect FE.

User có `google_id` thì password-reset bị chặn (không có / không dùng password thường).

## 9.2 itsdangerous URL token (verify email / reset password)

**Không phải** JWT session cookie. Đây là link một lần / có hạn trong email:

- `create_url_safe_token` / `decode_url_safe_token` trong `utils.py`
- Ký bằng `URLSafeTimedSerializer`, kiểm `max_age`
- Dùng cho `GET /users/verify/{token}`, password-reset confirm

Khác JWT: không gắn mọi API; chỉ chứng minh “người bấm link đúng hộp thư / đúng yêu cầu reset”.

**Tự kiểm M9:** Vì sao verify-email không đơn giản set `access_token` cookie luôn?

---

# Module 10 — AuthZ lớp 1: RBAC (`user_roles`)

Từ đây sang đoạn **C**. Giả định AuthN đã cho `user_id`.

## 10.1 RBAC *là gì?*

**Role-Based Access Control:** gắn quyền theo *vai trò*, không gắn từng API cho từng user một. User có tập roles; API/helper kiểm “có role X không?”.

## 10.2 Schema

```python
# models.py
class UserRolesOrm(Base):
    __tablename__ = "user_roles"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role: Mapped[str] = mapped_column(String(50), primary_key=True)
```

```python
# roles.py
VALID_ROLES = frozenset({"admin", "artist", "employer", "seller"})
DEFAULT_ROLE = "artist"
```

PK kép `(user_id, role)` → **một user nhiều role** (vd artist + seller).

Register / Google → `ensure_default_roles` → luôn có `artist`.

## 10.3 `require_roles` — Depends AuthZ

```python
# dependencies.py
def require_roles(*required: str):
    async def _checker(current_user_id: ..., db: ...) -> int:
        roles = await get_user_roles(db, current_user_id)
        if not required_set.issubset(roles):
            raise HTTPException(status_code=403, detail="HTTP_403_FORBIDDEN")
        return current_user_id
    return _checker
```

**Trong codebase thực tế:** gần như chỉ `require_roles("admin")` (admin REST, JM admin).  
`employer` / `seller` **không** đi qua Depends này — check trong helper, KYC approve, `enable-selling`, ownership.

## 10.4 Cách có từng role

| Role | Cách có trong product |
|------|------------------------|
| `artist` | Mặc định register/Google |
| `admin` | Bootstrap / admin gán |
| `employer` | Admin duyệt hiring KYC (hoặc seed jmco) |
| `seller` | `POST /marketplace/me/enable-selling` sau khi đủ eligibility |

FE: `GET /users/me/roles`.

**Tự kiểm M10:** Có role `employer` có *đồng nghĩa* `account_kind=organization` không?

---

# Module 11 — AuthZ lớp 2: account_kind (personal vs organization)

## 11.1 Vì sao cần lớp này?

Role `employer` một mình chưa đủ mô tả “đang đứng trên tư cách công ty”. Soft-live: tài khoản org **không** được làm một số việc cá nhân (tạo pin, apply job, sell/buy marketplace).

## 11.2 Công thức (không có cột role tên organization)

```python
# job_market/helpers.py — resolve_account_kind
# organization ⇔
#   "employer" ∈ user_roles
#   ∧ ∃ companies row: owner_user_id = me
#                   ∧ status ∈ (active, suspended)
# ngược lại → personal, company_id = None
```

Kết quả gắn vào `/me` qua `_user_out` → `UserOut.account_kind` + `company_id`.

User chỉ được gán `employer` nhưng **chưa** có company active → vẫn `personal`.

## 11.3 Soft-live gates (`role_gates.py`)

```text
assert_not_organization     → chặn org khỏi một số surface
assert_can_apply_to_job     → chặn org + admin
assert_can_manage_cv        → chặn org
assert_can_submit_hiring_kyc
assert_can_sell_on_marketplace → chặn admin + org
assert_can_buy_license         → chặn admin + org
assert_can_create_pin          → chặn org
```

**Ý sản phẩm:** company account và creator/buyer cá nhân tách surface trên cùng app.

**Tự kiểm M11:** Chỉ có `employer`, chưa có company — `account_kind`?

---

# Module 12 — AuthZ lớp 3: ownership & domain

## 12.1 Pattern chung

Đã có `user_id` từ JWT → load resource theo id → so field sở hữu → 403 (hoặc 404 để không lộ sự tồn tại).

```python
# ownership.py
async def assert_pin_owner(db, pin_id, user_id) -> PinsOrm:
    pin = await db.scalar(select(PinsOrm).where(PinsOrm.id == pin_id))
    if pin is None:
        raise HTTPException(404, detail="pin not found")
    if pin.user_id != user_id:
        raise HTTPException(403, detail="not pin owner")
    return pin
```

Cùng file / cùng ý: board owner, comment author, company owner, job post company owner, CV owner, KYC request owner, work experience owner…

## 12.2 Marketplace (thêm eligibility)

- **Sell:** không admin/org + đủ ngưỡng N/M/K/P + role `seller` + listing `seller_user_id == me`.
- **Buy:** không admin/org + order `buyer_user_id == me`.
- **SePay webhook:** không JWT user — **HMAC** (machine auth, CSRF exempt). Đây là AuthZ/AuthN kiểu máy, không phải đoạn A/B user.

## 12.3 Ví dụ nối đủ lớp — employer sửa JD

```
1. Cookie access → user_id                         (AuthN — M7)
2. "employer" ∈ roles                              (RBAC — M10)
3. company.owner_user_id == user_id                (ownership — M12)
4. Thường kèm account_kind == organization         (M11)
→ cho mutate JD; thiếu mắt xích → 403
   (hiring_rights_required / not company owner / …)
```

**Tự kiểm M12:** Admin qua `require_roles("admin")` — admin có được bán trên marketplace không?

---

# Module 13 — Ghép toàn hệ (cheatsheet)

## 13.1 Một hình duy nhất

```
┌─ A: LÂU DÀI (hiếm) ─────────────────────────────────────┐
│  password / Google  →  verify / upsert  →  phát JWT     │
└────────────────────────────┬────────────────────────────┘
                             │ một lần
                             ▼
┌─ B: NGẮN HẠN (mọi request) ─────────────────────────────┐
│  cookie access JWT → CSRF? → revoke? → decode → user_id │
│       ├─ hết hạn → refresh cookie → access mới          │
│       └─ logout  → Redis revoke + xóa cookie            │
└────────────────────────────┬────────────────────────────┘
                             │ đã có user_id
                             ▼
┌─ C: AUTHZ ──────────────────────────────────────────────┐
│  roles → account_kind (org?) → ownership / eligibility  │
│  (+ webhook HMAC không đi ống user)                     │
└─────────────────────────────────────────────────────────┘
```

`/me` nằm ngay sau B: đã có `user_id`, load profile cho FE. Không kiểm password; **có thể** 500 vì validate email — JWT vẫn còn.

## 13.2 HTTP status trong ngữ cảnh auth

| Code | Nghĩa |
|------|--------|
| **401** | Chưa chứng minh identity: sai pass, thiếu cookie, revoked, invalid token |
| **403** | Access hết hạn (FE refresh) **hoặc** CSRF fail **hoặc** thiếu quyền AuthZ |
| **404** | Đôi khi che “có resource nhưng không phải của bạn” |
| **500** | Bug sau AuthN (serialize `UserOut`, DB…) — **không** có nghĩa chưa login |

## 13.3 Case jmco bằng đúng thuật ngữ khóa học

1. **M2:** hash trong DB không khớp `SeedCoPass123!` → AuthN password 401.  
2. Reset hash → login 200, Set-Cookie → đoạn A+B server OK.  
3. **M6 bước 10:** `EmailStr` reject `@…local` → `/me` 500.  
4. **M6 bước 11:** `resolveSession` catch → `clearAuth` — UI chưa login dù JWT có thể đã set.  
5. **Không** kết luận “JWT bị xóa” từ 401 `/me` của lần login fail trước đó.

## 13.4 Bốn câu thuộc lòng

1. Password chứng minh identity lần đầu; JWT trong cookie chứng minh các lần sau.  
2. HttpOnly giữ JWT; csrf readable + header chống giả mutate.  
3. `get_current_user_id` = cổng AuthN; roles / org / ownership = AuthZ.  
4. Login 401 = AuthN; `/me` 500 = AuthN đã qua, vỡ profile.

---

# Đáp án tự kiểm

| # | Đáp |
|---|-----|
| M1 | Không. Login chỉ username + password; email là hồ sơ / verify. |
| M2 | Mỗi lần bcrypt hash kèm salt ngẫu nhiên khác nhau. |
| M3 | 401 Invalid token vì `sub != "access"` (sau khi decode). |
| M4 | Không cần localStorage; session thật là HttpOnly cookie. |
| M5 | GET `/me`: không. POST logout: có (đã có access + mutate). |
| M6 | AuthN thuần ≈ bước 3–6; hydrate UI ≈ 8–11. |
| M7 | Từ `encode_token` trong utils — không phải CSRF middleware. |
| M8 | Logout ghi Redis denylist; xóa cookie tay thì bản copy token vẫn dùng đến exp. |
| M9 | Verify email là one-shot signed URL, không phải session API liên tục. |
| M10 | Không — cần thêm owned company active/suspended. |
| M11 | `personal`. |
| M12 | Không — `assert_not_admin` / `admin_cannot_sell`. |

---

# Lộ trình 5 ngày

| Ngày | Module | Việc cụ thể |
|------|--------|-------------|
| 1 | 0–2 | Đọc bản đồ; mở `UsersOrm` + `utils.hash/verify` + đoạn `login_user` verify |
| 2 | 3–5 | Mở `create_*_token`, `security.py`, `middlewares.py`, `main.js` credentials+CSRF |
| 3 | 6–8 | Đi breakpoint login → `/me` → `resolveSession`; đọc refresh interceptor + revoke |
| 4 | 9–11 | Google routes skim; `roles.py` + `resolve_account_kind` + `role_gates.py` |
| 5 | 12–13 | `ownership.py` + một route JM/marketplace; kể lại case jmco không nhìn file |

**Điều kiện tốt nghiệp:** đóng file này, vẽ ống A→B→C trên giấy, rồi mở một route (vd xóa pin / sửa JD / enable-selling) và viết 5–8 dòng: AuthN đi qua đâu, AuthZ check những gì, fail ra status nào.
