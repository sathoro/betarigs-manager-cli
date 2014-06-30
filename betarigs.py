import requests, urllib, json

class Betarigs(object):
	root = 'https://www.betarigs.com'

	def __init__(self, key, pool_url, worker_name, worker_password):
		self.key = key
		self.pool_url = pool_url
		self.worker_name = worker_name
		self.worker_password = worker_password

	def url(self, uri, filters={}):
		return "%s%s%s" % (
			self.root, 
			uri if uri.startswith("/") else "/%s" % uri, 
			"?%s" % urllib.urlencode(filters) if filters else ""
		)

	def rent(self, rig_id, duration):
		body = \
			json.dumps({
				'rig': {'id': rig_id}, 
				'duration': {'value': duration, 'unit': 'hour'},
				'pool': {'url': self.pool_url, 'worker_name': self.worker_name, 'worker_password': self.worker_password}
			})

		headers = {'X-Api-Key': self.key, 'content-type': 'application/json'}

		resp = requests.post(self.url('/api/v1/rental.json'), headers=headers, data=body)
		decoded = json.loads(resp.text)
		if resp.status_code == 403:
			return {'success': False, 'error': 'Your Betarigs API key is incorrect!'}
		elif resp.status_code == 404:
			return {'success': False, 'error': 'That rig doesn\'t exist!'}
		elif resp.status_code == 400:
			return {'success': False, 'error': 'Betarigs error: %s' % decoded['error']['message']}
		elif resp.status_code != 200:
			return {'success': False, 'error': 'Unknown Betarigs API error! (%s)' % resp.status_code}

		return {'success': True, 'json': decoded}

	def update_rentals(self):
		resp = requests.get(self.url('/api/v1/rentals.json', {'status': 'executing'}), headers={'X-Api-Key': self.key})

		if resp.status_code == 403:
			print 'Your Betarigs API key is incorrect!'
		elif resp.status_code != 200:
			print 'Unknown Betarigs API error! (%s)' % resp.status_code
		else:
			for rig in json.loads(resp.text):
				resp = requests.put(
					self.url('/api/v1/rental/%s.json' % rig['id']),
					{
						'rig': {'id': rig['id']}, 
						'pool': {
							'url': self.pool_url,
							'worker_name': self.worker_name,
							'worker_password': self.worker_password
						}
					},
					headers={'X-Api-Key': self.key}
				)

				if resp.status_code == 403:
					print 'Your Betarigs API key is incorrect!'
				elif resp.status_code == 404:
					print 'That rental doesn\'t exist!'
				elif resp.status_code != 200:
					print 'Unknown Betarigs API error! (%s)' % resp.status_code
				else:
					print 'Rental updated'

	def algorithms(self):
		return requests.get(self.url('/api/v1/algorithms.json')).json()

	def rigs(self, page=1, algorithm=1):
		return requests.get(self.url('/api/v1/rigs.json', {'page': page, 'algorithm': algorithm})).json()