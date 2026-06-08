import pytest
from unittest.mock import patch, MagicMock
from prediction import (
    get_time_features,
    get_lag_features,
    predict_current_demand,
    FEATURE_COLS
)
from datetime import datetime
import pandas as pd


class TestTimeFeatures:
    """Test time feature extraction"""
    
    def test_get_time_features_returns_dict(self):
        """Should return a dictionary with required keys"""
        result = get_time_features()
        assert isinstance(result, dict)
        assert all(key in result for key in ['month', 'holiday', 'is_weekend', 'hour', 'minute'])
    
    def test_get_time_features_valid_ranges(self):
        """Should return values in valid ranges"""
        result = get_time_features()
        assert 1 <= result['month'] <= 12
        assert result['holiday'] in [0, 1]
        assert result['is_weekend'] in [0, 1]
        assert 0 <= result['hour'] <= 23
        assert result['minute'] in [0, 15, 30, 45]


class TestLagFeatures:
    """Test lag feature extraction"""
    
    @patch('requests.get')
    def test_get_lag_features_success(self, mock_get):
        """Should parse API response correctly"""
        mock_get.return_value.json.return_value = [{
            "Demand": "13,190",
            "ISGS": "5,766",
            "ImportData": "7,424"
        }]
        
        result = get_lag_features()
        assert isinstance(result, dict)
        assert all(key in result for key in ['y_lag_1', 'y_lag_24h', 'y_lag_7d'])
        assert result['y_lag_1'] == 13190.0
    
    @patch('requests.get')
    def test_get_lag_features_fallback(self, mock_get):
        """Should use fallback values on API error"""
        mock_get.side_effect = Exception("Connection error")
        
        result = get_lag_features()
        assert result['y_lag_1'] == 14500.0
        assert result['y_lag_24h'] == 14800.0
        assert result['y_lag_7d'] == 13900.0


class TestPrediction:
    """Test main prediction function"""
    
    @patch('prediction.get_weighted_temperature_now')
    @patch('prediction.get_time_features')
    @patch('prediction.get_lag_features')
    def test_predict_current_demand_returns_float(self, mock_lag, mock_time, mock_temp):
        """Should return a float prediction"""
        mock_temp.return_value = 28.5
        mock_time.return_value = {
            'month': 6, 'holiday': 0, 'is_weekend': 0,
            'hour': 14, 'minute': 30
        }
        mock_lag.return_value = {
            'y_lag_1': 13190.0, 'y_lag_24h': 13800.0, 'y_lag_7d': 13900.0
        }
        
        result = predict_current_demand()
        assert isinstance(result, float)
        assert result > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])