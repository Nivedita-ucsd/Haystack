from flask import Flask
from flask import abort, send_file
from PIL import Image
import redis
import StringIO
import requests
import io

r = redis.StrictRedis(host='redis3')

app = Flask(__name__)

@app.route('/')
def index():
    return "Inner Peace!"

@app.route('/photo/<string:photo_id>/<string:physical_id>/<string:logical_id>', methods=['GET'])
def get_task(photo_id, physical_id, logical_id):
	if r.exists(photo_id):
		image = io.BytesIO(r.get(photo_id))
		image.seek(0)
		return send_file(image, mimetype='image/jpeg')
	return call_sid(photo_id, physical_id, logical_id)

def call_sid(photo_id, physical_id, logical_id):
	machine = "store" + str(physical_id) + ":9999"
	url = "http://%s/getimage?imageId=%s&logicalFile=%s" % (machine, photo_id, logical_id)
	store_image = requests.get(url)
	if (store_image.ok):
		r.set(photo_id, store_image.content)
		image = io.BytesIO(store_image.content)
		image.seek(0)
		return send_file(image, mimetype='image/jpeg')
	return requests.get('http://www.namoraltv.com.br/assets/images/page-not-found.png').content

if __name__ == '__main__':
	app.run(debug=True, host='0.0.0.0', port=5000)



