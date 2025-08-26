"""
Robust HTTP Client for Master Server API Requests
Implements comprehensive error handling, retry logic, circuit breakers, and resilience patterns
"""

import asyncio
import aiohttp
import logging
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
import json
import time
import ssl
from urllib.parse import urljoin
import uuid


class CircuitBreakerState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, rejecting requests
    HALF_OPEN = "half_open"  # Testing if service is back


@dataclass
class RetryConfig:
    """Retry configuration"""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_status_codes: List[int] = field(default_factory=lambda: [500, 502, 503, 504, 429])
    retryable_exceptions: List[type] = field(default_factory=lambda: [
        aiohttp.ClientConnectionError,
        aiohttp.ClientTimeout,
        asyncio.TimeoutError,
        aiohttp.ServerTimeoutError
    ])


@dataclass 
class CircuitBreakerConfig:
    """Circuit breaker configuration"""
    failure_threshold: int = 5
    recovery_timeout: int = 60
    expected_exception: tuple = (aiohttp.ClientError, asyncio.TimeoutError)


@dataclass
class RequestConfig:
    """Individual request configuration"""
    timeout: float = 30.0
    headers: Optional[Dict[str, str]] = None
    retry_config: Optional[RetryConfig] = None
    circuit_breaker_enabled: bool = True


class RobustHttpClient:
    """
    Robust HTTP client with comprehensive error handling and resilience patterns
    
    Features:
    - Exponential backoff retry with jitter
    - Circuit breaker pattern
    - Request/response logging
    - Connection pooling
    - Timeout handling
    - Authentication management
    - Rate limiting
    - Health monitoring
    """
    
    def __init__(
        self, 
        base_url: str,
        api_key: str,
        default_timeout: float = 30.0,
        retry_config: Optional[RetryConfig] = None,
        circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
        max_connections: int = 100,
        enable_ssl_verification: bool = True
    ):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.default_timeout = default_timeout
        self.retry_config = retry_config or RetryConfig()
        self.circuit_breaker_config = circuit_breaker_config or CircuitBreakerConfig()
        
        # Circuit breaker state
        self._circuit_state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._circuit_lock = asyncio.Lock()
        
        # Session configuration
        self._session: Optional[aiohttp.ClientSession] = None
        self._connector_config = {
            'limit': max_connections,
            'limit_per_host': 30,
            'keepalive_timeout': 30,
            'enable_cleanup_closed': True
        }
        
        if not enable_ssl_verification:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            self._connector_config['ssl'] = ssl_context
        
        # Metrics and monitoring
        self.request_stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'retried_requests': 0,
            'circuit_breaker_trips': 0,
            'average_response_time': 0.0,
            'last_request_time': None
        }
        
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def _ensure_session(self):
        """Ensure HTTP session is created"""
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(**self._connector_config)
            timeout = aiohttp.ClientTimeout(total=self.default_timeout)
            
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={'User-Agent': 'MyOral-Client/1.0'},
                raise_for_status=False  # We'll handle status codes manually
            )
    
    async def close(self):
        """Close the HTTP session"""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def _check_circuit_breaker(self):
        """Check circuit breaker state and decide if request should proceed"""
        async with self._circuit_lock:
            if self._circuit_state == CircuitBreakerState.OPEN:
                if (self._last_failure_time and 
                    datetime.now() - self._last_failure_time > timedelta(seconds=self.circuit_breaker_config.recovery_timeout)):
                    self._circuit_state = CircuitBreakerState.HALF_OPEN
                    self.logger.info("Circuit breaker moving to HALF_OPEN state")
                else:
                    raise aiohttp.ClientError("Circuit breaker is OPEN - rejecting request")
            
            return self._circuit_state
    
    async def _record_success(self):
        """Record successful request for circuit breaker"""
        async with self._circuit_lock:
            if self._circuit_state == CircuitBreakerState.HALF_OPEN:
                self._circuit_state = CircuitBreakerState.CLOSED
                self._failure_count = 0
                self.logger.info("Circuit breaker closed - service recovered")
    
    async def _record_failure(self, exception: Exception):
        """Record failed request for circuit breaker"""
        async with self._circuit_lock:
            self._failure_count += 1
            self._last_failure_time = datetime.now()
            
            if (self._circuit_state == CircuitBreakerState.CLOSED and 
                self._failure_count >= self.circuit_breaker_config.failure_threshold):
                self._circuit_state = CircuitBreakerState.OPEN
                self.request_stats['circuit_breaker_trips'] += 1
                self.logger.warning(f"Circuit breaker OPENED after {self._failure_count} failures")
            
            elif self._circuit_state == CircuitBreakerState.HALF_OPEN:
                self._circuit_state = CircuitBreakerState.OPEN
                self.logger.warning("Circuit breaker reopened - service still failing")
    
    def _calculate_retry_delay(self, attempt: int, base_delay: float) -> float:
        """Calculate delay for retry with exponential backoff and jitter"""
        delay = min(
            base_delay * (self.retry_config.exponential_base ** attempt),
            self.retry_config.max_delay
        )
        
        if self.retry_config.jitter:
            import random
            delay *= (0.5 + random.random() * 0.5)  # Add 0-50% jitter
        
        return delay
    
    def _should_retry(self, attempt: int, exception: Exception, response: Optional[aiohttp.ClientResponse] = None) -> bool:
        """Determine if request should be retried"""
        if attempt >= self.retry_config.max_attempts:
            return False
        
        # Check if exception is retryable
        for exc_type in self.retry_config.retryable_exceptions:
            if isinstance(exception, exc_type):
                return True
        
        # Check if status code is retryable
        if response and response.status in self.retry_config.retryable_status_codes:
            return True
        
        return False
    
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        config: RequestConfig,
        **kwargs
    ) -> aiohttp.ClientResponse:
        """Make HTTP request with error handling"""
        await self._ensure_session()
        
        url = urljoin(self.base_url + '/', endpoint.lstrip('/'))
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'X-Request-ID': str(uuid.uuid4())
        }
        
        if config.headers:
            headers.update(config.headers)
        
        kwargs['headers'] = headers
        kwargs['timeout'] = aiohttp.ClientTimeout(total=config.timeout)
        
        self.logger.debug(f"Making {method} request to {url}")
        
        return await self._session.request(method, url, **kwargs)
    
    async def request(
        self, 
        method: str, 
        endpoint: str, 
        config: Optional[RequestConfig] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make robust HTTP request with retry logic and circuit breaker
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path
            config: Request configuration
            **kwargs: Additional arguments for aiohttp request
            
        Returns:
            Dict containing response data
            
        Raises:
            aiohttp.ClientError: For non-retryable errors
            asyncio.TimeoutError: For timeout errors
        """
        if config is None:
            config = RequestConfig()
        
        retry_config = config.retry_config or self.retry_config
        request_id = kwargs.get('headers', {}).get('X-Request-ID', str(uuid.uuid4()))
        start_time = time.time()
        
        # Update request stats
        self.request_stats['total_requests'] += 1
        self.request_stats['last_request_time'] = datetime.now()
        
        last_exception = None
        
        for attempt in range(retry_config.max_attempts):
            try:
                # Check circuit breaker
                if config.circuit_breaker_enabled:
                    await self._check_circuit_breaker()
                
                # Make the request
                response = await self._make_request(method, endpoint, config, **kwargs)
                
                # Log request details
                self.logger.info(
                    f"Request {request_id} - {method} {endpoint} - "
                    f"Status: {response.status} - Attempt: {attempt + 1}"
                )
                
                # Handle response based on status code
                if 200 <= response.status < 300:
                    # Success
                    if config.circuit_breaker_enabled:
                        await self._record_success()
                    
                    # Update stats
                    self.request_stats['successful_requests'] += 1
                    response_time = time.time() - start_time
                    self._update_average_response_time(response_time)
                    
                    # Parse response
                    try:
                        if response.content_type == 'application/json':
                            result = await response.json()
                        else:
                            result = {'text': await response.text()}
                        
                        return {
                            'success': True,
                            'data': result,
                            'status_code': response.status,
                            'headers': dict(response.headers),
                            'request_id': request_id,
                            'response_time': response_time
                        }
                    except Exception as e:
                        self.logger.error(f"Failed to parse response: {e}")
                        raise aiohttp.ClientError(f"Failed to parse response: {e}")
                
                else:
                    # HTTP error status
                    error_text = await response.text()
                    exception = aiohttp.ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=response.status,
                        message=f"HTTP {response.status}: {error_text}"
                    )
                    
                    if not self._should_retry(attempt, exception, response):
                        raise exception
                    
                    last_exception = exception
                    
            except Exception as e:
                last_exception = e
                
                if config.circuit_breaker_enabled:
                    await self._record_failure(e)
                
                if not self._should_retry(attempt, e):
                    break
                
                self.logger.warning(
                    f"Request {request_id} failed (attempt {attempt + 1}): {e}"
                )
            
            # Calculate retry delay
            if attempt < retry_config.max_attempts - 1:
                delay = self._calculate_retry_delay(attempt, retry_config.base_delay)
                self.logger.info(f"Retrying request {request_id} in {delay:.2f}s")
                await asyncio.sleep(delay)
        
        # All attempts failed
        self.request_stats['failed_requests'] += 1
        self.request_stats['retried_requests'] += 1
        
        self.logger.error(
            f"Request {request_id} failed after {retry_config.max_attempts} attempts: {last_exception}"
        )
        
        return {
            'success': False,
            'error': str(last_exception),
            'attempts': retry_config.max_attempts,
            'request_id': request_id,
            'response_time': time.time() - start_time
        }
    
    def _update_average_response_time(self, response_time: float):
        """Update rolling average response time"""
        current_avg = self.request_stats['average_response_time']
        total_successful = self.request_stats['successful_requests']
        
        if total_successful == 1:
            self.request_stats['average_response_time'] = response_time
        else:
            # Simple moving average
            self.request_stats['average_response_time'] = (
                (current_avg * (total_successful - 1) + response_time) / total_successful
            )
    
    async def get(self, endpoint: str, config: Optional[RequestConfig] = None, **kwargs) -> Dict[str, Any]:
        """Make GET request"""
        return await self.request('GET', endpoint, config, **kwargs)
    
    async def post(self, endpoint: str, data: Any = None, config: Optional[RequestConfig] = None, **kwargs) -> Dict[str, Any]:
        """Make POST request"""
        if data is not None:
            kwargs['json'] = data
        return await self.request('POST', endpoint, config, **kwargs)
    
    async def put(self, endpoint: str, data: Any = None, config: Optional[RequestConfig] = None, **kwargs) -> Dict[str, Any]:
        """Make PUT request"""
        if data is not None:
            kwargs['json'] = data
        return await self.request('PUT', endpoint, config, **kwargs)
    
    async def delete(self, endpoint: str, config: Optional[RequestConfig] = None, **kwargs) -> Dict[str, Any]:
        """Make DELETE request"""
        return await self.request('DELETE', endpoint, config, **kwargs)
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on master server"""
        config = RequestConfig(timeout=10.0, circuit_breaker_enabled=False)
        try:
            result = await self.get('/health', config)
            return {
                'healthy': result.get('success', False),
                'response_time': result.get('response_time', 0),
                'details': result.get('data', {})
            }
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e),
                'response_time': 0
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics"""
        total = self.request_stats['total_requests']
        successful = self.request_stats['successful_requests']
        
        return {
            **self.request_stats,
            'success_rate': (successful / total * 100) if total > 0 else 0,
            'circuit_breaker_state': self._circuit_state.value,
            'failure_count': self._failure_count,
            'last_failure_time': self._last_failure_time.isoformat() if self._last_failure_time else None
        }
    
    async def reset_circuit_breaker(self):
        """Manually reset circuit breaker"""
        async with self._circuit_lock:
            self._circuit_state = CircuitBreakerState.CLOSED
            self._failure_count = 0
            self._last_failure_time = None
            self.logger.info("Circuit breaker manually reset")
