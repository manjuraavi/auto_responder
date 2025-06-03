import psutil
from datetime import datetime
import logging
from typing import Dict, Any
from app.models.schemas import HealthCheck
from app.services.gmail_service import GmailService
from app.services.agent_service import AgentService
from app.services.document_service import DocumentService

logger = logging.getLogger(__name__)

class HealthService:
    @staticmethod
    async def get_detailed_health() -> HealthCheck:
        """Get detailed health status of all components"""
        try:
            # Service health checks
            gmail_status = "healthy" if await GmailService.verify_connection() else "unhealthy"
            agent_status = "healthy" if await AgentService.verify_connection() else "unhealthy"
            doc_status = "healthy" if await DocumentService.verify_connection() else "unhealthy"
            
            # System metrics
            system_metrics = {
                "cpu_usage": psutil.cpu_percent(),
                "memory_usage": psutil.virtual_memory().percent,
                "disk_usage": psutil.disk_usage('/').percent,
                "active_threads": psutil.Process().num_threads()
            }
            
            # Response times (in ms)
            response_times = await HealthService.check_response_times()
            
            overall_status = "healthy" if all([
                gmail_status == "healthy",
                agent_status == "healthy",
                doc_status == "healthy",
                system_metrics["cpu_usage"] < 80,
                system_metrics["memory_usage"] < 80
            ]) else "degraded"
            
            return HealthCheck(
                status=overall_status,
                timestamp=datetime.utcnow(),
                services={
                    "gmail_service": gmail_status,
                    "agent_service": agent_status,
                    "document_service": doc_status
                },
                metrics=system_metrics,
                response_times=response_times
            )
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return HealthCheck(
                status="unhealthy",
                timestamp=datetime.utcnow(),
                services={
                    "gmail_service": "unknown",
                    "agent_service": "unknown",
                    "document_service": "unknown"
                },
                error=str(e)
            )

    @staticmethod
    async def check_response_times() -> Dict[str, float]:
        """Check response times for key endpoints"""
        try:
            import time
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                start = time.time()
                async with session.get("/api/emails") as resp:
                    emails_time = (time.time() - start) * 1000
                
                start = time.time()
                async with session.get("/api/documents") as resp:
                    docs_time = (time.time() - start) * 1000
            
            return {
                "emails_endpoint": round(emails_time, 2),
                "documents_endpoint": round(docs_time, 2)
            }
        except Exception as e:
            logger.error(f"Response time check failed: {str(e)}")
            return {}