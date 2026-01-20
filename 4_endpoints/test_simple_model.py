#!/usr/bin/env python3
"""
Simple test model - minimal code to test CML model deployment.
"""
import cml.models_v1 as models

@models.cml_model
def predict(args):
    """Simple echo model for testing."""
    return {
        "status": "success",
        "message": "Model is working!",
        "received": args
    }

