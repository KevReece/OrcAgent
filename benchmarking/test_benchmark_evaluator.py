#!/usr/bin/env python3
"""
AI-Driven Benchmark Evaluator Tests

Tests for the AI-driven benchmark evaluation engine.
"""

import unittest
import os
import sys
import tempfile
import shutil
import json
from pathlib import Path
from unittest.mock import Mock, patch

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from benchmarking.benchmark_evaluator import (
    BenchmarkEvaluator, 
    EvaluationResult,
    EvaluationStep,
    ScenarioEvaluationResult
)


class TestBenchmarkEvaluator(unittest.TestCase):
    """Test the AI-driven benchmark evaluation engine."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.openai_api_key = "test-api-key"
        
        # Create test evaluation file
        self.test_evaluation_file = os.path.join(self.temp_dir, "test_evaluation.json")
        test_evaluation = {
            "name": "test_evaluation",
            "description": "Test evaluation",
            "initial_page": "/",
            "max_steps": 10,
            "steps": [
                {
                    "step": 1,
                    "action": "Navigate to homepage",
                    "expected": "Homepage should load",
                    "value": 1.0
                },
                {
                    "step": 2,
                    "action": "Check for contact form",
                    "expected": "Contact form should be present",
                    "value": 1.5
                }
            ]
        }
        
        with open(self.test_evaluation_file, 'w') as f:
            json.dump(test_evaluation, f)
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_evaluator_initialization(self):
        """Test that evaluator initializes correctly."""
        with BenchmarkEvaluator(self.openai_api_key) as evaluator:
            self.assertIsNotNone(evaluator)
            self.assertIsNotNone(evaluator.logger)
            self.assertIsNotNone(evaluator.openai_client)
    
    def test_load_evaluation_steps(self):
        """Test loading evaluation steps from JSON file."""
        with BenchmarkEvaluator(self.openai_api_key) as evaluator:
            steps, description, initial_page = evaluator._load_evaluation_steps(self.test_evaluation_file)
            
            self.assertEqual(len(steps), 2)
            self.assertEqual(steps[0].step, 1)
            self.assertEqual(steps[0].action, "Navigate to homepage")
            self.assertEqual(steps[0].value, 1.0)
            self.assertEqual(steps[1].step, 2)
            self.assertEqual(steps[1].action, "Check for contact form")
            self.assertEqual(steps[1].value, 1.5)
            self.assertEqual(description, "Test evaluation")
            self.assertEqual(initial_page, "/")
    
    def test_create_evaluation_prompt(self):
        """Test creation of evaluation prompt."""
        with BenchmarkEvaluator(self.openai_api_key) as evaluator:
            step = EvaluationStep(
                step=1,
                action="Click submit button",
                expected="Form should submit successfully",
                value=1.0
            )
            
            page_html = "<html><body><form><button type='submit'>Submit</button></form></body></html>"
            prior_evaluation_actions = ["Step 1: Previous evaluation action"]
            prior_playwright_actions = ["Action 1: click:button[type='submit'] - SUCCESS"]
            action_count = 2
            
            prompt = evaluator._create_evaluation_prompt(step, page_html, "Test evaluation", prior_evaluation_actions, prior_playwright_actions, action_count)
            
            self.assertIn("Test evaluation", prompt)
            self.assertIn("Click submit button", prompt)
            self.assertIn("Form should submit successfully", prompt)
            self.assertIn("<html>", prompt)
            self.assertIn("Step 1: Previous evaluation action", prompt)
            self.assertIn("Action 1: click:button[type='submit'] - SUCCESS", prompt)
            self.assertIn("Action 3/10", prompt)
            self.assertIn("You can perform up to 10 actions", prompt)
    
    @patch('openai.OpenAI')
    def test_get_ai_response(self, mock_openai):
        """Test getting AI response from OpenAI."""
        mock_client = Mock()
        mock_openai.return_value = mock_client
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "click:button[type='submit']"
        mock_client.chat.completions.create.return_value = mock_response
        
        with BenchmarkEvaluator(self.openai_api_key) as evaluator:
            response = evaluator._get_ai_response("test prompt")
            self.assertEqual(response, "click:button[type='submit']")
    
    def test_parse_and_execute_action_success(self):
        """Test parsing and executing success action."""
        with BenchmarkEvaluator(self.openai_api_key) as evaluator:
            step = EvaluationStep(
                step=1,
                action="Test action",
                expected="Success",
                value=1.0
            )
            
            result = evaluator._parse_and_execute_action("success", step)
            self.assertTrue(result['success'])
            self.assertEqual(result['reason'], 'Step requirement already met')
    
    def test_parse_and_execute_action_failure(self):
        """Test parsing and executing failure action."""
        with BenchmarkEvaluator(self.openai_api_key) as evaluator:
            step = EvaluationStep(
                step=1,
                action="Test action", 
                expected="Success",
                value=1.0
            )
            
            result = evaluator._parse_and_execute_action("failure", step)
            self.assertFalse(result['success'])
            self.assertEqual(result['reason'], 'Step cannot be completed')
    
    def test_parse_and_execute_action_sleep(self):
        """Test parsing and executing sleep action."""
        with BenchmarkEvaluator(self.openai_api_key) as evaluator:
            step = EvaluationStep(
                step=1,
                action="Test action",
                expected="Success", 
                value=1.0
            )
            
            result = evaluator._parse_and_execute_action("sleep", step)
            self.assertTrue(result['success'])
            self.assertEqual(result['reason'], 'Waited for page to load')
    
    def test_parse_and_execute_action_click(self):
        """Test parsing and executing click action."""
        with BenchmarkEvaluator(self.openai_api_key) as evaluator:
            step = EvaluationStep(
                step=1,
                action="Test action",
                expected="Success",
                value=1.0
            )
            
            # Mock the page.click method
            evaluator.page = Mock()
            
            result = evaluator._parse_and_execute_action("click:button[type='submit']", step)
            self.assertTrue(result['success'])
            self.assertEqual(result['reason'], "Clicked button[type='submit']")
            evaluator.page.click.assert_called_once_with("button[type='submit']")
    
    def test_parse_and_execute_action_fill(self):
        """Test parsing and executing fill action."""
        with BenchmarkEvaluator(self.openai_api_key) as evaluator:
            step = EvaluationStep(
                step=1,
                action="Test action",
                expected="Success",
                value=1.0
            )
            
            # Mock the page.fill method
            evaluator.page = Mock()
            
            result = evaluator._parse_and_execute_action("fill:input[name='email']:test@example.com", step)
            self.assertTrue(result['success'])
            self.assertEqual(result['reason'], "Filled input[name='email'] with test@example.com")
            evaluator.page.fill.assert_called_once_with("input[name='email']", "test@example.com")
    
    def test_parse_and_execute_action_navigate(self):
        """Test parsing and executing navigate action."""
        with BenchmarkEvaluator(self.openai_api_key) as evaluator:
            step = EvaluationStep(
                step=1,
                action="Test action",
                expected="Success",
                value=1.0
            )
            
            # Mock the page.goto method and url property
            evaluator.page = Mock()
            evaluator.page.url = "https://example.com"
            
            result = evaluator._parse_and_execute_action("navigate:/admin/contact", step)
            self.assertTrue(result['success'])
            self.assertIn("Navigated to", result['reason'])
            evaluator.page.goto.assert_called_once()
    
    def test_parse_and_execute_action_unknown(self):
        """Test parsing and executing unknown action."""
        with BenchmarkEvaluator(self.openai_api_key) as evaluator:
            step = EvaluationStep(
                step=1,
                action="Test action",
                expected="Success",
                value=1.0
            )
            
            result = evaluator._parse_and_execute_action("unknown_action", step)
            self.assertFalse(result['success'])
            self.assertEqual(result['reason'], "Unknown action: unknown_action")
    
    def test_evaluation_result_creation(self):
        """Test evaluation result creation."""
        result = EvaluationResult(
            evaluation_name="test_evaluation",
            passed=True,
            score=2.0,
            details="Test passed successfully",
            steps_completed=2,
            total_steps=2
        )
        
        self.assertEqual(result.evaluation_name, "test_evaluation")
        self.assertTrue(result.passed)
        self.assertEqual(result.score, 2.0)
        self.assertEqual(result.details, "Test passed successfully")
        self.assertEqual(result.steps_completed, 2)
        self.assertEqual(result.total_steps, 2)
        self.assertIsNone(result.error_message)
    
    def test_evaluation_step_creation(self):
        """Test evaluation step creation."""
        step = EvaluationStep(
            step=1,
            action="Test action",
            expected="Success",
            value=1.5
        )
        
        self.assertEqual(step.step, 1)
        self.assertEqual(step.action, "Test action")
        self.assertEqual(step.expected, "Success")
        self.assertEqual(step.value, 1.5)
    
    def test_execute_step_with_multiple_actions(self):
        """Test executing a step with multiple actions."""
        with BenchmarkEvaluator(self.openai_api_key) as evaluator:
            step = EvaluationStep(
                step=1,
                action="Fill form and submit",
                expected="Form should be submitted successfully",
                value=1.0
            )
            
            # Mock the page and AI response methods
            evaluator.page = Mock()
            evaluator.page.content.return_value = "<html><body><form><input name='email'><button type='submit'>Submit</button></form></body></html>"
            
            # Mock AI responses for multiple actions
            with patch.object(evaluator, '_get_ai_response') as mock_get_response:
                mock_get_response.side_effect = [
                    "fill:input[name='email']:test@example.com",
                    "click:button[type='submit']",
                    "success"
                ]
                
                result = evaluator._execute_step_with_ai(step, "Test evaluation", [])
                
                self.assertTrue(result['success'])
                self.assertIn("Step completed after 3 actions", result['reason'])
                self.assertEqual(mock_get_response.call_count, 3)


if __name__ == "__main__":
    unittest.main() 