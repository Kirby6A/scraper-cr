"""
Data Transformation Service for processing and transforming scraped data
"""
import json
import re
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from decimal import Decimal
from ..models import DataTransformation, TaskExecution


class DataTransformService:
    """Service for transforming scraped data"""
    
    def __init__(self):
        self.type_converters = {
            'string': self._to_string,
            'integer': self._to_integer,
            'float': self._to_float,
            'decimal': self._to_decimal,
            'boolean': self._to_boolean,
            'datetime': self._to_datetime,
            'date': self._to_date,
            'json': self._to_json,
            'list': self._to_list,
        }
        
        self.aggregation_functions = {
            'sum': self._aggregate_sum,
            'avg': self._aggregate_avg,
            'count': self._aggregate_count,
            'min': self._aggregate_min,
            'max': self._aggregate_max,
            'concat': self._aggregate_concat,
            'unique': self._aggregate_unique,
        }
    
    def apply_transformations(
        self,
        data: Any,
        transformations: List[DataTransformation]
    ) -> Any:
        """
        Apply a series of transformations to data
        
        Args:
            data: Input data to transform
            transformations: List of DataTransformation objects
        
        Returns:
            Transformed data
        """
        result = data
        
        # Sort transformations by apply_order
        sorted_transforms = sorted(transformations, key=lambda x: x.apply_order)
        
        for transformation in sorted_transforms:
            if not transformation.is_active:
                continue
            
            if transformation.transformation_type == 'field_mapping':
                result = self._apply_field_mapping(result, transformation.rules)
            elif transformation.transformation_type == 'type_conversion':
                result = self._apply_type_conversion(result, transformation.rules)
            elif transformation.transformation_type == 'aggregation':
                result = self._apply_aggregation(result, transformation.rules)
            elif transformation.transformation_type == 'filter':
                result = self._apply_filter(result, transformation.rules)
            elif transformation.transformation_type == 'custom':
                result = self._apply_custom_function(result, transformation.rules)
        
        return result
    
    def transform_execution_data(
        self,
        execution_id: str,
        transformation_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Transform data from a specific execution
        
        Args:
            execution_id: TaskExecution ID
            transformation_ids: Optional list of specific transformations to apply
        
        Returns:
            Transformed data with metadata
        """
        try:
            execution = TaskExecution.objects.get(id=execution_id)
        except TaskExecution.DoesNotExist:
            return {'error': f'Execution {execution_id} not found'}
        
        # Get transformations
        if transformation_ids:
            transformations = DataTransformation.objects.filter(
                id__in=transformation_ids,
                is_active=True
            )
        else:
            # Get all active transformations for the task
            transformations = DataTransformation.objects.filter(
                task=execution.task,
                is_active=True
            )
        
        # Apply transformations
        original_data = execution.scraped_data or {}
        transformed_data = self.apply_transformations(
            original_data,
            list(transformations)
        )
        
        return {
            'execution_id': str(execution_id),
            'original_data': original_data,
            'transformed_data': transformed_data,
            'transformations_applied': [
                {
                    'id': str(t.id),
                    'name': t.name,
                    'type': t.transformation_type
                }
                for t in transformations
            ],
            'timestamp': datetime.now().isoformat()
        }
    
    def _apply_field_mapping(
        self,
        data: Any,
        rules: Dict[str, Any]
    ) -> Any:
        """
        Apply field mapping transformation
        
        Rules format:
        {
            "mappings": {
                "old_field": "new_field",
                "nested.old": "nested.new"
            },
            "remove_unmapped": false,
            "flatten": false
        }
        """
        if not isinstance(data, dict):
            return data
        
        mappings = rules.get('mappings', {})
        remove_unmapped = rules.get('remove_unmapped', False)
        flatten = rules.get('flatten', False)
        
        if isinstance(data, list):
            return [self._apply_field_mapping(item, rules) for item in data]
        
        result = {}
        
        # Apply mappings
        for old_path, new_path in mappings.items():
            value = self._get_nested_value(data, old_path)
            if value is not None:
                self._set_nested_value(result, new_path, value)
        
        # Include unmapped fields if not removing them
        if not remove_unmapped:
            for key, value in data.items():
                if key not in mappings and not any(m.startswith(f"{key}.") for m in mappings):
                    result[key] = value
        
        # Flatten if requested
        if flatten:
            result = self._flatten_dict(result)
        
        return result
    
    def _apply_type_conversion(
        self,
        data: Any,
        rules: Dict[str, Any]
    ) -> Any:
        """
        Apply type conversion transformation
        
        Rules format:
        {
            "conversions": {
                "field_path": "target_type",
                "price": "float",
                "date": "datetime"
            }
        }
        """
        if not isinstance(data, (dict, list)):
            return data
        
        conversions = rules.get('conversions', {})
        
        if isinstance(data, list):
            return [self._apply_type_conversion(item, rules) for item in data]
        
        result = data.copy()
        
        for field_path, target_type in conversions.items():
            current_value = self._get_nested_value(result, field_path)
            if current_value is not None and target_type in self.type_converters:
                converted_value = self.type_converters[target_type](current_value)
                self._set_nested_value(result, field_path, converted_value)
        
        return result
    
    def _apply_aggregation(
        self,
        data: Any,
        rules: Dict[str, Any]
    ) -> Any:
        """
        Apply aggregation transformation
        
        Rules format:
        {
            "group_by": "category",
            "aggregations": {
                "price": "sum",
                "quantity": "avg",
                "items": "count"
            }
        }
        """
        if not isinstance(data, list):
            return data
        
        group_by = rules.get('group_by')
        aggregations = rules.get('aggregations', {})
        
        if not group_by:
            # No grouping, aggregate all data
            result = {}
            for field, func_name in aggregations.items():
                if func_name in self.aggregation_functions:
                    values = [self._get_nested_value(item, field) for item in data]
                    values = [v for v in values if v is not None]
                    result[f"{field}_{func_name}"] = self.aggregation_functions[func_name](values)
            return result
        
        # Group data
        groups = {}
        for item in data:
            if not isinstance(item, dict):
                continue
            
            group_key = self._get_nested_value(item, group_by)
            if group_key not in groups:
                groups[group_key] = []
            groups[group_key].append(item)
        
        # Aggregate each group
        results = []
        for group_key, group_items in groups.items():
            group_result = {group_by: group_key}
            
            for field, func_name in aggregations.items():
                if func_name in self.aggregation_functions:
                    values = [self._get_nested_value(item, field) for item in group_items]
                    values = [v for v in values if v is not None]
                    group_result[f"{field}_{func_name}"] = self.aggregation_functions[func_name](values)
            
            results.append(group_result)
        
        return results
    
    def _apply_filter(
        self,
        data: Any,
        rules: Dict[str, Any]
    ) -> Any:
        """
        Apply filter transformation
        
        Rules format:
        {
            "conditions": [
                {"field": "price", "operator": "gt", "value": 100},
                {"field": "status", "operator": "eq", "value": "active"}
            ],
            "logic": "and"  # or "or"
        }
        """
        if not isinstance(data, list):
            return data
        
        conditions = rules.get('conditions', [])
        logic = rules.get('logic', 'and')
        
        results = []
        for item in data:
            if not isinstance(item, dict):
                continue
            
            if self._evaluate_conditions(item, conditions, logic):
                results.append(item)
        
        return results
    
    def _apply_custom_function(
        self,
        data: Any,
        rules: Dict[str, Any]
    ) -> Any:
        """
        Apply custom transformation function
        
        Rules format:
        {
            "function": "normalize_prices",
            "params": {"currency": "USD", "round": 2}
        }
        """
        function_name = rules.get('function')
        params = rules.get('params', {})
        
        # Map of available custom functions
        custom_functions = {
            'normalize_prices': self._normalize_prices,
            'extract_numbers': self._extract_numbers,
            'clean_html': self._clean_html,
            'split_field': self._split_field,
            'merge_fields': self._merge_fields,
            'calculate_field': self._calculate_field,
        }
        
        if function_name in custom_functions:
            return custom_functions[function_name](data, params)
        
        return data
    
    # Type conversion helpers
    
    def _to_string(self, value: Any) -> str:
        """Convert value to string"""
        return str(value) if value is not None else ''
    
    def _to_integer(self, value: Any) -> Optional[int]:
        """Convert value to integer"""
        try:
            # Extract numbers from string if needed
            if isinstance(value, str):
                value = re.sub(r'[^\d.-]', '', value)
            return int(float(value))
        except (ValueError, TypeError):
            return None
    
    def _to_float(self, value: Any) -> Optional[float]:
        """Convert value to float"""
        try:
            if isinstance(value, str):
                value = re.sub(r'[^\d.-]', '', value)
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def _to_decimal(self, value: Any) -> Optional[Decimal]:
        """Convert value to decimal"""
        try:
            if isinstance(value, str):
                value = re.sub(r'[^\d.-]', '', value)
            return Decimal(str(value))
        except (ValueError, TypeError):
            return None
    
    def _to_boolean(self, value: Any) -> bool:
        """Convert value to boolean"""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', 'yes', '1', 'on')
        return bool(value)
    
    def _to_datetime(self, value: Any) -> Optional[str]:
        """Convert value to datetime string"""
        try:
            if isinstance(value, datetime):
                return value.isoformat()
            # Try to parse common date formats
            from dateutil import parser
            dt = parser.parse(str(value))
            return dt.isoformat()
        except:
            return None
    
    def _to_date(self, value: Any) -> Optional[str]:
        """Convert value to date string"""
        try:
            dt = self._to_datetime(value)
            if dt:
                return dt.split('T')[0]
        except:
            return None
    
    def _to_json(self, value: Any) -> Any:
        """Convert string to JSON"""
        if isinstance(value, str):
            try:
                return json.loads(value)
            except:
                return value
        return value
    
    def _to_list(self, value: Any) -> List:
        """Convert value to list"""
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            # Try to split by common delimiters
            if ',' in value:
                return [v.strip() for v in value.split(',')]
            elif ';' in value:
                return [v.strip() for v in value.split(';')]
        return [value] if value is not None else []
    
    # Aggregation functions
    
    def _aggregate_sum(self, values: List) -> float:
        """Sum aggregation"""
        numeric_values = [self._to_float(v) for v in values]
        numeric_values = [v for v in numeric_values if v is not None]
        return sum(numeric_values) if numeric_values else 0
    
    def _aggregate_avg(self, values: List) -> float:
        """Average aggregation"""
        numeric_values = [self._to_float(v) for v in values]
        numeric_values = [v for v in numeric_values if v is not None]
        return sum(numeric_values) / len(numeric_values) if numeric_values else 0
    
    def _aggregate_count(self, values: List) -> int:
        """Count aggregation"""
        return len([v for v in values if v is not None])
    
    def _aggregate_min(self, values: List) -> Any:
        """Minimum aggregation"""
        valid_values = [v for v in values if v is not None]
        return min(valid_values) if valid_values else None
    
    def _aggregate_max(self, values: List) -> Any:
        """Maximum aggregation"""
        valid_values = [v for v in values if v is not None]
        return max(valid_values) if valid_values else None
    
    def _aggregate_concat(self, values: List) -> str:
        """Concatenate aggregation"""
        str_values = [str(v) for v in values if v is not None]
        return ', '.join(str_values)
    
    def _aggregate_unique(self, values: List) -> List:
        """Unique values aggregation"""
        return list(set(v for v in values if v is not None))
    
    # Custom transformation functions
    
    def _normalize_prices(self, data: Any, params: Dict) -> Any:
        """Normalize price fields"""
        currency = params.get('currency', 'USD')
        round_to = params.get('round', 2)
        
        if isinstance(data, list):
            return [self._normalize_prices(item, params) for item in data]
        
        if isinstance(data, dict):
            result = data.copy()
            for key, value in result.items():
                if 'price' in key.lower() or 'cost' in key.lower():
                    normalized = self._to_float(value)
                    if normalized is not None:
                        result[key] = round(normalized, round_to)
                        result[f"{key}_currency"] = currency
            return result
        
        return data
    
    def _extract_numbers(self, data: Any, params: Dict) -> Any:
        """Extract numbers from text fields"""
        if isinstance(data, list):
            return [self._extract_numbers(item, params) for item in data]
        
        if isinstance(data, dict):
            result = data.copy()
            for key, value in result.items():
                if isinstance(value, str):
                    numbers = re.findall(r'\d+\.?\d*', value)
                    if numbers:
                        result[f"{key}_numbers"] = [float(n) for n in numbers]
            return result
        
        return data
    
    def _clean_html(self, data: Any, params: Dict) -> Any:
        """Remove HTML tags from text fields"""
        if isinstance(data, list):
            return [self._clean_html(item, params) for item in data]
        
        if isinstance(data, dict):
            result = data.copy()
            for key, value in result.items():
                if isinstance(value, str):
                    # Simple HTML tag removal
                    clean_text = re.sub(r'<[^>]+>', '', value)
                    clean_text = clean_text.strip()
                    result[key] = clean_text
            return result
        
        return data
    
    def _split_field(self, data: Any, params: Dict) -> Any:
        """Split a field into multiple fields"""
        field = params.get('field')
        delimiter = params.get('delimiter', ',')
        new_fields = params.get('new_fields', [])
        
        if isinstance(data, list):
            return [self._split_field(item, params) for item in data]
        
        if isinstance(data, dict) and field in data:
            result = data.copy()
            value = str(data[field])
            parts = value.split(delimiter)
            
            for i, new_field in enumerate(new_fields):
                if i < len(parts):
                    result[new_field] = parts[i].strip()
            
            return result
        
        return data
    
    def _merge_fields(self, data: Any, params: Dict) -> Any:
        """Merge multiple fields into one"""
        fields = params.get('fields', [])
        new_field = params.get('new_field', 'merged')
        separator = params.get('separator', ' ')
        
        if isinstance(data, list):
            return [self._merge_fields(item, params) for item in data]
        
        if isinstance(data, dict):
            result = data.copy()
            values = []
            for field in fields:
                value = self._get_nested_value(data, field)
                if value is not None:
                    values.append(str(value))
            
            if values:
                result[new_field] = separator.join(values)
            
            return result
        
        return data
    
    def _calculate_field(self, data: Any, params: Dict) -> Any:
        """Calculate new field based on formula"""
        formula = params.get('formula')  # e.g., "{price} * {quantity}"
        new_field = params.get('new_field', 'calculated')
        
        if isinstance(data, list):
            return [self._calculate_field(item, params) for item in data]
        
        if isinstance(data, dict) and formula:
            result = data.copy()
            
            # Replace field references with values
            calc_formula = formula
            field_refs = re.findall(r'\{([^}]+)\}', formula)
            
            for field_ref in field_refs:
                value = self._get_nested_value(data, field_ref)
                if value is not None:
                    calc_formula = calc_formula.replace(
                        f"{{{field_ref}}}",
                        str(value)
                    )
            
            # Evaluate the formula (be careful with security here)
            try:
                # Only allow basic math operations
                allowed_names = {
                    'abs': abs,
                    'round': round,
                    'min': min,
                    'max': max,
                }
                result[new_field] = eval(calc_formula, {"__builtins__": {}}, allowed_names)
            except:
                pass
            
            return result
        
        return data
    
    # Helper methods
    
    def _get_nested_value(self, data: Dict, path: str) -> Any:
        """Get value from nested dictionary using dot notation"""
        keys = path.split('.')
        value = data
        
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
            
            if value is None:
                return None
        
        return value
    
    def _set_nested_value(self, data: Dict, path: str, value: Any) -> None:
        """Set value in nested dictionary using dot notation"""
        keys = path.split('.')
        current = data
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value
    
    def _flatten_dict(self, data: Dict, parent_key: str = '', sep: str = '.') -> Dict:
        """Flatten nested dictionary"""
        items = []
        for key, value in data.items():
            new_key = f"{parent_key}{sep}{key}" if parent_key else key
            if isinstance(value, dict):
                items.extend(self._flatten_dict(value, new_key, sep=sep).items())
            else:
                items.append((new_key, value))
        return dict(items)
    
    def _evaluate_conditions(
        self,
        item: Dict,
        conditions: List[Dict],
        logic: str = 'and'
    ) -> bool:
        """Evaluate filter conditions on an item"""
        if not conditions:
            return True
        
        results = []
        for condition in conditions:
            field = condition.get('field')
            operator = condition.get('operator', 'eq')
            compare_value = condition.get('value')
            
            item_value = self._get_nested_value(item, field)
            
            if operator == 'eq':
                results.append(item_value == compare_value)
            elif operator == 'ne':
                results.append(item_value != compare_value)
            elif operator == 'gt':
                results.append(item_value > compare_value if item_value is not None else False)
            elif operator == 'gte':
                results.append(item_value >= compare_value if item_value is not None else False)
            elif operator == 'lt':
                results.append(item_value < compare_value if item_value is not None else False)
            elif operator == 'lte':
                results.append(item_value <= compare_value if item_value is not None else False)
            elif operator == 'contains':
                results.append(
                    compare_value in str(item_value) if item_value is not None else False
                )
            elif operator == 'in':
                results.append(item_value in compare_value if isinstance(compare_value, list) else False)
            elif operator == 'exists':
                results.append(item_value is not None)
            elif operator == 'not_exists':
                results.append(item_value is None)
        
        if logic == 'and':
            return all(results)
        elif logic == 'or':
            return any(results)
        else:
            return False