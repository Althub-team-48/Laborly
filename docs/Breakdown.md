# Laborly Backend — Breakdown of the `app/` Directory

This document explains the structure and responsibilities of each sub-folder within the `app/` directory of the Laborly backend.  
Each folder represents a distinct functional module of the application.

---

## Table of Contents

- [📁 app/admin/ — Administration](#-appadmin--administration)
- [📁 app/auth/ — Authentication and Authorization](#-appauth--authentication-and-authorization)
- [📁 app/client/ — Client Management](#-appclient--client-management)
- [📁 app/core/ — Core Utilities](#-appcore--core-utilities)
- [📁 app/database/ — Database Layer](#-appdatabase--database-layer)
- [📁 app/job/ — Job Management](#-appjob--job-management)
- [📁 app/messaging/ — User Messaging System](#-appmessaging--user-messaging-system)
- [📁 app/review/ — Ratings and Reviews](#-appreview--ratings-and-reviews)
- [📁 app/service/ — Service Listings](#-appservice--service-listings)
- [📁 app/worker/ — Worker Management](#-appworker--worker-management)

---

## 📁 `app/admin/` — Administration

**Purpose:**  
Manages all administrative features including moderation, KYC verification, and user account controls.

**Key Responsibilities:**
- **KYC Management:** Approve or reject worker identity verification requests.
- **User Account Control:** Freeze, ban, unban, and soft-delete users.
- **Review Moderation:** View and moderate flagged reviews.
- **User Management:** List and filter users across the platform.

**Contains:** `routes.py`, `services.py`, `schemas.py`

---

## 📁 `app/auth/` — Authentication and Authorization

**Purpose:**  
Handles user registration, authentication, session management, and related security processes.

**Key Responsibilities:**
- **Registration:** Sign up new users with password hashing and email verification.
- **Login:** Authenticate using email/password or Google OAuth2.
- **Email Verification:** Activate accounts through secure email tokens.
- **Password Reset:** Facilitate secure password changes.
- **Email Update:** Allow users to update their email address with confirmation.
- **Logout:** Securely invalidate sessions via JWT blacklisting.

**Contains:** `routes.py`, `services.py`, `schemas.py`

---

## 📁 `app/client/` — Client Management

**Purpose:**  
Contains features specific to users operating as Clients.

**Key Responsibilities:**
- **Profile Management:** Update personal details, manage profile pictures.
- **Favorite Workers:** Maintain a list of favorite workers.
- **Job History:** View past job engagements.
- **Public Profile:** Control visibility of public client profile data.

**Contains:** `models.py`, `routes.py`, `services.py`, `schemas.py`

---

## 📁 `app/core/` — Core Utilities

**Purpose:**  
Hosts shared configurations, utilities, and reusable functionalities.

**Key Responsibilities:**
- **Configuration:** Load settings from environment variables.
- **Authentication Dependencies:** Manage user and RBAC dependencies.
- **Logging:** Centralized logging setup.
- **Token Management:** Create and decode JWT tokens.
- **Security Utilities:** Rate limiting, blacklist handling, validation.
- **File Uploads:** Secure uploads to AWS S3 with validation.
- **Email Handling:** Send transactional emails via FastAPI-Mail.

**Contains:** Various utility modules (`config.py`, `dependencies.py`, `logging.py`, `upload.py`, `tokens.py`, etc.)

---

## 📁 `app/database/` — Database Layer

**Purpose:**  
Manages database connections, ORM base classes, and shared enumerations.

**Key Responsibilities:**
- **Session Management:** Configure async SQLAlchemy sessions.
- **Base Model Definition:** Unified ORM base metadata.
- **User Models:** Define `User` and `KYC` database schemas.
- **Enumerations:** Central enums like `UserRole`, `KYCStatus`, and `JobStatus`.

**Contains:** `base.py`, `enums.py`, `models.py`, `session.py`

---

## 📁 `app/job/` — Job Management

**Purpose:**  
Handles the lifecycle of jobs initiated by Clients and performed by Workers.

**Key Responsibilities:**
- **Job Creation:** Set up jobs with `NEGOTIATING` status.
- **State Management:** Progress jobs through statuses like `ACCEPTED`, `COMPLETED`, `REJECTED`.
- **Timestamping:** Track start, completion, and cancellation dates.
- **Linkages:** Connect jobs to services, clients, workers, and message threads.

**Contains:** `models.py`, `routes.py`, `services.py`, `schemas.py`

---

## 📁 `app/messaging/` — User Messaging System

**Purpose:**  
Enables communication between Clients and Workers through a secure messaging system.

**Key Responsibilities:**
- **Thread Management:** Manage conversation threads between users.
- **Message Handling:** Save and retrieve individual messages.
- **WebSocket Real-Time Chat:** Manage live chats through WebSocket connections.
- **Access Control:** Enforce participant-based messaging permissions.

**Contains:** `models.py`, `routes.py`, `services.py`, `schemas.py`, `manager.py`, `websocket.py`

---

## 📁 `app/review/` — Ratings and Reviews

**Purpose:**  
Manages client reviews and ratings for workers upon job completion.

**Key Responsibilities:**
- **Submit Reviews:** Allow Clients to submit a 1–5 star rating and text feedback.
- **Review Storage:** Link reviews to workers, clients, and jobs.
- **Moderation Ready:** Support for flagged reviews.
- **Worker Stats:** Calculate average ratings and review counts.

**Contains:** `models.py`, `routes.py`, `services.py`, `schemas.py`

---

## 📁 `app/service/` — Service Listings

**Purpose:**  
Manages service offerings created by Workers for Clients to discover.

**Key Responsibilities:**
- **Service CRUD:** Allow Workers to create, update, and delete services.
- **Public Search:** Enable Clients (and guests) to search and filter services by title or location.
- **Public Detail Views:** Display detailed information for specific services.

**Contains:** `models.py`, `routes.py`, `services.py`, `schemas.py`

---

## 📁 `app/worker/` — Worker Management

**Purpose:**  
Handles features specific to Worker users, including profiles and KYC verification.

**Key Responsibilities:**
- **Profile Management:** Update bio, skills, experience, and profile photos.
- **Availability:** Toggle "Available for Hire" status.
- **KYC Submission:** Upload and track KYC verification documents.
- **Job History:** View completed and active jobs.
- **Public Profile:** Provide limited public visibility into Worker profiles.

**Contains:** `models.py`, `routes.py`, `services.py`, `schemas.py`

---
