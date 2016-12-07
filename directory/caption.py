import requests

def get_caption(f):
	url = "https://api.projectoxford.ai/vision/v1.0/analyze?visualFeatures=Description,Tags,Categories&subscription-key=b5e815e0075048858acfa6198f44d2c2"
	try:
		r = requests.post(url, files={'file': f})
		# print r.reason
		best_cat = "NA"
		best_caption = "NA"
		if int(r.status_code) == 200:
			js = r.json()
			print js
			cat = js["categories"]
			captions = js["description"]["captions"]
			best_cat = sorted(cat, key=lambda x: x["score"])[-1]["name"]
			best_caption = sorted(captions, key=lambda x: x["confidence"])[-1]["text"]
			return {"category":best_cat, "caption":best_caption}
		return {"category":"NA", "caption":"NA"}
	except Exception, e:
		print e
		return {"category":"NA", "caption":"NA"}


