# Databricks notebook source
#this notebook is used to have the correct encoding of moneyView files. this notebook is used in pl_custom_moneyview.
import base64 
import io
import json
import zipfile

#fetch the value from adf trigger
inputv = dbutils.widgets.get("adf_input_value")

#correctly decode the variable
zip_string = base64.b64decode(inputv)



# COMMAND ----------

with zipfile.ZipFile(io.BytesIO(zip_string), "r") as zip_file:
    first_file_name = zip_file.namelist()[0]
    json_string = zip_file.read(first_file_name).decode("UTF-8")


# COMMAND ----------

# Show first part of the file
print(json_string[:100])

# COMMAND ----------

#return a variable on notebook exit
dbutils.notebook.exit(json.dumps({"adf_output_value":json_string}))
