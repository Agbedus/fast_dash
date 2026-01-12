# Fast Dash API Documentation

**Version:** 1.0.0  
**Base URL:** `/api/v1`

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Error Handling](#error-handling)
4. [Endpoints](#endpoints)
   - [Authentication](#authentication-endpoints)
   - [Users](#users-endpoints)
   - [Clients](#clients-endpoints)
   - [Projects](#projects-endpoints)
   - [Tasks](#tasks-endpoints)
   - [Notes](#notes-endpoints)
   - [Events](#events-endpoints)
   - [Decisions](#decisions-endpoints)
5. [Permission Model](#permission-model)
6. [Common Patterns](#common-patterns)

---

## Overview

Fast Dash is a project management API built with FastAPI. It provides comprehensive endpoints for managing users, clients, projects, tasks, notes, events, and decisions.

### Key Features

- **JWT Authentication** with optional cookie-based auth for browsers
- **Role-based access control** (USER, CLIENT, STAFF, MANAGER, ADMIN, SUPER_ADMIN)
- **Resource ownership** and sharing mechanisms
- **RESTful API** design with standard CRUD operations
- **Automatic API documentation** at `/docs` (Swagger UI) and `/redoc`

---

## Authentication

### Authentication Methods

The API supports two authentication methods:

1. **Bearer Token** (for API clients): Include `Authorization: Bearer {token}` header
2. **HTTP-only Cookie** (for browsers): Automatically set after login

### Registration

**POST** `/api/v1/auth/register`

Register a new user account.

**Request Body:**

```json
{
  "email": "user@example.com",
  "password": "securepassword123",
  "full_name": "John Doe"
}
```

**Response:** `201 Created`

```json
{
  "id": "uuid-string",
  "email": "user@example.com",
  "full_name": "John Doe",
  "roles": ["user"],
  "created_at": "2025-12-22T12:00:00.000Z"
}
```

### Login

**POST** `/api/v1/auth/login`

Authenticate and receive an access token.

**Request Body (form-data):**

```
username=user@example.com
password=securepassword123
```

**Response:** `200 OK`

```json
{
  "access_token": "eyJhbGci...",
  "token_type": "bearer"
}
```

**Note:** The access_token is also set as an HTTP-only cookie named `access_token`.

### Logout

**GET** `/api/v1/auth/logout`

Clear the authentication cookie and redirect to login page.

**Response:** `307 Temporary Redirect` to `/login`

---

## Error Handling

### Standard Error Response

```json
{
  "detail": "Error message describing what went wrong"
}
```

### Common HTTP Status Codes

| Code | Meaning               | Description                   |
| ---- | --------------------- | ----------------------------- |
| 200  | OK                    | Request successful            |
| 201  | Created               | Resource created successfully |
| 400  | Bad Request           | Invalid request data          |
| 401  | Unauthorized          | Authentication required       |
| 403  | Forbidden             | Insufficient permissions      |
| 404  | Not Found             | Resource doesn't exist        |
| 422  | Unprocessable Entity  | Validation error              |
| 500  | Internal Server Error | Server error                  |

---

### System Endpoints

#### Health Check

- **GET** `/api/v1/health`
- **Auth Required:** No
- **Expected Response Payload:**
  ```json
  {
    "status": "ok"
  }
  ```

---

## Endpoints

### Authentication Endpoints

#### Register User

- **POST** `/api/v1/auth/register`
- **Auth Required:** No
- **Expected Payload:**
  ```json
  {
    "email": "user@example.com",
    "password": "securepassword123",
    "full_name": "John Doe"
  }
  ```
- **Returns:** User object

#### Login

- **POST** `/api/v1/auth/login`
- **Auth Required:** No
- **Expected Payload (form-data):**
  ```
  username=user@example.com
  password=securepassword123
  ```
- **Returns:** `{ access_token, token_type }`

#### Logout

- **GET** `/api/v1/auth/logout`
- **Auth Required:** No (but clears cookies)
- **Returns:** Redirect to `/login`

---

### Users Endpoints

Base path: `/api/v1/users`

#### List All Users

- **GET** `/api/v1/users`
- **Auth Required:** Admin only
- **Query Params:** `skip` (default: 0), `limit` (default: 100)
- **Expected Response Payload:**
  ```json
  [
    {
      "id": "uuid-1",
      "email": "user1@example.com",
      "full_name": "User One",
      "roles": ["staff"],
      "created_at": "2025-01-01T00:00:00.000Z"
    }
  ]
  ```

#### Create User

- **POST** `/api/v1/users`
- **Auth Required:** Admin only
- **Expected Payload:**
  ```json
  {
    "email": "newuser@example.com",
    "password": "securepassword123",
    "full_name": "New User",
    "roles": ["staff"],
    "avatar_url": "https://example.com/avatar.jpg"
  }
  ```
- **Returns:** User object

#### Get Current User

- **GET** `/api/v1/users/me`
- **Auth Required:** Yes
- **Expected Response Payload:**
  ```json
  {
    "id": "current-user-uuid",
    "email": "me@example.com",
    "full_name": "My Name",
    "roles": ["user"],
    "created_at": "2025-12-23T10:00:00.000Z"
  }
  ```

#### Update Current User

- **PUT** `/api/v1/users/me`
- **Auth Required:** Yes
- **Expected Payload:**
  ```json
  {
    "full_name": "Updated Name",
    "password": "newsecurepassword123",
    "avatar_url": "https://example.com/new-avatar.jpg"
  }
  ```
- **Returns:** Updated user profile

**Example Request:**

```json
{
  "full_name": "Jane Smith",
  "avatar_url": "https://example.com/avatar.jpg"
}
```

#### Get User by ID

- **GET** `/api/v1/users/{user_id}`
- **Auth Required:** Yes (own profile) or Admin
- **Expected Response Payload:**
  ```json
  {
    "id": "user-uuid",
    "email": "user@example.com",
    "full_name": "John Doe",
    "roles": ["user"],
    "created_at": "2025-12-23T10:00:00.000Z"
  }
  ```

#### Update User

- **PUT** `/api/v1/users/{user_id}`
- **Auth Required:** Admin only
- **Expected Payload:**
  ```json
  {
    "email": "updated@example.com",
    "full_name": "Updated Name",
    "roles": ["admin"]
  }
  ```
- **Returns:** Updated user object

#### Delete User

- **DELETE** `/api/v1/users/{user_id}`
- **Auth Required:** Admin only
- **Returns:** Deleted user object
- **Note:** Cannot delete yourself

---

### Clients Endpoints

Base path: `/api/v1/clients`

Clients are shared resources representing companies or organizations.

#### List Clients

- **GET** `/api/v1/clients`
- **Auth Required:** Yes
- **Query Params:** `skip`, `limit`
- **Returns:** Array of Client objects
- **Permissions:** All authenticated users can view

**Example Response:**

```json
[
  {
    "id": "uuid",
    "company_name": "Acme Corporation",
    "contact_person_name": "John Smith",
    "contact_email": "john@acme.com",
    "website_url": "https://acme.com",
    "created_at": "2025-01-01T00:00:00.000Z"
  }
]
```

#### Get Client

- **GET** `/api/v1/clients/{client_id}`
- **Auth Required:** Yes
- **Expected Response Payload:**
  ```json
  {
    "id": "uuid",
    "company_name": "Acme Corporation",
    "contact_person_name": "John Smith",
    "contact_email": "john@acme.com",
    "website_url": "https://acme.com",
    "created_at": "2025-01-01T00:00:00.000Z"
  }
  ```

#### Create Client

- **POST** `/api/v1/clients`
- **Auth Required:** Yes
- **Expected Payload:**
  ```json
  {
    "company_name": "New Client Ltd",
    "contact_person_name": "Jane Doe",
    "contact_email": "jane@example.com",
    "website_url": "https://example.com"
  }
  ```
- **Returns:** Client object

#### Update Client

- **PATCH** `/api/v1/clients/{client_id}`
- **Auth Required:** Admin only
- **Expected Payload:**
  ```json
  {
    "company_name": "Updated Company Name",
    "contact_person_name": "New Contact"
  }
  ```
- **Returns:** Updated client object

#### Delete Client

- **DELETE** `/api/v1/clients/{client_id}`
- **Auth Required:** Admin only
- **Returns:** `{ status: "success", detail: "Client deleted" }`

---

### Projects Endpoints

Base path: `/api/v1/projects`

Projects have ownership controls. Users can only see/modify their own projects unless they are admins.

#### List Projects

- **GET** `/api/v1/projects`
- **Auth Required:** Yes
- **Query Params:** `skip`, `limit`
- **Returns:** Array of Project objects
- **Permissions:** Admins see all, users see only their own

**Example Response:**

```json
[
  {
    "id": 1,
    "name": "Website Redesign",
    "key": "PROJ-001",
    "description": "Complete redesign of company website",
    "status": "in_progress",
    "priority": "high",
    "owner_id": "user-uuid",
    "client_id": "client-uuid",
    "start_date": "2025-01-01",
    "end_date": "2025-03-31",
    "budget": 50000,
    "spent": 15000,
    "currency": "USD",
    "billing_type": "billable",
    "is_archived": 0,
    "created_at": "2025-01-01T00:00:00.000Z",
    "updated_at": "2025-01-15T10:30:00.000Z"
  }
]
```

**Field Reference:**

- `status`: `"planning"`, `"in_progress"`, `"completed"`, `"on_hold"`
- `priority`: `"low"`, `"medium"`, `"high"`
- `billing_type`: `"billable"`, `"non_billable"`
- `budget` / `spent`: Amounts in smallest currency unit (cents for USD)

#### Get Project

- **GET** `/api/v1/projects/{project_id}`
- **Auth Required:** Yes (owner) or Admin
- **Expected Response Payload:**
  ```json
  {
    "id": 1,
    "name": "Website Redesign",
    "key": "PROJ-001",
    "description": "Complete redesign",
    "status": "in_progress",
    "priority": "high",
    "owner_id": "user-uuid",
    "client_id": "client-uuid",
    "start_date": "2025-01-01",
    "end_date": "2025-03-31",
    "budget": 50000,
    "spent": 15000,
    "currency": "USD",
    "billing_type": "billable",
    "is_archived": 0,
    "created_at": "2025-01-01T00:00:00.000Z",
    "updated_at": "2025-01-15T10:30:00.000Z"
  }
  ```

#### Create Project

- **POST** `/api/v1/projects`
- **Auth Required:** Yes
- **Expected Payload:**
  ```json
  {
    "name": "Mobile App Development",
    "key": "PROJ-002",
    "description": "Build iOS and Android apps",
    "status": "planning",
    "priority": "high",
    "client_id": "client-uuid",
    "start_date": "2025-02-01",
    "end_date": "2025-06-30",
    "budget": 100000,
    "currency": "USD",
    "billing_type": "billable"
  }
  ```
- **Returns:** Created project object
- **Note:** `owner_id` defaults to current user if not provided

#### Update Project

- **PATCH** `/api/v1/projects/{project_id}`
- **Auth Required:** Yes (owner) or Admin
- **Expected Payload:**
  ```json
  {
    "status": "completed",
    "spent": 20000,
    "is_archived": 0
  }
  ```
- **Returns:** Updated project object

#### Delete Project

- **DELETE** `/api/v1/projects/{project_id}`
- **Auth Required:** Yes (owner) or Admin
- **Returns:** `{ status: "success", detail: "Project deleted" }`

---

### Tasks Endpoints

Base path: `/api/v1/tasks`

Tasks support multi-user assignment through the `assignees` field.

#### List Tasks

- **GET** `/api/v1/tasks`
- **Auth Required:** Yes
- **Query Params:** `skip`, `limit`, `project_id?`
- **Returns:** Array of `TaskReadWithAssignees` objects
- **Permissions:** All authenticated users can view all tasks

**Example Response:**

```json
[
  {
    "id": 1,
    "name": "Design homepage mockup",
    "description": "Create high-fidelity mockup for new homepage",
    "due_date": "2025-01-30",
    "priority": "high",
    "status": "in_progress",
    "project_id": 1,
    "created_at": "2025-12-22T12:00:00.000Z",
    "updated_at": "2025-12-22T13:00:00.000Z",
    "task_assignees": [
      {
        "task_id": 1,
        "user_id": "user-uuid-1"
      }
    ]
  }
]
```

**Field Reference:**

- `priority`: `"low"`, `"medium"`, `"high"`
- `status`: Customizable per workflow (e.g., `"task"`, `"in_progress"`, `"completed"`, `"waiting"`)
- `task_assignees`: Array of objects containing `task_id` and `user_id`

#### Get Task

- **GET** `/api/v1/tasks/{task_id}`
- **Auth Required:** Yes
- **Expected Response Payload:**
  ```json
  {
    "id": 1,
    "name": "Design homepage mockup",
    "description": "Create high-fidelity mockup",
    "due_date": "2025-01-30",
    "priority": "high",
    "status": "in_progress",
    "project_id": 1,
    "created_at": "2025-12-22T12:00:00.000Z",
    "updated_at": "2025-12-22T13:00:00.000Z",
    "task_assignees": [
      {
        "task_id": 1,
        "user_id": "user-uuid-1"
      }
    ]
  }
  ```

#### Create Task

- **POST** `/api/v1/tasks`
- **Auth Required:** Yes
- **Expected Payload:**
  ```json
  {
    "name": "Implement login API",
    "description": "Create JWT authentication endpoints",
    "due_date": "2025-02-01",
    "priority": "high",
    "status": "task",
    "project_id": 1,
    "assignees": ["user-uuid-1", "user-uuid-2"]
  }
  ```
- **Returns:** `TaskReadWithAssignees` object

#### Update Task

- **PATCH** `/api/v1/tasks/{task_id}`
- **Auth Required:** Yes
- **Expected Payload:**
  ```json
  {
    "status": "in_progress",
    "assignees": ["user-uuid-3"]
  }
  ```
- **Returns:** Updated `TaskReadWithAssignees` object

**Note:** Setting `assignees` to `[]` removes all assignees. Omitting `assignees` leaves them unchanged.

#### Delete Task

- **DELETE** `/api/v1/tasks/{task_id}`
- **Auth Required:** Yes
- **Returns:** `{ status: "success", detail: "Task deleted" }`

---

### Notes Endpoints

Base path: `/api/v1/notes`

Notes support ownership and sharing with other users.

#### List Notes

- **GET** `/api/v1/notes`
- **Auth Required:** Yes
- **Query Params:** `skip`, `limit`, `task_id?`
- **Returns:** Array of Note objects
- **Permissions:** Admins see all, users see only their own

**Example Response:**

```json
[
  {
    "id": 1,
    "title": "Meeting Notes - Jan 15",
    "content": "Discussed project timeline and deliverables...",
    "type": "note",
    "tags": "[\"meeting\", \"important\"]",
    "is_pinned": 1,
    "is_archived": 0,
    "is_favorite": 0,
    "user_id": "owner-uuid",
    "task_id": null,
    "created_at": "2025-01-15T00:00:00.000Z",
    "updated_at": "2025-01-15T10:00:00.000Z"
  }
]
```

**Field Reference:**

- `type`: `"note"`, `"checklist"`, `"todo"`, `"journal"`
- `tags`: JSON string array (e.g., `'["tag1", "tag2"]'`)
- `is_pinned`, `is_archived`, `is_favorite`: 0 or 1 (boolean flags)

#### Get Note

- **GET** `/api/v1/notes/{note_id}`
- **Auth Required:** Yes (owner) or Admin
- **Expected Response Payload:**
  ```json
  {
    "id": 1,
    "title": "Meeting Notes - Jan 15",
    "content": "Discussed project timeline...",
    "type": "note",
    "tags": "[\"meeting\", \"important\"]",
    "is_pinned": 1,
    "is_archived": 0,
    "is_favorite": 0,
    "user_id": "owner-uuid",
    "task_id": null,
    "created_at": "2025-01-15T00:00:00.000Z",
    "updated_at": "2025-01-15T10:00:00.000Z"
  }
  ```

#### Create Note

- **POST** `/api/v1/notes`
- **Auth Required:** Yes
- **Expected Payload:**
  ```json
  {
    "title": "Project Ideas",
    "content": "Brainstorming session results...",
    "type": "note",
    "tags": "[\"brainstorm\", \"ideas\"]",
    "is_pinned": 1,
    "shared_with": ["user-uuid-1", "user-uuid-2"]
  }
  ```
- **Returns:** Created note object

#### Update Note

- **PATCH** `/api/v1/notes/{note_id}`
- **Auth Required:** Yes (owner) or Admin
- **Expected Payload:**
  ```json
  {
    "content": "Updated content...",
    "is_pinned": 0,
    "shared_with": ["user-uuid-3"]
  }
  ```
- **Returns:** Updated note object

#### Delete Note

- **DELETE** `/api/v1/notes/{note_id}`
- **Auth Required:** Yes (owner) or Admin
- **Returns:** `{ status: "success", detail: "Note deleted" }`

---

### Events Endpoints

Base path: `/api/v1/events`

Events are shared calendar resources. All users can view, but only creators or admins can modify.

#### List Events

- **GET** `/api/v1/events`
- **Auth Required:** Yes
- **Query Params:** `skip`, `limit`
- **Returns:** Array of Event objects
- **Permissions:** All users can view

**Example Response:**

```json
[
  {
    "id": 1,
    "title": "Team Standup",
    "description": "Daily standup meeting",
    "start": "2025-01-22T09:00:00Z",
    "end": "2025-01-22T09:30:00Z",
    "all_day": 0,
    "location": "Zoom",
    "organizer": "manager@example.com",
    "attendees": "[\"user1@example.com\", \"user2@example.com\"]",
    "status": "confirmed",
    "privacy": "public",
    "color": "#6366f1",
    "user_id": "creator-uuid",
    "created_at": "2025-01-20T10:00:00Z",
    "updated_at": "2025-01-20T10:00:00Z"
  }
]
```

**Field Reference:** (Note: `status`, `privacy`, and `recurrence` are case-insensitive)

- `start` / `end`: ISO 8601 datetime strings (required)
- `all_day`: 0 (time-specific) or 1 (all-day event)
- `status`: `"tentative"`, `"confirmed"`, `"cancelled"`
- `privacy`: `"public"`, `"private"`, `"confidential"`
- `attendees`: JSON array of email strings (e.g., `["user1@example.com", "user2@example.com"]`)
- `recurrence`: `"none"`, `"daily"`, `"weekly"`, `"monthly"`, `"yearly"`
- `reminders`: JSON array of EventReminder objects `{ days, hours, minutes }`
- `color`: HEX color string (e.g., `"#6366f1"`)
- `user_id`: UUID of the event creator
- `created_at` / `updated_at`: ISO 8601 timestamp strings

#### Get Event

- **GET** `/api/v1/events/{event_id}`
- **Auth Required:** Yes
- **Expected Response Payload:**
  ```json
  {
    "id": 1,
    "title": "Team Standup",
    "description": "Daily standup meeting",
    "start": "2025-01-22T09:00:00Z",
    "end": "2025-01-22T09:30:00Z",
    "all_day": 0,
    "location": "Zoom",
    "organizer": "manager@example.com",
    "attendees": ["user1@example.com", "user2@example.com"],
    "status": "confirmed",
    "privacy": "public",
    "recurrence": "none",
    "reminders": [{ "days": 0, "hours": 0, "minutes": 15 }],
    "color": "#6366f1",
    "user_id": "creator-uuid",
    "created_at": "2025-01-20T10:00:00Z",
    "updated_at": "2025-01-20T10:00:00Z"
  }
  ```

#### Create Event

- **POST** `/api/v1/events`
- **Auth Required:** Yes
- **Expected Payload:**
  ```json
  {
    "title": "Client Meeting",
    "description": "Quarterly business review",
    "start": "2025-01-25T14:00:00Z",
    "end": "2025-01-25T15:30:00Z",
    "location": "Conference Room A",
    "attendees": ["client@acme.com", "sales@example.com"],
    "status": "confirmed",
    "privacy": "private",
    "recurrence": "none",
    "reminders": [{ "days": 1, "hours": 0, "minutes": 0 }],
    "color": "#f43f5e"
  }
  ```
- **Returns:** Created event object

#### Update Event

- **PATCH** `/api/v1/events/{event_id}`
- **Auth Required:** Yes (creator) or Admin
- **Expected Payload:**
  ```json
  {
    "title": "Updated Meeting Title",
    "status": "cancelled"
  }
  ```
- **Returns:** Updated event object

#### Delete Event

- **DELETE** `/api/v1/events/{event_id}`
- **Auth Required:** Yes (creator) or Admin
- **Returns:** `{ status: "success", detail: "Event deleted" }`

---

### Decisions Endpoints

Base path: `/api/v1/decisions`

Decisions have ownership. Users can only see/modify their own unless they are admins.

#### List Decisions

- **GET** `/api/v1/decisions`
- **Auth Required:** Yes
- **Query Params:** `skip`, `limit`
- **Returns:** Array of Decision objects
- **Permissions:** Admins see all, users see only their own

**Example Response:**

```json
[
  {
    "id": 1,
    "name": "Choose tech stack for new project",
    "due_date": "2025-01-31",
    "user_id": "owner-uuid"
  }
]
```

#### Get Decision

- **GET** `/api/v1/decisions/{decision_id}`
- **Auth Required:** Yes (owner) or Admin
- **Expected Response Payload:**
  ```json
  {
    "id": 1,
    "name": "Choose tech stack",
    "due_date": "2025-01-31",
    "user_id": "owner-uuid"
  }
  ```

#### Create Decision

- **POST** `/api/v1/decisions`
- **Auth Required:** Yes
- **Expected Payload:**
  ```json
  {
    "name": "Decide on cloud provider",
    "due_date": "2025-02-15"
  }
  ```
- **Returns:** Created decision object
- **Note:** `user_id` defaults to current user if not provided

#### Update Decision

- **PATCH** `/api/v1/decisions/{decision_id}`
- **Auth Required:** Yes (owner) or Admin
- **Expected Payload:**
  ```json
  {
    "name": "Decide on AWS vs Azure",
    "due_date": "2025-02-28"
  }
  ```
- **Returns:** Updated decision object

#### Delete Decision

- **DELETE** `/api/v1/decisions/{decision_id}`
- **Auth Required:** Yes (owner) or Admin
- **Returns:** `{ status: "success", detail: "Decision deleted" }`

---

### Admin Endpoints

These endpoints are restricted to Administrators and Super Administrators.

#### Legacy Create User

- **POST** `/api/v1/user-admin/create`
- **Auth Required:** Admin only
- **Expected Payload:** Same as **POST** `/api/v1/users`
- **Returns:** User object

#### Generic Table Update

- **PATCH** `/api/v1/admin-db/tables/{table_name}/{pk_column}/{pk_value}`
- **Auth Required:** Super Admin only
- **Expected Payload:**
  ```json
  {
    "column_name_1": "new_value",
    "column_name_2": 123
  }
  ```
- **Returns:** `{ status: "success", rows_affected: 1 }`

#### Generic Table Create

- **POST** `/api/v1/admin-db/tables/{table_name}`
- **Auth Required:** Super Admin only
- **Expected Payload:**
  ```json
  {
    "id": "optional-uuid",
    "column_name_1": "value1",
    "column_name_2": "value2"
  }
  ```
- **Returns:** `{ status: "success", detail: "Record created" }`

---

## Permission Model

### User Roles

| Role          | Access Level                                     |
| ------------- | ------------------------------------------------ |
| `USER`        | Basic user, minimal permissions                  |
| `CLIENT`      | External client with limited access              |
| `STAFF`       | Internal staff member (default for new users)    |
| `MANAGER`     | Project manager with elevated permissions        |
| `ADMIN`       | Administrator with full access to most resources |
| `SUPER_ADMIN` | Super administrator with complete system access  |

### Resource Permissions Summary

| Resource      | View           | Create    | Update                  | Delete           |
| ------------- | -------------- | --------- | ----------------------- | ---------------- |
| **Users**     | Self or Admin  | Admin     | Self (limited) or Admin | Admin (not self) |
| **Clients**   | All users      | All users | Admin                   | Admin            |
| **Projects**  | Owner or Admin | All users | Owner or Admin          | Owner or Admin   |
| **Tasks**     | All users      | All users | All users               | All users        |
| **Notes**     | Owner or Admin | All users | Owner or Admin          | Owner or Admin   |
| **Events**    | All users      | All users | Creator or Admin        | Creator or Admin |
| **Decisions** | Owner or Admin | All users | Owner or Admin          | Owner or Admin   |

---

## Common Patterns

### Pagination

Most list endpoints support pagination via query parameters:

```
GET /api/v1/projects?skip=20&limit=10
```

- `skip`: Number of records to skip (default: 0)
- `limit`: Maximum records to return (default: 100)

### Filtering

Some endpoints support filtering:

```
GET /api/v1/tasks?project_id=1
GET /api/v1/notes?task_id=5
```

### Partial Updates

Use PATCH for partial updates. Only include fields you want to change:

```json
PATCH /api/v1/projects/1
{
  "status": "completed"
}
```

### Multi-User Assignment/Sharing

Tasks and Notes support assigning/sharing with multiple users:

**Tasks** use `assignees` array:

```json
{
  "assignees": ["user-uuid-1", "user-uuid-2"]
}
```

**Notes** use `shared_with` array:

```json
{
  "shared_with": ["user-uuid-1", "user-uuid-2"]
}
```

- Pass an array to set/replace assignees/shares
- Pass `[]` to remove all assignees/shares
- Omit the field to leave unchanged

### JSON String Arrays

Some fields store JSON arrays as strings:

- `Project.tags`
- `Event.attendees`
- `Event.reminders`
- `Note.tags`

**Format:** `'["item1", "item2", "item3"]'`

**Example:**

```json
{
  "tags": "[\"urgent\", \"backend\", \"api\"]"
}
```

### Date Formats

- **Dates:** ISO 8601 format `YYYY-MM-DD` (e.g., `"2025-01-31"`)
- **Datetimes:** ISO 8601 format `YYYY-MM-DDTHH:MM:SSZ` (e.g., `"2025-01-22T14:30:00Z"`)

### Currency Amounts

Budget and spent amounts are in the smallest currency unit:

- USD: cents (e.g., `$500.00` = `50000` cents)
- EUR: cents (e.g., `€250.50` = `25050` cents)

---

## Interactive API Documentation

FastAPI provides automatic interactive documentation:

- **Swagger UI:** `http://your-domain.com/docs`
- **ReDoc:** `http://your-domain.com/redoc`

These interfaces allow you to:

- View all endpoints
- See request/response schemas
- Test endpoints directly from the browser
- Authenticate and make real API calls

---

## Getting Help

For additional support or questions:

1. Check the interactive docs at `/docs`
2. Review this documentation
3. Contact the backend team

**API Version:** 1.0.0  
**Last Updated:** December 31, 2025
