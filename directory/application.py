from flask import Flask
from flask import render_template,request, Response, redirect, jsonify
import time
from helpers import id_generator
from random import randint, choice
import requests
from caption import get_caption
from io import BytesIO
from time import sleep

app = Flask(__name__)

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


machine_mapping = {}
machine_mapping[1] = [1,2]
machine_mapping[2] = [1,2]
port_mapping = {}
port_mapping[1] = "store1:9999"
port_mapping[2] = "store2:9999"
local_port = {}
local_port[1] = "9998"
local_port[2] = "9999"


# Create logical vols
requests.get("http://%s/create/1" % port_mapping[1])
requests.get("http://%s/create/1" % port_mapping[2])
requests.get("http://%s/create/2" % port_mapping[1])
requests.get("http://%s/create/2" % port_mapping[2])
print "Created all logical vols! :D"

#MongoDB connect
from pymongo import MongoClient
client = MongoClient('db', 27017)
print "Connected to Mongo"
db = client['haystack']
collection = db['haystack-collection']


def get_url(item):
    physical_ids = item["physical_ids"]
    machine = choice(physical_ids)
    ## Construct URL from machine ID
    return "http://%s/photo/%s/%s/%s" \
            % ("localhost:5001", item["_id"], machine, item["logical_id"])

@app.route('/')
def main():
    items = get_all_photos()
    return render_template("dashboard.html", jobs_list = items)


@app.route('/photo/<photoid>')
def get_photo_url(photoid):
    # check in Cassandra for physical vol and logical vol
    item = collection.find_one(photoid)
    if item:
        return get_url(item)

@app.route('/delete/<photoid>')
def delete_photo(photoid):
    # check in Cassandra for physical vol and logical vol
    item = collection.delete_one({"_id": photoid})
    if item.deleted_count == 1:
        return "true"
    else:
        return "false"

@app.route('/allphotos')
def get_all_photos():
    # check in Cassandra for physical vol and logical vol
    items = []
    for item in collection.find():
        item["url"] = get_url(item)
        items.append(item)
    return items


@app.route('/upload', methods=['POST'])
def upload_photo():
    if request.method == 'POST':
        if 'file_data' not in request.files:
            return "File data not found"
        file = request.files['file_data']
        filename = file.filename
        if file and allowed_file(file.filename):
            logical_id = choice([1,2])
            physical_ids = machine_mapping[logical_id]
            photoid = id_generator()
            payload = {"logicalFile":logical_id, "imageId": photoid}
            try:
                for phy in physical_ids:
                    r1 = requests.post("http://%s/addimage" % (port_mapping[phy]), data=payload, files={'file': file})
                    file.seek(0)
                r2 = get_caption(file)
            except Exception,e:
                print e
                return jsonify({"error":"There was some issue in uploading you files. Please try again."})
            # Insert into Mongo if request succeeded
            item = {"logical_id" : logical_id,
                    "_id": photoid,
                    "physical_ids" : physical_ids,
                    "caption": r2["caption"],
                    "category": r2["category"]}
            item["url"] = get_url(item)
            collection.insert_one(item)
            return jsonify(item)
        else:
            return jsonify({"error":"File name not allowed!"})


if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0', port = 5000)



# session.execute("INSERT INTO cool (user_name) VALUES (%s)", ["sg"])  # right
