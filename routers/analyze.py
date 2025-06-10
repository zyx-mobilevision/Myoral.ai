from datetime import datetime, timezone, timedelta 
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status, Path
from fastapi.security  import HTTPBearer, HTTPAuthorizationCredentials
import secrets 
import numpy as np 
from PIL import Image 
import io 
import os 
import uuid 
from pydantic import BaseModel 
from typing import Dict 
from sqlalchemy.orm import Session
from database import get_db, fetch_user_by_token 
# ---------- 模块化设计说明 ----------
# 1. 路由组织使用APIRouter实现模块化 
# 2. 安全验证通过OAuth2Bearer实现JWT验证 
# 3. 请求/响应模型使用Pydantic严格定义 
# 4. 错误处理统一规范化 
# 5. 生成签名URL满足云存储访问需求 
# 6. 模拟实际分析过程提供测试接口 
# --------------------------------- 
router = APIRouter()
# --- 安全验证配置 --- 
security = HTTPBearer()
def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    token = credentials.credentials
    user = fetch_user_by_token(token, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    return user.userId

# --- 数据模型定义 --- 
class MaskOffset(BaseModel):
    x: int 
    y: int 
class AnalysisResponse(BaseModel):
    results: Dict 
    message: str 
# --- 常量定义 (来自Appendix B) --- 
TEETH_MAP = {
    # 永久牙 (perm)
    1: "Upper left central incisor (perm)",
    2: "Upper left lateral incisor (perm)",
    # ... 完整映射见下文生成代码 
}
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
# ---------- 核心业务逻辑 ----------
def generate_mask_image(mask_array: np.ndarray)  -> Image:
    """根据标注要求生成RGBA掩码图像"""
    height, width = mask_array.shape  
    rgba = np.zeros((height,  width, 4), dtype=np.uint8) 
    
    # 红通道: 牙齿标识 
    rgba[..., 0] = mask_array[..., 0] * 2  # 增强可视化效果 
    # 绿通道: 牙齿问题 
    rgba[..., 1] = mask_array[..., 1] * 85  # 增强可视化效果 
    # 蓝通道: 牙龈问题 
    rgba[..., 2] = mask_array[..., 2] * 28   # 增强可视化效果 
    rgba[..., 3] = 255  # 完全不透明 
    
    return Image.fromarray(rgba) 
def generate_signed_url(user_id: str, filename: str) -> str:
    """生成带签名的资源URL (伪代码示例)"""
    expiry = (datetime.now(timezone.utc)  + timedelta(days=365)).isoformat()
    signature = secrets.token_urlsafe(16) 
    return f"https://api.myoral.ai/analysis/{user_id}/mask/{filename}?expiry={expiry}&signature={signature}" 
def analyze_oral_health(image: Image) -> Dict:
    """模拟AI分析过程 - 实际应替换为真实模型调用"""
    # 1. 创建随机掩码 (实际实现需替换为模型推理)
    np_image = np.array(image)[...,  :3]  # 忽略alpha通道 
    mask_array = np.zeros((*np_image.shape[:2],  3), dtype=np.uint8) 
    
    # 在中央区域生成模拟牙齿标识 
    h, w = mask_array.shape[:2] 
    cx, cy = w//2, h//2 
    for y in range(cy-10, cy+10):
        for x in range(cx-5, cx+5):
            mask_array[y, x, 0] = np.random.choice([1,  9, 17, 25])  # 随机门牙 
    
    # 随机添加牙齿问题和牙龈问题 
    for _ in range(20):
        y, x = np.random.randint(10,  h-10), np.random.randint(10,  w-10)
        mask_array[y, x, 1] = np.random.choice([0,  1, 2, 3], p=[0.7, 0.1, 0.1, 0.1])
        mask_array[y, x, 2] = np.random.choice([0,  1, 3, 6], p=[0.8, 0.05, 0.1, 0.05])
    
    # 2. 生成诊断结论 
    if np.max(mask_array[...,1:])  > 1:
        diagnosis = "Dental illnesses detected. Please consult a dentist."
    elif np.max(mask_array[...,1:])  > 0:
        diagnosis = "Early symptoms of dental issues detected. Please improve your oral hygiene"
    else:
        diagnosis = "Your teeth are healthy"
    
    return {
        "diagnosis": diagnosis,
        "mask_array": mask_array,
        "offset": {"x": cx-5, "y": cy-10}  # 模拟偏移值 
    }
# ---------- API端点实现 ----------
@router.post( 
    "/v1/analysis/{user_id}",
    response_model=AnalysisResponse,
    status_code=200,
    responses={
        400: {"description": "Invalid image format"},
        401: {"description": "Unauthorized"},
        404: {"description": "User not found"},
        500: {"description": "Processing error"}
    }
)
async def analyze_photos(
    user_id: str = Path(..., description="User identifier"),
    image: UploadFile = File(..., description="Oral photo in JPEG/PNG format"),
    token: str = Depends(verify_token)  # JWT验证 
):
    """
    牙齿健康分析端点:
    1. 验证用户身份 
    2. 接收并校验口腔照片 
    3. 运行AI分析算法 
    4. 生成牙齿标注掩码 
    5. 返回诊断结果和资源URL 
    """
    # 1. 验证用户存在性 (伪代码)
    if not user_exists(user_id):  # 应替换为真实用户服务调用 
        raise HTTPException(status_code=404, detail="User not found")
    # 2. 校验图像格式 
    if image.content_type  not in ["image/jpeg", "image/png"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid image format. Only JPEG/PNG accepted"
        )
    try:
        # 3. 处理上传图像 
        contents = await image.read() 
        uploaded_img = Image.open(io.BytesIO(contents)).convert("RGB") 
        
        # 4. 执行健康分析 (模拟)
        analysis_data = analyze_oral_health(uploaded_img)
        
        # 5. 生成并存储掩码图像 
        mask_filename = f"{uuid.uuid4().hex}-mask.png" 
        mask_img = generate_mask_image(analysis_data["mask_array"])
        mask_img.save(f"./static/masks/{mask_filename}")   # 实际应使用云存储 
        
        # 6. 生成签名访问URL 
        mask_url = generate_signed_url(user_id, mask_filename)
        
        return AnalysisResponse(
            results={
                "diagnosis": analysis_data["diagnosis"],
                "maskImageUrl": mask_url,
                "maskOffset": analysis_data["offset"]
            },
            message="Analysis completed successfully"
        )
        
    except Exception as e:
        # 记录详细错误日志 
        log_error(f"Processing failed for {user_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Image processing error"
        )
# ---------- 工具函数 ----------
def user_exists(user_id: str) -> bool:
    """验证用户ID有效性 (应连接用户数据库)"""
    return user_id.startswith("user_")   # 简化演示 
def log_error(message: str):
    """错误日志记录 (应接入日志系统)"""
    print(f"[ERROR] {datetime.now()}:  {message}")
# 生成完整的牙齿映射表 (实际应放在独立配置文件中)
def generate_full_teeth_map():
    full_map = {}
    # 永久牙 (1-32)
    positions = ["Upper left", "Upper right", "Lower left", "Lower right"]
    teeth_types = ["central incisor", "lateral incisor", "canine", 
                  "first premolar", "second premolar", 
                  "first molar", "second molar", "third molar"]
    
    start_idx = 0 
    for prefix in positions:
        for i, tooth in enumerate(teeth_types):
            full_map[start_idx + i + 1] = f"{prefix} {tooth} (perm)"
        start_idx += 8 
    
    # 乳牙 (33-52)
    primary_start = 33 
    # ... 类似规则生成 
    
    # 义齿 (53-84)
    denture_start = 53 
    # ... 类似规则生成 
    
    return full_map 
TEETH_MAP = generate_full_teeth_map()
# ---------- 本地测试支持 ----------
if __name__ == "__main__":
    # 创建测试图像 
    test_img = Image.new("RGB",  (300, 300), (255, 255, 255))
    test_img.save("test.jpg") 
    
    print("Generated test image: test.jpg") 