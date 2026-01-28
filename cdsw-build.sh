#!/bin/bash
# CML Build Script - installs dependencies for model endpoints

echo "Installing dependencies for CML model endpoints..."

pip install --upgrade pip
pip install xgboost>=2.0.0
pip install scikit-learn>=1.3.0
pip install pandas>=2.0.0
pip install numpy>=1.24.0

echo "Dependencies installed successfully."
