"""Cloudinary media storage service"""
import os
import logging
import cloudinary
import cloudinary.uploader
from typing import Optional, Dict, Union

logger = logging.getLogger(__name__)

class StorageService:
    def __init__(self):
        cloudinary_url = os.environ.get('CLOUDINARY_URL')
        if not cloudinary_url:
            logger.error("CLOUDINARY_URL environment variable is not set")
            return

        try:
            # Parse and configure Cloudinary properly
            cloudinary.config(cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
                            api_key=os.environ.get('CLOUDINARY_API_KEY'),
                            api_secret=os.environ.get('CLOUDINARY_API_SECRET'))
            logger.info("Cloudinary storage service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Cloudinary: {str(e)}")

    def upload_media(self, file_data: bytes, resource_type: str = "auto", 
                    public_id: Optional[str] = None) -> Optional[Dict[str, str]]:
        """
        Upload media file to Cloudinary
        Args:
            file_data: The binary data of the file to upload
            resource_type: Type of resource (auto, image, video, audio, raw)
            public_id: Optional custom public ID for the uploaded file
        Returns:
            Dictionary containing URLs and metadata or None if upload fails
        """
        if not cloudinary.config().cloud_name:
            logger.error("Cloudinary is not properly configured")
            return None

        try:
            logger.info(f"Attempting to upload media file of type: {resource_type}")
            upload_args = {
                "resource_type": resource_type,
            }
            if public_id:
                upload_args["public_id"] = public_id

            # Set specific options for audio files
            if resource_type == "audio":
                upload_args.update({
                    "format": "mp3",
                    "resource_type": "video",  # Cloudinary handles audio under video type
                    "audio_codec": "mp3"
                })

            response = cloudinary.uploader.upload(file_data, **upload_args)
            logger.info(f"Successfully uploaded media to Cloudinary: {response['public_id']}")

            return {
                "url": response["secure_url"],
                "public_id": response["public_id"],
                "resource_type": response["resource_type"]
            }
        except Exception as e:
            logger.error(f"Error uploading to Cloudinary: {str(e)}")
            return None