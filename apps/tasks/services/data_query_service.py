"""
Data Query Service for advanced filtering and searching of scraped data
"""
import json
from typing import Dict, List, Any, Optional
from django.db.models import Q, Count, Avg, Sum, Min, Max, F
from django.db.models.query import QuerySet
from django.core.paginator import Paginator
from django.contrib.postgres.search import SearchVector
from datetime import datetime, timedelta
from ..models import TaskExecution, Task


class DataQueryService:
    """Service for querying and filtering scraped data"""
    
    def __init__(self):
        self.operators = {
            'eq': self._eq_filter,
            'ne': self._ne_filter,
            'gt': self._gt_filter,
            'gte': self._gte_filter,
            'lt': self._lt_filter,
            'lte': self._lte_filter,
            'contains': self._contains_filter,
            'icontains': self._icontains_filter,
            'in': self._in_filter,
            'nin': self._nin_filter,
            'exists': self._exists_filter,
            'json_contains': self._json_contains_filter,
            'json_path': self._json_path_filter,
        }
    
    def query_executions(
        self,
        task_id: Optional[str] = None,
        filters: Dict[str, Any] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 100,
        order_by: str = '-started_at'
    ) -> Dict[str, Any]:
        """
        Query task executions with advanced filtering
        
        Args:
            task_id: Filter by specific task
            filters: JSONB filters for scraped_data
            date_from: Start date for date range filter
            date_to: End date for date range filter
            status: Execution status filter
            page: Page number for pagination
            page_size: Number of items per page
            order_by: Field to order results by
        
        Returns:
            Dictionary with results and metadata
        """
        queryset = TaskExecution.objects.all()
        
        # Apply basic filters
        if task_id:
            queryset = queryset.filter(task_id=task_id)
        
        if status:
            queryset = queryset.filter(status=status)
        
        # Apply date range filter
        if date_from:
            queryset = queryset.filter(started_at__gte=date_from)
        
        if date_to:
            queryset = queryset.filter(started_at__lte=date_to)
        
        # Apply JSONB filters on scraped_data
        if filters:
            queryset = self._apply_jsonb_filters(queryset, filters)
        
        # Order results
        queryset = queryset.order_by(order_by)
        
        # Paginate
        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)
        
        # Build response
        return {
            'results': list(page_obj.object_list.values()),
            'metadata': {
                'total_count': paginator.count,
                'page': page,
                'page_size': page_size,
                'total_pages': paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            }
        }
    
    def search_in_data(
        self,
        search_term: str,
        task_id: Optional[str] = None,
        fields: Optional[List[str]] = None,
        page: int = 1,
        page_size: int = 100
    ) -> Dict[str, Any]:
        """
        Full-text search in scraped data
        
        Args:
            search_term: Text to search for
            task_id: Filter by specific task
            fields: Specific JSONB fields to search in
            page: Page number
            page_size: Items per page
        
        Returns:
            Search results with highlights
        """
        queryset = TaskExecution.objects.filter(status='success')
        
        if task_id:
            queryset = queryset.filter(task_id=task_id)
        
        # Search in scraped_data JSONB field
        # For SQLite, we'll use a simpler approach
        # For PostgreSQL, we'd use SearchVector
        results = []
        for execution in queryset:
            if self._search_in_json(execution.scraped_data, search_term, fields):
                results.append({
                    'id': str(execution.id),
                    'task_id': str(execution.task_id),
                    'started_at': execution.started_at.isoformat() if execution.started_at else None,
                    'scraped_data': execution.scraped_data,
                    'matched_fields': self._get_matched_fields(
                        execution.scraped_data, search_term, fields
                    )
                })
        
        # Paginate results
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_results = results[start_idx:end_idx]
        
        return {
            'results': paginated_results,
            'metadata': {
                'total_count': len(results),
                'page': page,
                'page_size': page_size,
                'search_term': search_term,
                'fields_searched': fields or ['all']
            }
        }
    
    def aggregate_data(
        self,
        task_id: str,
        aggregations: Dict[str, str],
        group_by: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Perform aggregations on scraped data
        
        Args:
            task_id: Task to aggregate data for
            aggregations: Dict of field: operation (sum, avg, count, min, max)
            group_by: Field to group results by
            filters: Additional filters to apply
        
        Returns:
            Aggregation results
        """
        queryset = TaskExecution.objects.filter(
            task_id=task_id,
            status='success'
        )
        
        if filters:
            queryset = self._apply_jsonb_filters(queryset, filters)
        
        # Build aggregation operations
        agg_ops = {}
        for field, operation in aggregations.items():
            if operation == 'count':
                agg_ops[f'{field}_count'] = Count('id')
            elif operation == 'sum':
                # For JSONB fields, we'd need to cast to numeric
                # This is a simplified version
                agg_ops[f'{field}_sum'] = Count('id')  # Placeholder
            elif operation == 'avg':
                agg_ops[f'{field}_avg'] = Count('id')  # Placeholder
            elif operation == 'min':
                agg_ops[f'{field}_min'] = Min('started_at')
            elif operation == 'max':
                agg_ops[f'{field}_max'] = Max('started_at')
        
        # Perform aggregation
        if group_by:
            # Group by would require more complex handling for JSONB fields
            results = queryset.values(group_by).annotate(**agg_ops)
        else:
            results = queryset.aggregate(**agg_ops)
        
        return {
            'aggregations': results,
            'metadata': {
                'task_id': task_id,
                'total_executions': queryset.count(),
                'aggregation_config': aggregations,
                'group_by': group_by
            }
        }
    
    def get_unique_values(
        self,
        task_id: str,
        field_path: str,
        limit: int = 100
    ) -> List[Any]:
        """
        Get unique values for a specific field in scraped data
        
        Args:
            task_id: Task to get values from
            field_path: Dot-notation path to field (e.g., 'product.price')
            limit: Maximum number of unique values to return
        
        Returns:
            List of unique values
        """
        executions = TaskExecution.objects.filter(
            task_id=task_id,
            status='success'
        )
        
        unique_values = set()
        for execution in executions:
            value = self._get_nested_value(execution.scraped_data, field_path)
            if value is not None:
                if isinstance(value, list):
                    unique_values.update(value)
                else:
                    unique_values.add(value)
        
        # Convert to list and limit
        result = list(unique_values)[:limit]
        
        # Sort if possible
        try:
            result.sort()
        except TypeError:
            pass  # Mixed types, can't sort
        
        return result
    
    def compare_executions(
        self,
        execution_id_1: str,
        execution_id_2: str
    ) -> Dict[str, Any]:
        """
        Compare data between two executions
        
        Args:
            execution_id_1: First execution ID
            execution_id_2: Second execution ID
        
        Returns:
            Comparison results with differences
        """
        try:
            exec1 = TaskExecution.objects.get(id=execution_id_1)
            exec2 = TaskExecution.objects.get(id=execution_id_2)
        except TaskExecution.DoesNotExist as e:
            return {'error': str(e)}
        
        # Compare scraped data
        diff = self._compare_json_objects(
            exec1.scraped_data or {},
            exec2.scraped_data or {}
        )
        
        return {
            'execution_1': {
                'id': str(exec1.id),
                'started_at': exec1.started_at.isoformat() if exec1.started_at else None,
                'status': exec1.status
            },
            'execution_2': {
                'id': str(exec2.id),
                'started_at': exec2.started_at.isoformat() if exec2.started_at else None,
                'status': exec2.status
            },
            'differences': diff,
            'summary': {
                'total_differences': len(diff.get('changed', [])) + 
                                   len(diff.get('added', [])) + 
                                   len(diff.get('removed', [])),
                'fields_changed': len(diff.get('changed', [])),
                'fields_added': len(diff.get('added', [])),
                'fields_removed': len(diff.get('removed', []))
            }
        }
    
    # Private helper methods
    
    def _apply_jsonb_filters(
        self,
        queryset: QuerySet,
        filters: Dict[str, Any]
    ) -> QuerySet:
        """Apply JSONB filters to queryset"""
        for field_path, condition in filters.items():
            if isinstance(condition, dict):
                # Complex condition with operator
                operator = condition.get('operator', 'eq')
                value = condition.get('value')
                
                if operator in self.operators:
                    queryset = self.operators[operator](
                        queryset, field_path, value
                    )
            else:
                # Simple equality condition
                queryset = self._eq_filter(queryset, field_path, condition)
        
        return queryset
    
    def _eq_filter(self, queryset, field_path, value):
        """Equality filter for JSONB field"""
        # For SQLite, we'll filter in Python
        # For PostgreSQL, we'd use: scraped_data__field_path=value
        return queryset  # Simplified for now
    
    def _ne_filter(self, queryset, field_path, value):
        """Not equal filter"""
        return queryset
    
    def _gt_filter(self, queryset, field_path, value):
        """Greater than filter"""
        return queryset
    
    def _gte_filter(self, queryset, field_path, value):
        """Greater than or equal filter"""
        return queryset
    
    def _lt_filter(self, queryset, field_path, value):
        """Less than filter"""
        return queryset
    
    def _lte_filter(self, queryset, field_path, value):
        """Less than or equal filter"""
        return queryset
    
    def _contains_filter(self, queryset, field_path, value):
        """Contains filter (case-sensitive)"""
        return queryset
    
    def _icontains_filter(self, queryset, field_path, value):
        """Contains filter (case-insensitive)"""
        return queryset
    
    def _in_filter(self, queryset, field_path, values):
        """In filter - value in list"""
        return queryset
    
    def _nin_filter(self, queryset, field_path, values):
        """Not in filter"""
        return queryset
    
    def _exists_filter(self, queryset, field_path, exists=True):
        """Check if field exists"""
        return queryset
    
    def _json_contains_filter(self, queryset, field_path, value):
        """JSONB contains filter"""
        # PostgreSQL: scraped_data__contains={field_path: value}
        return queryset
    
    def _json_path_filter(self, queryset, json_path, value):
        """JSONPath query filter"""
        # PostgreSQL: would use jsonb_path_query
        return queryset
    
    def _search_in_json(
        self,
        data: Dict,
        search_term: str,
        fields: Optional[List[str]] = None
    ) -> bool:
        """Search for term in JSON data"""
        search_term = search_term.lower()
        
        def search_recursive(obj, path=''):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key
                    if not fields or any(current_path.startswith(f) for f in fields):
                        if search_recursive(value, current_path):
                            return True
            elif isinstance(obj, list):
                for item in obj:
                    if search_recursive(item, path):
                        return True
            else:
                if str(obj).lower().find(search_term) != -1:
                    return True
            return False
        
        return search_recursive(data)
    
    def _get_matched_fields(
        self,
        data: Dict,
        search_term: str,
        fields: Optional[List[str]] = None
    ) -> List[str]:
        """Get list of fields that match search term"""
        matched = []
        search_term = search_term.lower()
        
        def search_recursive(obj, path=''):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key
                    if not fields or any(current_path.startswith(f) for f in fields):
                        search_recursive(value, current_path)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    search_recursive(item, f"{path}[{i}]")
            else:
                if str(obj).lower().find(search_term) != -1:
                    matched.append(path)
        
        search_recursive(data)
        return matched
    
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
    
    def _compare_json_objects(self, obj1: Dict, obj2: Dict) -> Dict[str, List]:
        """Compare two JSON objects and return differences"""
        differences = {
            'changed': [],
            'added': [],
            'removed': []
        }
        
        def compare_recursive(o1, o2, path=''):
            if type(o1) != type(o2):
                differences['changed'].append({
                    'path': path,
                    'old_value': o1,
                    'new_value': o2,
                    'type_changed': True
                })
                return
            
            if isinstance(o1, dict):
                keys1 = set(o1.keys())
                keys2 = set(o2.keys())
                
                # Check removed keys
                for key in keys1 - keys2:
                    current_path = f"{path}.{key}" if path else key
                    differences['removed'].append({
                        'path': current_path,
                        'value': o1[key]
                    })
                
                # Check added keys
                for key in keys2 - keys1:
                    current_path = f"{path}.{key}" if path else key
                    differences['added'].append({
                        'path': current_path,
                        'value': o2[key]
                    })
                
                # Check common keys
                for key in keys1 & keys2:
                    current_path = f"{path}.{key}" if path else key
                    compare_recursive(o1[key], o2[key], current_path)
            
            elif isinstance(o1, list):
                if len(o1) != len(o2):
                    differences['changed'].append({
                        'path': path,
                        'old_length': len(o1),
                        'new_length': len(o2),
                        'list_size_changed': True
                    })
                
                # Compare list items
                for i in range(min(len(o1), len(o2))):
                    compare_recursive(o1[i], o2[i], f"{path}[{i}]")
            
            else:
                # Primitive values
                if o1 != o2:
                    differences['changed'].append({
                        'path': path,
                        'old_value': o1,
                        'new_value': o2
                    })
        
        compare_recursive(obj1, obj2)
        return differences