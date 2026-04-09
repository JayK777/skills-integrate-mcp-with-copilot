# Mergington High School Activities API

A FastAPI application that allows students and staff to manage extracurricular activities with token-based authentication and role checks.

## Features

- Token-based login sessions
- Role-based authorization (`student`, `instructor`, `coordinator`, `admin`)
- Profile management and password changes
- View all available extracurricular activities
- Protected signup/unregister for activities

## Getting Started

1. Install the dependencies:

   ```
   pip install fastapi uvicorn
   ```

2. Run the application:

   ```
   python app.py
   ```

3. Open your browser and go to:
   - API documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc

## API Endpoints

| Method | Endpoint                                                          | Description                                                         |
| ------ | ----------------------------------------------------------------- | ------------------------------------------------------------------- |
| POST   | `/auth/signup`                                                    | Register a new user account                                         |
| POST   | `/auth/login`                                                     | Login and receive bearer token                                      |
| POST   | `/auth/logout`                                                    | Logout and invalidate current token                                 |
| GET    | `/auth/me`                                                        | Get authenticated user profile                                      |
| PATCH  | `/auth/me`                                                        | Update profile fields                                                |
| POST   | `/auth/change-password`                                           | Change password for current user                                    |
| GET    | `/activities`                                                     | Get all activities with details and participant count               |
| POST   | `/activities/{activity_name}/signup`                              | Protected signup (self; staff can target via `?email=`)            |
| DELETE | `/activities/{activity_name}/unregister`                          | Protected unregister (self; staff can target via `?email=`)        |
| GET    | `/admin/users`                                                    | Admin-only user listing                                             |

## Auth Flow

1. Call `POST /auth/signup` with role and profile fields.
2. Call `POST /auth/login` to receive `access_token`.
3. Send `Authorization: Bearer <access_token>` on protected endpoints.
4. Use `POST /auth/logout` when done.

Role requirements:

- Any authenticated role can call `/auth/me`, `/auth/me` (PATCH), and `/auth/change-password`.
- `student` can sign up/unregister themself from activities.
- `instructor`, `coordinator`, and `admin` can sign up/unregister other users by providing `email`.
- Only `admin` can call `/admin/users`.

## Legacy Migration Note

To support a migration path from pre-auth versions, the app auto-creates student accounts in-memory for legacy participant emails already present in activity lists.
These users are seeded with placeholder credentials/profile data and can later be updated through authenticated profile endpoints.

## Data Model

The application uses a simple data model with meaningful identifiers:

1. **Activities** - Uses activity name as identifier:

   - Description
   - Schedule
   - Maximum number of participants allowed
   - List of student emails who are signed up

2. **Students** - Uses email as identifier:
   - Name
   - Grade level

All data is stored in memory, which means data will be reset when the server restarts.
