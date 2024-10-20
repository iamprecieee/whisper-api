# Whisper: Developer's Guide and API Documentation

## Table of Contents
1. [Introduction](#1-introduction)
2. [Getting Started](#2-getting-started)
3. [Authentication](#3-authentication)
4. [API Endpoints](#4-api-endpoints)
5. [WebSocket Communication](#5-websocket-communication)
6. [Deployment](#6-deployment)
7. [Testing](#7-testing)


## 1. Introduction

Whisper is a real-time chat application built with Django - Django Rest Framework, and Django Channels. This document serves as a comprehensive guide on the operation of Whisper.

### Key Features
- Passwordless user authentication (incorporating social authentication) with email verification and 2FA support
- Real-time messaging using WebSockets
- Support for text, image, audio, and video messages
- Message reply functionality
- User online/offline status and room-joining tracking

### Tech Stack
The application is built on Django and uses the following key components:

- Django rest framework (DRF) for RESTful API endpoints
- Whitenoise for static files storage
- drf_spectacular for openAPI documentation
- drf-social-oauth2 for google authentication support
- Django otp for 2FA support
- Django rest framework's simplejwt for JWT authentication
- Django channels for websockets communication
- nanoid for database model ids generation
- Nginx as reverse-proxy
- Ngrok for local-public tunnelling


## 2. Getting Started

### Prerequisites
- Python 3.8+
- Linux OS or WSL

### Setting Up the Development Environment
1. Clone the repository:
   ```bash
   cd $HOME
   git clone https://github.com/iamprecieee/whisper.git
   cd whisper
   ```

2. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source ./venv/bin/activate
   ```

3. Make shell scripts executable:
    ```bash
    chmod +x ./pkg-install.sh ./entrypoint.sh
    ```

4. Install dependencies:
   ```bash
   ./pkg-install.sh requirements
   ```

6. Set up environment variables:
   Create a `.env` file in the project root and add the following variables (these are just placeholders):
   ```
   SECRET_KEY_VALUE=...
   DEBUG_VALUE=...
   ALLOWED_HOSTS_VALUE=...
   SERVER_COMMAND=...
   CURRENT_HOST=...
   SENDER_EMAIL=...
   EMAIL_BACKEND_VALUE=...
   EMAIL_HOST_VALUE=...
   EMAIL_HOST_USER_VALUE=...
   EMAIL_HOST_PASSWORD_VALUE=...
   EMAIL_PORT_VALUE=...
   CERT_FILE=...
   KEY_FILE=...
   SOCIAL_AUTH_GOOGLE_OAUTH2_KEY=...
   SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET=...

7. Start the development server:
   ```bash
   ./entrypoint.sh
   ```

## 3. Authentication

Whisper employs both passwordless/social authentication (google oauth2) with 2FA and JWTAuthentication as the primary authentication class.

### Model Backend Authentication Flow
- User registers an account with their email, to which an OTP (one per user at a time) is sent for verification.
- On a successful verification, the email is stored in session [via `WhisperSession`, and retrieved for subsequent requests] and the user i prompted to begin 2FA setup. If the verification fails [due to expired token or db transaction failure], the user can request a new verification link manually.
- On a successful 2FA setup, the user proceeds to login using their email and a totp code generated from their authenticator app. On login, JWT access and refresh tokens are generated for the user; the refresh token and email are saved to session.
- The user can then make requests to protected endpoints using the access token.

### Social Backend Authentication Flow
- The user initiates social authentication (https://.../api/v1/user/social/begin/google-oauth2).
- The `custom_create_user` pipeline checks for an existing user with the same social email. If none is found, it proceeds to register a fresh account; else it checks if the existing account's email has been verified, and proceeds with the authentication if so.
- On registration of a new user, the user is given an "is_new" tag with a truthy value, and on subsequent logins, the "is_new" tag has a falsy value.
- The emails used in successful social authentication are automatically verified and stored in sessions.
- For new accounts or those without 2FA enabled, the user is prompted to complete 2FA setup.
- On a successful TOTP verification, the user receives JWT access and refresh tokens(and updates username if randomly generated).
- Access token is used to make authenticated requests, and refresh token is used to obtain a new access token when it expires.

### Two-Factor Authentication (2FA) Flow
- A new unconfirmed totp device is created for the user's account using their email.
- The user then requests a QR code which they use to set up their authenticator app.
- After setting up the app, they confirm the device using a totp code generated from their authenticator app.
- On device confirmation, their authenticator app can be used to generate codes for subsequent logins.

### JWT Token Handling
- Access tokens are stored in the `JWTAccessToken` model.
- Refresh tokens are managed by the `WhisperSession` class.

### Setting up social authentication (Google)
1. Install dependencies:
   ```bash
   ./pkg-install.sh drf_social_oauth2
   ```

2. Add these to installed apps:
   ```bash
   "oauth2_provider",
   "social_django",
   "drf_social_oauth2",
   ```

3. Additional settings:
   ```bash
   SOCIAL_AUTH_USER_MODEL = "user.User"
   SOCIAL_AUTH_JSONFIELD_ENABLED = True # For postgres
   SOCIAL_AUTH_REDIRECT_IS_HTTPS = True

   AUTHENTICATION_BACKENDS = [
      "django.contrib.auth.backends.ModelBackend",
      "social_core.backends.google.GoogleOAuth2",
   ]
   ```
### Signals
- The `send_otp_email` signal listens for newly created users and creates jwt_access_token relations (used for storing user access tokens). If a model backend was used for registration, it sends out the verification emails.

### Middleware
- The `ClearAuthenticationHeaderMiddleware` prevents reuse of invalid tokens and removes authentication headers from 'anonymous' endpoints.


## 4. API Endpoints

This section provides an in-depth description of all API endpoints available in the Whisper application. All endpoints are prefixed with `/api/v1/`.

### Authentication Endpoints
-  <b>Register</b>
- URL: `user/register/`
- Method: POST
- Description: Register a new user account.
- Request Body:
   ```json
   {
   "email": "user@example.com",
   "username": "username123"
   }
   ```
- Response:
   ```json
   Status: 201 Created

   {
   "id": "KQPkpdZU0h5gO-o1tCEXK",
   "email": "user@example.com",
   "username": "username123",
   "is_email_verified": false,
   "is_username_set": true,
   "message": "Check your email for a verification link."
   }
   ```

- <b>Verify Email (Begin)</b>
- URL: `user/verify-email/begin/`
- Method: POST
- Description: Initiate email verification process.
- Request Body:
   ```json
   {
   "email": "user@example.com"
   }
   ```
- Response:
   ```json
   Status: 200 OK
   
   {
   "message": "Check your email for a verification link."
   }
   ```

- <b>Verify Email (Complete)</b>
- URL: `user/verify-email/complete/<token>/`
- Method: POST
- Description: Complete email verification process.
- Response:
   ```json
   Status: 200 OK

   {
   "id": "KQPkpdZU0h5gO-o1tCEXK",
   "email": "user@example.com",
   "username": "username123",
   "is_email_verified": true,
   "is_username_set": true,
   "message": "Proceed to 2FA setup."
   }
   ```

- <b>Create TOTP Device</b>
- URL: `user/totp-device/create/`
- Method: POST
- Description: Create a new TOTP device for 2FA.
- Request Body: Empty (email is retrieved from session)
- Response:
   ```json
   Status: 201 CREATED

   {
   "user": "KQPkpdZU0h5gO-o1tCEXK",
   "name": "user@example.com",
   "confirmed": false
   }
   ```

- <b>Get QR Code</b>
- URL: `user/qr-code/`
- Method: POST
- Description: Get QR code for TOTP device setup.
- Request Body: Empty (email is retrieved from session)
- Response:
   ```json
   Status: 200 OK
   Content-Type: image/png
   Body: Binary data of QR code image
   ```

- <b>Verify TOTP Device</b>
- URL: `user/totp-device/verify/`
- Method: POST
- Description: Verify the TOTP device.
- Request Body:
   ```json
   {
   "otp_token": "123456"
   }
   ```
- Response:
   ```json
   Status: 200 OK
   
   {
   "user": "KQPkpdZU0h5gO-o1tCEXK",
   "name": "user@example.com",
   "confirmed": true,
   "message": "TOTP Device verified successfully. Proceed to login."
   }
   ```

- <b>Login</b>

- URL: `user/login/`
- Method: POST
- Description: Initiate user login.
- Request Body:
   ```json
   {
   "email": "user@example.com"
   }
   ```
- Response: Redirects to TOTP verification

- <b>Verify TOTP (Login)</b>
- URL: `/user/totp/verify/`
- Method: POST
- Description: Verify TOTP for login.
- Request Body:
   ```json
   {
   "otp_token": "123456"
   }
   ```
- Response:
   ```json
   Status: 200 OK

   {
   "id": "KQPkpdZU0h5gO-o1tCEXK",
   "email": "user@example.com",
   "access": "access_token",
   "refresh": "refresh_token"
   }
   ```

- <b>Refresh Token</b>
- URL: `user/refresh/`
- Method: POST
- Description: Refresh the access token.
- Authentication: Requires valid refresh token
- Response:
   ```json
   Status: 200 OK

   {
   "id": "KQPkpdZU0h5gO-o1tCEXK",
   "email": "user@example.com",
   "access": "new_access_token",
   "refresh": "new_refresh_token"
   }
   ```

- <b>Social Authentication (Begin)</b>
- URL: `user/social/begin/<backend>/{extra}`
- Method: GET
- Description: Initiate social authentication.
- URL Parameters: Social auth provider (e.g., "google-oauth2")
- Response: Redirects to social auth provider

- <b>Social Authentication (Complete)</b>
- URL: `user/social/complete/<backend>/`
- Method: GET
- Description: Complete social authentication.
- URL Parameters: Social auth provider (e.g., "google-oauth2")
- Response:

   For new users:
   ```json
   Status: 201 Created
   Body: User data with message to proceed to 2FA setup
   ```
   For existing users without 2FA:
   ```json
   Status: 401 Unauthorized
   Body: Message to complete 2FA setup
   ```
   For existing users with 2FA: Redirects to TOTP verification endpoint.


### Room Endpoints
- <b>List Rooms</b>

- URL: `chat/room-list/`
- Method: GET
- Description: Get a list of all rooms.
- Authentication: Requires valid access token
- Response:
   ```json
   Status: 200 OK

   [
   {
      "id": "vFYEuZKrHMOdfyaRpjvgN",
      "room_name": "Room Name",
      "users": ["KQPkpdZU0h5gO-o1tCEXK", "1urDbsabPV3FjSBK-vEdK"],
      "creator": "creator_id",
      "created": "2023-10-18T12:00:00Z"
   }, ...
   ]
   ```

- <b>Create Room</b>
- URL: `chat/room-list/`
- Method: POST
- Description: Create a new room.
- Authentication: Requires valid access token
- Request Body:
   ```json
      {
      "room_name": "My New Room",
      "user_ids": ["KQPkpdZU0h5gO-o1tCEXK", "1urDbsabPV3FjSBK-vEdK"]
      }
   ```
- Response:
   ```json
   Status: 201 Created
   
   {
   "id": "vFYEuZKrHMOdfyaRpjvgN",
   "room_name": "My New Room",
   "users": ["KQPkpdZU0h5gO-o1tCEXK", "1urDbsabPV3FjSBK-vEdK"],
   "creator": "KQPkpdZU0h5gO-o1tCEXK",
   "created": "2023-10-18T12:00:00Z"
   }
   ```

- <b>Get Room Messages</b>
- URL: `chat/home/<room_id>/`
- Method: GET
- Description: Get messages for a specific room.
- Authentication: Requires valid access token
- Query Parameters: Pagination cursor for previous messages
- Response:
   ```json
   HTML Response (default)

   Status: 200 OK
   Content-Type: text/html
   Body: Rendered HTML page with room messages
   ```
- JSON Response (when Accept header is application/json):
   ```json
   Status: 200 OK
   
   {
   "results": [
      {
         "id": "EYoT9lPS1H0oP5_CjuDDk",
         "message_format": "text",
         "text_content": "Hello, World!",
         "sender": "1urDbsabPV3FjSBK-vEdK",
         "room": "vFYEuZKrHMOdfyaRpjvgN",
         "created": "Oct. 18, 2023, 12:00 p.m.",
         "date": "Oct. 18, 2023",
         "time": "12:00 p.m.",
         "username": "username123",
         ...
      },
      ...
   ],
   "previous_messages": "http://.../api/v1/rooms/vFYEuZKrHMOdfyaRpjvgN/?cursor=cursor_value"
   }
   ```


## 5. WebSocket Communication

WebSocket communication is handled by the `RoomConsumer` class, which extends `AsyncWebsocketConsumer`. Clients can connect to a WebSocket for real-time updates in a specific room. A special async-compatible message serializer is utilized in this area.
Key features include:
- Connecting users to rooms
- Handling different types of messages (text, image, audio, video)
- Managing user online/offline status
- Sending notifications for user activities

### WebSocket Connection
- **URL**: `wss://.../ws/chat/<room_id>/`
- **Headers**:
  - Authorization: Bearer <access_token>

### Message Types

#### Text Message
```json
{
  "message_type": "message",
  "message": "Hello, World!"
}
```

#### Reply Message
```json
{
  "message_type": "reply",
  "message": "Hello back!",
  "previous_message_id": "EYoT9lPS1H0oP5_CjuDDk"
}
```

#### Media Message
For media [and media-reply] messages (image, audio, video), the message is sent as bytes data with the following structure:
1. JSON metadata
2. Delimiter: `<delimiter>`
3. Binary media data

JSON metadata example:
```json
{
  "message_type": "media",
  "message_format": "image",
  "media_format": "image"
}

Followed by: <delimiter>
Last part: Binary media data

```

#### Media Reply Message
```json
{
  "message_type": "reply",
  "previous_message_id": "vFYEuZKrHMOdfyaRpjvgN",
  "media_format": "image"
}

Followed by: <delimiter>
Last part: Binary media data
```

### WebSocket Events

#### User Joined
```json
{
  "type": "chat.notification",
  "content": "John Doe was added to the chat."
}
```

#### Active Users Count
```json
{
  "type": "chat.active",
  "content": 5
}
```

#### New Message
```json
{
  "type": "chat.message",
  "id": "wW1PZ_xiD_rIzjysnfs1j",
  "text_content": "Hello, World!",
  "message_format": "text",
  "username": "johndoe",
  "created": "Sep. 23, 2023",
  "time": "12:34 PM"
}
```

#### User Typing
```json
{
  "type": "chat.typing",
  "content": "johndoe is typing..."
}
```

### Signals
- The `notify_new_room_user` signal listens for newly added/removed users to/from rooms and sends a `chat.notification` message to the websocket.


## 6. Deployment

The application can be deployed using different server options:

### Daphne (ASGI server)
```bash
daphne -b 0.0.0.0 -p 8000 portal.asgi:application
```

### Gunicorn with Uvicorn workers
```bash
gunicorn portal.asgi:application -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

### Uvicorn
```bash
uvicorn portal.asgi:application --host 0.0.0.0 --port 8000 --reload
```

The `entrypoint.sh` script handles the deployment process, including:
- Loading environment variables
- Making and applying database migrations
- Collecting static files (in production)
- Generating SSL certificates (in development)
- Starting the appropriate server based on the `SERVER_COMMAND` environment variable

For development purposes, self-signed SSL certificates can be generated using the `generate_certs.py` script.

The Whisper chat application is deployed using a combination of Daphne/Gunicorn/Uvicorn (ASGI server), Nginx as a reverse proxy, and Ngrok for tunneling. This setup allows for secure HTTPS connections and global access to the application.

### Server Setup

#### Daphne (ASGI server)
Daphne is configured to run on port 8000 and is managed as a system service.

- File: `/etc/systemd/system/daphne.service`
```ini
[Unit]
Description=daphne daemon
After=network.target

[Service]
User=<username>
Group=www-data
WorkingDirectory=/home/<username>/whisper-api
EnvironmentFile=/home/<username>/whisper-api/.env
ExecStart=/bin/bash -c "source /home/<username>/whisper-api/venv/bin/activate && /home/<username>/whisper-api/entrypoint.sh"
Restart=on-failure
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target

```

To start the Daphne service:
```bash
sudo systemctl start daphne
sudo systemctl enable daphne
```

#### Nginx Configuration
Nginx is set up to listen on ports 8080 (HTTP) and 443 (HTTPS), redirecting all HTTP traffic to HTTPS and proxying requests to the Daphne server.

- Create a `nginx.conf` file in the project base directory from `nginx.conf.example` sample. Replace "<username>" with your username.
- Create a `/etc/nginx/nginx.conf` file from your `nginx.conf` file.
```bash
sudo cp $HOME/whisper-api/nginx.conf /etc/nginx/nginx.conf
```

To reload Nginx after configuration changes:
```bash
sudo nginx -t
sudo systemctl reload nginx
```

#### Ngrok Setup
Ngrok is used to create a secure tunnel to the local server, making it accessible globally.

- Create a `ngrok.service` file in the project base directory from `ngrok.service.example` sample. Replace "<username>" with your username.
- Create a `/etc/systemd/system/ngrok.service` file from your `ngrok.service` file.
```bash
sudo cp $HOME/whisper-api/ngrok.service /etc/systemd/system/ngrok.service
```


To start the Ngrok service:
```bash
sudo systemctl start ngrok
sudo systemctl enable ngrok
```