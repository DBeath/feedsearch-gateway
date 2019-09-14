import boto3
import os

dynamodb = boto3.client("dynamodb")
table_name = os.environ["DYNAMODB_TABLE"]


try:
    dynamodb.delete_table(TableName=table_name)
    print("Table deleted successfully.")
except Exception as e:
    print("Could not delete table. Please try again in a moment. Error:")
    print(e)
