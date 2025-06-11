from datetime import datetime, timezone, timedelta 
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status, Path
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import secrets 
import numpy as np 
from PIL import Image 
import io 
import os 
import uuid 
from pydantic import BaseModel 
from typing import Dict, Optional
from sqlalchemy.orm import Session
from database import get_db, fetch_user_by_token
import urllib.parse

# ---------- Router Configuration ----------
router = APIRouter()
security = HTTPBearer()

# ---------- Models ----------
class MaskOffset(BaseModel):
    x: int 
    y: int 

class AnalysisResponse(BaseModel):
    results: Dict 
    message: str 

# ---------- Constants ----------
DENTAL_ISSUES = {
    0: "No issue",
    1: "Moderate caries",
    2: "Severe caries",
    3: "Fracture"
}

GUM_ISSUES = {
    0: "No issue",
    1: "Moderate gum inflammation",
    2: "Severe gum inflammation",
    3: "Gingivitis",
    4: "Gum swelling",
    5: "Redness",
    6: "Receding gum",
    7: "Gum bleeding",
    8: "Gum boil"
}

# ---------- Helper Functions ----------
def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    token = credentials.credentials
    user = fetch_user_by_token(token, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    return user.userId

def user_exists(userId: str) -> bool:
    """Validate user ID existence"""
    # In production, query your user database
    return bool(userId and len(userId.strip()) > 0)

def log_error(message: str):
    """Log error messages"""
    print(f"[ERROR] {datetime.now()}: {message}")
    # In production, use proper logging system

def generate_mask_image(mask_array: np.ndarray) -> Image:
    """Generate RGBA mask image from annotation array"""
    height, width = mask_array.shape[:2]
    rgba = np.zeros((height, width, 4), dtype=np.uint8)
    
    rgba[..., 0] = mask_array[..., 0] * 2  # Teeth identification
    rgba[..., 1] = mask_array[..., 1] * 85  # Dental issues
    rgba[..., 2] = mask_array[..., 2] * 28  # Gum issues
    rgba[..., 3] = 255  # Opacity
    
    return Image.fromarray(rgba)

def generate_signed_url(user_id: str, filename: str) -> str:
    """Generate signed URL for accessing mask images"""
    expiry = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
    signature = secrets.token_urlsafe(16)
    return f"https://api.myoral.ai/analysis/{user_id}/mask/{filename}?expiry={expiry}&signature={signature}"

def analyze_oral_health(image: Image) -> Dict:
    """Analyze oral health from image (mock implementation)"""
    np_image = np.array(image.convert("RGB"))
    mask_array = np.zeros((*np_image.shape[:2], 3), dtype=np.uint8)
    
    h, w = mask_array.shape[:2]
    cx, cy = w//2, h//2
    
    # Generate sample teeth markers
    for y in range(cy-10, cy+10):
        for x in range(cx-5, cx+5):
            if 0 <= y < h and 0 <= x < w:
                mask_array[y, x, 0] = np.random.choice([1, 9, 17, 25])
    
    # Add sample issues
    for _ in range(20):
        y, x = np.random.randint(10, h-10), np.random.randint(10, w-10)
        mask_array[y, x, 1] = np.random.choice([0, 1, 2, 3], p=[0.7, 0.1, 0.1, 0.1])
        mask_array[y, x, 2] = np.random.choice([0, 1, 3, 6], p=[0.8, 0.05, 0.1, 0.05])
    
    # Generate diagnosis
    max_issue = np.max(mask_array[..., 1:])
    if max_issue > 1:
        diagnosis = "Dental illnesses detected. Please consult a dentist."
    elif max_issue > 0:
        diagnosis = "Early symptoms of dental issues detected. Please improve your oral hygiene"
    else:
        diagnosis = "Your teeth are healthy"
    
    return {
        "diagnosis": diagnosis,
        "mask_array": mask_array,
        "offset": {"x": cx-5, "y": cy-10}
    }

def normalize_timestamp(timestamp: str) -> str:
    """Convert URL-encoded timestamp to filesystem-safe format"""
    # Decode URL-encoded timestamp
    decoded = urllib.parse.unquote(timestamp)
    # Convert Z to UTC offset if needed
    decoded = decoded.replace('Z', '+00:00')
    # Convert to datetime and back to get consistent format
    try:
        dt = datetime.fromisoformat(decoded)
        # Use the same format as photoUpload.py
        return dt.isoformat().replace(':', '-')
    except ValueError as e:
        log_error(f"Failed to parse timestamp {decoded}: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid timestamp format. Expected ISO format like '2025-06-10T08:31:03.435867Z'"
        )

def get_photo_paths(userId: str, timestamp: str) -> Dict[str, str]:
    """Construct and validate photo paths"""
    try:
        # Normalize the timestamp for filesystem
        normalized_timestamp = normalize_timestamp(timestamp)
        
        # Construct base directory
        photo_dir = os.path.join("uploads", userId, normalized_timestamp)
        
        # For debugging
        log_error(f"Looking for photos in directory: {photo_dir}")
        
        # Define photo paths
        photos = {
            "front": os.path.join(photo_dir, "front.jpg"),
            "left": os.path.join(photo_dir, "left.jpg"),
            "right": os.path.join(photo_dir, "right.jpg")
        }
        
        # List available files for debugging
        if os.path.exists(photo_dir):
            files = os.listdir(photo_dir)
            log_error(f"Files found in directory: {files}")
        else:
            log_error(f"Directory not found: {photo_dir}")
            # Check parent directory
            parent_dir = os.path.dirname(photo_dir)
            if os.path.exists(parent_dir):
                log_error(f"User directory exists. Available timestamps:")
                parent_files = os.listdir(parent_dir)
                log_error(str(parent_files))
            else:
                log_error(f"User directory not found: {parent_dir}")
        
        # Verify directory exists
        if not os.path.exists(photo_dir):
            raise HTTPException(
                status_code=404,
                detail=f"Photo directory not found. Please ensure photos are uploaded first."
            )
        
        # Verify at least front photo exists
        if not os.path.exists(photos["front"]):
            raise HTTPException(
                status_code=404,
                detail=f"Front photo not found. Please ensure all required photos are uploaded."
            )
        
        return photos
    except HTTPException:
        raise
    except Exception as e:
        log_error(f"Error in get_photo_paths: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process photo paths: {str(e)}"
        )

# ---------- API Endpoint ----------
@router.post(
    "/analysis/{userId}/{timestamp}",
    summary="Analyze uploaded photos",
    description="Analyzes the oral health status from previously uploaded photos",
    response_model=AnalysisResponse,
    status_code=200,
    responses={
        400: {"description": "Invalid photo IDs or request"},
        401: {"description": "Unauthorized - Invalid or missing token"},
        403: {"description": "Forbidden - Not authorized for this user"},
        404: {"description": "Photos not found"},
        500: {"description": "Internal server error - Processing failed"}
    }
)
async def analyze_photos(
    userId: str = Path(..., description="User identifier"),
    timestamp: str = Path(..., description="Timestamp of photo upload"),
    current_user: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Analyze oral health from uploaded photos."""
    
    # Authorization check
    if userId != current_user:
        log_error(f"Unauthorized access attempt to user {userId}'s photos by {current_user}")
        raise HTTPException(
            status_code=403,
            detail="Not authorized to analyze photos for other users"
        )
      
    # User existence check
    if not user_exists(userId):
        log_error(f"Analysis attempted for non-existent user: {userId}")
        raise HTTPException(status_code=404, detail="User not found")
    
    try:
        # Get validated photo paths
        try:
            photos = get_photo_paths(userId, timestamp)
        except HTTPException as e:
            log_error(f"Photo access error for user {userId}: {str(e)}")
            raise
        
        analysis_results = {}
        mask_urls = {}
        
        # Process each available photo
        for position, path in photos.items():
            if not os.path.exists(path):
                log_error(f"Missing {position} photo for user {userId}")
                continue
                
            try:
                # Process image
                img = Image.open(path).convert("RGB")
                
                # Analyze health
                analysis = analyze_oral_health(img)
                
                # Generate and store mask
                mask_filename = f"{uuid.uuid4().hex}-{position}-mask.png"
                mask_dir = os.path.join("static", "masks")
                os.makedirs(mask_dir, exist_ok=True)
                
                mask_path = os.path.join(mask_dir, mask_filename)
                mask_img = generate_mask_image(analysis["mask_array"])
                mask_img.save(mask_path)
                
                # Store results
                mask_urls[position] = generate_signed_url(userId, mask_filename)
                analysis_results[position] = {
                    "diagnosis": analysis["diagnosis"],
                    "maskImageUrl": mask_urls[position],
                    "maskOffset": analysis["offset"]
                }
            except IOError as e:
                log_error(f"Failed to process {position} image for user {userId}: {str(e)}")
                continue
        
        if not analysis_results:
            raise HTTPException(
                status_code=500,
                detail="Failed to process any of the uploaded photos"
            )
        
        # Combine diagnoses to make overall assessment
        diagnoses = [result["diagnosis"] for result in analysis_results.values()]
        if any("Dental illnesses detected" in d for d in diagnoses):
            overall_diagnosis = "Dental illnesses detected. Please consult a dentist."
        elif any("Early symptoms" in d for d in diagnoses):
            overall_diagnosis = "Early symptoms of dental issues detected. Please improve your oral hygiene"
        else:
            overall_diagnosis = "Your teeth are healthy"
        
        return AnalysisResponse(
            results={
                "overall_diagnosis": overall_diagnosis,
                "detailed_analysis": analysis_results
            },
            message="Analysis completed successfully"
        )
        
    except IOError as e:
        log_error(f"Image processing failed for {userId}: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid image data or format: {str(e)}"
        )
    except Exception as e:
        log_error(f"Analysis failed for {userId}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e) if str(e) else "Internal server error during analysis"
        )