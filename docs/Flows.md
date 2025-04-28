Alright — you gave me a very well-structured base.  
# Laborly — Platform User Flow Guide

---

## Table of Contents

- [1. Common Flows (All Users)](#1-common-flows-all-users)
  - [1.1 Registration](#11-registration)
  - [1.2 Email Verification](#12-email-verification)
  - [1.3 Login](#13-login)
  - [1.4 Password Reset](#14-password-reset)
  - [1.5 Email Address Update](#15-email-address-update)
- [2. Client User Flow](#2-client-user-flow)
- [3. Worker User Flow](#3-worker-user-flow)
- [4. Admin User Flow](#4-admin-user-flow)

---

## 1. Common Flows (All Users)

### 1.1 Registration

1. **Visit Signup Page:**  
   Navigate to the registration page.

2. **Enter Details:**  
   Provide first name, last name, email address, phone number, password, and select a role (Client or Worker).

3. **Agree to Terms:**  
   Accept the Terms and Conditions.

4. **Submit:**  
   A basic, unverified user account is created.

5. **Email Sent:**  
   A verification link is sent to the user's email address.

> **Note:** Admins are created internally and do not register publicly.

---

### 1.2 Email Verification

1. **Check Email:**  
   Access the verification email sent by Laborly.

2. **Click Verification Link:**  
   Click the link before it expires.

3. **Verification Confirmed:**  
   The system marks the account as verified.

4. **Welcome Email:**  
   A welcome email confirms successful activation.

5. **Login Enabled:**  
   User can now access their account.

---

### 1.3 Login

1. **Visit Login Page:**  
   Navigate to the login page.

2. **Enter Credentials:**  
   Submit registered email and password.

3. **Submit:**  
   Credentials are authenticated against stored values.

4. **Authentication:**  
   If successful and email is verified, a secure JWT session token is issued.

5. **Alternative Login:**  
   Users may authenticate via Google OAuth, automatically creating an account if it's their first login.

---

### 1.4 Password Reset

1. **Visit Forgot Password Page:**  
   Click the "Forgot Password" link.

2. **Enter Registered Email:**  
   Submit email to request reset.

3. **Email Sent:**  
   A secure, time-limited reset link is emailed.

4. **Click Reset Link:**  
   Access the reset password page.

5. **Set New Password:**  
   Enter and confirm a new password meeting security requirements.

6. **Password Updated:**  
   Password is saved, reset link invalidated, and confirmation email sent.

---

### 1.5 Email Address Update

1. **Request Change:**  
   From profile settings, request an email update.

2. **Verification Email Sent:**  
   A confirmation link is sent to the new email address.

3. **Notification Sent:**  
   A notification is sent to the old email address.

4. **Confirm New Email:**  
   Click the confirmation link sent to the new email.

5. **Update Completed:**  
   Email address is updated and a confirmation is sent.

---

## 2. Client User Flow

Clients seek to find and hire Workers for services.

1. **Login:**  
   Access the Client dashboard.

2. **Search for Workers:**  
   Use filters like service type, location, availability, and ratings.

3. **View Worker Profiles:**  
   Review Worker bios, experience, skills, average ratings, and KYC status.

4. **Save Favorites (Optional):**  
   Bookmark promising Workers.

5. **Initiate Contact:**  
   Click "Contact" or "Message" on a Worker’s profile.

6. **Send Initial Message:**  
   Describe the required service and start a messaging thread.

7. **Negotiate:**  
   Discuss service details, scope, timeline, and price via the message thread.

8. **Initiate Job:**  
   Once agreed, initiate a job record with status `NEGOTIATING`.

9. **Worker Accepts Job:**  
   Worker accepts the job, updating the status to `ACCEPTED`.

10. **Monitor Progress:**  
    Track active job statuses through the dashboard.

11. **Mark as Completed:**  
    Confirm job completion once work is finished.

12. **Leave Review:**  
    Provide a 1–5 star rating and optional text review.

13. **View Job History:**  
    Access a complete history of past jobs and reviews.

---

## 3. Worker User Flow

Workers aim to get verified, list services, and complete jobs to build their reputation.

1. **Login:**  
   Access the Worker dashboard.

2. **Complete Profile:**  
   Provide a professional bio, skills, experience, and optionally a profile picture.

3. **Submit KYC Documents:**  
   Upload selected ID document and selfie.

4. **Await KYC Approval:**  
   Admins review the submission. Service listing is disabled until approval.

5. **List Services:**  
   Create detailed service listings with title, description, category, and location.

6. **Set Availability:**  
   Toggle availability status (e.g., Available/Not Available).

7. **Receive Messages:**  
   Get inquiries from potential Clients.

8. **Negotiate:**  
   Discuss and finalize service terms via messaging.

9. **Receive Job Offer:**  
   Clients initiate formal job offers.

10. **Accept or Reject Job:**
    - **Accept:** Status changes to `ACCEPTED`.
    - **Reject:** Status changes to `REJECTED`, and messaging may close.

11. **Perform the Work:**  
    Deliver the agreed-upon service.

12. **Mark as Completed:**  
    Finalize job by marking it as completed.

13. **Receive Review:**  
    Collect Client ratings and feedback post-completion.

14. **Monitor Dashboard:**  
    Track job assignments, review history, ratings, and KYC status.

---

## 4. Admin User Flow

Admins manage platform integrity, verification, and moderation.

1. **Login:**  
   Access the Admin dashboard.

2. **Review Pending KYCs:**  
   Access submitted documents and verify identity proof.

3. **Approve or Reject KYCs:**  
   Update Worker status to `APPROVED` or `REJECTED` based on review.

4. **Manage Users:**  
   Perform moderation actions:
   - **Freeze/Unfreeze** accounts
   - **Ban/Unban** users
   - **Delete** user accounts logically

5. **Moderate Reviews (Optional/Future):**  
   Review and remove flagged user reviews if necessary.

6. **Monitor Platform Activity:**  
   Use system logs and dashboards to oversee platform health.

---
