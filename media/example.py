#!/usr/bin/env python3
"""
Deployment automation script for container services.
Handles rolling deployments with health checks and rollback capabilities.
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import aiohttp
import yaml

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class DeployConfig:
    """Configuration for deployment process."""
    service_name: str
    image_tag: str
    namespace: str = "default"
    replicas: int = 3
    health_check_path: str = "/health"
    timeout_seconds: int = 300
    rollback_on_failure: bool = True

class DeploymentManager:
    """Manages container deployments with health checks."""
    
    def __init__(self, config: DeployConfig):
        self.config = config
        self.kubectl_cmd = ["kubectl", "-n", config.namespace]
        
    async def deploy(self) -> bool:
        """Execute deployment with health checks."""
        try:
            logger.info(f"Starting deployment of {self.config.service_name}:{self.config.image_tag}")
            
            # Update deployment
            if not await self._update_deployment():
                return False
                
            # Wait for rollout
            if not await self._wait_for_rollout():
                if self.config.rollback_on_failure:
                    await self._rollback()
                return False
                
            # Verify health
            if not await self._verify_health():
                logger.error("Health check failed after deployment")
                return False
                
            logger.info("Deployment completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Deployment failed: {str(e)}")
            return False
    
    async def _update_deployment(self) -> bool:
        """Update the Kubernetes deployment."""
        cmd = self.kubectl_cmd + [
            "set", "image", 
            f"deployment/{self.config.service_name}",
            f"{self.config.service_name}={self.config.image_tag}"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"Failed to update deployment: {result.stderr}")
            return False
            
        logger.info("Deployment updated successfully")
        return True
    
    async def _wait_for_rollout(self) -> bool:
        """Wait for deployment rollout to complete."""
        cmd = self.kubectl_cmd + [
            "rollout", "status", 
            f"deployment/{self.config.service_name}",
            f"--timeout={self.config.timeout_seconds}s"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0
    
    async def _verify_health(self) -> bool:
        """Verify service health after deployment."""
        service_url = f"http://{self.config.service_name}.{self.config.namespace}.svc.cluster.local"
        health_url = f"{service_url}{self.config.health_check_path}"
        
        async with aiohttp.ClientSession() as session:
            for attempt in range(5):
                try:
                    async with session.get(health_url, timeout=10) as response:
                        if response.status == 200:
                            logger.info("Health check passed")
                            return True
                except Exception as e:
                    logger.warning(f"Health check attempt {attempt + 1} failed: {str(e)}")
                    await asyncio.sleep(10)
        
        return False
    
    async def _rollback(self) -> None:
        """Rollback to previous deployment."""
        logger.warning("Rolling back deployment")
        cmd = self.kubectl_cmd + ["rollout", "undo", f"deployment/{self.config.service_name}"]
        subprocess.run(cmd, capture_output=True, text=True)

def load_config(config_path: str) -> DeployConfig:
    """Load deployment configuration from YAML file."""
    config_file = Path(config_path)
    
    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with open(config_file, 'r') as f:
        data = yaml.safe_load(f)
    
    return DeployConfig(**data)

async def main():
    """Main deployment orchestration."""
    if len(sys.argv) != 3:
        print("Usage: deploy.py <config-file> <image-tag>")
        sys.exit(1)
    
    config_file, image_tag = sys.argv[1], sys.argv[2]
    
    try:
        config = load_config(config_file)
        config.image_tag = image_tag
        
        manager = DeploymentManager(config)
        success = await manager.deploy()
        
        if success:
            logger.info("🚀 Deployment successful!")
            sys.exit(0)
        else:
            logger.error("❌ Deployment failed!")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Script failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())