"""
Shared utility functions for CodeAlpha Credit Scoring Model.
This module consolidates data processing and validation logic.
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, Any, Tuple, Optional
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score, accuracy_score
import joblib
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_and_validate_dataset(data_path: str) -> pd.DataFrame:
    """
    Load and validate the credit score dataset.
    
    Args:
        data_path: Path to the CSV dataset
        
    Returns:
        Loaded and validated DataFrame
        
    Raises:
        FileNotFoundError: If dataset file is not found
        ValueError: If dataset format is invalid
    """
    try:
        if not os.path.exists(data_path):
            raise FileNotFoundError(f"Dataset not found at: {data_path}")
        
        logger.info(f"Loading dataset from: {data_path}")
        data = pd.read_csv(data_path)
        
        # Validate dataset structure
        required_columns = ['Credit Score', 'Gender', 'Education', 'Marital Status', 'Home Ownership']
        missing_columns = [col for col in required_columns if col not in data.columns]
        
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        
        logger.info(f"Dataset loaded successfully. Shape: {data.shape}")
        return data
        
    except Exception as e:
        logger.error(f"Error loading dataset: {str(e)}")
        raise


def preprocess_credit_data(data: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Preprocess credit score data with comprehensive validation and encoding.
    
    Args:
        data: Raw dataset DataFrame
        
    Returns:
        Tuple of (processed_data, preprocessing_info)
    """
    try:
        logger.info("Starting data preprocessing...")
        
        # Create a copy to avoid modifying original
        processed_data = data.copy()
        preprocessing_info = {}
        
        # Store original shape
        preprocessing_info['original_shape'] = processed_data.shape
        
        # Handle missing values
        missing_before = processed_data.isnull().sum().sum()
        processed_data = processed_data.dropna()
        missing_after = len(data) - len(processed_data)
        
        if missing_after > 0:
            logger.warning(f"Removed {missing_after} rows with missing values")
            preprocessing_info['missing_rows_removed'] = missing_after
        
        # Encode categorical variables
        categorical_columns = ['Gender', 'Education', 'Marital Status', 'Home Ownership']
        processed_data = pd.get_dummies(processed_data, columns=categorical_columns, drop_first=True)
        preprocessing_info['categorical_encoded'] = categorical_columns
        
        # Map 'Credit Score' to numerical values
        credit_mapping = {'Low': 0, 'Average': 1, 'High': 2}
        processed_data['Credit Score'] = processed_data['Credit Score'].map(credit_mapping)
        preprocessing_info['credit_mapping'] = credit_mapping
        
        # Validate target variable
        if processed_data['Credit Score'].isnull().any():
            logger.warning("Some credit scores could not be mapped. Check data quality.")
        
        preprocessing_info['final_shape'] = processed_data.shape
        logger.info("Data preprocessing completed successfully")
        
        return processed_data, preprocessing_info
        
    except Exception as e:
        logger.error(f"Error in data preprocessing: {str(e)}")
        raise


def prepare_features_and_target(data: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
    """
    Separate features and target variable with validation.
    
    Args:
        data: Preprocessed DataFrame
        
    Returns:
        Tuple of (features, target)
    """
    try:
        # Separate features and target
        target = data['Credit Score']
        features = data.drop('Credit Score', axis=1)
        
        logger.info(f"Features shape: {features.shape}, Target shape: {target.shape}")
        logger.info(f"Target distribution: {target.value_counts().to_dict()}")
        
        return features, target
        
    except Exception as e:
        logger.error(f"Error preparing features and target: {str(e)}")
        raise


def split_and_scale_data(X: pd.DataFrame, y: pd.Series, 
                        test_size: float = 0.2, 
                        random_state: int = 42) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, StandardScaler]:
    """
    Split data into train/test sets and apply scaling.
    
    Args:
        X: Feature DataFrame
        y: Target Series
        test_size: Proportion of data for testing
        random_state: Random seed for reproducibility
        
    Returns:
        Tuple of (X_train_scaled, X_test_scaled, y_train, y_test, scaler)
    """
    try:
        # Split the data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state, stratify=y
        )
        
        # Scale the features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        logger.info(f"Data split: Train {X_train_scaled.shape}, Test {X_test_scaled.shape}")
        
        return X_train_scaled, X_test_scaled, y_train, y_test, scaler
        
    except Exception as e:
        logger.error(f"Error in data splitting and scaling: {str(e)}")
        raise


def evaluate_model_performance(model, X_test: np.ndarray, y_test: np.ndarray) -> Dict[str, Any]:
    """
    Comprehensive model evaluation with multiple metrics.
    
    Args:
        model: Trained ML model
        X_test: Test features
        y_test: Test targets
        
    Returns:
        Dictionary of evaluation metrics
    """
    try:
        # Make predictions
        y_pred = model.predict(X_test)
        y_pred_proba = model.predict_proba(X_test)
        
        # Calculate metrics
        accuracy = accuracy_score(y_test, y_pred)
        roc_auc = roc_auc_score(y_test, y_pred_proba, multi_class='ovr')
        
        # Get classification report
        class_report = classification_report(y_test, y_pred, output_dict=True)
        
        evaluation_results = {
            'accuracy': accuracy,
            'roc_auc_score': roc_auc,
            'classification_report': class_report,
            'predictions': y_pred,
            'prediction_probabilities': y_pred_proba
        }
        
        logger.info(f"Model evaluation completed. Accuracy: {accuracy:.4f}, ROC-AUC: {roc_auc:.4f}")
        
        return evaluation_results
        
    except Exception as e:
        logger.error(f"Error in model evaluation: {str(e)}")
        raise


def save_model_and_scaler(model, scaler: StandardScaler, model_dir: str = 'models') -> Dict[str, str]:
    """
    Save trained model and scaler with proper error handling.
    
    Args:
        model: Trained ML model
        scaler: Fitted StandardScaler
        model_dir: Directory to save models
        
    Returns:
        Dictionary with saved file paths
    """
    try:
        # Create models directory if it doesn't exist
        os.makedirs(model_dir, exist_ok=True)
        
        # Save model and scaler
        model_path = os.path.join(model_dir, 'credit_scoring_model.pkl')
        scaler_path = os.path.join(model_dir, 'scaler.pkl')
        
        joblib.dump(model, model_path)
        joblib.dump(scaler, scaler_path)
        
        logger.info(f"Model saved to: {model_path}")
        logger.info(f"Scaler saved to: {scaler_path}")
        
        return {
            'model_path': model_path,
            'scaler_path': scaler_path
        }
        
    except Exception as e:
        logger.error(f"Error saving model: {str(e)}")
        raise


def validate_input_data(input_dict: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validate input data for credit score prediction.
    
    Args:
        input_dict: Dictionary of input features
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    required_fields = ['Age', 'Gender', 'Income', 'Education', 'Marital Status', 'Number of Children', 'Home Ownership']
    
    try:
        # Check for missing fields
        missing_fields = [field for field in required_fields if field not in input_dict]
        if missing_fields:
            return False, f"Missing required fields: {', '.join(missing_fields)}"
        
        # Validate data types and ranges
        validations = [
            ('Age', lambda x: isinstance(x, (int, float)) and 18 <= x <= 100),
            ('Income', lambda x: isinstance(x, (int, float)) and 0 <= x <= 1000000),
        ]
        
        for field, validator in validations:
            if field in input_dict and not validator(input_dict[field]):
                return False, f"Invalid value for {field}: {input_dict[field]}"
        
        return True, "Valid input data"
        
    except Exception as e:
        logger.error(f"Error validating input data: {str(e)}")
        return False, f"Validation error: {str(e)}"