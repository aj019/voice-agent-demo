
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv
import os
load_dotenv()

db_username = os.getenv("MONGODB_USER")
db_password = os.getenv("MONGODB_PASS")

uri = "mongodb+srv://"+db_username+":"+db_password+"@customer-support.bnkexoe.mongodb.net/?appName=customer-support"
print(uri)
# Create a new client and connect to the server
client = MongoClient(uri, server_api=ServerApi('1'))

# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
    db = client.get_database("voice-agent-db")
    print(db.list_collection_names())
    collection = db.get_collection("orders")
    # print(collection.find_one())

    #// Get order with order id 1001
    order = collection.find_one({"order_id": "SC100056"})
    print(order)
except Exception as e:
    print(e)