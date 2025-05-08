# Databricks notebook source
"""This script is used to decode MoneyView content and save it as parquet files.

This script performs the following tasks:

1. Reads a Base64 encoded ZIP file from ADLS.
2. Extracts the JSON file from the ZIP archive.
3. Converts the JSON file into a Parquet file.
4. Moves the Parquet file to the designated ingestion location for the external table.

This notebook is used in the pl_custom_moneyview pipeline.
"""

import os
import io
import base64
import json
import zipfile
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

def validate_inputs(encoded_zip_file_path, workspace_tmp_dir, adls_target_path):
    """Validate that all required parameters are provided."""
    if not all([encoded_zip_file_path, workspace_tmp_dir, adls_target_path]):
        raise ValueError("Missing required parameters")

def extract_json_from_zip(zip_string: bytes) -> tuple[str, str]:
    """Extract and validate JSON content from a zip file.
    
    Args:
        zip_string: Base64 decoded zip file content as bytes
        
    Returns:
        tuple: (file_name, json_string) containing:

            
    Raises:
        ValueError: If any of the following occurs:
            - Zip file is invalid
            - Content is not valid JSON
            - Other error
    """
    try:
        with zipfile.ZipFile(io.BytesIO(zip_string), "r") as zip_file:
            # Check if zip file is empty
            if not zip_file.namelist():
                raise ValueError("Zip file is empty")
            
            # Get the first file from the zip
            file_name = zip_file.namelist()[0]
            
            # Read and decode the file content
            json_string = zip_file.read(file_name).decode("UTF-8")
            
            # Validate JSON format
            try:
                json.loads(json_string)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON content: {str(e)}")
            
            return file_name, json_string
            
    except zipfile.BadZipFile:
        raise ValueError("Invalid zip file format")
    except Exception as e:
        raise ValueError(f"Error processing zip file: {str(e)}")

def create_dataframe(file_name, json_string) -> pd.DataFrame:
    """Create a pandas DataFrame with file name and JSON data.
    
    Args:
        file_name: Name of the processed file
        json_string: JSON content as string
        
    Returns:
        pandas.DataFrame: DataFrame containing file name and data
    """
    return pd.DataFrame([{"file_name": file_name, "data": json_string}])

def save_as_parquet(df: pd.DataFrame, workspace_tmp_dir: str, file_name: str, adls_target_path: str) -> None:
    """Save DataFrame as parquet file and move to target location.
    
    Args:
        df: pandas DataFrame to save
        workspace_tmp_dir: Temporary directory path
        file_name: Original file name
        adls_target_path: Target path for the parquet file
        
    Raises:
        ValueError: If there are issues with file operations
        
    Note:
        We use pyarrow directly instead of pandas' to_parquet method because:
        1. pandas.to_parquet requires additional dependencies (fsspec or fastparquet)
        2. These dependencies are not available in our Databricks environment
        3. Direct pyarrow usage works without additional dependencies
        4. This approach is more efficient as it uses the native pyarrow implementation
        
        Alternative approaches that were considered but not possible:
        - df.to_parquet() -> Requires fsspec
        - df.to_parquet(engine="pyarrow") -> Still requires fsspec
        - df.to_parquet(engine="fastparquet") -> Requires fastparquet package
    """
    try:
        # Validate inputs
        if df.empty:
            raise ValueError("DataFrame is empty")
            
        # Create the temp directory if it doesn't exist
        dbutils.fs.mkdirs(workspace_tmp_dir)
        
        # Prepare file paths
        target_file_name = os.path.splitext(file_name)[0] + '.parquet'
        temp_file = os.path.join(workspace_tmp_dir, target_file_name)
        
        print(f"Writing to temporary location: {temp_file}")
        
        # Convert and write parquet using pyarrow directly
        # This approach works without additional dependencies
        table = pa.Table.from_pandas(df)
        pq.write_table(table=table, where=temp_file, compression="snappy")
        
        # Verify the file was created by trying to list it
        try:
            dbutils.fs.ls(temp_file)
        except Exception:
            raise ValueError(f"Failed to create parquet file at {temp_file}")
        
        # Move to final location
        print(f"Moving to final location: {adls_target_path}")
        dbutils.fs.mv(temp_file, adls_target_path)
            
    except Exception as e:
        # Clean up temp file if it exists
        if 'temp_file' in locals() and dbutils.fs.ls(temp_file):
            dbutils.fs.rm(temp_file)
        raise ValueError(f"Error saving or moving parquet file: {str(e)}")

def read_and_decode_file(temp_file_path: str) -> bytes:
    """Read and decode the file content from the temporary location.
    
    Args:
        temp_file_path: Path to the temporary file
        
    Returns:
        bytes: Decoded zip content
        
    Raises:
        ValueError: If file cannot be read or decoded properly
    """
    try:
        # Read the file content
        file_content = pd.read_json(temp_file_path)
        if file_content.empty:
            raise ValueError("File content is empty")
            
        # Get the encoded content and decode it
        encoded_content = file_content.iloc[0,1]
        return base64.b64decode(encoded_content)
    except Exception as e:
        raise ValueError(f"Error reading or decoding file: {str(e)}")

def decode_moneyview_data(encoded_zip_file_path: str, workspace_tmp_dir: str, adls_target_path: str) -> None:
    """Decode MoneyView content and save as parquet.
    
    Args:
        encoded_zip_file_path: Path to the encoded zip file
        workspace_tmp_dir: Temporary directory path
        adls_target_path: Target path for the parquet file
    """
    # Validate inputs
    validate_inputs(encoded_zip_file_path, workspace_tmp_dir, adls_target_path)
    
    print(f"Processing moneyview file for creation of external table: {adls_target_path}")
    

    temp_file_path = None
    try:
        
        
        # Create a temporary file path
        temp_file_path = os.path.join(workspace_tmp_dir, "temp_zip_file_string.json")
        
        # Copy the file from ADLS to a temporary location
        dbutils.fs.cp(encoded_zip_file_path, temp_file_path)    
        
        # Read and decode the file content
        zip_string = read_and_decode_file(temp_file_path)
        
        # Extract JSON from zip
        file_name, json_string = extract_json_from_zip(zip_string)
        
        # Create DataFrame with desired columns
        df = create_dataframe(file_name, json_string)
        
        # Save the DataFrame as a parquet file
        save_as_parquet(df, workspace_tmp_dir, file_name, adls_target_path)
        
        print("Processing completed successfully")
        
    except Exception as e:
        print(f"Error during processing: {str(e)}")
        raise
    finally:
        # Cleanup temporary files
        try:
            if temp_file_path and dbutils.fs.ls(temp_file_path):
                dbutils.fs.rm(temp_file_path)
            if workspace_tmp_dir and dbutils.fs.ls(workspace_tmp_dir):
                dbutils.fs.rm(workspace_tmp_dir, recurse=True)
        except Exception as cleanup_error:
            print(f"Warning: Error during cleanup: {str(cleanup_error)}")

# Main execution
if __name__ == "__main__":
    encoded_zip_file_path = dbutils.widgets.get("encoded_zip_file_path")
    workspace_tmp_dir = dbutils.widgets.get("dbx_workspace_tmp_dir")
    adls_target_path = dbutils.widgets.get("adls_target_path")
    decode_moneyview_data(encoded_zip_file_path, workspace_tmp_dir, adls_target_path)