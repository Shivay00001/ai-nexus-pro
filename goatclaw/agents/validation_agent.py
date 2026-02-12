"""
GOATCLAW Validation Agent
AI-powered output validation with self-healing capabilities.

Enhanced with:
- AI-powered validation rules
- Self-healing suggestions
- Schema validation
- Semantic validation
- Auto-fix capabilities
"""

import asyncio
import re
import json
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
import logging

from goatclaw.core.structs import (
    TaskNode, TaskStatus, ValidationResult,
    SecurityContext, LLMConfig, LLMProvider
)
from goatclaw.core.event_bus import EventBus, Event
from goatclaw.agents.base_agent import BaseAgent

logger = logging.getLogger("goatclaw.validation_agent")


class ValidationAgent(BaseAgent):
    """
    USP: AI-powered validation with self-healing.
    
    Features:
    - Multiple validation strategies
    - AI-powered semantic validation
    - Auto-fix suggestions
    - Schema validation
    - Custom validation rules
    """

    def __init__(self, event_bus: EventBus, config: Optional[Dict] = None):
        config = config or {}
        super().__init__("ValidationAgent", event_bus, config)
        
        self._validators: Dict[str, Callable] = {
            "schema": self._validate_schema,
            "type": self._validate_type,
            "range": self._validate_range,
            "format": self._validate_format,
            "custom": self._validate_custom,
            "semantic": self._validate_semantic,
        }
        
        self._auto_fix_enabled = config.get("auto_fix_enabled", True)
        self._llm_config = config.get("llm_config")
        
        logger.info("ValidationAgent initialized with AI capabilities")

    async def execute(
        self,
        task_node: TaskNode,
        context: SecurityContext
    ) -> Dict[str, Any]:
        """Execute validation on task output."""
        validation_rule = task_node.validation_rule
        output_data = task_node.output_data
        
        if not validation_rule:
            return {
                "valid": True,
                "message": "No validation rule specified"
            }
        
        # Parse validation rule
        validator_type, rule_config = self._parse_rule(validation_rule)
        
        # Execute validation
        result = await self._execute_validation(
            validator_type,
            rule_config,
            output_data,
            task_node
        )
        
        # Create validation result
        validation_result = ValidationResult(
            node_id=task_node.node_id,
            rule=validation_rule,
            passed=result["valid"],
            expected=result.get("expected"),
            actual=result.get("actual"),
            message=result.get("message", ""),
            confidence_score=result.get("confidence", 1.0),
            suggestions=result.get("suggestions", []),
            auto_fixable=result.get("auto_fixable", False)
        )
        
        # Publish validation event
        await self.event_bus.publish(Event(
            event_type=f"validation.{'passed' if result['valid'] else 'failed'}",
            source=self.agent_type,
            payload={
                "node_id": task_node.node_id,
                "result": result,
                "rule": validation_rule
            },
            priority=0 if result["valid"] else 1
        ))
        
        # Attempt auto-fix if enabled and failed
        if not result["valid"] and self._auto_fix_enabled and result.get("auto_fixable"):
            fix_result = await self._attempt_auto_fix(task_node, validation_result)
            if fix_result["fixed"]:
                logger.info(f"Auto-fixed validation issue for {task_node.node_id}")
                validation_result.passed = True
                validation_result.message += " (auto-fixed)"
        
        return {
            "valid": validation_result.passed,
            "message": validation_result.message,
            "expected": validation_result.expected,
            "actual": validation_result.actual,
            "suggestions": validation_result.suggestions,
            "confidence": validation_result.confidence_score
        }

    def _parse_rule(self, rule: str) -> tuple[str, Dict[str, Any]]:
        """
        Parse validation rule string into validator type and config.
        
        Examples:
        - "output.status == 'success'" -> (custom, {expression: ...})
        - "schema: {type: object}" -> (schema, {schema: ...})
        - "type: string" -> (type, {expected_type: string})
        """
        if rule.startswith("schema:"):
            schema_str = rule[7:].strip()
            try:
                schema = json.loads(schema_str)
                return "schema", {"schema": schema}
            except json.JSONDecodeError:
                return "schema", {"schema": {}}
        
        if rule.startswith("type:"):
            expected_type = rule[5:].strip()
            return "type", {"expected_type": expected_type}
        
        if rule.startswith("range:"):
            range_str = rule[6:].strip()
            # Parse "min:0,max:100"
            parts = dict(part.split(":") for part in range_str.split(","))
            return "range", parts
        
        if rule.startswith("format:"):
            format_type = rule[7:].strip()
            return "format", {"format": format_type}
        
        if rule.startswith("semantic:"):
            semantic_rule = rule[9:].strip()
            return "semantic", {"rule": semantic_rule}
        
        # Default to custom expression
        return "custom", {"expression": rule}

    async def _execute_validation(
        self,
        validator_type: str,
        rule_config: Dict[str, Any],
        output_data: Dict[str, Any],
        task_node: TaskNode
    ) -> Dict[str, Any]:
        """Execute the appropriate validator."""
        validator = self._validators.get(validator_type)
        
        if not validator:
            return {
                "valid": False,
                "message": f"Unknown validator type: {validator_type}"
            }
        
        return await validator(rule_config, output_data, task_node)

    async def _validate_schema(
        self,
        config: Dict[str, Any],
        output: Dict[str, Any],
        task_node: TaskNode
    ) -> Dict[str, Any]:
        """Validate output against a JSON schema."""
        schema = config.get("schema", {})
        
        # Simple schema validation (can be enhanced with jsonschema library)
        if "type" in schema:
            expected_type = schema["type"]
            actual_type = type(output).__name__
            
            if expected_type == "object" and not isinstance(output, dict):
                return {
                    "valid": False,
                    "expected": "object",
                    "actual": actual_type,
                    "message": f"Expected object, got {actual_type}",
                    "auto_fixable": False
                }
        
        if "required" in schema:
            required_fields = schema["required"]
            missing = [f for f in required_fields if f not in output]
            
            if missing:
                return {
                    "valid": False,
                    "expected": required_fields,
                    "actual": list(output.keys()),
                    "message": f"Missing required fields: {missing}",
                    "suggestions": [f"Add field: {f}" for f in missing],
                    "auto_fixable": True
                }
        
        return {
            "valid": True,
            "message": "Schema validation passed"
        }

    async def _validate_type(
        self,
        config: Dict[str, Any],
        output: Dict[str, Any],
        task_node: TaskNode
    ) -> Dict[str, Any]:
        """Validate output type."""
        expected_type = config.get("expected_type", "")
        actual_type = type(output).__name__
        
        type_mapping = {
            "string": str,
            "int": int,
            "float": float,
            "bool": bool,
            "list": list,
            "dict": dict,
            "object": dict,
        }
        
        expected_class = type_mapping.get(expected_type.lower())
        
        if expected_class and not isinstance(output, expected_class):
            return {
                "valid": False,
                "expected": expected_type,
                "actual": actual_type,
                "message": f"Type mismatch: expected {expected_type}, got {actual_type}",
                "auto_fixable": True,
                "suggestions": [f"Convert to {expected_type}"]
            }
        
        return {
            "valid": True,
            "message": "Type validation passed"
        }

    async def _validate_range(
        self,
        config: Dict[str, Any],
        output: Dict[str, Any],
        task_node: TaskNode
    ) -> Dict[str, Any]:
        """Validate numeric range."""
        if not isinstance(output, (int, float)):
            return {
                "valid": False,
                "message": "Range validation requires numeric output"
            }
        
        min_val = float(config.get("min", float("-inf")))
        max_val = float(config.get("max", float("inf")))
        
        if not (min_val <= output <= max_val):
            return {
                "valid": False,
                "expected": f"{min_val} <= value <= {max_val}",
                "actual": output,
                "message": f"Value {output} out of range [{min_val}, {max_val}]",
                "auto_fixable": True,
                "suggestions": [
                    f"Clamp to range: {max(min_val, min(output, max_val))}"
                ]
            }
        
        return {
            "valid": True,
            "message": "Range validation passed"
        }

    async def _validate_format(
        self,
        config: Dict[str, Any],
        output: Dict[str, Any],
        task_node: TaskNode
    ) -> Dict[str, Any]:
        """Validate output format (e.g., email, url, date)."""
        format_type = config.get("format", "")
        
        if not isinstance(output, str):
            return {
                "valid": False,
                "message": "Format validation requires string output"
            }
        
        patterns = {
            "email": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
            "url": r"^https?://[^\s]+$",
            "uuid": r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
            "date": r"^\d{4}-\d{2}-\d{2}$",
        }
        
        pattern = patterns.get(format_type.lower())
        
        if pattern:
            if not re.match(pattern, output):
                return {
                    "valid": False,
                    "expected": format_type,
                    "actual": output,
                    "message": f"Invalid {format_type} format",
                    "auto_fixable": False
                }
        
        return {
            "valid": True,
            "message": "Format validation passed"
        }

    async def _validate_custom(
        self,
        config: Dict[str, Any],
        output: Dict[str, Any],
        task_node: TaskNode
    ) -> Dict[str, Any]:
        """
        Validate using custom expression.
        
        Expression can reference:
        - output: the output data
        - task: the task node
        
        Example: "output.confidence > 0.5"
        """
        expression = config.get("expression", "")
        
        try:
            # Create safe evaluation context
            context = {
                "output": output,
                "task": task_node,
                "len": len,
                "str": str,
                "int": int,
                "float": float,
            }
            
            # Evaluate expression
            result = eval(expression, {"__builtins__": {}}, context)
            
            if isinstance(result, bool):
                return {
                    "valid": result,
                    "message": f"Expression '{expression}' evaluated to {result}",
                    "confidence": 1.0
                }
            else:
                return {
                    "valid": False,
                    "message": f"Expression must return boolean, got {type(result).__name__}"
                }
        
        except Exception as e:
            logger.exception(f"Error evaluating expression '{expression}': {e}")
            return {
                "valid": False,
                "message": f"Expression evaluation error: {str(e)}"
            }

    async def _validate_semantic(
        self,
        config: Dict[str, Any],
        output: Dict[str, Any],
        task_node: TaskNode
    ) -> Dict[str, Any]:
        """
        USP: AI-powered semantic validation.
        
        Uses LLM to validate if output semantically matches the rule.
        """
        rule = config.get("rule", "")
        
        # Real LLM-powered semantic validation
        output_str = json.dumps(output, indent=2) if isinstance(output, dict) else str(output)
        
        prompt = f"""
        Validate if the following output semantically follows the rule:
        Rule: {rule}
        Output: {output_str}
        
        Provide your response as a JSON object with:
        - "valid" (boolean)
        - "confidence" (float, 0-1)
        - "message" (string explaining the result)
        """
        system = "You are an expert quality assurance agent. Your output must be valid JSON."
        
        response = await self._call_llm(prompt, system=system)
        
        try:
            if "{" in response:
                json_part = response[response.find("{"):response.rfind("}")+1]
                result = json.loads(json_part)
                return {
                    "valid": result.get("valid", False),
                    "confidence": result.get("confidence", 0.0),
                    "message": result.get("message", "Semantic validation complete")
                }
        except Exception as e:
            logger.error(f"Semantic validation parsing failed: {e}")
        
        return {
            "valid": False,
            "confidence": 0.0,
            "message": "Semantic validation failed due to parsing error"
        }

    async def _attempt_auto_fix(
        self,
        task_node: TaskNode,
        validation_result: ValidationResult
    ) -> Dict[str, Any]:
        """
        USP: Attempt to auto-fix validation failures.
        
        Returns:
            Dictionary with 'fixed' boolean and 'output' if successful
        """
        # Check if auto-fixable
        if not validation_result.auto_fixable:
            return {"fixed": False}
        
        output = task_node.output_data
        
        # Type conversion
        if "type" in validation_result.rule.lower():
            try:
                expected_type = validation_result.expected
                if expected_type == "string":
                    task_node.output_data = str(output)
                elif expected_type == "int":
                    task_node.output_data = int(output)
                elif expected_type == "float":
                    task_node.output_data = float(output)
                
                logger.info(f"Auto-fixed type for {task_node.node_id}")
                return {"fixed": True, "output": task_node.output_data}
            except (ValueError, TypeError):
                return {"fixed": False}
        
        # Range clamping
        if "range" in validation_result.rule.lower() and isinstance(output, (int, float)):
            # Extract min/max from suggestions
            suggestion = validation_result.suggestions[0] if validation_result.suggestions else ""
            if "Clamp to range:" in suggestion:
                try:
                    value = float(suggestion.split(":")[-1].strip())
                    task_node.output_data = value
                    logger.info(f"Auto-fixed range for {task_node.node_id}")
                    return {"fixed": True, "output": value}
                except ValueError:
                    pass
        
        # Add missing required fields (with default values)
        if "missing required fields" in validation_result.message.lower():
            if isinstance(output, dict):
                for suggestion in validation_result.suggestions:
                    if suggestion.startswith("Add field:"):
                        field = suggestion.split(":")[-1].strip()
                        task_node.output_data[field] = None
                
                logger.info(f"Auto-fixed missing fields for {task_node.node_id}")
                return {"fixed": True, "output": task_node.output_data}
        
        return {"fixed": False}

    def register_custom_validator(
        self,
        name: str,
        validator: Callable
    ):
        """
        Register a custom validator function.
        
        Args:
            name: Name of the validator
            validator: Async function that validates output
        """
        self._validators[name] = validator
        logger.info(f"Registered custom validator: {name}")

    def get_validation_stats(self) -> Dict[str, Any]:
        """Get validation statistics."""
        return {
            **self.get_metrics(),
            "auto_fix_enabled": self._auto_fix_enabled,
            "custom_validators": len(self._validators) - 6,  # Excluding built-in
        }
