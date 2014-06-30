from cement.core import backend, foundation, controller, handler
import sys, ConfigParser, urllib, requests, hashlib, hmac, time, json
from betarigs import Betarigs

class RentalController(controller.CementBaseController):
	class Meta:
		label = 'base'
		description = 'Betarigs Manager'

	@controller.expose(help="Use this to generate or update your config file")
	def setup(self):
		print "\nInput the API keys and pool information below to easily populate your configuration file."
		print "Leave any information blank that you don\'t have or don\'t want to change and the values will not be set.\n"

		config = ConfigParser.RawConfigParser()
		config.read('./manager.conf')

		config.set('Keys', 'betarigs_api_key', 
			raw_input('Betarigs API key: ') or app.config.get('Keys', 'betarigs_api_key'))
		config.set('Keys', 'coinbase_api_key', 
			raw_input('Coinbase API key: ') or app.config.get('Keys', 'coinbase_api_key'))
		config.set('Keys', 'coinbase_api_secret', 
			raw_input('Coinbase API secret: ') or app.config.get('Keys', 'coinbase_api_secret'))

		config.set('Pool', 'url', 
			raw_input('Pool URL: ') or app.config.get('Pool', 'url'))
		config.set('Pool', 'worker_name', 
			raw_input('Pool Worker Name: ') or app.config.get('Pool', 'worker_name'))
		config.set('Pool', 'worker_password', 
			raw_input('Pool Worker Password: ') or app.config.get('Pool', 'worker_password'))

		with open('./manager.conf', 'wb+') as configfile:
			config.write(configfile)

	@controller.expose(help="Mass-rent rigs")
	def rent(self):
		self.betarigs = Betarigs(
			app.config.get('Keys', 'betarigs_api_key'),
			app.config.get('Pool', 'url'),
			app.config.get('Pool', 'worker_name'),
			app.config.get('Pool', 'worker_password')
		)

		print "\nEnter rental information below and suitable rigs will be displayed."
		print "You may then confirm or cancel the rentals."
		print "Upon confirming rentals they will be created at Betarigs and your Coinbase account will send the designated amount to Betarigs.\n"

		print "Fetching algorithms... "
		for algo in self.betarigs.algorithms():
			print "%s: %s" % (algo['id'], algo['name'])
		algorithm = int(raw_input("Choose an algorithm (enter the number): "))

		max_price_mhd = float(raw_input('Maximum price (BTC/Mh/day): '))
		if max_price_mhd <= 0:
			print 'Maximum price must be above 0 BTC'
			sys.exit(0)

		hashing_power_khs = float(raw_input('Total hashing power to rent (Mh/s): ')) * 1000
		if hashing_power_khs <= 400:
			print 'Hashing power is too small'
			sys.exit(0)

		rental_duration = int(raw_input('Rental duration in hours: '))
		if rental_duration is None:
			print 'Invalid rental duration'
			sys.exit(0)

		print "Finding rigs..."
		page = 1
		next_page = True
		rigs_to_rent = []
		rigs_table = [['Rig Name', 'Speed (Mh/s)', 'Price (BTC/Mh/d)']]
		btc_total = 0
		total_hashing_power = 0
		while True:
			rigs = self.betarigs.rigs(page, algorithm)['items']
			if not rigs:
				break
			
			for rig in rigs:
				if rig['declared_speed']['unit'] == 'Kh/s' and \
					rig['price']['per_speed_unit']['unit'] == 'BTC/Mh/day' and \
					float(rig['price']['per_speed_unit']['value']) <= float(max_price_mhd) and \
					(hashing_power_khs - int(rig['declared_speed']['value'])) >= 0 and \
					[x for x in rig['rental_durations'] if x['value'] == rental_duration]:

					rigs_to_rent.append({
						'id': rig['id'], 
						'name': rig['name'],
						'desc': rig['description'],
						'speed_mhs': int(rig['declared_speed']['value']) / 1000.0,
						'price_mhd': float(rig['price']['per_speed_unit']['value']),
						'price_day': float(rig['price']['total']['value'])
					})
					rigs_table.append([rigs_to_rent[-1]['name'][:50], str(rigs_to_rent[-1]['speed_mhs']), str(rigs_to_rent[-1]['price_mhd'])])

					btc_total += (rental_duration / 24.0) * rigs_to_rent[-1]['price_day']
					total_hashing_power += rigs_to_rent[-1]['speed_mhs']

					hashing_power_khs -= int(rig['declared_speed']['value']);
					if hashing_power_khs <= 400:
						next_page = False
						break
			
			if not next_page:
				break

			page += 1

		num_rigs = len(rigs_to_rent)
		if num_rigs <= 0:
			print 'No rigs found, exiting...'
			sys.exit(0)

		print '%s rigs found:\n' % num_rigs
		print_table(rigs_table)
		print '\nTotal cost in BTC (including 3%% Betarigs fee): %s' % (btc_total * 1.03)
		print 'Total hashing power (Mh/s): %s' % total_hashing_power

		confirm = raw_input('Should continue with rental? (y/n): ')
		if not(confirm == 'y' or confirm == 'yes'):
			sys.exit(0)

		for rig in rigs_to_rent:
			resp = self.betarigs.rent(rig['id'], rental_duration)
			if not resp['success']:
				print resp['error']
				sys.exit(0)
			else:
				if resp['json']['payment']['bitcoin']['price']['unit'] != 'BTC':
					print 'Payment unit not in Bitcoin, exiting...'
					sys.exit(0)
				else:
					send_request = send_money(
						app.config.get('Keys', 'coinbase_api_key'),
						app.config.get('Keys', 'coinbase_api_secret'),
						resp['json']['payment']['bitcoin']['payment_address'], 
						resp['json']['payment']['bitcoin']['price']['value']
					)

					if send_request and isinstance(send_request, bool):
						print 'Rig successfully rented and paid for!'
					else:
						print 'Coinbase payment not successful.'
						print send_request

	@controller.expose(help='Update all existing rentals to a new pool configuration')
	def update_pool(self):
		print "\nThis will update your existing rentals to the pool information stored in your configuration file."
		confirm = raw_input('Continue? (y/n): ')
		if not(confirm == 'y' or confirm == 'yes'):
			sys.exit(0)
		
		betarigs = Betarigs(
			app.config.get('Keys', 'betarigs_api_key'),
			app.config.get('Pool', 'url'),
			app.config.get('Pool', 'worker_name'),
			app.config.get('Pool', 'worker_password')
		)
		
		betarigs.update_rentals()


class BetarigsManager(foundation.CementApp):
	class Meta:
		label = 'betarigs-manager'
		base_controller = RentalController
		config_files = ['./manager.conf']

def send_money(key, secret, addr, amount, additional_fee=False):
	url = 'https://coinbase.com/api/v1/transactions/send_money'
	nonce = int(time.time() * 1e6)
	body = \
		json.dumps({
			'transaction': {
				'to': addr,
				'amount': amount,
				'notes': 'Betarigs',
				'user_fee': '.0002' if additional_fee else ''
			}
		})
	message = str(nonce) + url + body
	signature = hmac.new(secret, message, hashlib.sha256).hexdigest()
	headers = {
		'ACCESS_KEY': key,
		'ACCESS_SIGNATURE': signature,
		'ACCESS_NONCE': nonce,
		'content-type': 'application/json'
	}
	resp = requests.post(url, data=body, headers=headers)
	if resp.status_code is not 200:
		return 'Coinbase returned status code %s' % resp.status_code

	resp_json = json.loads(resp.text)
	if not resp_json['success']:
		fee_error = 'This transaction requires a 0.0002 BTC fee to be accepted by the bitcoin network. Do you want to add it?  (This fee does not go to Coinbase.)'
		if not additional_fee and resp_json['errors'][0] == fee_error:
			print 'Coinbase says: %s' % fee_error
			confirm = raw_input('Would you like to add the 0.0002 BTC fee to the transaction (if not, the transaction will be cancelled) (y/n): ')
			if not(confirm == 'y' or confirm == 'yes'):
				return 'Transaction not accepted because the fee wasn\'t added'
			return send_money(key, secret, addr, amount, True)
		else:
			return resp_json['errors'][0]
	else:
		return True


def get_max_width(table, index):
    return max([len(row[index]) for row in table])

def print_table(table):
    col_paddings = []
    
    for i in range(len(table[0])):
        col_paddings.append(get_max_width(table, i))

    for row in table:
        print row[0].ljust(col_paddings[0] + 1),
        for i in range(1, len(row)):
            col = row[i].rjust(col_paddings[i] + 2)
            print col,
        print ""

app = BetarigsManager()

try:
	app.setup()
	app.run()
finally:
	app.close()