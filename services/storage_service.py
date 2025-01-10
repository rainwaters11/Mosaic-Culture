"""Cloudinary media storage service"""
import os
import cloudinary
import cloudinary.uploader
from typing import Optional

class StorageService:
    def __init__(self):
        cloudinary_url = os.environ.get('CLOUDINARY_URL')
        if cloudinary_url:
            cloudinary.config(cloud_name=cloudinary_url)

    def upload_media(self, file_data: bytes, resource_type: str = "auto", 
                    public_id: Optional[str] = None) -> dict:
        """
        Upload media file to Cloudinary
        Returns upload response containing URLs and metadata
        """
        try:
            upload_args = {
                "resource_type": resource_type,
            }
            if public_id:
                upload_args["public_id"] = public_id

            response = cloudinary.uploader.upload(file_data, **upload_args)
            return {
                "url": response["secure_url"],
                "public_id": response["public_id"],
                "resource_type": response["resource_type"]
            }
        except Exception as e:
            print(f"Error uploading to Cloudinary: {str(e)}")
            return None
