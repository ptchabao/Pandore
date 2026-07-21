# -*- encoding: utf-8 -*-

"""
TikTok Video Uploader Module
Uploads recorded videos to TikTok via Content Posting API
Designed to be error-resilient and non-blocking
"""

import time
import logging
import os
from typing import Optional, Dict, Any
import httpx

# Configure dedicated logger for TikTok uploads
logger = logging.getLogger('TikTokUploader')
logger.setLevel(logging.INFO)

# Create logs directory if it doesn't exist
log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
os.makedirs(log_dir, exist_ok=True)

# File handler
log_file = os.path.join(log_dir, 'tiktok_upload.log')
file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setLevel(logging.INFO)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.WARNING)

# Formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)


class TikTokUploader:
    """
    TikTok video uploader using Content Posting API.
    All methods are designed to never raise exceptions to the caller.
    """
    
    API_BASE_URL = "https://open.tiktokapis.com/v2/post/publish"
    
    def __init__(self, access_token: str, open_id: str, timeout: int = 300, max_retries: int = 3):
        """
        Initialize TikTok uploader.
        
        Args:
            access_token: TikTok user access token
            open_id: TikTok user open ID
            timeout: Upload timeout in seconds (default: 300)
            max_retries: Maximum number of retry attempts (default: 3)
        """
        self.access_token = access_token
        self.open_id = open_id
        self.timeout = timeout
        self.max_retries = max_retries
        self.headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
    
    def validate_token(self) -> bool:
        """
        Validate if the access token is non-empty.
        Note: Full token validation requires an API call, which we skip to avoid delays.
        
        Returns:
            bool: True if token appears valid, False otherwise
        """
        try:
            if not self.access_token or not self.access_token.strip():
                logger.error("TikTok access token is empty")
                return False
            if not self.open_id or not self.open_id.strip():
                logger.error("TikTok open ID is empty")
                return False
            return True
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            return False
    
    def _retry_with_backoff(self, func, *args, **kwargs) -> Optional[Any]:
        """
        Execute a function with exponential backoff retry logic.
        
        Args:
            func: Function to execute
            *args, **kwargs: Arguments to pass to the function
            
        Returns:
            Function result or None if all retries failed
        """
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except httpx.TimeoutException as e:
                wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                logger.warning(f"Timeout on attempt {attempt + 1}/{self.max_retries}: {e}. Retrying in {wait_time}s...")
                if attempt < self.max_retries - 1:
                    time.sleep(wait_time)
                else:
                    logger.error(f"All retry attempts exhausted due to timeout")
                    return None
            except httpx.NetworkError as e:
                wait_time = 2 ** attempt
                logger.warning(f"Network error on attempt {attempt + 1}/{self.max_retries}: {e}. Retrying in {wait_time}s...")
                if attempt < self.max_retries - 1:
                    time.sleep(wait_time)
                else:
                    logger.error(f"All retry attempts exhausted due to network error")
                    return None
            except Exception as e:
                logger.error(f"Unexpected error on attempt {attempt + 1}/{self.max_retries}: {e}")
                return None
        
        return None
    
    def init_video_upload(self, video_size: int) -> Optional[Dict[str, Any]]:
        """
        Initialize video upload session and get upload URL.
        
        Args:
            video_size: Size of video file in bytes
            
        Returns:
            Dict containing publish_id and upload_url, or None on failure
        """
        try:
            url = f"{self.API_BASE_URL}/inbox/video/init/"
            
            payload = {
                "source_info": {
                    "source": "FILE_UPLOAD",
                    "video_size": video_size,
                    "chunk_size": video_size,
                    "total_chunk_count": 1
                }
            }
            
            def _make_request():
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(url, json=payload, headers=self.headers)
                    response.raise_for_status()
                    return response.json()
            
            result = self._retry_with_backoff(_make_request)
            
            if result and result.get('error', {}).get('code') == 'ok':
                data = result.get('data', {})
                logger.info(f"Upload session initialized. Publish ID: {data.get('publish_id')}")
                return data
            else:
                error_msg = result.get('error', {}).get('message', 'Unknown error') if result else 'No response'
                logger.error(f"Failed to initialize upload: {error_msg}")
                return None
                
        except Exception as e:
            logger.error(f"Exception during upload initialization: {e}")
            return None
    
    def upload_video_file(self, upload_url: str, video_path: str) -> bool:
        """
        Upload video file to TikTok servers.
        
        Args:
            upload_url: Upload URL from init_video_upload
            video_path: Local path to video file
            
        Returns:
            bool: True if upload successful, False otherwise
        """
        try:
            if not os.path.exists(video_path):
                logger.error(f"Video file not found: {video_path}")
                return False
            
            file_size = os.path.getsize(video_path)
            
            def _upload():
                with open(video_path, 'rb') as video_file:
                    video_data = video_file.read()
                
                upload_headers = {
                    'Content-Type': 'video/mp4',
                    'Content-Range': f'bytes 0-{file_size - 1}/{file_size}'
                }
                
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.put(upload_url, content=video_data, headers=upload_headers)
                    response.raise_for_status()
                    return True
            
            result = self._retry_with_backoff(_upload)
            
            if result:
                logger.info(f"Video file uploaded successfully: {os.path.basename(video_path)}")
                return True
            else:
                logger.error(f"Failed to upload video file: {os.path.basename(video_path)}")
                return False
                
        except Exception as e:
            logger.error(f"Exception during video file upload: {e}")
            return False
    
    def check_upload_status(self, publish_id: str, max_wait: int = 60) -> bool:
        """
        Poll upload status until processing is complete or timeout.
        
        Args:
            publish_id: Publish ID from init_video_upload
            max_wait: Maximum time to wait in seconds (default: 60)
            
        Returns:
            bool: True if upload processing completed successfully, False otherwise
        """
        try:
            url = f"{self.API_BASE_URL}/status/fetch/"
            payload = {"publish_id": publish_id}
            
            start_time = time.time()
            
            while time.time() - start_time < max_wait:
                try:
                    with httpx.Client(timeout=30) as client:
                        response = client.post(url, json=payload, headers=self.headers)
                        response.raise_for_status()
                        result = response.json()
                    
                    if result.get('error', {}).get('code') == 'ok':
                        data = result.get('data', {})
                        status = data.get('status')
                        
                        if status == 'PUBLISH_COMPLETE':
                            logger.info(f"Upload completed successfully. Publish ID: {publish_id}")
                            return True
                        elif status == 'FAILED':
                            fail_reason = data.get('fail_reason', 'Unknown')
                            logger.error(f"Upload failed. Reason: {fail_reason}")
                            return False
                        else:
                            # Still processing, wait and retry
                            logger.info(f"Upload status: {status}. Waiting...")
                            time.sleep(5)
                    else:
                        error_msg = result.get('error', {}).get('message', 'Unknown error')
                        logger.error(f"Status check failed: {error_msg}")
                        return False
                        
                except Exception as e:
                    logger.warning(f"Status check exception: {e}. Retrying...")
                    time.sleep(5)
            
            logger.warning(f"Status check timeout after {max_wait}s. Upload may still be processing.")
            return False
            
        except Exception as e:
            logger.error(f"Exception during status check: {e}")
            return False
    
    def upload_video_to_tiktok(self, video_path: str, description: str = "", 
                                privacy_level: str = "PUBLIC_TO_EVERYONE") -> bool:
        """
        Main function to upload a video to TikTok.
        This is a complete workflow: init -> upload -> check status.
        
        Args:
            video_path: Local path to video file
            description: Video description/caption (optional)
            privacy_level: Privacy setting (default: PUBLIC_TO_EVERYONE)
            
        Returns:
            bool: True if entire upload process succeeded, False otherwise
        """
        try:
            logger.info(f"Starting TikTok upload for: {os.path.basename(video_path)}")
            
            # Validate token
            if not self.validate_token():
                logger.error("Token validation failed. Aborting upload.")
                return False
            
            # Check file exists and get size
            if not os.path.exists(video_path):
                logger.error(f"Video file not found: {video_path}")
                return False
            
            video_size = os.path.getsize(video_path)
            
            # Check file size (TikTok has limits, e.g., max 4GB for most accounts)
            if video_size > 4 * 1024 * 1024 * 1024:  # 4GB
                logger.error(f"Video file too large: {video_size / (1024**3):.2f}GB. Max is 4GB.")
                return False
            
            if video_size == 0:
                logger.error("Video file is empty (0 bytes)")
                return False
            
            logger.info(f"Video file size: {video_size / (1024**2):.2f}MB")
            
            # Step 1: Initialize upload session
            init_data = self.init_video_upload(video_size)
            if not init_data:
                logger.error("Failed to initialize upload session")
                return False
            
            publish_id = init_data.get('publish_id')
            upload_url = init_data.get('upload_url')
            
            if not publish_id:
                logger.error("No publish_id received from initialization")
                return False
            
            # Step 2: Upload video file (only if upload_url is provided)
            if upload_url:
                upload_success = self.upload_video_file(upload_url, video_path)
                if not upload_success:
                    logger.error("Video file upload failed")
                    return False
            else:
                # For PULL_FROM_URL method, upload_url might not be needed
                logger.info("No upload_url provided, assuming PULL_FROM_URL method")
            
            # Step 3: Check upload status
            status_success = self.check_upload_status(publish_id, max_wait=120)
            
            if status_success:
                logger.info(f"✅ TikTok upload completed successfully! Publish ID: {publish_id}")
                logger.info("User will receive notification in TikTok app to review and publish the draft.")
                return True
            else:
                logger.error(f"Upload status check failed for publish_id: {publish_id}")
                return False
                
        except Exception as e:
            logger.error(f"Unexpected exception in upload_video_to_tiktok: {e}")
            return False


def upload_to_tiktok_safe(video_path: str, record_name: str, access_token: str, 
                          open_id: str, description: str = "", max_retries: int = 3) -> None:
    """
    Safe wrapper for TikTok upload that catches all exceptions.
    Designed to be called from a separate thread without blocking the main program.
    
    Args:
        video_path: Path to video file
        record_name: Name of the recording (for logging)
        access_token: TikTok access token
        open_id: TikTok open ID
        description: Video description
        max_retries: Number of retry attempts
    """
    try:
        logger.info(f"[{record_name}] Starting TikTok upload process")
        
        uploader = TikTokUploader(
            access_token=access_token,
            open_id=open_id,
            timeout=300,
            max_retries=max_retries
        )
        
        success = uploader.upload_video_to_tiktok(
            video_path=video_path,
            description=description,
            privacy_level="PUBLIC_TO_EVERYONE"
        )
        
        if success:
            print(f"✅ [{record_name}] TikTok上传成功! 用户将在TikTok收到通知")
            logger.info(f"[{record_name}] Upload completed successfully")
        else:
            print(f"⚠️ [{record_name}] TikTok上传失败,请查看日志文件")
            logger.warning(f"[{record_name}] Upload failed, but recording is saved locally")
            
    except Exception as e:
        # Final safety net - catch any unexpected exceptions
        logger.error(f"[{record_name}] Critical error in upload_to_tiktok_safe: {e}")
        print(f"⚠️ [{record_name}] TikTok上传出错: {str(e)}")
    finally:
        # Always log completion
        logger.info(f"[{record_name}] TikTok upload thread completed")
