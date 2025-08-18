#!/usr/bin/env python3
"""
Configuration variables for the main application.
"""

INITIATOR_CHAT_MAX_ROUNDS = 300 # Maximum number of rounds for the initiator chat
DELEGATION_LIMIT = 300 # Maximum number of delegations
DELEGATION_CHAT_MAX_ROUNDS = 100 # Maximum number of rounds for any delegation chat
TIME_LIMIT_PROMPTS = 100 # Maximum number of prompts to complete the task before automatic termination

# Rate limiting configuration
RATE_LIMIT_MAX_RETRIES = 6  # Maximum number of retries for rate limit errors
RATE_LIMIT_BASE_DELAY = 2.0  # Base delay in seconds for exponential backoff
RATE_LIMIT_MAX_DELAY = 60.0  # Maximum delay in seconds
RATE_LIMIT_JITTER = 0.1

# API timeout configuration
API_TIMEOUT_SECONDS = 600  # 10 minute timeout for OpenAI API calls
