# Databricks notebook source
#this notebook is used to have the correct encoding of moneyView files. this notebook is used in pl_custom_moneyview.
import base64 
import json

#fetch the value from adf trigger
inputv=dbutils.widgets.get("adf_input_value")

#correctly decode the variable
csv_string = base64.b64decode(inputv)

#return a variable on notebook exit
dbutils.notebook.exit(json.dumps({"adf_output_value":csv_string}))
