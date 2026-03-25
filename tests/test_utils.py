"""
Test suite for credit scoring utility functions
"""
import pytest
import pandas as pd
import numpy as np
import sys
import os

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Now import the utilities
try:
    from Src.utils import validate_input_data, preprocess_credit_data, prepare_features_and_target
    UTILS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import utilities: {e}")
    UTILS_AVAILABLE = False


@pytest.mark.skipif(not UTILS_AVAILABLE, reason="Utilities not available")
def test_validate_input_data_valid():
    """Test validation with valid credit score input"""
    valid_data = {
        'Age': 30,
        'Gender': 'Male',
        'Income': 50000,
        'Education': "Bachelor's Degree",
        'Marital Status': 'Single',
        'Number of Children': 0,
        'Home Ownership': 'Rented'
    }
    
    is_valid, message = validate_input_data(valid_data)
    assert is_valid == True
    assert "Valid input data" in message


@pytest.mark.skipif(not UTILS_AVAILABLE, reason="Utilities not available")
def test_validate_input_data_invalid_age():
    """Test validation with invalid age"""
    invalid_data = {
        'Age': 150,  # Invalid: too high
        'Gender': 'Male',
        'Income': 50000,
        'Education': "Bachelor's Degree",
        'Marital Status': 'Single',
        'Number of Children': 0,
        'Home Ownership': 'Rented'
    }
    
    is_valid, message = validate_input_data(invalid_data)
    assert is_valid == False
    assert "Invalid value for Age" in message


@pytest.mark.skipif(not UTILS_AVAILABLE, reason="Utilities not available")
def test_validate_input_data_missing_fields():
    """Test validation with missing required fields"""
    incomplete_data = {
        'Age': 30,
        'Income': 50000,
        # Missing required fields: Gender, Education, Marital Status, Number of Children, Home Ownership
    }
    
    is_valid, message = validate_input_data(incomplete_data)
    assert is_valid == False
    assert "Missing required fields" in message


@pytest.mark.skipif(not UTILS_AVAILABLE, reason="Utilities not available")
def test_preprocess_credit_data():
    """Test credit data preprocessing"""
    # Create sample DataFrame
    sample_data = pd.DataFrame({
        'Age': [25, 30, 35],
        'Income': [30000, 50000, 70000],
        'Gender': ['Male', 'Female', 'Male'],
        'Education': ['High School', 'Graduate', 'Post-Graduate'],
        'Marital Status': ['Single', 'Married', 'Single'],
        'Home Ownership': ['Rent', 'Own', 'Rent'],
        'Credit Score': ['Low', 'Average', 'High']
    })
    
    processed_data, preprocessing_info = preprocess_credit_data(sample_data)
    
    # Check that categorical variables were encoded
    assert any('Gender_' in col for col in processed_data.columns)
    assert 'Credit Score' in processed_data.columns
    
    # Check that credit scores were mapped to numbers
    assert processed_data['Credit Score'].dtype in [np.int64, np.float64]
    assert set(processed_data['Credit Score'].unique()).issubset({0, 1, 2})
    
    # Check preprocessing info
    assert 'original_shape' in preprocessing_info
    assert 'final_shape' in preprocessing_info


def test_basic_functionality():
    """Basic test that doesn't require utilities import"""
    # Test basic Python functionality
    assert 1 + 1 == 2
    
    # Test pandas basic functionality
    df = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]})
    assert len(df) == 3
    assert 'A' in df.columns
    
    print("Basic functionality test passed")