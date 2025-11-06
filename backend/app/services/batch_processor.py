"""
Batch Processor Service
Handles batch processing with retry logic
"""
from typing import List, Dict, Any, Callable, Optional
from datetime import datetime
import asyncio
import structlog

logger = structlog.get_logger()


class BatchProcessor:
    """
    Process large datasets in batches with retry and error handling
    """
    
    def __init__(
        self,
        batch_size: int = 500,
        max_retries: int = 3,
        retry_delay: int = 2
    ):
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.retry_delay = retry_delay
    
    async def process_batches(
        self,
        items: List[Any],
        processor: Callable,
        on_progress: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Process items in batches with retry logic
        
        Args:
            items: List of items to process
            processor: Async function to process each batch
            on_progress: Optional callback for progress updates
            
        Returns:
            Statistics about processing
        """
        total_items = len(items)
        total_batches = (total_items + self.batch_size - 1) // self.batch_size
        
        processed = 0
        failed = 0
        errors = []
        
        logger.info("batch_processing_started",
                   total_items=total_items,
                   total_batches=total_batches,
                   batch_size=self.batch_size)
        
        for batch_num in range(total_batches):
            start_idx = batch_num * self.batch_size
            end_idx = min(start_idx + self.batch_size, total_items)
            batch = items[start_idx:end_idx]
            
            # Try processing batch with retries
            retry_count = 0
            batch_success = False
            
            while retry_count <= self.max_retries and not batch_success:
                try:
                    await processor(batch, batch_num + 1, total_batches)
                    processed += len(batch)
                    batch_success = True
                    
                    logger.info("batch_processed",
                               batch=batch_num + 1,
                               total=total_batches,
                               items=len(batch))
                    
                except Exception as e:
                    retry_count += 1
                    error_msg = f"Batch {batch_num + 1} failed: {str(e)}"
                    
                    if retry_count <= self.max_retries:
                        logger.warning("batch_retry",
                                      batch=batch_num + 1,
                                      retry=retry_count,
                                      error=str(e))
                        await asyncio.sleep(self.retry_delay * retry_count)
                    else:
                        logger.error("batch_failed",
                                    batch=batch_num + 1,
                                    error=str(e))
                        failed += len(batch)
                        errors.append({
                            "batch": batch_num + 1,
                            "error": error_msg,
                            "items": len(batch)
                        })
            
            # Progress callback
            if on_progress:
                progress = (processed / total_items) * 100
                await on_progress({
                    "processed": processed,
                    "total": total_items,
                    "progress_percentage": progress,
                    "current_batch": batch_num + 1,
                    "total_batches": total_batches
                })
        
        result = {
            "total_items": total_items,
            "processed": processed,
            "failed": failed,
            "success_rate": (processed / total_items * 100) if total_items > 0 else 0,
            "errors": errors
        }
        
        logger.info("batch_processing_completed", **result)
        return result
    
    @staticmethod
    def chunk_list(items: List[Any], chunk_size: int) -> List[List[Any]]:
        """Split list into chunks"""
        return [
            items[i:i + chunk_size] 
            for i in range(0, len(items), chunk_size)
        ]
