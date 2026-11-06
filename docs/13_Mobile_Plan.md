# 13 — Mobile Application Roadmap

## 1. Decision

A native-style mobile app is a planned future client, not an MVP dependency. Build the responsive web app and stable DRF API first.

## 2. Proposed technology

- Flutter stable channel.
- Dart version compatible with selected Flutter release.
- Dio or maintained HTTP client.
- Secure token storage using platform Keychain/Android Keystore integration.
- Push notifications through an approved provider.
- Deep links to request and connection screens.
- Leaflet is web-only; mobile map implementation can use a Flutter-compatible map package after licensing/provider review.

Exact Flutter/package versions must be pinned when the mobile phase begins and recorded in `pubspec.lock`.

## 3. Mobile app screens

1. Splash and onboarding.
2. Registration/login.
3. Verification.
4. Dashboard.
5. Donor profile and availability.
6. Donor search and filters.
7. Donor public profile.
8. Create blood request.
9. Request detail.
10. Incoming contact requests.
11. Outgoing contact requests.
12. Accepted connection detail.
13. Notifications.
14. Privacy and account settings.
15. Report/block.
16. Help and safety.

## 4. Shared backend rules

- Same user identity and permissions as web.
- Same donor/request/contact state machines.
- API versioning under `/api/v1/`.
- No direct database access.
- Same contact disclosure rules.
- Push notifications contain no sensitive health/contact details.
- Deep links require authentication and authorization.

## 5. Mobile security

- Store refresh tokens only in secure platform storage.
- Use short-lived access tokens.
- Support refresh rotation and revocation.
- Clear tokens on logout/deactivation.
- Do not store donor private data in unencrypted local cache.
- Protect screenshots/notifications where platform capabilities and product risk justify it.
- Do not log tokens or private API responses.

## 6. Release sequence

- M1: API contract stable.
- M2: Flutter project and authentication.
- M3: donor profile and search.
- M4: requests and contact flow.
- M5: push notifications and deep links.
- M6: accessibility, security, store testing and release.

## 7. Out of scope for initial mobile milestone

- Offline creation of blood requests.
- Medical screening features.
- Blood inventory management.
- Government identity capture.
- Background location tracking.
