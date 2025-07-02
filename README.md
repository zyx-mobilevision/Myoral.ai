# Myoral

Myoral is the backend for an AI-powered oral photo diagnosis app. Users can take oral photos via the app, and the backend uses deep learning models to segment and analyze the images, returning diagnostic results. This repository contains all backend code, including API routes, environment configuration, database design, and model training scripts.

## Project Structure

```
Myoral/
├── routers/           # FastAPI routes (e.g., analyze.py, register.py, update.py)
├── models/            # Trained model files 
├── Training/          # Dataset, training scripts, data splitting, visualization tools
├── masks/             # Generated segmentation masks
├── uploads/           # Uploaded user images
├── dataset/           # Raw/processed datasets 
├── myenv/             # Python virtual environment
├── .gitignore
├── requirements.txt   # Python dependencies
└── ...
```

## Main Features

- **User Management:** Registration, login, profile update, and avatar upload.
- **Oral Photo Analysis:** Upload oral photos for AI-based segmentation and diagnosis (teeth, caries, gum, etc.).
- **Model Training & Inference:** Integrated YOLOv8 segmentation model with custom training and inference support.
- **Data Management:** Dataset splitting, mask visualization, and related utilities.

## Getting Started

1. **Environment Setup**

   It is recommended to use Python 3.8+ and a virtual environment:

   ```sh
   python -m venv myenv
   # On Windows:
   myenv\Scripts\activate
   # On macOS/Linux:
   source myenv/bin/activate
   pip install -r requirements.txt
   ```

2. **Model Files**

   Place your trained model files (e.g., `models/6_26best.pt`) in the `models/` directory.  
   *Note: Model files are not included in the repository due to size limits.*

3. **Start the Backend Server**

   ```sh
   uvicorn main:app --reload
   ```

4. **API Endpoints**

   - `/v1/register` — User registration
   - `/v1/analysis` — Upload and analyze oral photos
   - `/v1/analysis/mask/{userid}` — Get segmentation mask results
   - See the `routers/` directory for more endpoints and details

## Training & Data

- Training scripts and dataset utilities are in the `Training/` directory.
- Supports custom dataset splitting and mask visualization.

## Notes

- Folders like `models/`, `masks/`, `uploads/`, and `dataset/` are ignored by `.gitignore` and not tracked by git.
- Model files must be downloaded or trained separately.

## Contribution

Feel free to open issues or submit pull requests to help improve this project!

---

**This project is for research and educational purposes only. Commercial use is prohibited.**