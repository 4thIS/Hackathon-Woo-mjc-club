# API 명세 — MJC Club Archive

**이 문서가 계약이다.** 백엔드는 여기 적힌 형태로 만들고, 프론트는 백엔드가 없어도 여기만 보고 mock으로 개발한다.
바꾸려면 PR 전에 PM(@ssenu)과 합의하고 PR 제목에 `[계약]`을 붙인다. (`CLAUDE.md` §계약)

기획: [`specs/2026-08-06-동아리웹-기획서.md`](specs/2026-08-06-동아리웹-기획서.md) · 구현계획: [`plans/2026-08-06-구현계획.md`](plans/2026-08-06-구현계획.md)

---

## 0. 공통 규약

| 항목 | 값 |
|---|---|
| Base URL | `/api` (Vite dev proxy → `http://localhost:8000`) |
| 형식 | 요청·응답 모두 JSON. 파일 업로드만 `multipart/form-data` |
| 필드명 | `snake_case` |
| 날짜 | `YYYY-MM-DD` / 일시는 ISO 8601 UTC (`2026-08-06T09:12:33Z`) |
| 인증 | httpOnly 세션 쿠키 `session`. 모든 요청 `credentials: "include"` |
| CORS | `http://localhost:5173` 허용, `allow_credentials=True` |

### 0.1 에러 응답

**모든** 4xx·5xx는 이 형태 하나다. 프론트는 `code`로 분기하고 `message`를 그대로 사용자에게 보여준다.

```json
{ "detail": { "code": "CLUB_NOT_RECRUITING", "message": "현재 모집중이 아닙니다." } }
```

| 상태 | 언제 | 대표 code |
|---|---|---|
| 400 | 값이 잘못됨 | `INVALID_INPUT` |
| 401 | 로그인 안 됨 | `UNAUTHORIZED` |
| 403 | 권한 없음 | `FORBIDDEN`, `EMAIL_NOT_VERIFIED`, `OB_NOT_ALLOWED` |
| 404 | 없음 | `NOT_FOUND` |
| 409 | 상태 충돌 | `DUPLICATE_STUDENT_ID`, `ALREADY_REQUESTED`, `LEADER_CANNOT_GRADUATE` |
| 422 | 처리 불가 | `MEMO_REQUIRED`, `PDF_UNREADABLE` |
| 502 | 외부 실패 | `AI_GATEWAY_ERROR` |

> 프론트 규칙: `code`를 모르면 `message`만 띄운다. 화면 분기가 필요한 code는 각 절에 명시했다.

### 0.2 열거값 (문자열 그대로 주고받는다)

```
category         학술·전공 | 공연·예술 | 체육 | 봉사 | 취미·교양 | 종교
recruit_status   모집중 | 모집마감 | 상시모집
club_status      활동중 | 보관
academic_status  재학 | 휴학 | 졸업
role             동아리장 | 부원
membership       활동중 | OB
request_status   심사중 | 승인 | 거절 | 취소
gender           남 | 여
```

### 0.3 권한 레벨 표기

각 엔드포인트에 붙는 표기다. 기획서 §3.2 권한표와 1:1로 대응한다.

| 표기 | 의미 |
|---|---|
| `공개` | 비로그인 포함 누구나 |
| `인증` | 로그인 + 이메일 인증 완료 |
| `부원` | 해당 동아리의 활동중 멤버 |
| `소속` | 해당 동아리의 부원 · OB · 동아리장 |
| `장` | 해당 동아리의 동아리장 |
| `관리자` | `is_admin` |

미인증 계정은 비로그인과 동일 권한이다(기획서 §3.2). `인증` 이상이 필요한 곳에서 미인증이면 **403 `EMAIL_NOT_VERIFIED`**.

### 0.4 공통 객체

```jsonc
// ClubSummary — 목록·카드용
{
  "id": 3,
  "name": "필름사진동아리 그늘",
  "category": "취미·교양",
  "recruit_status": "모집중",
  "image": "/uploads/clubs/3.jpg",   // null이면 프론트가 카테고리 그라데이션으로 대체
  "member_count": 38                  // 활동중 + OB (PM 결정, §9 미정1)
}

// UserBrief
{ "id": "26011234", "name": "박찬우", "dept": "컴퓨터공학과" }

// PostSummary — 캐러셀·타임라인·목록용
{
  "id": 91,
  "club_id": 3,
  "club_name": "필름사진동아리 그늘",
  "category": "취미·교양",                     // 사진 없는 카드의 분야 그라데이션용
  "title": "성북동 출사, 필름 두 롤",
  "excerpt": "10월 12일 성북동 일대에서…",   // 본문 앞 120자
  "photo": "/uploads/posts/91-0.jpg",        // 대표 1장, 없으면 null
  "activity_date": "2025-10-12",
  "tags": ["출사", "필름"],
  "is_public": true,
  "like_count": 7,
  "liked_by_me": false                        // 비로그인이면 항상 false
}
```

---

## 1. 헬스체크

### `GET /api/health` — `공개`

```json
{ "status": "ok" }
```

---

## 2. 인증·계정 (T1 · wj)

### `POST /api/auth/signup` — `공개`

```jsonc
// 요청
{
  "email": "26011234@mjc.ac.kr",   // @mjc.ac.kr 또는 @on.mjc.ac.kr 만 허용
  "password": "……",                 // 8자 이상
  "student_id": "2022261026",      // 숫자 10자리 고정. 이메일 로컬파트와 일치해야 한다
  "name": "박찬우",
  "dept": "컴퓨터공학과",
  "birth": "2006-03-11",
  "gender": "남",
  "grade": 1                       // 1~4. 생략하거나 null 이면 미입력
}
```

`201` → `{ "student_id": "2022261026", "email_sent": true }`

`email_sent: false`면 SMTP가 죽은 것이다. 서버는 죽지 않고 **콘솔에 인증 링크를 출력**한다(백엔드 규칙). 프론트는 "인증 메일 발송에 실패했습니다. 운영자에게 문의하세요" 안내를 띄운다.

| 에러 | code |
|---|---|
| 400 | `INVALID_EMAIL_DOMAIN` · `INVALID_STUDENT_ID`(숫자 10자리 아님) · `EMAIL_ID_MISMATCH` · `WEAK_PASSWORD` |
| 409 | `DUPLICATE_STUDENT_ID` (도메인이 달라도 학번이 같으면 막는다 · 기획서 §4.1) · `DUPLICATE_EMAIL` |

### `POST /api/auth/login` — `공개`

`{ "email": "...", "password": "..." }` → `200` + `Set-Cookie: session=…; HttpOnly; SameSite=Lax`

응답 본문은 아래 `Me` 객체와 동일하다.

| 에러 | code |
|---|---|
| 401 | `INVALID_CREDENTIALS` |

미인증 계정도 **로그인은 성공한다.** `Me.email_verified: false`로 내려가고, 프론트는 "인증 메일을 확인해주세요 / 다시 보내기" 배너를 띄운다(기획서 §4.2).

### `POST /api/auth/logout` — `공개`

`204`. 쿠키 만료.

### `GET /api/auth/verify?token=…` — `공개`

이메일 링크가 직접 여는 주소다. JSON이 아니라 **302 리다이렉트**로 응답한다.

```
302 → {FRONTEND_URL}/verify?status=ok | expired | invalid
```

### `POST /api/auth/verify/resend` — `공개`

`{ "email": "..." }` → `204`. 존재 여부를 노출하지 않기 위해 없는 이메일이어도 `204`.

### `GET /api/me` — `로그인`

```jsonc
// Me
{
  "id": "26011234",
  "email": "26011234@mjc.ac.kr",
  "name": "박찬우",
  "dept": "컴퓨터공학과",
  "birth": "2006-03-11",
  "gender": "남",
  "grade": 1,                       // 본인이 고른 값. 미입력이면 null (§9-6)
  "academic_status": "재학",
  "email_verified": true,
  "is_admin": false,
  "ai_key": { "registered": true, "masked": "****a91f" }   // 미등록이면 {"registered": false, "masked": null}
}
```

비로그인이면 `401 UNAUTHORIZED`. 프론트는 앱 부팅 시 1회 호출해 로그인 상태를 판별한다.

### `PATCH /api/me` — `로그인`

```jsonc
{ "password": "새 비밀번호", "dept": "전자공학과", "academic_status": "졸업", "grade": 3 }  // 전부 optional
```

`200` → `Me`

이름·학번·생년월일·성별·이메일은 **받지 않는다.** 보내면 무시한다(기획서 §4.3).

`grade` 는 **보냈는지 여부**로 판단한다. 안 보내면 그대로 두고, `null` 을 명시적으로 보내면 비운다. 1~4 밖의 값은 400 `INVALID_INPUT`.

| 에러 | code | 설명 |
|---|---|---|
| 409 | `LEADER_CANNOT_GRADUATE` | 동아리장을 맡은 동아리가 있으면 졸업 전환 불가. `message`에 해당 동아리명을 담는다 |

`academic_status`가 `졸업`이 되면 서버가 모든 `club_members.membership`을 `OB`로 바꾼다.

### `GET /api/me/clubs` — `로그인`

```json
[
  { "club": { "id": 3, "name": "필름사진동아리 그늘", "category": "취미·교양", "recruit_status": "모집중", "image": null, "member_count": 38 },
    "role": "동아리장", "membership": "활동중", "gen": 12 }
]
```

### `GET /api/me/requests` — `로그인`

내 신청 현황. 세 종류를 한 번에 준다(기획서 §4.4).

```json
{
  "join":   [ { "id": 12, "club_id": 3, "club_name": "그늘", "status": "심사중", "created_at": "2026-08-05T02:00:00Z", "cancellable": true } ],
  "create": [ { "id": 4,  "name": "보드게임연구회", "status": "거절", "reject_reason": "유사 동아리가 이미 있습니다", "created_at": "…", "cancellable": false } ],
  "leave":  [ { "id": 7,  "club_id": 5, "club_name": "축구부", "status": "심사중", "created_at": "…", "auto_approve_at": "2026-08-12T02:00:00Z", "cancellable": true } ]
}
```

### `POST /api/me/ai-key` — `인증`

```json
{ "api_key": "sk-…" }
```

저장 **전에** 게이트웨이 모델 목록 조회로 유효성을 확인한다(기획서 §4.5). 통과하면 Fernet 암호화 저장.

`200` → `{ "registered": true, "masked": "****a91f" }`

| 에러 | code |
|---|---|
| 400 | `INVALID_AI_KEY` — 게이트웨이가 키를 거부함 |
| 502 | `AI_GATEWAY_ERROR` — 게이트웨이 자체가 응답 없음 (키 문제 아님) |

### `DELETE /api/me/ai-key` — `인증`

`204`. 저장된 키는 **어떤 경로로도 다시 읽을 수 없다.**

### `DELETE /api/me` — `로그인` (회원 탈퇴)

```json
{ "password": "현재 비밀번호" }
```

되돌릴 수 없으므로 비밀번호를 다시 확인한다. `204` + 세션 쿠키 만료.

**함께 지우는 것**: 동아리 소속 · 가입 신청 · 탈퇴 요청 · 개설 신청 · 좋아요 · 인증 토큰

**남기는 것**: **활동 글.** 기록은 동아리의 자산이지 개인 소유가 아니다. `author_id`만 비우고 화면에는 `탈퇴한 회원`으로 표시한다.

학번을 지우므로 **같은 학번으로 다시 가입할 수 있다.** 실제 재학생이 계정을 다시 만들 수 있어야 하기 때문이다.

| 에러 | code | 설명 |
|---|---|---|
| 403 | `INVALID_PASSWORD` | 비밀번호 불일치 |
| 409 | `LEADER_CANNOT_LEAVE` | 동아리장인 동아리가 있으면 탈퇴 불가. 먼저 위임한다 (기획서 §5.5) |
| 409 | `LAST_ADMIN` | 마지막 관리자는 탈퇴할 수 없다 |

---

## 3. 동아리 탐색 (T2 · cw)

### `GET /api/clubs` — `공개`

아카이브 화면은 실시간 검색을 하므로 **필터 없이 전체를 한 번에** 받는 것이 기본이다. 쿼리는 전부 optional.

| 쿼리 | 값 |
|---|---|
| `category` | 카테고리 1개 |
| `recruit` | `모집중` \| `모집마감` \| `상시모집` |
| `q` | 이름 부분일치 |

```json
{ "items": [ /* ClubSummary[] */ ], "total": 42 }
```

`status`가 `보관`인 동아리는 목록에서 제외한다(직접 URL 접근은 열람 가능).

### `GET /api/clubs/{club_id}` — `공개`

```jsonc
{
  "id": 3,
  "name": "필름사진동아리 그늘",
  "category": "취미·교양",
  "founded_year": 2014,
  "purpose": "필름 카메라로 …",       // 줄바꿈 포함 원문. 프론트가 문단 분리
  "advisor": "김지훈",
  "image": null,
  "meet_day": "수요일", "meet_time": "18:00", "meet_place": "학생회관 302",
  "recruit_status": "모집중",
  "current_gen": 12,
  "status": "활동중",
  "leader": { "id": "24010001", "name": "이우진", "dept": "시각디자인과" },
  "counts": { "active": 26, "ob": 12, "total": 38 },
  "has_join_form": true,
  "my": {                              // 비로그인이면 null
    "is_member": false,
    "role": null, "membership": null, "gen": null,
    "join_request_status": null,       // "심사중" | "거절" | null
    "can_apply": true                  // false면 가입 버튼 비활성 (OB·이미 부원·미인증·심사중)
  }
}
```

### `GET /api/clubs/{club_id}/posts` — `공개`

타임라인 배치 로드용. **오래된 순**(기획서 시안: 타임라인은 과거→현재).

| 쿼리 | 기본 | 설명 |
|---|---|---|
| `offset` | 0 | |
| `limit` | 5 | 최대 20 |

```json
{ "items": [ /* PostSummary[] */ ], "total": 23, "has_more": true, "first_year": 2019 }
```

- 비로그인·미소속: 공개 글만. `total`도 공개 글 기준이다.
- 소속·관리자: 비공개 글 포함. 각 항목의 `is_public`으로 구분해 배지를 붙인다.
- `first_year`는 타임라인 끝 표지(`YYYY년부터 N건`)에 쓴다.

### `GET /api/clubs/{club_id}/members` — `공개`

인원 모달용. 기수별 그룹, 최신 기수 → 오래된 기수 → OB 순.

```jsonc
{
  "total": 38,
  "groups": [
    { "gen": 12, "label": "12기", "count": 6,
      "members": [ { "id": "26011234", "name": "박찬우", "dept": "컴퓨터공학과", "role": "동아리장" } ] },
    { "gen": null, "label": "OB", "count": 12, "members": [] }
  ]
}
```

**비로그인·미인증에는 `members`를 빈 배열로 내리고 `count`만 준다.** (PM 결정, §9 미정2 — 기획서 §9 최소 노출 원칙)
프론트는 `members`가 비면 "로그인하면 부원 목록을 볼 수 있어요"를 그 자리에 표시한다.

### `GET /api/posts/highlights` — `공개`

메인 곡선 캐러셀용.

| 쿼리 | 기본 |
|---|---|
| `limit` | 12 (최대 20) |

**선정 기준: 공개 글 중 최신순, 동아리당 최대 1건.** (PM 결정, §9 미정4 — 한 동아리가 캐러셀을 독점하면 "여러 동아리가 살아있다"는 메시지가 죽는다)

`PostSummary[]` — 캐러셀 카드는 `photo` + `title` + 호 라벨의 `club_name`만 쓴다.

### `GET /api/posts/{post_id}` — `공개` (비공개 글은 `소속`)

```jsonc
{
  "id": 91,
  "club_id": 3, "club_name": "필름사진동아리 그늘",
  "author": { "id": "24010001", "name": "이우진", "dept": "시각디자인과" },
  "title": "성북동 출사, 필름 두 롤",
  "body": "…",                        // 줄바꿈 포함 평문 (마크다운 아님)
  "photos": ["/uploads/posts/91-0.jpg", "/uploads/posts/91-1.jpg"],
  "activity_date": "2025-10-12",
  "tags": ["출사", "필름"],
  "is_public": true,
  "like_count": 7, "liked_by_me": false,
  "created_at": "2025-10-13T11:20:00Z",
  "can_edit": false
}
```

비공개 글을 권한 없이 요청하면 존재를 숨기기 위해 **403이 아니라 404 `NOT_FOUND`**를 준다.

### `GET /api/stats` — `공개`

메인 브랜드 섹션 지표 4개.

```json
{ "clubs": 42, "recruiting": 17, "posts": 268, "categories": 5 }
```

---

## 4. 가입·탈퇴·부원 (T3/T4 · th)

### `GET /api/clubs/{club_id}/join-form` — `공개`

```jsonc
{ "required": true,
  "fields": [ { "key": "motive", "label": "지원 동기", "type": "text", "required": true } ] }
```

폼이 없으면 `{ "required": false, "fields": [] }`. **404를 쓰지 않는다** — 프론트 분기를 줄이기 위해서다.

`type`은 `text`(한 줄) · `textarea`(여러 줄) 두 가지만. (구현계획 T3 컷라인)

### `PUT /api/clubs/{club_id}/join-form` — `장`

위 객체를 그대로 보낸다. `200` → 저장된 객체.

### `POST /api/clubs/{club_id}/join-requests` — `인증`

```json
{ "answers": { "motive": "필름 카메라를 배우고 싶습니다" } }
```

`201` → `{ "id": 12, "status": "심사중" }`

| 에러 | code | 프론트 처리 |
|---|---|---|
| 403 | `OB_NOT_ALLOWED` | OB는 신규 가입 불가 (기획서 §3.2) |
| 409 | `ALREADY_MEMBER` | |
| 409 | `ALREADY_REQUESTED` | 심사중 신청이 이미 있음 |
| 409 | `CLUB_NOT_RECRUITING` | **모집 아님 모달**(디자인 §5.3 모달2)을 띄운다 |
| 400 | `FORM_REQUIRED` | 필수 폼 미작성 |

거절된 뒤에는 다시 신청할 수 있다(기획서 §5.3).

### `GET /api/clubs/{club_id}/join-requests` — `장`

**이름 · 학과 · 학년만 내려간다.** 학번 전체·성별·생년월일은 응답에 넣지 않는다(기획서 §5.3 · §9).

```json
[ { "id": 12, "name": "박찬우", "dept": "컴퓨터공학과", "grade": 1,   // 미입력이면 null
    "answers": { "motive": "…" }, "created_at": "…", "status": "심사중" } ]
```

### `POST /api/join-requests/{id}/approve` — `장`

`200` → `{ "status": "승인", "gen": 12 }` — 동아리의 `current_gen`이 자동 부여된다(기획서 §5.3.1). 결과 메일 발송.

### `POST /api/join-requests/{id}/reject` — `장`

`{ "reason": "…" }` (optional) → `200` `{ "status": "거절" }`

### `DELETE /api/join-requests/{id}` — `본인`

심사중일 때만. `200` → `{ "status": "취소" }`

### `POST /api/clubs/{club_id}/leave-requests` — `부원`

`201` → `{ "id": 7, "status": "심사중", "auto_approve_at": "2026-08-13T…" }`

동아리장 본인은 `403 LEADER_MUST_TRANSFER` (기획서 §5.4).

### `GET /api/clubs/{club_id}/leave-requests` — `장`

이 엔드포인트를 호출할 때 **서버가 7일 지난 건을 먼저 자동 승인 처리한다.** 스케줄러 없음(구현계획 §2).

### `POST /api/leave-requests/{id}/approve` — `장`

`200` → `{ "status": "승인" }`

### `GET /api/clubs/{club_id}/members/manage` — `장`

부원 관리 화면용. 공개 `/members`와 달리 학년과 신청일이 포함된다.

```json
[ { "user": { "id": "26011234", "name": "박찬우", "dept": "컴퓨터공학과" },
    "role": "부원", "membership": "활동중", "gen": 12 } ]
```

### `PATCH /api/clubs/{club_id}/members/{user_id}` — `장`

`{ "gen": 11 }` → `200`. 기수만 바꾼다. 부원 본인은 호출할 수 없다(기획서 §5.3.1).

### `PATCH /api/clubs/{club_id}` — `장`

```jsonc
{ "purpose": "…", "image": "/uploads/clubs/3.jpg",
  "meet_day": "수요일", "meet_time": "18:00", "meet_place": "학생회관 302",
  "recruit_status": "모집중", "current_gen": 13 }   // 전부 optional
```

이름·카테고리·창립년도·지도교수는 개설 신청 시 확정되며 여기서 바꾸지 않는다(기획서 §5.1).

### `POST /api/clubs/{club_id}/transfer` — `장`

`{ "user_id": "24010001" }` → `200`. 대상은 **활동중인 부원**이어야 한다. 위임하면 본인은 `부원`이 된다.

| 에러 | code |
|---|---|
| 400 | `TARGET_NOT_ACTIVE_MEMBER` |

---

## 5. 동아리 개설·관리자 (T4 · th)

### `POST /api/club-applications` — `인증`

```json
{ "name": "보드게임연구회", "category": "취미·교양", "founded_year": 2026,
  "purpose": "…", "advisor": "김지훈" }
```

`201` → `{ "id": 4, "status": "심사중" }`. OB는 `403 OB_NOT_ALLOWED`.

### `DELETE /api/club-applications/{id}` — `본인`

심사중일 때만 취소.

### `GET /api/admin/club-applications` — `관리자`

`?status=심사중` (기본 전체)

```json
[ { "id": 4, "name": "보드게임연구회", "category": "취미·교양", "founded_year": 2026,
    "purpose": "…", "advisor": "김지훈",
    "applicant": { "id": "26011234", "name": "박찬우", "dept": "컴퓨터공학과" },
    "status": "심사중", "created_at": "…" } ]
```

### `POST /api/admin/club-applications/{id}/approve` — `관리자`

`200` → `{ "status": "승인", "club_id": 44 }` — 동아리가 생성되고 **신청자가 동아리장 1기**가 된다.

### `POST /api/admin/club-applications/{id}/reject` — `관리자`

`{ "reason": "유사 동아리가 이미 있습니다" }` — **`reason`은 필수**다. 사유와 함께 메일로 통보한다(기획서 §5.2).

### `PATCH /api/admin/clubs/{club_id}` — `관리자`

```jsonc
{ "status": "보관", "leader_id": "24010001" }   // 둘 다 optional
```

`leader_id`는 동아리장 강제 교체(기획서 §5.5). 대상은 해당 동아리 부원이어야 한다.

### `GET /api/admin/clubs` — `관리자`

공개 목록(`GET /clubs`)은 **활동중만** 준다. 관리자는 보관된 동아리도 봐야 하므로 별도다.

```
?q=필름           이름·분야 부분 일치
&status=보관       운영 상태 (활동중 | 보관)
&category=체육
```

```jsonc
{ "total": 8, "items": [
  { "id": 1, "name": "필름사진동아리 그늘", "category": "취미·교양",
    "recruit_status": "모집중", "status": "활동중", "current_gen": 12,
    "member_count": 4, "post_count": 3,
    "leader": { "id": "24010001", "name": "이우진", "dept": "시각디자인과" } }
] }
```

`leader`는 동아리장이 없으면 `null`이다 — 관리자가 강제 교체해야 할 대상이다 (기획서 §5.5).

### `GET /api/admin/users` — `관리자`

```
?q=박찬우          이름·학번·학과·이메일 부분 일치
&status=재학       학적 상태
&admin=true        관리자만
```

```jsonc
{ "total": 7, "items": [
  { "id": "24010001", "email": "24010001@mjc.ac.kr", "name": "이우진",
    "dept": "시각디자인과", "birth": "2005-03-11", "gender": "남", "grade": 3,
    "academic_status": "재학", "email_verified": true, "is_admin": false,
    "clubs": [ { "id": 1, "name": "필름사진동아리 그늘", "role": "동아리장", "membership": "활동중" } ] }
] }
```

`clubs`를 함께 주는 이유: 학적을 졸업으로 바꾸려 할 때 동아리장인지 화면에서 미리 보여주기 위해서다.

### `PATCH /api/admin/users/{user_id}` — `관리자`

```jsonc
// 전부 optional. 보낸 것만 바뀐다
{ "name": "이우진", "dept": "컴퓨터공학과", "birth": "2005-03-11", "gender": "남",
  "email": "24010001@on.mjc.ac.kr", "academic_status": "졸업",
  "email_verified": true, "is_admin": false }
```

기획서 §4.3이 잠긴 필드에 대해 "변경이 필요하면 관리자 문의"라고 안내하므로, **관리자는 이름·생년월일·성별·이메일까지 고칠 수 있다.** 학번(`id`)만은 PK라 바꿀 수 없다.

`200` → 위 `GET`의 항목과 같은 형태

| 에러 | code | 설명 |
|---|---|---|
| 400 | `INVALID_EMAIL_DOMAIN` · `EMAIL_ID_MISMATCH` | 가입과 같은 규칙 |
| 400 | `INVALID_INPUT` | 학적·성별 값이 열거값이 아님 |
| 409 | `DUPLICATE_EMAIL` | 다른 사람이 쓰는 이메일 |
| 409 | `LEADER_CANNOT_GRADUATE` | 동아리장인 동아리가 있으면 졸업 불가. 관리자도 같다 — 먼저 위임하거나 강제 교체한다 |
| 409 | `LAST_ADMIN` | 마지막 관리자의 권한은 뺏을 수 없다. 자기 자신도 마찬가지 |

**유저 삭제는 없다.** 활동 글·멤버십·신청 이력이 딸려 있어 되돌릴 수 없다. 필요하면 DB에서 직접 처리한다.

---

## 6. 활동 글 (T5 · cw)

### `POST /api/uploads` — `인증`

`multipart/form-data`, 필드명 `file`. 이미지만(`jpg/png/webp`), 10MB 이하.

`201` → `{ "url": "/uploads/posts/tmp-8f2a.jpg" }`

글 저장과 분리돼 있다. 프론트는 업로드 후 받은 `url` 배열을 글 본문과 함께 보낸다.

### `POST /api/clubs/{club_id}/posts` — `장`

```jsonc
{
  "title": "성북동 출사, 필름 두 롤",
  "body": "…",
  "photos": ["/uploads/posts/tmp-8f2a.jpg"],
  "activity_date": "2025-10-12",
  "tags": ["출사", "필름"],
  "is_public": false            // 생략 시 false. 기본 비공개 (기획서 §6.1)
}
```

`201` → 글 상세 객체.

### `PATCH /api/posts/{post_id}` — `장`(본인 동아리) · `관리자`

위 필드 전부 optional.

### `DELETE /api/posts/{post_id}` — `장`(본인 동아리) · `관리자`

`204`.

### `POST /api/posts/{post_id}/like` — `인증`

토글이다. 같은 엔드포인트를 다시 부르면 취소된다.

`200` → `{ "liked": true, "like_count": 8 }`

---

## 7. AI 활동 글 초안 (T6 · wj) ⭐

### `POST /api/ai/draft` — `인증` + AI 키 등록됨

`multipart/form-data`

| 필드 | 필수 | 설명 |
|---|:--:|---|
| `memo` | △ | 한두 줄. **사실의 출처** |
| `photos` | | 이미지 여러 장 |
| `pdf` | △ | 활동 결과보고서. 서버가 pypdf로 텍스트 추출 |
| `club_id` | ○ | 동아리명·분야를 프롬프트 맥락에 넣는다 |

`memo`와 `pdf` 중 **최소 하나는 있어야 한다.**

```json
{ "title": "성북동에서 필름 두 롤을 태우다",
  "body": "10월 12일, 12명이 성북동 일대에서 …",
  "tags": ["출사", "필름", "성북동"],
  "used": { "memo": true, "pdf": false, "photos": 3, "vision": false } }
```

`used.vision`은 게이트웨이가 이미지 입력을 실제로 받았는지다. `false`면 프론트가 "사진은 첨부만 되었습니다" 안내를 띄운다(기획서 §7.4).

| 에러 | code | message (그대로 노출) |
|---|---|---|
| 422 | `MEMO_REQUIRED` | 무슨 활동이었는지 한 줄만 적어주세요. 사진만으로는 초안을 만들지 않습니다. |
| 422 | `PDF_UNREADABLE` | 내용을 읽을 수 없습니다. 메모로 적어주세요. |
| 403 | `AI_KEY_NOT_REGISTERED` | 내 정보에서 AI API 키를 등록하면 사용할 수 있어요. |
| 502 | `AI_GATEWAY_ERROR` | AI 응답을 받지 못했습니다. 잠시 후 다시 시도해주세요. |
| 429 | `AI_QUOTA_EXCEEDED` | 키의 사용 한도를 초과했습니다. |

**`MEMO_REQUIRED`는 버그가 아니라 설계다**(기획서 §7.2). 프론트는 이 code를 에러 토스트가 아니라 **warn 3색 박스**(디자인 §6-5)로 렌더한다.

**시연 폴백:** 백엔드 `.env`에 `DEMO_FALLBACK=1`이면 게이트웨이를 호출하지 않고 미리 준비한 초안을 반환한다(구현계획 §6). 응답 형태는 동일하며 `used.vision: false`.

---

## 8. 프론트 mock 규칙

백엔드가 아직 없는 엔드포인트는 `frontend/src/api/index.js` **안에서만** mock으로 대체하고 `// MOCK` 주석을 남긴다. 컴포넌트는 mock 여부를 몰라야 하며, 붙일 때 mock 블록만 지운다.

| 화면 | 실데이터 없이도 되는가 |
|---|---|
| 메인 캐러셀 | `GET /api/posts/highlights` mock 12건이면 기하 확인까지 끝난다 |
| 아카이브 | `GET /api/clubs` mock 40건 — 검색·파셋 전부 클라이언트 계산이라 백엔드 무관 |
| 상세 타임라인 | `GET /api/clubs/{id}/posts` offset/limit mock으로 배치 로드까지 검증 가능 |
| 글 작성 | `POST /api/ai/draft` mock으로 T6 전에 화면 완성 |

---

## 9. 이 문서에서 PM이 확정한 것 (디자인 기획 §7 미정)

| # | 미정이던 것 | 확정 | 근거 |
|---|---|---|---|
| 1 | 인원 버튼 숫자에 OB 포함 여부 | **포함** (`counts.total`) | 목업 확정값 38이 포함 기준이다 |
| 2 | 인원 모달 실명 노출 범위 | **로그인 시에만 실명**, 비로그인은 기수별 인원수만 | 기획서 §9 최소 노출 |
| 3 | 활동 글 본문 형식 | **평문**(줄바꿈만) | 마크다운 렌더러는 시연에 이득 없음 |
| 4 | 캐러셀 선정 기준 | **공개 글 최신순, 동아리당 1건** | 한 동아리가 독점하면 메시지가 죽는다 |
| 5 | 비공개 글 무권한 접근 | **404** (403 아님) | 존재 자체를 숨긴다 |
| 6 | 학년을 어떻게 얻는가 | **본인이 고르고 고친다**(가입 시 입력 · `PATCH /api/me`). 서버가 학번에서 계산하지 않는다 | 휴학·재수·편입이면 학번과 학년이 어긋난다. 학년은 동아리장이 신청자를 심사할 때 보는 **유일한 학적 정보**라 틀리면 판단이 틀어진다 |
| 7 | 학번 형식 | **숫자 10자리 고정** (예: `2022261026`) | 명지전문대 학번 체계. 앞 4자리가 입학년도지만 학년 계산에는 쓰지 않는다 |

## 10. 이 명세에서 뺀 것

| 뺀 것 | 대신 |
|---|---|
| 페이지네이션 표준(`page`/`size`) | 타임라인만 `offset`/`limit`. 나머지는 전량 반환 — 데이터가 수십 건 규모다 |
| ETag·캐시 헤더 | 없음 |
| 관리자 **게시글** 목록 API | 동아리장이 자기 동아리 글을 관리한다. 전체 관리가 필요하면 DB 직접 |
| 유저 **삭제** | 활동 이력이 딸려 있어 되돌릴 수 없다. DB 직접 (§5 유저 관리 참고) |
| 알림 API | 이메일 + `/api/me/requests` |
| 파일 삭제 API | 업로드된 고아 파일은 그대로 둔다 |
