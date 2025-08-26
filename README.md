# Myoral

> **📌 NOTICE**: This project has been restructured into a master-client architecture. Please refer to the comprehensive documentation in the master_client_architecture folder for the latest implementation details.

## 🔄 Project Migration

This repository has been updated to implement a secure, HIPAA-compliant master-client architecture for the MyOral dental health application. The monolithic structure has been refactored into scalable, privacy-focused microservices.

## 📖 Updated Documentation

**👉 For complete documentation, setup instructions, and deployment guides, please see:**

### **[Master-Client Architecture Documentation](./master_client_architecture/README.md)**

The new documentation includes:
- ✅ Complete system architecture overview
- ✅ Security and HIPAA compliance features
- ✅ Database schema and API endpoints
- ✅ Deployment instructions with uvicorn
- ✅ Development and production setup guides
- ✅ Integration examples and code samples

## �️ **Database Update Plan**

**👉 For database migration and admin management features, please see:**

### **[Solution 1: Admin Management Implementation](./SOLUTION1_IMPLEMENTATION.md)**

This document contains the complete database update plan including:
- 📋 **Database Schema Changes** - Admin management with self-referential foreign keys
- 🔧 **Migration Scripts** - Ready-to-execute SQL migration files
- 🔑 **Admin Management APIs** - New endpoints for managing elderly users
- 📝 **Implementation Guide** - Step-by-step setup instructions
- 🧪 **Testing Procedures** - Validation and testing guidelines

**⚠️ IMPORTANT**: Execute the database migration before using the new admin features.

## �🚀 Quick Start

For immediate setup, navigate to the master_client_architecture folder:

```bash
cd master_client_architecture
```

Then follow the instructions in the [Master-Client Architecture README](./master_client_architecture/README.md).

**For database updates**, follow the migration guide in [SOLUTION1_IMPLEMENTATION.md](./SOLUTION1_IMPLEMENTATION.md).

---

## 📋 Legacy Information (Pre-Architecture Update)

<details>
<summary>Click to view original README content</summary>

Myoral is a deep learning-powered backend for intelligent oral photo analysis. Users upload oral images via the frontend app; the backend automatically performs tooth segmentation, caries (cavity) detection, gum recession analysis, and returns diagnostic images and detailed reports. The system supports user registration, login, profile management, photo uploads, and includes comprehensive model training and data processing tools.

### Project Structure

```
Myoral/
├── routers/           # FastAPI routes (user, analysis, upload, etc.)
├── models/            # Trained model files (not included)
├── Training/          # Training scripts, dataset splitting, mask visualization
├── masks/             # Generated segmentation masks
├── uploads/           # Uploaded user images
├── users/             # User avatars and resources
├── dataset/           # Raw/processed datasets (not included)
├── myenv/             # Python virtual environment
├── .gitignore
├── requirements.txt
└── ...
```

### Main Features

- **User Management:** Registration (email/phone), login (JWT token), profile update, avatar upload, token authentication.
- **Oral Photo Analysis:** Upload oral images for AI-based segmentation and diagnosis (teeth, caries, gum recession, etc.), with diagnostic images and structured reports.
- **Model Inference:** Integrated YOLOv8 segmentation model, supports automatic GPU/CPU switching.
- **Data Management:** Unified storage and management of photos, masks, user info.
- **Training & Data Tools:** Custom dataset splitting, mask visualization, model training and fine-tuning.
- **RESTful API:** CORS support, suitable for frontend-backend separation.

### Core API Endpoints

All endpoints are prefixed with `/v1`:

- `POST   /v1/register`         — User registration (email/phone)
- `POST   /v1/login`            — User login, returns JWT token
- `PUT    /v1/users/{userId}`   — Update user info
- `GET    /v1/users/{userId}`   — Get user info
- `POST   /v1/photoUpload`      — Upload oral photo
- `GET    /v1/readPhoto/{photoId}` — Get original photo
- `POST   /v1/analysis`         — Upload and analyze photo, returns diagnostic image and report
- `GET    /v1/analysis/mask/{userId}` — Get segmentation mask (supports latest/all/specific time)

### Notes

- This project is for academic and research use only. Commercial use is prohibited.
- Model files and datasets must be prepared separately and are not included in the repository.
- Keep your secret keys and database credentials secure.

</details>

---

**Myoral — Intelligent Oral Analysis Backend with Master-Client Architecture for Better Oral Health Management**
