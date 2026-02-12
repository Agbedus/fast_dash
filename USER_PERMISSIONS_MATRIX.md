# User Permission Matrix

This document outlines the simplified user permission matrix for the Fast Dash application. The goal is to align with standard corporate structures while maintaining the specific constraints requested.

## Summary of Roles

| Role              | Description                                                                                                                      |
| :---------------- | :------------------------------------------------------------------------------------------------------------------------------- |
| **Super Admin**   | System owner with full access to all data and operations.                                                                        |
| **Admin/Manager** | Operational lead who manages projects and clients but lacks system-level control (User management) and destructive capabilities. |
| **Staff**         | Internal team member focused on task execution. Access is limited to their own or shared work.                                   |
| **Client/User**   | External or limited-access users. (To be defined further).                                                                       |

---

## Detailed Matrix

| Feature/Model     | Super Admin |    Admin/Manager     |           Staff           |   Client/User   |
| :---------------- | :---------: | :------------------: | :-----------------------: | :-------------: |
| **Clients**       |    CRUD     | Create, Read, Update |           None            |      None       |
| **Projects**      |    CRUD     | Create, Read, Update |     Read (Own/Shared)     |  Read (Shared)  |
| **Tasks**         |    CRUD     | Create, Read, Update | Create, Read (Own/Shared) |  Read (Shared)  |
| **Notes**         |    CRUD     | Create, Read, Update | Create, Read (Own/Shared) |  Read (Shared)  |
| **Events**        |    CRUD     | Create, Read, Update | Create, Read (Own/Shared) |  Read (Shared)  |
| **Decisions**     |    CRUD     | Create, Read, Update | Create, Read (Own/Shared) |  Read (Shared)  |
| **Users**         |    CRUD     |         Read         |           None            |      None       |
| **Notifications** |    CRUD     |    Read (Global)     |   Read (Personal Only)    | Read (Personal) |

**Key:**

- **C**: Create
- **R**: Read
- **U**: Update
- **D**: Delete
- **Own/Shared**: Access restricted to records owned by the user or explicitly shared with them.

---

## Role-Specific Constraints

### 1. Super Admin

- **Full Access**: Can perform all operations (CRUD) on all models.
- **User Management**: Can create, edit, and delete user accounts.
- **Data Integrity**: The only role authorized to delete records (Clients, Projects, etc.).
- **System Alerts**: Receives notifications for all user signups and logins.
- **Global Awareness**: Receives notifications for all creation/update operations across all models.

### 2. Admin/Manager

- **Operational Management**: Can see and manage all clients, tasks, projects, notes, and events.
- **No Delete**: Cannot delete any records.
- **User Visibility**: Can see the user list to assign tasks, but cannot manage user accounts (create/delete/promote).
- **Client Visibility**: Full visibility into the client list and related data.
- **Model Alerts**: Receives notifications for all creations and updates of Tasks, Projects, Notes, and Events.

### 3. Staff

- **Productivity Focus**: Can create new tasks, projects (if allowed), notes, and events.
- **Selective Visibility**: Can only see objects they created or those shared with them.
- **No Edit/Delete**: Cannot edit or delete any records (even their own, as per current requirement - _Clarification needed: Is editing own objects allowed?_).
- **Zero Visibility**: Cannot see the user list or the client list.
- **Actionable Alerts**: Receives notifications only for items shared with them or assigned to them (e.g., Task Assignment, Note Shared).

### 4. Client/User (Proposed)

- **External/Limited Read**: Typically should only see Projects/Tasks specifically assigned or shared with them.
- **No Creation**: Usually Read-only access to progress reports/tasks.
- **Decision Needed**: Should they be able to create Notes or Events (e.g., feedback)?

## Corporate Alignment

This structure mimics a **Privacy-First Corporate Model**:

- **Super Admin** acts as the IT/Security department.
- **Admin/Manager** acts as the Business Operations/Account Management.
- **Staff** acts as the Delivery/Execution team.
- **Clients** have a "Guest" or "Stakeholder" view.

---

## Notification Triggers & Delivery

The system uses a hybrid model for notifications to ensure both persistence and real-time delivery.

### 1. Delivery Methods

- **Real-time**: Delivered instantly via WebSocket if the user is online.
- **Persistent**: Stored in the database for later retrieval (Notification Center).

### 2. Notification Matrix (Who gets what)

| Event                        | Super Admin | Admin/Manager |  Staff   | Client/User |
| :--------------------------- | :---------: | :-----------: | :------: | :---------: |
| **New User Signup**          |  Receives   |       -       |    -     |      -      |
| **User Login**               |  Receives   |       -       |    -     |      -      |
| **Task: Created/Updated**    |  Receives   |   Receives    |    -     |      -      |
| **Task: Assigned to You**    |  Receives   |   Receives    | Receives |  Receives   |
| **Note: Created/Updated**    |  Receives   |   Receives    |    -     |      -      |
| **Note: Shared with You**    |  Receives   |   Receives    | Receives |  Receives   |
| **Project: Created/Updated** |  Receives   |   Receives    |    -     |      -      |
| **Event: Created/Updated**   |  Receives   |   Receives    |    -     |      -      |

---

> [!NOTE]
> **Super Admins** and **Managers** act as observers for all operational changes. **Staff** and **Clients** receive targeted "Actionable" notifications only when directly involved.

---

> [!IMPORTANT]
> This matrix will be implemented across all API endpoints once validated.
