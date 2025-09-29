import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import StandardScaler, LabelEncoder
from collections import Counter

# Load and analyze the UNSW-NB15 dataset
def analyze_data():
    # Load the dataset
    df = pd.read_csv('training_data/UNSW_NB15.csv')

    print("Dataset Shape:", df.shape)
    print("\nColumn Names:")
    print(df.columns.tolist())

    print("\nFirst few rows:")
    print(df.head())

    print("\nDataset Info:")
    print(df.info())

    print("\nMissing Values:")
    print(df.isnull().sum())

    print("\nTarget Variable Distribution:")
    print("Label distribution:")
    print(df['label'].value_counts())

    print("\nAttack Category Distribution:")
    print(df['attack_cat'].value_counts())

    # Basic statistics
    print("\nNumerical Features Statistics:")
    numerical_cols = df.select_dtypes(include=[np.number]).columns
    print(f"Number of numerical features: {len(numerical_cols)}")

    categorical_cols = df.select_dtypes(include=['object']).columns
    print(f"Number of categorical features: {len(categorical_cols)}")

    return df

if __name__ == "__main__":
    df = analyze_data()