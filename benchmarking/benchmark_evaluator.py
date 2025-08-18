#!/usr/bin/env python3
"""
AI-Driven Benchmark Evaluator Module

Implements AI-driven evaluation using OpenAI completions and Playwright actions
for benchmark scenario assessment.
"""

import json
import os
import re
import time
from typing import List, Optional, Tuple, Dict, Any
from dataclasses import dataclass
from pathlib import Path

import openai
import requests
from playwright.sync_api import sync_playwright
from logger.log_wrapper import get_logger
from dotenv import load_dotenv
import traceback

# Load environment variables
load_dotenv()


@dataclass
class EvaluationStep:
    """Represents a single evaluation step."""
    step: int
    action: str
    expected: str
    value: float


@dataclass
class EvaluationResult:
    """Result of evaluating a single evaluation."""
    evaluation_name: str
    passed: bool
    score: float
    details: str
    steps_completed: int
    total_steps: int
    error_message: Optional[str] = None


@dataclass
class ScenarioEvaluationResult:
    """Complete evaluation result for a scenario."""
    scenario_id: str
    scenario_name: str
    total_score: float
    max_possible_score: float
    passed_evaluations: int
    total_evaluations: int
    evaluation_results: List[EvaluationResult]
    execution_time_minutes: float
    log_file_path: str
    model_used: str


class BenchmarkEvaluator:
    """AI-driven evaluator using OpenAI completions and Playwright."""
    
    def __init__(self, openai_api_key: Optional[str] = None):
        self.logger = get_logger("benchmark:evaluator", __name__)
        
        # Get OpenAI API key from environment if not provided
        if not openai_api_key:
            openai_api_key = os.getenv('OPENAI_API_KEY')
            if not openai_api_key:
                raise ValueError("OPENAI_API_KEY environment variable is required")
        
        self.openai_client = openai.OpenAI(api_key=openai_api_key)
        self.playwright = None
        self.browser = None
        self.page = None
        self.evaluation_log_file: Optional[Path] = None
        self.evaluation_logger: Optional[Any] = None
        
    def __enter__(self):
        """Context manager entry."""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=True)
        self.page = self.browser.new_page()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self.page:
            self.page.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
    
    def _setup_evaluation_logging(self, scenario_id: str, log_file_path: str, scenario_dir: Path) -> None:
        """Set up detailed evaluation logging to a dedicated log file."""
        try:
            # Create evaluation log file in the scenario directory
            evaluation_log_path = scenario_dir / f"{scenario_id}_evaluation_detailed.log"
            
            # Create a file handler for detailed evaluation logging
            import logging
            evaluation_logger = logging.getLogger(f"benchmark:evaluator:detailed:{scenario_id}")
            evaluation_logger.setLevel(logging.INFO)
            
            # Remove existing handlers to avoid duplicates
            for handler in evaluation_logger.handlers[:]:
                evaluation_logger.removeHandler(handler)
            
            # Create file handler
            file_handler = logging.FileHandler(evaluation_log_path)
            file_handler.setLevel(logging.INFO)
            
            # Create formatter
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(formatter)
            
            # Add handler to logger
            evaluation_logger.addHandler(file_handler)
            evaluation_logger.propagate = False  # Don't propagate to parent loggers
            
            self.evaluation_log_file = evaluation_log_path
            self.evaluation_logger = evaluation_logger
            
            self.logger.info(f"Detailed evaluation logging set up: {evaluation_log_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to set up evaluation logging: {e}")
            self.evaluation_log_file = None
            self.evaluation_logger = None

    def evaluate_scenario(self, scenario_id: str, scenario_name: str, 
                         evaluation_files: List[str], log_file_path: str,
                         execution_time_minutes: float, model: str,
                         website_url: str, scenario_dir: Path) -> ScenarioEvaluationResult:
        """
        Evaluate a scenario using AI-driven evaluation.
        
        Args:
            scenario_id: Unique identifier for the scenario
            scenario_name: Human-readable name of the scenario
            evaluation_files: List of evaluation JSON file paths
            log_file_path: Path to the execution log file
            execution_time_minutes: Time taken to execute the scenario
            model: LLM model used for the scenario
            website_url: URL of the deployed website to test
            scenario_dir: Directory where evaluation results and logs will be saved
            
        Returns:
            ScenarioEvaluationResult with complete evaluation
        """
        self.logger.info(f"Starting AI-driven evaluation for scenario: {scenario_name}")
        
        # Set up detailed evaluation logging
        self._setup_evaluation_logging(scenario_id, log_file_path, scenario_dir)
        
        # Validate website URL presence and accessibility before any navigation
        if not website_url or not website_url.strip():
            self.logger.error("website_url is required for evaluation but was missing or empty")
            raise ValueError("website_url is required for evaluation")
        if not re.match(r"^https?://", website_url.strip()):
            self.logger.error("website_url must include http(s) scheme")
            raise ValueError("website_url must include http(s) scheme, e.g. https://example.com")
        # Verify HTTP accessibility (positive status code) prior to running steps
        self._verify_http_accessible(website_url.strip())

        evaluation_results = []
        total_score = 0.0
        max_possible_score = 0.0
        passed_evaluations = 0
        
        for evaluation_file in evaluation_files:
            self.logger.info(f"Processing evaluation file: {Path(evaluation_file).name}")
            try:
                result = self._evaluate_evaluation(evaluation_file, website_url)
                evaluation_results.append(result)
                
                if result.passed:
                    passed_evaluations += 1
                
                # Add score regardless of pass/fail status
                total_score += result.score
                
                steps, _, _ = self._load_evaluation_steps(evaluation_file)
                max_possible_score += result.score + sum(
                    step.value for step in steps[1:]
                )
                    
            except Exception as e:
                self.logger.error(f"Error evaluating {evaluation_file}: {e}")
                error_result = EvaluationResult(
                    evaluation_name=Path(evaluation_file).stem,
                    passed=False,
                    score=0.0,
                    details=f"Evaluation failed: {str(e)}",
                    steps_completed=0,
                    total_steps=0,
                    error_message=str(e)
                )
                evaluation_results.append(error_result)
        
        return ScenarioEvaluationResult(
            scenario_id=scenario_id,
            scenario_name=scenario_name,
            total_score=total_score,
            max_possible_score=max_possible_score,
            passed_evaluations=passed_evaluations,
            total_evaluations=len(evaluation_files),
            evaluation_results=evaluation_results,
            execution_time_minutes=execution_time_minutes,
            log_file_path=log_file_path,
            model_used=model
        )
    
    def _verify_http_accessible(self, website_url: str) -> None:
        """Verify that the website URL returns a positive HTTP response.
        Positive means 2xx or 3xx response codes.
        Logs a warning when inaccessible but does not raise to allow evaluation to continue.
        """
        try:
            response = requests.get(website_url, allow_redirects=True, timeout=15)
        except Exception as exc:
            if hasattr(self, 'evaluation_logger') and self.evaluation_logger:
                self.evaluation_logger.warning(f"HTTP check failed for {website_url}: {exc}")
            self.logger.warning(f"HTTP check failed for {website_url}: {exc}")
            return

        status = response.status_code
        if not (200 <= status < 400):
            if hasattr(self, 'evaluation_logger') and self.evaluation_logger:
                self.evaluation_logger.warning(
                    f"HTTP check for {website_url} returned non-positive status: {status}"
                )
            self.logger.warning(
                f"HTTP check for {website_url} returned non-positive status: {status}"
            )
            return
        else:
            if hasattr(self, 'evaluation_logger') and self.evaluation_logger:
                self.evaluation_logger.info(
                    f"HTTP check passed for {website_url} with status {status}"
                )
            self.logger.info(
                f"HTTP check passed for {website_url} with status {status}"
            )

    def _load_evaluation_steps(self, evaluation_file: str) -> Tuple[List[EvaluationStep], str, str]:
        """Load evaluation steps from JSON file."""
        with open(evaluation_file, 'r') as f:
            data = json.load(f)
        
        steps = []
        for step_data in data.get('steps', []):
            step = EvaluationStep(
                step=step_data['step'],
                action=step_data['action'],
                expected=step_data['expected'],
                value=step_data['value']
            )
            steps.append(step)
        
        evaluation_description = data.get('description', '')
        initial_page = data.get('initial_page', '/')
        
        return steps, evaluation_description, initial_page
    
    def _evaluate_evaluation(self, evaluation_file: str, website_url: str) -> EvaluationResult:
        """Evaluate a single evaluation using AI-driven testing."""
        steps, evaluation_description, initial_page = self._load_evaluation_steps(evaluation_file)
        evaluation_name = Path(evaluation_file).stem
        
        self.logger.info(f"Evaluating evaluation: {evaluation_name}")
        
        # Log evaluation start to detailed log
        if hasattr(self, 'evaluation_logger') and self.evaluation_logger:
            self.evaluation_logger.info(f"=== STARTING EVALUATION: {evaluation_name} ===")
            self.evaluation_logger.info(f"Evaluation file: {evaluation_file}")
            self.evaluation_logger.info(f"Website URL: {website_url}")
            self.evaluation_logger.info(f"Initial page: {initial_page}")
            self.evaluation_logger.info(f"Total steps: {len(steps)}")
            self.evaluation_logger.info(f"Evaluation description: {evaluation_description}")
            self.evaluation_logger.info("=" * 80)
        
        total_score = 0.0
        steps_completed = 0
        details: List[str] = []
        prior_evaluation_actions: List[str] = []
        
        try:
            # Navigate to the initial page
            if self.page is None:
                raise RuntimeError("Playwright page is not initialized. Use BenchmarkEvaluator as a context manager.")
            initial_url = website_url.rstrip('/') + initial_page
            self.page.goto(initial_url)
            time.sleep(2)  # Allow page to load
            
            for step in steps:
                self.logger.info(f"Executing step {step.step}: {step.action}")
                
                # Log step details to evaluation log
                if hasattr(self, 'evaluation_logger') and self.evaluation_logger:
                    self.evaluation_logger.info(f"--- STEP {step.step} ---")
                    self.evaluation_logger.info(f"Action: {step.action}")
                    self.evaluation_logger.info(f"Expected: {step.expected}")
                    self.evaluation_logger.info(f"Value: {step.value}")
                    self.evaluation_logger.info(f"Prior evaluation actions: {prior_evaluation_actions}")
                
                step_result = self._execute_step_with_ai(step, evaluation_description, prior_evaluation_actions)
                
                if step_result['success']:
                    total_score += step.value
                    steps_completed += 1
                    details.append(f"Step {step.step}: PASSED - {step.action}")
                    prior_evaluation_actions.append(f"Step {step.step}: {step.action} - SUCCESS")
                    self.logger.info(f"Step {step.step} passed")
                    
                    # Log success to evaluation log
                    if hasattr(self, 'evaluation_logger') and self.evaluation_logger:
                        self.evaluation_logger.info(f"Step {step.step} PASSED - {step.action}")
                        self.evaluation_logger.info(f"Current score: {total_score}")
                else:
                    details.append(f"Step {step.step}: FAILED - {step.action} - {step_result['reason']}")
                    prior_evaluation_actions.append(f"Step {step.step}: {step.action} - FAILED: {step_result['reason']}")
                    self.logger.info(f"Step {step.step} failed: {step_result['reason']}")
                    
                    # Log failure to evaluation log
                    if hasattr(self, 'evaluation_logger') and self.evaluation_logger:
                        self.evaluation_logger.error(f"Step {step.step} FAILED - {step.action}")
                        self.evaluation_logger.error(f"Failure reason: {step_result['reason']}")
                    
                    break  # Stop at first failure
            
            passed = steps_completed == len(steps)
            
            # Log evaluation completion
            if hasattr(self, 'evaluation_logger') and self.evaluation_logger:
                self.evaluation_logger.info("=" * 80)
                self.evaluation_logger.info(f"=== EVALUATION COMPLETED: {evaluation_name} ===")
                self.evaluation_logger.info(f"Steps completed: {steps_completed}/{len(steps)}")
                self.evaluation_logger.info(f"Total score: {total_score}")
                self.evaluation_logger.info(f"Passed: {passed}")
                self.evaluation_logger.info(f"Details: {'; '.join(details)}")
                self.evaluation_logger.info("=" * 80)
            
            return EvaluationResult(
                evaluation_name=evaluation_name,
                passed=passed,
                score=total_score,
                details="; ".join(details),
                steps_completed=steps_completed,
                total_steps=len(steps)
            )
            
        except Exception as e:
            self.logger.error(f"Error in evaluation: {e}")
            # Log error to evaluation log as well
            if hasattr(self, 'evaluation_logger') and self.evaluation_logger:
                self.evaluation_logger.error("=" * 80)
                self.evaluation_logger.error(f"=== EVALUATION FAILED: {evaluation_name} ===")
                self.evaluation_logger.error(f"Error: {e}")
                self.evaluation_logger.error(f"Stack trace: {traceback.format_exc()}")
                self.evaluation_logger.error("=" * 80)
            return EvaluationResult(
                evaluation_name=evaluation_name,
                passed=False,
                score=0.0,
                details=f"Evaluation error: {str(e)}",
                steps_completed=0,
                total_steps=len(steps),
                error_message=str(e)
            )
    
    def _execute_step_with_ai(self, step: EvaluationStep, evaluation_description: str, prior_evaluation_actions: List[str]) -> Dict[str, Any]:
        """Execute a single step using AI-driven evaluation with up to 10 actions per step."""
        try:
            action_count = 0
            max_actions = 10
            prior_playwright_actions: List[str] = []
            
            # Log step execution start
            if hasattr(self, 'evaluation_logger') and self.evaluation_logger:
                self.evaluation_logger.info(f"Starting AI-driven execution for step {step.step}")
                self.evaluation_logger.info(f"Step action: {step.action}")
                self.evaluation_logger.info(f"Step expected: {step.expected}")
                self.evaluation_logger.info(f"Max actions allowed: {max_actions}")
            
            while action_count < max_actions:
                # Get current page HTML
                if self.page is None:
                    raise RuntimeError("Playwright page is not initialized. Use BenchmarkEvaluator as a context manager.")
                page_html = self.page.content()
                
                # Create AI prompt for evaluation
                prompt = self._create_evaluation_prompt(step, page_html, evaluation_description, prior_evaluation_actions, prior_playwright_actions, action_count)
                
                # Log AI prompt to evaluation log
                if hasattr(self, 'evaluation_logger') and self.evaluation_logger:
                    self.evaluation_logger.info(f"--- AI ACTION {action_count + 1} ---")
                    if self.page is not None:
                        self.evaluation_logger.info(f"Current page URL: {self.page.url}")
                        self.evaluation_logger.info(f"Page title: {self.page.title()}")
                    self.evaluation_logger.info(f"AI Prompt: {prompt}")
                
                # Get AI response
                response = self._get_ai_response(prompt)
                
                # Log AI response to evaluation log
                if hasattr(self, 'evaluation_logger') and self.evaluation_logger:
                    self.evaluation_logger.info(f"AI Response: {response}")
                
                # Parse AI response and execute action
                action_result = self._parse_and_execute_action(response, step)
                
                # Log action result to evaluation log
                if hasattr(self, 'evaluation_logger') and self.evaluation_logger:
                    self.evaluation_logger.info(f"Action result: {action_result}")
                
                if action_result['success']:
                    if response == "success":
                        # Step requirement is met
                        if hasattr(self, 'evaluation_logger') and self.evaluation_logger:
                            self.evaluation_logger.info(f"Step requirement met after {action_count + 1} actions")
                        return {'success': True, 'reason': f'Step completed after {action_count + 1} actions'}
                    elif response == "failure":
                        # Step cannot be completed
                        if hasattr(self, 'evaluation_logger') and self.evaluation_logger:
                            self.evaluation_logger.error(f"Step cannot be completed after {action_count + 1} actions")
                        return {'success': False, 'reason': f'Step failed after {action_count + 1} actions: Step cannot be completed'}
                    else:
                        # Action was successful, continue to next action
                        action_count += 1
                        prior_playwright_actions.append(f"Action {action_count}: {response} - SUCCESS")
                        if hasattr(self, 'evaluation_logger') and self.evaluation_logger:
                            self.evaluation_logger.info(f"Action {action_count} successful: {response}")
                        continue
                else:
                    # Action failed
                    if hasattr(self, 'evaluation_logger') and self.evaluation_logger:
                        self.evaluation_logger.error(f"Action {action_count + 1} failed: {action_result['reason']}")
                    return {'success': False, 'reason': f'Step failed after {action_count + 1} actions: {action_result["reason"]}'}
            
            # Reached max actions without success
            if hasattr(self, 'evaluation_logger') and self.evaluation_logger:
                self.evaluation_logger.error(f"Reached maximum actions ({max_actions}) without success")
            return {'success': False, 'reason': f'Step failed after {max_actions} actions: Maximum actions reached'}
            
        except Exception as e:
            if hasattr(self, 'evaluation_logger') and self.evaluation_logger:
                self.evaluation_logger.error(f"Exception during step execution: {e}")
                self.evaluation_logger.error(f"Stack trace: {traceback.format_exc()}")
            return {
                'success': False,
                'reason': f'Error during step execution: {str(e)}'
            }
    
    def _create_evaluation_prompt(self, step: EvaluationStep, page_html: str, evaluation_description: str, prior_evaluation_actions: List[str], prior_playwright_actions: List[str], action_count: int) -> str:
        """Create AI prompt for step evaluation."""
        prior_evaluation_text = "\n".join(prior_evaluation_actions) if prior_evaluation_actions else "No prior evaluation steps"
        prior_playwright_text = "\n".join(prior_playwright_actions) if prior_playwright_actions else "No prior actions in this step"
        
        return f"""
You are an AI evaluator testing a website. Your task is to evaluate the current step and provide the next action.

Evaluation Description: {evaluation_description}

Prior Evaluation Steps:
{prior_evaluation_text}

Prior Actions in Current Step:
{prior_playwright_text}

Current Step: {step.step} (Action {action_count + 1}/10)
Action Required: {step.action}
Expected Result: {step.expected}

Current Page HTML (truncated for brevity):
{page_html[:10000]}...

You can perform up to 10 actions to complete this step. Each action should bring you closer to completing the step requirement.

Based on the current page content and the step requirements, respond with exactly one of the following:

1. A Playwright action in the format: "click:selector" or "fill:selector:value" or "navigate:url"
2. "success" - if the step requirement is already met
3. "failure" - if the step cannot be completed
4. "sleep" - if you need more time to observe the page

Examples:
- "click:button[type='submit']"
- "fill:input[name='email']:test@example.com"
- "navigate:/admin/contact"
- "success"
- "failure"
- "sleep"

Respond with only the action, no additional text.
"""
    
    def _get_ai_response(self, prompt: str) -> str:
        """Get response from OpenAI."""
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-5",
                messages=[
                    {"role": "system", "content": "You are a precise AI evaluator that responds with only the required action."},
                    {"role": "user", "content": prompt}
                ],
                max_completion_tokens=5000
            )
            
            # Handle potential None content with better error logging
            content = response.choices[0].message.content
            if content is None:
                self.logger.error("AI response content is None")
                if hasattr(self, 'evaluation_logger') and self.evaluation_logger:
                    self.evaluation_logger.error("AI response content is None")
                    self.evaluation_logger.error(f"Response finish reason: {response.choices[0].finish_reason}")
                    self.evaluation_logger.error(f"Response usage: {response.usage}")
                return "failure"
            
            stripped_content = content.strip()
            if not stripped_content:
                self.logger.error(f"AI response is empty after stripping. Original content: '{content}'")
                if hasattr(self, 'evaluation_logger') and self.evaluation_logger:
                    self.evaluation_logger.error(f"AI response is empty after stripping. Original content: '{content}'")
                    self.evaluation_logger.error(f"Response finish reason: {response.choices[0].finish_reason}")
                    self.evaluation_logger.error(f"Response usage: {response.usage}")
                return "failure"
            
            return stripped_content
        except Exception as e:
            self.logger.error(f"Error getting AI response: {e}")
            # Log error to evaluation log as well
            if hasattr(self, 'evaluation_logger') and self.evaluation_logger:
                self.evaluation_logger.error(f"Error getting AI response: {e}")
                self.evaluation_logger.error(f"Stack trace: {traceback.format_exc()}")
            return "failure"
    
    def _parse_and_execute_action(self, response: str, step: EvaluationStep) -> Dict[str, Any]:
        """Parse AI response and execute the corresponding action."""
        try:
            # Log action execution start
            if hasattr(self, 'evaluation_logger') and self.evaluation_logger:
                self.evaluation_logger.info(f"Executing action: {response}")
                if self.page is not None:
                    self.evaluation_logger.info(f"Current page URL: {self.page.url}")
            
            if response == "success":
                if hasattr(self, 'evaluation_logger') and self.evaluation_logger:
                    self.evaluation_logger.info("Action: Step requirement already met")
                return {'success': True, 'reason': 'Step requirement already met'}
            
            elif response == "failure":
                if hasattr(self, 'evaluation_logger') and self.evaluation_logger:
                    self.evaluation_logger.error("Action: Step cannot be completed")
                return {'success': False, 'reason': 'Step cannot be completed'}
            
            elif response == "sleep":
                if hasattr(self, 'evaluation_logger') and self.evaluation_logger:
                    self.evaluation_logger.info("Action: Sleeping for 2 seconds")
                time.sleep(2)
                return {'success': True, 'reason': 'Waited for page to load'}
            
            elif response.startswith("click:"):
                selector = response[6:]
                if hasattr(self, 'evaluation_logger') and self.evaluation_logger:
                    self.evaluation_logger.info(f"Action: Clicking selector '{selector}'")
                if self.page is None:
                    raise RuntimeError("Playwright page is not initialized. Use BenchmarkEvaluator as a context manager.")
                self.page.click(selector)
                time.sleep(1)
                if hasattr(self, 'evaluation_logger') and self.evaluation_logger:
                    if self.page is not None:
                        self.evaluation_logger.info(f"Click successful, new URL: {self.page.url}")
                return {'success': True, 'reason': f'Clicked {selector}'}
            
            elif response.startswith("fill:"):
                parts = response[5:].split(":")
                if len(parts) >= 2:
                    selector = parts[0]
                    value = ":".join(parts[1:])
                    if hasattr(self, 'evaluation_logger') and self.evaluation_logger:
                        self.evaluation_logger.info(f"Action: Filling selector '{selector}' with value '{value}'")
                    if self.page is None:
                        raise RuntimeError("Playwright page is not initialized. Use BenchmarkEvaluator as a context manager.")
                    self.page.fill(selector, value)
                    time.sleep(0.5)
                    if hasattr(self, 'evaluation_logger') and self.evaluation_logger:
                        self.evaluation_logger.info("Fill successful")
                    return {'success': True, 'reason': f'Filled {selector} with {value}'}
                else:
                    if hasattr(self, 'evaluation_logger') and self.evaluation_logger:
                        self.evaluation_logger.error(f"Invalid fill format: {response}")
                    return {'success': False, 'reason': 'Invalid fill format'}
            
            elif response.startswith("navigate:"):
                url = response[9:]
                if hasattr(self, 'evaluation_logger') and self.evaluation_logger:
                    self.evaluation_logger.info(f"Action: Navigating to '{url}'")
                if url.startswith("/"):
                    # Relative URL
                    if self.page is None:
                        raise RuntimeError("Playwright page is not initialized. Use BenchmarkEvaluator as a context manager.")
                    current_url = self.page.url
                    base_url = current_url.split("/")[0] + "//" + current_url.split("/")[2]
                    full_url = base_url + url
                else:
                    full_url = url
                
                if hasattr(self, 'evaluation_logger') and self.evaluation_logger:
                    self.evaluation_logger.info(f"Full navigation URL: {full_url}")
                if self.page is None:
                    raise RuntimeError("Playwright page is not initialized. Use BenchmarkEvaluator as a context manager.")
                self.page.goto(full_url)
                time.sleep(2)
                if hasattr(self, 'evaluation_logger') and self.evaluation_logger:
                    if self.page is not None:
                        self.evaluation_logger.info(f"Navigation successful, new URL: {self.page.url}")
                return {'success': True, 'reason': f'Navigated to {full_url}'}
            
            else:
                if hasattr(self, 'evaluation_logger') and self.evaluation_logger:
                    self.evaluation_logger.error(f"Unknown action format: {response}")
                return {'success': False, 'reason': f'Unknown action: {response}'}
                
        except Exception as e:
            if hasattr(self, 'evaluation_logger') and self.evaluation_logger:
                self.evaluation_logger.error(f"Exception during action execution: {e}")
                self.evaluation_logger.error(f"Stack trace: {traceback.format_exc()}")
            return {'success': False, 'reason': f'Error executing action: {str(e)}'}
    
    def check_website_accessible(self, website_url: str) -> Tuple[bool, str]:
        """Check if website is accessible."""
        try:
            if self.page is None:
                return False, "Playwright page is not initialized. Use BenchmarkEvaluator as a context manager."
            self.page.goto(website_url)
            time.sleep(3)
            
            if self.page.url == website_url:
                return True, f"Website accessible at {website_url}"
            else:
                return False, f"Website redirected to {self.page.url}"
                
        except Exception as e:
            return False, f"Error accessing website: {str(e)}" 