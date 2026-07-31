# NOVA CORE Mobile Platform

## Overview
Flutter-based mobile client for NOVA CORE, providing comprehensive dashboards, chat, workflow management, and monitoring for Android and iOS.

## Tech Stack
- **Framework**: Flutter 3.16+
- **Language**: Dart 3.2+
- **State Management**: Provider 6
- **Routing**: go_router 14
- **HTTP**: http 1.2
- **WebSocket**: web_socket_channel 2.4
- **Storage**: shared_preferences + flutter_secure_storage
- **Notifications**: flutter_local_notifications
- **Biometric**: local_auth
- **Database**: sqflite (offline)
- **Testing**: flutter_test + mockito

## Architecture
```
mobile/
  lib/
    main.dart                    # App entry point
    core/
      config/app_config.dart     # Environment configuration
      api/api_client.dart        # HTTP client consuming API Platform
      api/websocket_client.dart  # WebSocket client with reconnection
      api/exceptions.dart        # Custom exception types
      theme/app_theme.dart       # Dark/light themes
      theme/app_colors.dart      # Color constants
      router/app_router.dart     # GoRouter navigation
    models/nova_models.dart      # All data models
    repositories/nova_repository.dart  # Data layer with offline cache
    providers/
      theme_provider.dart        # Theme state
      auth_provider.dart         # Authentication state
      app_provider.dart          # Global app state
      chat_provider.dart         # Chat/WebSocket state
    services/
      connectivity_service.dart  # Network connectivity monitoring
    notifications/
      notification_service.dart  # Push notification handling
    localization/
      localization.dart          # i18n architecture
    widgets/
      app_scaffold.dart          # Main scaffold with nav
      app_drawer.dart            # Navigation drawer
      common_widgets.dart        # MetricCard, StatusBadge, etc.
    screens/                     # 25+ screen implementations
  tests/
    core/config/                 # Config tests
    core/api/                    # API client tests
    core/theme/                  # Theme tests
    models/                      # Model parsing tests
    providers/                   # Provider state tests
    widgets/                     # Widget tests
    localization/                # Localization tests
    notifications/               # Notification tests
    services/                    # Service tests
```

## Getting Started

### Prerequisites
- Flutter 3.16+
- Dart 3.2+
- Android Studio / Xcode
- NOVA CORE backend running

### Installation
```bash
cd mobile
flutter pub get
```

### Run
```bash
# Android
flutter run -d android

# iOS
flutter run -d ios

# Web (limited)
flutter run -d chrome
```

### Configure Backend URL
```bash
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000 --dart-define=WS_BASE_URL=ws://10.0.2.2:8000
```

## Testing
```bash
flutter test
```

## Build
```bash
# Android APK
flutter build apk --release

# iOS
flutter build ios --release
```

## Features
- 25+ dashboard screens covering all NOVA CORE modules
- Real-time chat with WebSocket streaming
- Dark/light theme support
- Responsive layout (phone/tablet)
- Offline mode with local cache
- Push notifications for workflow/task updates
- Biometric authentication interface
- Deep linking support
- State restoration

## Offline Support
- Local SQLite database for persistent cache
- SharedPreferences for settings and session data
- Automatic sync when connectivity is restored
- Conflict resolution via last-write-wins

## API Integration
Mobile Platform consumes exclusively:
- **API Platform** (FastAPI backend) via HTTP REST
- **WebSocket interfaces** for real-time chat and events
- **NOVA_CORE SDK** patterns for API interaction

No backend business logic is duplicated.
