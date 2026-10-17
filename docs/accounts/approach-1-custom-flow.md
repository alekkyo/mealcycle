# Approach 1 (not chosen): a custom passwordless flow

**Status:** Reference only. We chose `django-allauth` headless (see [auth.md](auth.md)) because Apple and Google login are coming, and allauth already solves account linking, Apple's relay emails and ID-token verification.

This doc describes how the email login would have been built by hand with DRF + `djangorestframework-simplejwt`. It's meant to be **read, not implemented**: a guided tour of what a library like allauth does for us.

## The pieces

```
accounts/
├── models.py        User (exists), Profile, LoginCode
├── services.py      request_login(), verify_code(), verify_link()   ← business logic
├── serializers.py   EmailSerializer, VerifyCodeSerializer, MeSerializer
├── views.py         RequestLoginView, VerifyCodeView, VerifyLinkView, MeView
├── urls.py          /auth/email/, /auth/verify/, /auth/verify-link/, /me/
└── tests/
```

Putting the logic in `services.py` keeps views thin, the same as Laravel's "thin controllers, logic in services/actions".

## 1. Models

```python
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    trial_started_at = models.DateTimeField(default=timezone.now)

    @property
    def trial_ends_at(self):
        return self.trial_started_at + timedelta(days=14)

    @property
    def trial_is_active(self):
        return timezone.now() < self.trial_ends_at


class LoginCode(models.Model):
    email = models.EmailField(db_index=True)          # not a FK: the user may not exist yet
    code_hash = models.CharField(max_length=64)       # never store the code itself
    link_token_hash = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    used_at = models.DateTimeField(null=True, blank=True)
```

Notes:
- `OneToOneField` ≈ Eloquent `hasOne`/`belongsTo`. `user.profile` and `profile.user` both work.
- `@property` makes a method readable like a field: `profile.trial_is_active`, with no `()` (≈ an Eloquent accessor).
- **`LoginCode.email` instead of a user FK:** we only create the `User` once the code is verified, so typos and bots don't leave behind thousands of unverified accounts.
- **Hashes, not codes.** If the database leaked, the codes would be useless. We'd use `hmac.new(SECRET_KEY, code, sha256)` instead of a plain hash, because a 6-digit code has only 1,000,000 possibilities and a plain hash would be trivial to reverse.

## 2. Service: requesting a login

```python
CODE_LIFETIME = timedelta(minutes=10)

def request_login(email: str) -> None:
    email = normalize_email_address(email)
    LoginCode.objects.filter(email=email, used_at__isnull=True).delete()  # one active code per email

    code = f"{secrets.randbelow(1_000_000):06d}"      # "004821": cryptographically random, zero-padded
    link_token = secrets.token_urlsafe(32)            # long random string for the magic link
    LoginCode.objects.create(
        email=email,
        code_hash=_hmac(code),
        link_token_hash=_hmac(link_token),
        expires_at=timezone.now() + CODE_LIFETIME,
    )
    send_mail(
        subject=f"Your MealCycle code: {code}",
        message=f"Your code is {code}.\nOr tap: https://app.mealcycle.com/login?token={link_token}",
        from_email=None,                              # uses DEFAULT_FROM_EMAIL
        recipient_list=[email],
    )
```

- `secrets` (not `random`) is Python's module for **security-grade** randomness (≈ PHP `random_int()`).
- `used_at__isnull=True` uses the ORM's **double-underscore lookups**: `field__isnull`, `field__gte`, `field__icontains` … (≈ `whereNull('used_at')`).
- The link is an **https universal link**: iOS/Android open the app if it's installed, and a web page otherwise. That avoids the "opens Safari" problem with custom `mealcycle://` schemes.

## 3. Service: verifying

```python
MAX_ATTEMPTS = 5

def verify_code(email: str, code: str) -> User:
    email = normalize_email_address(email)
    login_code = (
        LoginCode.objects.filter(email=email, used_at__isnull=True, expires_at__gt=timezone.now())
        .order_by("-created_at")
        .first()
    )
    if login_code is None:
        raise InvalidCode()

    login_code.attempts += 1
    login_code.save(update_fields=["attempts"])
    if login_code.attempts > MAX_ATTEMPTS:
        login_code.delete()                            # too many guesses: they must request a new code
        raise InvalidCode()

    if not hmac.compare_digest(login_code.code_hash, _hmac(code)):
        raise InvalidCode()

    login_code.used_at = timezone.now()
    login_code.save(update_fields=["used_at"])
    return _get_or_create_user(email)


@transaction.atomic
def _get_or_create_user(email: str) -> User:
    user, created = User.objects.get_or_create(email=email)
    if created:
        Profile.objects.create(user=user)              # the 14-day trial starts here
    return user
```

- **One error for everything** (`InvalidCode`). "No code", "expired", "wrong code" and "too many attempts" all look the same to the caller, so an attacker learns nothing.
- **`hmac.compare_digest`** compares in **constant time**. A normal `==` stops at the first different character, and the timing difference can leak information.
- **Attempts are counted before checking.** Guessing all 1,000,000 codes is impossible with 5 tries per code.
- **`@transaction.atomic`** (≈ `DB::transaction(fn() => ...)`): the user and profile are created together or not at all.
- `get_or_create` returns a **tuple** `(object, created_bool)`, unpacked into two variables.

`verify_link(token)` would be the same, looked up by `link_token_hash`.

## 4. Tokens (simplejwt)

```python
def tokens_for(user):
    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}
```

```python
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=60),
    "ROTATE_REFRESH_TOKENS": True,          # each refresh hands out a new refresh token...
    "BLACKLIST_AFTER_ROTATION": True,       # ...and the old one stops working (stolen tokens expire)
}
REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"] = [
    "rest_framework_simplejwt.authentication.JWTAuthentication",
]
```

simplejwt also ships the views for `POST /auth/token/refresh/`, and logout means blacklisting the refresh token.

## 5. Serializers and views

```python
class EmailSerializer(serializers.Serializer):
    email = serializers.EmailField()

class VerifyCodeSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.RegexField(r"^\d{6}$")


class RequestLoginView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "login_request"                   # e.g. "5/hour", set in REST_FRAMEWORK

    def post(self, request):
        serializer = EmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)      # invalid input → automatic 400 with field errors
        request_login(serializer.validated_data["email"])
        return Response(status=status.HTTP_202_ACCEPTED)  # same answer whether the email exists or not


class VerifyCodeView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "login_verify"

    def post(self, request):
        serializer = VerifyCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = verify_code(**serializer.validated_data)
        except InvalidCode:
            return Response({"detail": "Invalid or expired code."}, status=400)
        return Response(tokens_for(user))


class MeView(APIView):                                 # uses the global IsAuthenticated default
    def get(self, request):
        return Response(MeSerializer(request.user).data)
```

- A **serializer** here works like a Laravel **FormRequest**: `is_valid(raise_exception=True)` ≈ `$request->validated()`, returning 400 on failure.
- `**serializer.validated_data` spreads a dict into named arguments: `verify_code(email=..., code=...)`.
- **Throttling** is DRF's built-in rate limiter (≈ Laravel's `throttle` middleware). It needs a shared cache (Redis) once there's more than one server.
- **202 Accepted, always**, so the endpoint can't be used to find out who has an account (*user enumeration*).

## 6. Tests it would need

- Happy path: request → `mail.outbox` has 1 email containing a 6-digit code → verify → 200 with tokens → `/me` works with the token.
- A new email creates a User + Profile with `trial_started_at`. An existing email doesn't create a second one.
- A wrong code, an expired code (time moved forward), a reused code and a 6th attempt all give the same 400.
- A new request invalidates the previous code.
- The request endpoint returns 202 for unknown emails, and rate limits return 429.
- `/me` without a token gives 401. An expired access token gives 401. Refresh returns a new pair, and the old refresh token is rejected after rotation.
- Codes are stored hashed: the plain code never appears in the database.

## What allauth gives us instead

Everything above (code generation, hashing, expiry, attempt limits, rate limits, enumeration protection, the email, tokens, and the endpoints), plus **Apple/Google login with account linking** later, as configuration rather than code. What's left for us is the `Profile`/trial logic, the email template, and the tests proving it all works together.
