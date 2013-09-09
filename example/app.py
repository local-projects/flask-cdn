from flask import Flask, render_template_string
from flask.ext.cdn import CDN, url_for
from flask.ext.cdn_rackspace import upload_rackspace_image

app = Flask(__name__)

app.config['CDN_DEBUG'] = True
app.config['CDN_HTTPS'] = False
app.config['CDN_USE_RACKSPACE'] = True
app.config['CDN_RACKSPACE_USERNAME'] = 'username'
app.config['CDN_RACKSPACE_KEY'] = 'rs_key'
app.config['CDN_RACKSPACE_CONTAINER'] = 'container'
app.config['CDN_RACKSPACE_REGION'] = 'DFW'
app.config['CDN_HOSTED_IMAGES_LOCAL_DIR'] = '/tmp'
app.config['CDN_ALLOWED_EXTENSIONS'] = ['.jpg', '.gif', '.png', '.jpeg', '.jpe', '.svg', '.bmp']

CDN(app)


@app.route('/')
def index():
	# TODO this won't work wtf
    template_str = """{{ url_for('static', filename="test0.jpg") }}"""
    return render_template_string(template_str)

@app.route('/test')
def test():
	return url_for('static', filename='testrrr.jpg')

@app.route('/upload')
def upload():
	result = upload_rackspace_image('/tmp/testcat.jpg')
	return str(result)


if __name__ == '__main__':
    app.run(debug=True)
