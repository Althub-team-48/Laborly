## Laborly Platform Overview

This document explains the user experience and overall flow of the Laborly platform. It outlines how the system works for clients, workers, and admins, along with key features included in the MVP (Minimum Viable Product).

---

### 1. User Types
- **Clients:** Individuals who need services and want to find skilled workers.
- **Workers:** Skilled individuals offering services who can be discovered and hired.
- **Admins:** Trusted internal users responsible for moderation and safety.

---

### 2. Registration & Login
- Users can sign up using email and password.
- Login is via secure token-based authentication.
- Google or Apple login is also supported.
- Terms and Conditions must be accepted before account creation.

---

### 3. Profiles
- Clients and Workers have dedicated profile pages.
- Workers can update their service offerings, location, and availability.
- Clients can update personal details and view saved workers.

---

### 4. Worker Discovery
- Clients can search and filter workers by:
  - Type of service
  - Location
  - Rating
  - Availability
- Workers can be saved to a "favorites" list.

---

### 5. KYC (Verification)
- Workers must upload a valid ID and selfie for manual identity verification.
- This ensures that workers are legitimate and helps build trust.
- Workers cannot offer services until approved.

---

### 6. Messaging & Contact
- Clients initiate private message threads with workers.
- Workers can reply and continue the conversation.
- Contact details (phone/email) are hidden until a job is formally accepted.

---

### 7. Job Acceptance Flow
- After agreeing on terms in a chat, either party can confirm a job.
- The system creates a job record marked as "negotiating."
- Once both parties are aligned, the job becomes "accepted."
- Either party can mark the job as "completed."
- When both confirm completion, the job is "finalized."
- Jobs can be cancelled if needed, with reasons recorded.

---

### 8. Ratings & Reviews
- Clients can rate and review workers after job completion.
- One review is allowed per job.
- Ratings use a 1–5 star system with optional written feedback.
- Workers accumulate average ratings over time.

---

### 9. Admin Controls
- Admins can:
  - Approve or reject worker KYC documents
  - Freeze or ban user accounts
  - Delete user accounts on request
  - Moderate inappropriate reviews
- Admins do not interfere with job details unless absolutely necessary.

---

### 10. Dashboards
- **Clients** see:
  - Active jobs
  - Past job history
  - Favorited workers

- **Workers** see:
  - Active and completed jobs
  - KYC status
  - Profile and service info
  - Received reviews and ratings

---

### 11. Platform Security
- All user inputs are validated to prevent errors and abuse.
- Uploaded documents are scanned and sanitized.
- Role-based access ensures users only access their permitted features.
- The system logs all admin actions and critical user events.

---

### 12. Future Enhancements (Beyond MVP)
- Automated KYC using third-party services
- Admin dashboard UI
- Notifications and alerts
- Payment or escrow functionality

---