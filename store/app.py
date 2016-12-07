from flask import Flask, abort, send_file, request, jsonify
from io import BytesIO
import PIL.Image as Image, redis, fcntl
import sys

redis_host = sys.argv[1]

app = Flask(__name__)

logical1 = None
logical2 = None
logical3 = None
namesUsed = []



def get_logical(logicalName):
    global logical1
    global logical2
    global logical3
    if ((logical1 is not None) and logical1.fileName == logicalName):
        return logical1
    elif ((logical2 is not None) and logical2.fileName == logicalName):
        return logical2
    elif ((logical3 is not None) and logical3.fileName == logicalName):
        return logical3
    else:
        return None

@app.route('/create/<logicalname>')
def Create(logicalname):
    global logical1, logical2, logical3, namesUsed

    logicalName = logicalname
    try:
        redis_connect = redis.StrictRedis( host=redis_host, port=6379, db=0)
        redis_connect.echo("Check")
    except redis.ConnectionError:
        response = {'Status':0, 'Reason':'Redis Connection Faield'}
        return jsonify(**response)

    if(logicalName in namesUsed):
        response = {'Status':0, 'Reason':'This file name already exist!!' }
        return jsonify(**response)

    if (logical1 is None):
        logical1 = LogicalFile(logicalName, redis_connect)
    elif (logical2 is None):
        logical2 = LogicalFile(logicalName, redis_connect)
    elif (logical3 is None):
        logical3 = LogicalFile(logicalName, redis_connect)
    else:
        response = {'Status':0, 'Reason':'No Space'}
        return jsonify(**response)

    namesUsed += logicalName
    return jsonify(Status=1)


@app.route('/addimage', methods=['GET', 'POST'])
def AddImage():
    if request.method == 'POST':
        print "I was just called!"
        # print request.data
        # print request.form
        # print request.args
        imageId = request.form['imageId']
        logicalName = request.form['logicalFile']
        print 'CameHere: ', imageId, logicalName
        logicalFile = get_logical(logicalName)

        if logicalFile is None:
            response = {'Status':0, 'Reason':'Logical File not found on this server'}
            return jsonify(**response)
        if 'file' not in request.files:
            response = {'Status':0, 'Reason':'Missing Image data'}
            return jsonify(**response)

        imageFile = BytesIO(request.files['file'].read())
        imageData = Image.open(imageFile)

        status, reason = logicalFile.addImage(imageId, imageData)
        response = {"Status":status, 'Reason': reason}
        return jsonify(**response)

def serve_pil_image(pil_img):
    img_io = StringIO()
    pil_img.save(img_io, 'JPEG', quality=70)
    img_io.seek(0)
    return send_file(img_io, mimetype='image/jpeg')


@app.route('/getimage', methods=['GET', 'POST'])
def GetImage():
    imageId = request.args['imageId']
    print imageId
    logicalFile = get_logical(request.args['logicalFile'])
    if logicalFile is None:
        response = {'Status':0, 'Reason':'Logical File not found on this server'}
        return jsonify(**response)

    image = logicalFile.readImage(imageId)

    if image == 0:
        return jsonify(Status=-1, Reason='Image Deleted')
    elif image == -1:
        return jsonify(Status=0, Reason='Image Not Found')
    elif image == -2:
        return jsonify(Status=0, Reason='Something Went Wrong!!!!')

    byte_io = BytesIO()
    # image.save('Generated.jpg')
    image.save(byte_io, 'JPEG')
    byte_io.seek(0)
    return send_file(byte_io, mimetype='image/jpeg')

magicWord = 'Sid143Sid'

#[magic, isDeleted, imageId, width, height, mode, image, magic]
def deserializeImage(imageBytesArray):
    magicCheck = imageBytesArray[:9]
    if (magicWord != magicCheck):
        return -1, "Something wrong with image offset" , -1

    index = 9;

    isDeleted = int(imageBytesArray[index])
    index += 1
    imageId = ''.join(imageBytesArray[index:index+10])
    index += 10
    width = int(''.join(imageBytesArray[index:index+5]))
    index += 5
    height = int(''.join(imageBytesArray[index:index+5]))
    index += 5
    imageMode = getMode(int(''.join(imageBytesArray[index:index+2])))
    index += 2

    imageBytes = imageBytesArray[index:]
    image = Image.frombytes(imageMode, (width, height), imageBytes)

    return (imageId, image, isDeleted)

def serializeImage(imageId, image, isDeleted):
    imageMode = image.mode
    width, height = image.size
    imageBytes = image.tobytes()

    serialImage = ''
    serialImage += magicWord
    serialImage += str(isDeleted)
    serialImage += imageId
    serialImage += '{0:05d}'.format(width)
    serialImage += '{0:05d}'.format(height)
    serialImage += '{0:02d}'.format(getModeBits(imageMode))

    return serialImage, imageBytes

def getMode(imageModeByte):
    return {
        0:'1', 1:'L', 2:'P', 3:'RGB', 4:'RGBA', 5:'CMYK',
        6:'YCbCr', 7:'LAB', 8:'HSV', 9:'I', 10:'F'
    }[imageModeByte]

def getModeBits(imageMode):
    return {
        '1':0, 'L':1, 'P':2, 'RGB':3, 'RGBA':4, 'CMYK':5,
        'YCbCr':6, 'LAB':7, 'HSV':8, 'I':9, 'F':10
    }[imageMode]

class LogicalFile:
    def __init__(self, fileName, redisConnect):
        self.fileName = fileName
        self.readOnly = False
        self.fileWriteDescriptor = file(fileName,'a', 0)
        self.fileReadDescriptor = file(fileName,'r')
        self.redisConnect = redisConnect

    def addImage(self,imageId, openImage):
        try:
            if(self.redisConnect.hexists(self.fileName, imageId)):
                return '0', 'ImageId Already Exists'

            imagePad, image = serializeImage(imageId, openImage, 0)

            #obtain file lock
            fcntl.flock(self.fileWriteDescriptor, fcntl.LOCK_EX)
            currentSize = self.fileWriteDescriptor.tell()
            self.fileWriteDescriptor.write(imagePad)
            self.fileWriteDescriptor.write(image)
            sizeImage = self.fileWriteDescriptor.tell() - currentSize
            infoTuple = str((currentSize, sizeImage, 0))
            self.redisConnect.hset(self.fileName, imageId, infoTuple)
            #release the lock
            fcntl.flock(self.fileWriteDescriptor, fcntl.LOCK_UN)

            return '1', 'Success'
        except:
            return '0',

    def readImage(self, imageId):
        try:
            if(not self.redisConnect.hexists(self.fileName, imageId)):
                return -1
            offset, size, deleted= eval(self.redisConnect.hget(self.fileName, imageId))
            print offset, size, deleted
            self.fileReadDescriptor.seek(offset)
            imageBytes = self.fileReadDescriptor.read(size)

            imageId, image, isDeleted = deserializeImage(imageBytes)

            if(isDeleted==1):
                return 0
            else:
                return image
        except:
            return -2


if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0', port = 9999)

